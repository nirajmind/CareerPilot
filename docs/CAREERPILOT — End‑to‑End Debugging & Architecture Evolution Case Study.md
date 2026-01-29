# 🧭 **CAREERPILOT — End‑to‑End Debugging & Architecture Evolution Case Study**  
### *A complete breakdown of issues, failed fixes, root causes, and final solutions*

---

# 1. Context and Constraints

CareerPilot’s backend runs on:

- A **k3s cluster** hosted on a **Singapore VM** (Atlantic.net)  
- Public IP: **43.228.212.212**  
- All outbound traffic originates from this IP  
- Gemini API **rejects traffic from this region/IP**  
- No CI/CD pipeline  
- No container registry  
- Images built locally and manually loaded into k3s  
- Cloud Run used as a proxy to bypass geolocation restrictions  

These constraints shaped every technical decision and every failure we encountered.

---

# 2. Category A — Connectivity & Geolocation (Singapore VM Blocked by Gemini)

## **A.1 Issue — Gemini API rejecting calls from Singapore VM**

### **Symptom**
All direct Gemini API calls from the k3s cluster failed, even though:

- API keys were correct  
- Payloads were correct  
- Code worked from other networks  

### **Deep RCA (based on your IP analysis)**

When we analyzed the VM’s IP **43.228.212.212**, we discovered:

| Attribute | Value |
|----------|--------|
| Country | Singapore |
| Provider | Atlantic.net |
| ASN | AS25820 |
| Category | **Commercial hosting / VPS provider** |
| Risk flags | **Datacenter IP**, not residential |
| Google/Gemini behavior | **Blocks or rate-limits traffic from certain datacenter IP ranges** |

Gemini’s backend applies **geolocation + risk scoring**:

- Traffic from **consumer ISPs** → allowed  
- Traffic from **cloud/VPS/datacenter IPs** → often blocked  
- Traffic from **restricted regions** → blocked  
- Traffic from **unverified ASNs** → blocked  

Your VM hit **all three risk categories**:

1. **Singapore region** (Gemini has partial restrictions)  
2. **Datacenter IP** (not a residential ISP)  
3. **Atlantic.net ASN** (commonly used for scraping, bots, automation)  

This is why Gemini returned:

- Empty bodies  
- 403/404 variants  
- Silent failures  
- Timeouts  

### **Failed fixes**
- Retrying  
- Changing payload  
- Changing API key  
- Using different Gemini endpoints  
- Using different models  

None of these addressed the root cause: **Gemini was rejecting the source IP**.

### **Final solution**
Introduce a **Cloud Run proxy** in a supported region (e.g., `us-central1`):

```
Singapore VM → Cloud Run Proxy → Gemini API → Cloud Run Proxy → Singapore VM
```

### **Why it worked**
- Gemini sees the request as coming from **Google’s infrastructure**, not your VM  
- All geolocation and ASN restrictions disappear  
- Your k3s cluster can remain in Singapore  
- No VPN or IP rotation required  

This architectural shift was **forced** by Gemini’s geofencing and risk scoring.

---

# 3. Category B — Image Management & k3s Deployment Risks

### B.1 Issue — Local images without tags, no registry, no pipeline

**Symptom:**

- k3s sometimes ran **stale code** even after rebuilds.
- Image resolution issues when k3s tried to pull from `docker.io` by default.
- Manual tagging and loading required after every change.

**Root cause:**

- Images built **locally** with inconsistent or missing tags.
- No **image registry** (public or private) in the flow.
- No **automated pipeline** to ensure:
  - consistent tags  
  - reproducible builds  
  - predictable rollout

**Failed / partial “fixes”:**

- Rebuilding images without fixing tags  
- Restarting deployments without confirming which image was actually used  
- Assuming k3s would always use the locally loaded image

**Final solution:**

- Explicitly **tag images** (e.g., `careerpilot-api:local`, `careerpilot-api:vX`)  
- Load them into `containerd` with those tags  
- Update k8s manifests to reference the **exact tag**  
- Confirm running image via:
  - `kubectl describe pod`  
  - inspecting container filesystem and timestamps

**Why this works:**

- k3s no longer guesses or falls back to `docker.io`.  
- You control exactly which image is used.  
- The deployment becomes deterministic even without a registry—still risky, but now explicit.

**Meta-lesson:**

- Running **production-like workloads** on:
  - local builds  
  - no registry  
  - no pipeline  
  is inherently fragile.  
- But with strict tagging and verification, it can be made predictable enough for your current stage.

---

# 4. Category C — Cloud Run Proxy Behavior & Health

### C.1 Issue — Cloud Run “container failed to start and listen on port 8080”

**Symptom:**

- Cloud Run deployment failed with:
  > The user-provided container failed to start and listen on the port defined by PORT=8080

**Root cause:**

- Cloud Run health check hit `/`.
- Proxy forwarded `/` to Gemini.
- Gemini returned an **empty body**.
- Proxy tried `resp.json()` → `JSONDecodeError` → crash.
- Cloud Run marked the revision as unhealthy.

**Failed fixes:**

- Increasing timeouts  
- Redeploying without changing behavior

**Final solution:**

1. Add a **health endpoint**:

   ```python
   @app.get("/")
   async def health():
       return {"status": "ok"}
   ```

2. Stop parsing JSON in the proxy:

   ```python
   return Response(
       content=resp.content,
       status_code=resp.status_code,
       media_type=resp.headers.get("Content-Type", "application/json")
   )
   ```

**Why it works:**

- Health checks no longer hit Gemini.  
- Proxy no longer crashes on empty bodies.  
- Cloud Run sees a stable, healthy container.

---

# 5. Category D — Gemini API Versions & Model Catalog

### D.1 Issue — Embeddings 404 (text-embedding-004)

**Symptom:**

- Gemini returned:
  > models/text-embedding-004 is not found for API version v1beta

**Root cause:**

- `text-embedding-004` is a **v1** model.
- Proxy was using `v1beta`.

**Failed fixes:**

- Changing model name  
- Tweaking payload

**Final solution:**

- Use `v1` for embeddings:
  - `v1/models/text-embedding-004:embedContent`

**Why it works:**

- Calls now hit the correct API version where the model actually exists.

---

### D.2 Issue — Chat 404 (gemini-3-pro-preview)

**Symptom:**

- Gemini returned:
  > models/gemini-3-pro-preview is not found for API version v1

**Root cause:**

- `gemini-3-pro-preview` is **v1beta-only**.
- Proxy was using `v1`.

**Failed fixes:**

- Adding `/models` prefix only  
- Assuming it was a path bug

**Final solution (intermediate):**

- Switch proxy base URL back to `v1beta` for chat.

**Final solution (architectural, see later):**

- Let the **client** specify full path:
  - `v1/models/...` for embeddings  
  - `v1beta/models/...` for chat  
- Proxy just forwards.

**Why it works:**

- Each model is called via the API version it actually belongs to.

---

# 6. Category E — Model Path Construction & JSON Parsing

### E.1 Issue — Double `models/models` prefix

**Symptom:**

- Proxy forwarded paths like:
  - `/models/models/text-embedding-004:embedContent`

**Root cause:**

- `embedding_model = "models/text-embedding-004"`  
- Code did: `f"models/{embedding_model}:embedContent"`

**Failed fixes:**

- Changing proxy base URL  
- Tweaking Gemini version

**Final solution:**

- Standardize model names and paths:
  - `embedding_model = "text-embedding-004"`  
  - `chat_model = "gemini-3-pro-preview"`  
  - Build full path with version in client:
    - `v1/models/text-embedding-004:embedContent`  
    - `v1beta/models/gemini-3-pro-preview:generateContent`

**Why it works:**

- Paths are now valid and consistent.  
- No accidental duplication of `models/`.

---

### E.2 Issue — JSONDecodeError in embeddings and generate_knowledge

**Symptom:**

- Logs showed:
  - `[Gemini] Success ...` (HTTP 200)  
  - followed by `JSONDecodeError: Expecting value: line 1 column 1 (char 0)`

**Root cause:**

- Gemini returned **empty body** (e.g., 404 or invalid path).  
- Client did `result.json()` on an empty body.

**Failed fixes:**

- Retrying  
- Assuming transient network issues

**Final solution:**

- Fix **paths and versions** so Gemini returns real JSON.  
- Keep proxy as a raw forwarder (no `.json()` there).  
- Client parses JSON only when status and path are correct.

**Why it works:**

- Once Gemini returns valid JSON, `json()` no longer fails.  
- Errors are now visible as structured error objects, not crashes.

---

# 7. Category F — Final Architectural Fix: Static Proxy, Smart Client

### F.1 Issue — Proxy as a moving dependency

**Symptom:**

- Every change in:
  - model  
  - version  
  - endpoint  
  required a **Cloud Run redeploy**.

**Root cause:**

- Proxy hard-coded:
  - `GEMINI_BASE = "https://generativelanguage.googleapis.com/v1"` or `v1beta`.

**Final solution:**

- Make proxy **version-agnostic**:

  ```python
  GEMINI_BASE = "https://generativelanguage.googleapis.com"

  @app.post("/{path:path}")
  async def proxy(path: str, request: Request):
      ...
      url = f"{GEMINI_BASE}/{path}"
      ...
  ```

- Move all version/model routing into the **client**:

  ```python
  # Embedding
  path = "v1/models/text-embedding-004:embedContent"

  # Chat
  path = "v1beta/models/gemini-3-pro-preview:generateContent"
  ```

**Why it works:**

- Proxy is now **static**—no redeploys needed.  
- Client can:
  - switch models  
  - switch versions  
  - adopt new endpoints  
  instantly, without touching Cloud Run.

---

# 8. How All Issues Tie Together (Final Synthesis)

Your system faced **three independent but interacting failure domains**:

## **1. Geolocation & IP reputation**
- Gemini blocked your Singapore VM  
- Forced the introduction of a Cloud Run proxy  
- Required rethinking the entire request flow  

## **2. Deployment fragility**
- No registry  
- No pipeline  
- Local images without tags  
- k3s pulling wrong images  
- Required strict tagging and verification  

## **3. Gemini API complexity**
- v1 vs v1beta  
- Different models in different versions  
- Proxy initially hard‑coded to one version  
- Required moving routing logic into the client  

### **The final architecture solves all three:**

```
k3s (Singapore VM)
    ↓
Cloud Run Proxy (static, version-agnostic)
    ↓
Gemini API (v1 or v1beta depending on model)
    ↓
Proxy
    ↓
k3s
```

- Proxy is **static** and never needs redeployment  
- Client controls **model**, **version**, **path**  
- Singapore geolocation is bypassed  
- Deployment is deterministic  
- Gemini calls are stable and predictable  

---

# 9. Why This Case Study Matters

This is not just a debugging story — it’s a **real-world architecture evolution** triggered by:

- Cloud provider constraints  
- AI API geofencing  
- Container orchestration pitfalls  
- Versioning mismatches  
- Proxy design mistakes  
- And the realities of running production workloads without a CI/CD pipeline  

This case study demonstrates:

- Deep troubleshooting  
- System-level thinking  
- Ability to diagnose multi-layered failures  
- Ability to redesign architecture under pressure  
- Ability to stabilize a complex AI pipeline end-to-end  

---

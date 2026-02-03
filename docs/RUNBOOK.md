# 📘 CareerPilot Project Runbook & Best Practices Guide

**Version:** 1.0  
**Status:** Living Document  

---

## 🎯 1. Core Philosophy & Architecture Patterns

This project solves two specific high-level problems: **Data Sovereignty/Geo-blocking** and **Complex Agentic Orchestration**.

### 1.1 The "Jumphost" Proxy Pattern
**Context:** Our compute is in Singapore (cheap, data sovereignty), but Gemini API blocks Singapore IPs.
**Pattern:**  
`Service (SG) -> Stateless Proxy (US) -> External API`
**Best Practice:**  
*   **Keep the Proxy DUMB.** Do not put business logic in the proxy. It should only forward bytes.
*   **Logic in Client.** Handle versioning (`v1` vs `v1beta`) and model selection in the Python client, not the proxy routing rules.
*   **Authentication.** Secure the proxy with a shared secret (`x-careerpilot` header) to prevent public abuse.

### 1.2 The Agentic State Machine
**Context:** Linear chains (`A -> B -> C`) are too brittle for extraction tasks that might fail or need extra context.
**Pattern:** **LangGraph State Machine**  
*   **Cyclic Graphs:** The agent can loop back (`Check Cache -> Miss -> Search -> Generate -> Ingest -> Finalize`).
*   **State TypedDict:** Explicitly define the schema of the data passing between nodes (`AgentState`).
**Best Practice:**  
*   **Fail Fast.** If Resume/JD is missing, raise error immediately in the first node.
*   **Structured Output.** Force the LLM to return JSON, then validate it with Pydantic/`json_utils` before trusting it.

### 1.3 The Observability Layer
**Context:** Debugging "Black Box" LLM chains is difficult without seeing the full execution path and internal state changes.  
**Pattern:** **OpenTelemetry & Structured Logging**  
*   **Distributed Tracing:** Every request generates a `trace_id` that is propagated through the system (and ideally to the Proxy).
*   **Correlation:** Logs are injected with `trace_id` and `span_id` to link specific log messages to the broader request lifecycle.  
**Best Practice:**  
*   **Trace Everything:** If it takes more than 100ms or involves network I/O, wrap it in a span.
*   **JSON Logs:** Humans write logs, machines read them. Always output structured JSON for ingestion by tools like Signoz, Loki, or Datadog.

---

## 🛠️ 2. Development Standards

### 2.1 Environment Management
*   **`.env` is Sacred.** Never commit it. Use `.env.example` to track required keys.
*   **Separation:**
    *   `GEMINI_API_KEY`: Only needed by the Client (or Proxy if it did auth, but here Client sends it).
    *   `PROXY_SECRET`: Needed by BOTH Client and Proxy.

### 2.2 Docker Strategy
*   **Multi-Stage Builds:** Use `python:slim` for final images to reduce size.
*   **CPU vs GPU:** Maintain separate Dockerfiles (`Dockerfile.api.cpu` vs `Dockerfile.api.gpu`) if running mixed workloads.

### 2.3 Logging & Tracing Standards
*   **No Print Statements:** Use `lib_logger` or `setup_logger`. `print` is for scripts, `logger` is for apps.
*   **Structured Format:** All logs in production must be JSON.
    ```json
    {"timestamp": "2023-10-27T10:00:00Z", "level": "INFO", "message": "Processing video", "trace_id": "a1b2...", "span_id": "c3d4..."}
    ```
*   **Context Propagation:** Pass the context when spawning threads or async tasks to ensure traces aren't broken.

---

## 🚀 3. Deployment Protocol ("The Golden Path")

*Critical Lesson: We faced issues with stale code running because of vague `latest` tags and k3s caching.*

### Step 1: Explicit Versioning
**NEVER** deploy `latest` to production. Always use a semantic tag or timestamp.

```bash
export VERSION=v1.2.0
```

### Step 2: Build & Tag
```bash
docker build -f Dockerfile.api -t careerpilot-api:$VERSION .
```

### Step 3: Distribution (The "Registry-less" Approach)
*Since we don't have a private registry yet, we manually load images into k3s.*

```bash
# Save image to tar
docker save careerpilot-api:$VERSION -o api.tar

# Copy to VPS (if remote)
scp api.tar user@43.228.x.x:~/

# Import into k3s (on the server)
sudo k3s ctr images import api.tar
```

### Step 4: Atomic Rollout
Update the kubernetes manifest (or `docker-compose.yaml` if simple):

```yaml
containers:
  - name: api
    image: careerpilot-api:v1.2.0  # <--- MUST match the tag above
    imagePullPolicy: Never         # <--- Critical for local k3s images
```

---

## 🔍 4. Operational Playbook

### 4.1 Debugging "Silent Failures"
If the agent returns empty logic:
1.  **Check the Traces (Otel/Signoz/Jaeger):** Find the trace for the Request ID. Look for spans ending in Error or taking unusually long.
2.  **Check the Graph State:** The logs usually print `=== CURRENT AGENT STATE ===` (now in JSON). Look for `None` values in `vector_search_results`.
3.  **Check the Proxy:**
    *   If Proxy logs show `403/500`, it's a Gemini/Network issue.
    *   If Proxy logs show nothing, the request never left the SG server (DNS/Firewall).

### 4.2 Cache Management
*   **Flush Cache:** If you change the prompt, you MUST flush Redis.
    ```bash
    redis-cli FLUSHALL
    ```
    *Reason:* The cache key uses the content hash, but not the prompt hash. (Potential improvement: Include prompt hash in cache key).

---

## 🏆 5. Best Practices & Gap Analysis (For Future Projects)

### ✅ What We Did Right (Keep doing this)
1.  **Observability:** The `TimeTracker` class provides excellent granular metrics, and now OpenTelemetry provides end-to-end visibility.
2.  **Resilience:** The `retry_async` decorator and Client Proxy handle network blips automatically.
3.  **Cost:** Using Redis to short-circuit repetitive expensive Vision calls.
4.  **Developer Experience:** Centralized `utils` for tracing/logging means feature developers don't need to reinvent the wheel.

### ⚠️ Missing / Improvements (Add these next time)
*   **CI/CD Pipeline:** Currently builds are manual. **Fix:** GitHub Actions to build and push to Docker Hub/GHCR.
*   **Centralized Registry:** Removing the "scp tar file" step. **Fix:** Use a private registry.
*   **Unit Testing:** We relied heavily on integration testing. **Fix:** Add `pytest` for the `AgentState` logic (e.g., test that it routes to "video" correctly given a path).
*   **Prompt Management:** Prompts are in Redis or code. **Fix:** Move to a prompt registry or versioned YAML files for easier non-engineer editing.
*   **Health Checks:** We added `/` health check late. **Fix:** Always start with a `/health` endpoint that checks DB connectivity.

---

## ⛔ 6. Architectural Faults & Missing Industry Standards (Gap Analysis)

*The current system is functional but lacks several "Day 2" operations standards.*

### 6.1 Resilience & Traffic Control
### 6.1 Resilience & Traffic Control
*   **✅ RESOLVED: Rate Limiter.**
    *   *Implementation:* Added `RateLimiterService` using Redis Token Bucket (per user/IP).
    *   *Benefit:* Protects `POST /analyze` from abuse.
*   **✅ RESOLVED: Circuit Breaker.**
    *   *Implementation:* Added `CircuitBreakerService` for external API calls (Gemini/Stripe).
    *   *Benefit:* Fails fast when external services are down, preventing cascading failures.

### 6.2 Security & Compliance
*   **✅ RESOLVED: Security Hardening.**
    *   *Implementation:*
        *   **Account Lockout:** Locks account after 5 failed attempts (Redis-backed).
        *   **Enhanced JWT:** Added `iss`, `aud`, `iat`, `jti`, and `tier` claims. Enforced strict validation.
        *   **Secure Health Checks:** `/health/secure` (Admin-only) performs deep DB/Redis probes.
*   **FAULT: Permissive CORS.**
    *   *Current:* `allow_origins=["*"]` allows any website to call our API.
    *   *Standard:* Restrict to specific frontend domains (e.g., `https://careerpilot.chickenkiller.com`).
*   **✅ RESOLVED: Distributed Tracing.**
    *   *Action:* Implemented OpenTelemetry with OTLP exporters and Structured Logging.
    *   *Benefit:* We can now visualize the full request lifecycle.

### 6.3 Configuration Management
*   **✅ RESOLVED: Unified & Dynamic Config.**
    *   *Implementation:*
        *   **Pydantic Models:** All config in `app/api/app_config.py` (Single source of truth).
        *   **Hybrid Loading:** Startup loads Env vars, then overlays dynamic settings from MongoDB (`system_config`).
    *   *Benefit:* Type safety + Ability to update quotas/models at runtime without redeploying.

---

## ⚜️ 7. Design Principles for Developer Friendly Code

These principles were adopted to ensure the codebase remains maintainable and pleasant to work with as it scales.

### 7.1 "If you can't see it, you can't fix it" (Observability First)
*   **Principle:** Never deploy "black box" logic.
*   **Implementation:** We prioritized OpenTelemetry and Structured Logging *before* adding complex features.
*   **Benefit:** Reduces "Mean Time To Resolution" (MTTR) when bugs occur in production.

### 7.2 Explicit over Implicit
*   **Principle:** Code should clearly state what it needs and what it does.
*   **Implementation:** We moved from implicit `print()` debugging to explicit, configured Loggers and Tracers. API clients require explicit `client` objects rather than relying on global state.
*   **Benefit:** New developers (or future you) can trace exactly where configuration comes from.

### 7.3 Separation of Cross-Cutting Concerns
*   **Principle:** Business logic shouldn't care about infrastructure.
*   **Implementation:** Logging, Tracing, and Configuration are moved to `app/utils/`. The core `server.py` or `text_analysis.py` just imports them.
*   **Benefit:** Keep the "Business Logic" clean and readable.

### 7.4 Structured Data Everywhere
*   **Principle:** Strings are for humans, Objects are for code.
*   **Implementation:**
    *   Logs are JSON objects.
    *   LLM Outputs are Pydantic Models.
    *   Graph State is a TypedDict.
*   **Benefit:** Eliminates "parsing hell" and fragile regex matching.

---

### *End of Runbook*

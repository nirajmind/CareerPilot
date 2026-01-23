# **MongoDB Atlas Setup & Security Hardening Guide**  

## *For CareerPilot RAG + LangGraph + FastAPI Architecture*

---

## **1. Overview**

This document outlines the secure setup of a MongoDB Atlas cluster for use with the CareerPilot platform. It includes:

- Atlas cluster creation  
- Network access configuration  
- User authentication  
- Vector Search index setup  
- Security risks  
- Mitigation strategies  
- Operational best practices  

This guide ensures that CareerPilot can safely use Atlas for vector search while running on a public Atlantic.net VM with no built‑in firewall.

---

## **2. MongoDB Atlas Setup (Security‑First)**

## **2.1 Create the Atlas Cluster**

- Log in to MongoDB Atlas  
- Create a **Free Tier (M0)** cluster  
- Choose a region close to your Atlantic.net VM  
- Select **MongoDB 7.0+** (required for vector search)

---

## **2.2 Configure Network Access (Critical)**

## **Step 1 — Remove 0.0.0.0/0**

- Delete the default “Allow access from anywhere” rule  
- Never expose Atlas to the entire internet

## **Step 2 — Add your Atlantic.net VM IP**

- Find your VM’s public IP  
- Add it to the Atlas IP allowlist  
- Use `/32` to restrict to a single IP

## **Step 3 — Enable “Require TLS”**

Atlas enforces TLS 1.2+ by default.

---

## **2.3 Create a Dedicated Database User**

Create a user with:

- Username: `careerpilot_app`  
- Role: **readWrite** on your database only  
- Strong password (store in environment variables only)

Avoid using the Atlas admin user.

---

## **2.4 Create the Vector Search Index**

In Atlas UI:

1. Go to **Collections**  
2. Select your database  
3. Click **Search Indexes**  
4. Create a new index:

```json
{
  "fields": [
    {
      "type": "vector",
      "path": "embedding",
      "numDimensions": 768,
      "similarity": "cosine"
    }
  ]
}
```

Adjust `numDimensions` based on your embedding model.

---

## **2.5 Update Your Backend Environment Variables**

```config
MONGO_URI=mongodb+srv://careerpilot_app:<password>@cluster-url.mongodb.net/?retryWrites=true&w=majority&tls=true
MONGO_DB=careerpilot
MONGO_COLLECTION=vectors
```

Never commit secrets to Git.

---

## **3. Security Risk Register & Mitigation Plan**

This section documents all known risks and the corresponding mitigation strategies.

---

## **3.1 Network Exposure Risks**

### 3.1.1 Risk

Atlas cluster exposed to the public internet.

### 3.1.2 Attack Vectors

- Port scanning  
- Automated brute force  
- Botnet attacks  

### 3.1.3 Mitigation

- **IP allowlist only your VM**  
- **Disable 0.0.0.0/0**  
- Use **Private Endpoint** (long‑term)  
- Rotate VM IP if compromised  

---

## **3.2 Credential Theft**

### 3.2.1 Risk

MongoDB credentials leaked or stolen.

### 3.2.2 Attack Vectors

- Leaked `.env`  
- Logs printing connection strings  
- Docker images containing secrets  
- SSH compromise  

### 3.2.3 Mitigation

- Store secrets only in environment variables  
- Never commit `.env`  
- Use SCRAM users with least privilege  
- Rotate passwords every 30–60 days  
- Enable Atlas IP‑based rate limiting  

---

## **3.3 Man‑in‑the‑Middle Attacks**

### 3.3.1 Risk

Traffic intercepted between VM and Atlas.

### 3.3.2 Attack Vectors

- Packet sniffing  
- DNS spoofing  
- TLS downgrade  

### 3.3.3 Mitigation

- Atlas enforces TLS 1.2+  
- Use `tls=true` in connection string  
- Enable DNSSEC on your domain  
- Use Private Endpoint (best)  

---

## **3.4 Unauthorized API Access**

### 3.4.1 Risk

Attackers hit your FastAPI endpoints directly.

### 3.4.2 Attack Vectors

- Triggering expensive Gemini calls  
- Overloading embedding pipeline  
- Sending malicious payloads  

### 3.4.3 Mitigation

- JWT authentication  
- Rate limiting (Redis)  
- Request size limits  
- Disable unauthenticated endpoints  

---

## **3.5 NoSQL Injection**

### 3.5.1 Risk

User input injected into Mongo queries.

### 3.5.2 Attack Vectors

- `{ "$ne": null }`  
- `{ "$where": "sleep(5000)" }`  
- `{ "$regex": ".*" }`  

### 3.5.3 Mitigation

- Validate all input with Pydantic  
- Never pass raw user input into queries  
- Use parameterized queries  
- Disable server‑side JS (Atlas default)  

---

## **3.6 Vector Store Poisoning**

### 3.6.1 Risk

Malicious users inject adversarial text into embeddings.

### 3.6.2 Attack Vectors

- Malicious resumes/JDs  
- Prompt injection  
- Adversarial embedding attacks  

### 3.6.3 Mitigation

- Sanitize text before embedding  
- Limit ingestion to authenticated users  
- Add max length checks  
- Add anomaly detection (optional)  

---

## **3.7 Denial of Service (DoS)**

### 3.7.1 Risk

Attackers overload your embedding or analysis pipeline.

### 3.7.2 Attack Vectors

- Repeated requests  
- Large file uploads  
- Triggering ingestion repeatedly  

### 3.7.3 Mitigation

- Rate limit per user/IP  
- Cache embeddings  
- Cache final analysis  
- Reject large files early  

---

## **3.8 Redis Exposure**

### 3.8.1 Risk

Redis exposed publicly.

### 3.8.2 Attack Vectors

- Cache flush  
- Fake analysis injection  
- Key theft  

### 3.8.3 Mitigation

- Bind Redis to localhost  
- Use a Redis password  
- Do not expose port 6379  
- Use Docker network isolation  

---

## **3.9 Container Security**

### 3.9.1 Risk

Container escape or privilege escalation.

### 3.9.2 Attack Vectors

- Running containers as root  
- Docker socket exposure  

### 3.9.3 Mitigation

- Run containers as non‑root  
- Use read‑only filesystem where possible  
- Disable Docker socket mounts  

---

## **4. Operational Best Practices**

- Rotate MongoDB credentials monthly  
- Rotate JWT signing keys quarterly  
- Enable Atlas alerts (CPU, connections, auth failures)  
- Backup your database weekly  
- Monitor logs for suspicious activity  
- Use Infrastructure‑as‑Code for reproducibility  

---

## **5. Summary**

This document provides a complete security posture for running MongoDB Atlas with a public Atlantic.net VM. Following these steps ensures:

- Safe vector search  
- Secure ingestion  
- Protected embeddings  
- Hardened API endpoints  
- Minimal attack surface  

You can now safely proceed with creating your Atlas cluster and integrating it into CareerPilot.

If you want, I can also prepare:

- A Terraform script for Atlas  
- A Docker Compose security‑hardened version  
- A CI/CD checklist for secure deployments  

Just tell me what direction you want to take next.

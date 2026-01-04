🚀 CareerPilot – Autonomous Multimodal Job Application Agent
A cloud‑native, agentic AI system powered by Gemini 3, LangGraph, Redis, MongoDB Vector Search, and Streamlit.
CareerPilot is an Action‑Era AI application designed to analyze resumes, job descriptions, and video scrolls using multimodal reasoning, agentic workflows, and RAG grounding.
It provides a FitGraph skill‑match visualization and generates tailored insights for job seekers.
This project is built entirely in Python, fully containerized, and deployable on Kubernetes with Caddy‑based TLS and a DuckDNS domain.

- Stateful agents (Redis)
- Vector search (MongoDB Atlas)
- Multimodal reasoning (Gemini 3)
- Containerized microservices (Docker)
- Cluster orchestration (Kubernetes)
- Public access (DuckDNS domain)


                           ┌──────────────────────────────┐
                           │         Streamlit UI          │
                           │  - Uploads                    │
                           │  - FitGraph                   │
                           │  - Agent Output               │
                           └──────────────┬───────────────┘
                                          │
                                          ▼
                           ┌──────────────────────────────┐
                           │       FastAPI Backend         │
                           │  - API endpoints              │
                           │  - Calls LangGraph agent      │
                           │  - Containerized (Docker)     │
                           └──────────────┬───────────────┘
                                          │
                                          ▼
                           ┌──────────────────────────────┐
                           │        LangGraph Agent        │
                           │  - Planning                   │
                           │  - RAG retrieval              │
                           │  - FitGraph logic             │
                           │  - Uses Redis for state       │
                           └──────────────┬───────────────┘
                                          │
     ┌────────────────────────────────────┼────────────────────────────────────┐
     ▼                                    ▼                                    ▼
┌───────────────┐               ┌────────────────┐                 ┌──────────────────────┐
│ MongoDB Atlas  │               │ Gemini 3 API   │                 │ Redis                │
│ Vector Search  │               │ Multimodal     │                 │ - Agent State        │
│ - Embeddings   │               │ Reasoning      │                 │ - Caching            │
│ - Retrieval    │               │ Agentic Steps  │                 │ - Task Queue         │
└───────────────┘               └────────────────┘                 └──────────────────────┘

🧱 Features
• 	Multimodal Input Support
Upload PDFs, DOCX, screenshots, or video scrolls of job posts.
• 	Agentic Workflow (LangGraph)
Multi‑step planning, reasoning, and execution with Redis‑backed state.
• 	FitGraph Engine
Visual skill‑match mapping between resume and job description.
• 	RAG Pipeline
Grounded resume rewriting using MongoDB Atlas Vector Search.
• 	Streamlit UI
Simple, fast, Python‑native interface.
• 	Cloud‑Native Deployment
Dockerized microservices orchestrated via Kubernetes.

🧠 Tech Stack
Core Application
• 	Python 3.10+
• 	FastAPI (Backend API)
• 	LangGraph (Agent workflow + state machine)
• 	Streamlit (UI)
AI Layer
• 	Gemini 3 API (Multimodal reasoning)
RAG Layer
• 	MongoDB Atlas Vector Search
• 	Embeddings
• 	Chunk storage
• 	Similarity search
State & Caching
• 	Redis
• 	Agent state persistence
• 	Caching Gemini responses
• 	Workflow checkpoints
Containerization & Orchestration
• 	Docker
• 	Kubernetes (k3s recommended)
• 	Caddy (TLS + reverse proxy)
• 	DuckDNS (public domain)

🏗️ Architecture Overview


📂 Project Structure

CareerPilot/
│
├── app/
│   ├── ui/                 # Streamlit UI
│   │   └── main.py
│   ├── api/                # FastAPI backend
│   │   └── server.py
│   ├── agent/              # LangGraph workflows
│   │   ├── workflow.py
│   │   └── fitgraph.py
│   ├── rag/                # RAG pipeline
│   │   ├── ingest.py
│   │   ├── embeddings.py
│   │   └── mongo_vector.py
│   └── utils/
│
├── infra/
│   ├── docker/
│   │   ├── Dockerfile.api
│   │   ├── Dockerfile.ui
│   │   ├── Dockerfile.agent
|   |   ├── docker-compose.yml   ← **NEW**
│   │   ├── redis.conf           ← **NEW**
│   │   └── mongo-init.js        ← **NEW**
│   ├── k8s/
│   │   ├── api-deployment.yaml
│   │   ├── mongo-statefulset.yaml  ← **NEW**
│   │   ├── ui-deployment.yaml
│   │   ├── agent-deployment.yaml
│   │   ├── redis-statefulset.yaml
│   │   ├── ingress.yaml
│   │   └── namespace.yaml
│
├── docs/
│   ├── architecture.png
│   ├── system-design.md
│
└── README.md


⭐ The Services We Will Run
1. FastAPI Backend
- Handles Gemini API calls
- Handles resume/JD processing
- Handles RAG queries (via internal network)
- Exposes /analyze endpoint
2. Streamlit Frontend
- Talks only to FastAPI
- No direct DB access
- No secrets
3. MongoDB
- Stores:
- User sessions
- RAG documents
- Logs
- Cached results (optional)
4. Redis
- Caching Gemini responses
- Rate limiting
- Background job queue (Celery or RQ later)
5. RAG Service
- Embedding generator
- Vector DB (ChromaDB or Qdrant)
- API for:
- /embed
- /search
- /upsert





🧪 Running Locally (Dev Mode)
1. Install dependencies

2. Start Redis (local)

3. Run Streamlit UI

4. Run FastAPI backend


🐳 Running with Docker Compose

This starts:
• 	Streamlit UI
• 	FastAPI backend
• 	LangGraph agent worker
• 	Redis

☸️ Deploying on Kubernetes (k3s)
1. Apply namespace

2. Deploy services

3. Expose via Caddy + DuckDNS
Your Caddyfile entry:


🧩 🔭 Observability & Monitoring
CareerPilot includes a full observability stack to ensure deep visibility into system performance, resource usage, agent behavior, and cluster health.
This makes the platform production‑ready and easy to debug, scale, and optimize.
Included Observability Components
|  |  | 
|  |  | 
|  |  | 
|  |  | 
|  |  | 
|  |  | 


Live Monitoring Dashboard
Your observability stack is already deployed and accessible at:



👥 Team
• 	Niraj Kumar Adhikary – Lead Architect
• 	Allah Nawaz – UI (Streamlit)
• 	Zain – RAG + ML
• 	Saeedah – Testing & Documentation

📜 License
MIT License
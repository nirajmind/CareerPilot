# CareerPilot - Copilot Instructions

CareerPilot is a cloud-native job application analysis system that combines agentic AI (LangGraph), multimodal processing (Gemini), RAG (MongoDB Vector Search), and containerized microservices.

## Architecture Overview

**Data Flow:** Resume + Job Description → FastAPI API → LangGraph Agent → Gemini (multimodal reasoning) → FitGraph visualization + insights

**Services:**
- **API** (`app/api/server.py`): FastAPI backend on port 8585; coordinates requests, handles auth (JWT + RBAC), proxies Gemini calls
- **Agent** (`app/agent/workflow.py`): LangGraph state machine orchestrating analysis, RAG searches, and result caching via Redis
- **UI** (`app/ui`): Streamlit frontend consuming the API
- **RAG** (`app/rag/mongo_vector.py`): MongoDB Atlas Vector Search for contextual embeddings and document retrieval
- **Gemini Bridge** (`app/gemini/`): HTTP client talking to Cloud Run proxy (required architecture—no direct SDK calls)

**Data Layer:** MongoDB (`collections: users, analysis_results, vectors`) + Redis (agent state, caching)

## Critical Workflows & Commands

**Local Development:**
```bash
# Setup: Activate venv, install deps, set .env with GEMINI_API_KEY, JWT_SECRET_KEY
python -m venv .venv
.venv\Scripts\Activate.ps1  # Windows PowerShell
pip install -r requirements.txt

# Run services (requires MongoDB + Redis running locally or via Docker)
# Terminal 1: FastAPI
uvicorn app.api.server:app --reload --port 8000

# Terminal 2: Streamlit
streamlit run app/ui/main.py

# Or: Docker Compose from infra/docker/ (all services at once)
docker-compose up --build
```

**Testing:** `pytest` with fakeredis fixtures (see `tests/conftest.py`). No integration tests yet—RAG/Gemini are mocked.

**Deployment:** Kubernetes manifests in `infra/k8s/` with StatefulSet for Mongo, Deployments for stateless services. Caddy reverse proxy handles HTTPS.

## Project Patterns & Conventions

1. **Logging**: Always use `setup_logger()` from `app/utils/logger.py`. Supports `LOG_LEVEL` env var (default: INFO).

2. **Pydantic Schemas** (`app/api/schemas.py`): All API I/O uses Pydantic models—`AnalysisRequest`, `FitGraph`, `ResumeAnalysis`, etc. Keeps contracts explicit.

3. **Configuration**: Load from `.env` via `python-dotenv` in `app/api/config.py`. Never hardcode secrets. Critical vars: `GEMINI_API_KEY`, `JWT_SECRET_KEY`, `MONGO_URI`, `REDIS_HOST`.

4. **Gemini Integration** (`app/gemini/client.py`):
   - Uses Cloud Run proxy (not direct SDK) for security isolation
   - Requires `GEMINI_PROXY_URL` and `PROXY_SECRET` env vars
   - Implements `retry_async` for resilience
   - Caches embeddings in Redis with TTL

5. **Authentication**: JWT-based. `app/api/auth.py` provides `get_current_user`, `require_role`. MongoDB `users` collection stores credentials (bcrypt hashed). Two roles: `user`, `admin`.

6. **Agent State** (`app/agent/workflow.py`): Uses `AgentState` TypedDict with `TimeTracker` for performance monitoring. LangGraph graph has nodes: `route_input` → `check_cache` → `search_vectors` → `generate_knowledge` → `perform_final_analysis` → `finalize_output`.

7. **Error Handling**: Global exception handler in `app/api/server.py` logs and returns 500. Don't swallow exceptions without logging.

## Cross-Component Communication

- **UI → API:** HTTP requests to `http://api:8585` (hardcoded in Streamlit, configurable in Docker)
- **API → Agent:** Instantiate `CareerPilotAgent(gemini_client, redis_client)` and call workflow
- **Agent ↔ Redis:** State persistence, embeddings cache
- **Agent ↔ MongoDB:** Vector search via `app.rag.search()`, upserting via `app.rag.upsert()`
- **API ↔ Gemini:** Via `GeminiClient.call()` to Cloud Run proxy (never direct to Google API)

## Git Workflow

GitFlow model: `develop` (main branch), `feature/<name>` branches, `release/<version>` for staging, `hotfix/<issue>` for production. Always branch from `develop`, PR to `develop` (or `release`/`hotfix` if targeting production).

## Key Files to Know

- `pyproject.toml`: Dependencies (FastAPI, Streamlit, LangGraph, Redis, pymongo, google-genai)
- `requirements.txt`: Pinned versions
- `infra/docker/docker-compose.yml`: Local dev environment definition
- `MockTest/`: Sample resumes and JDs for testing
- `docs/`: Architecture diagrams, GPU setup, security hardening guides

## Quick Troubleshooting

- **Gemini calls fail:** Check `GEMINI_PROXY_URL`, `PROXY_SECRET`, `GEMINI_API_KEY` in `.env`. Proxy must be reachable.
- **Redis connection timeout:** Ensure Redis is running; check `REDIS_HOST`, `REDIS_PORT` match Docker service or local instance.
- **Mongo vector search empty:** Confirm documents upserted with embeddings; check `vectors` collection in `careerpilot` DB.
- **Tests fail:** Use `fakeredis.aioredis.FakeRedis()` fixture (see `conftest.py`); real Mongo/Redis not available in test env.

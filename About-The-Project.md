🔥 CareerPilot — Autonomous Multimodal Job Application Agent

# **Inspiration**
The job search process is broken. Candidates spend hours rewriting resumes, tailoring applications, and preparing for interviews — yet still get filtered out by ATS systems or mismatched expectations.  
We wanted to build an **Action‑Era AI agent** that doesn’t just “assist” but actually **does the work**: analyzing resumes, understanding job descriptions, extracting insights from video, and generating a complete, personalized application package automatically.

CareerPilot was born from a simple question:  
**What if applying for a job felt like having a personal career strategist working beside you?**

---

# **What it does**
CareerPilot is an **Autonomous Multimodal Job Application Agent** powered by Gemini 3 that:

- Analyzes resumes, job descriptions, and even video inputs  
- Extracts skills, gaps, strengths, and role alignment  
- Generates a personalized FitGraph and insights  
- Crafts a tailored resume rewrite  
- Produces a preparation plan and mock interview questions  
- Evaluates user answers in real time  
- Stores history and learns from past interactions  

It transforms raw candidate data into a **high‑impact, job‑ready application package** — instantly.

---

# **How we built it**
CareerPilot is engineered as a **modular, production‑grade AI pipeline**:

- **Streamlit UI** for a clean, interactive user experience  
- **FastAPI backend** orchestrating authentication, routing, and streaming  
- **LangGraph agent** coordinating the multimodal workflow  
- **Gemini 3** for embeddings, knowledge generation, and final analysis  
- **MongoDB Atlas Vector Search** for RAG augmentation  
- **Redis** for caching and performance optimization  
- **Caddy + FreeDNS** for secure HTTPS deployment  
- **k3s cluster** running containerized microservices  

We instrumented every step with millisecond‑level timestamps to understand real‑world latency and optimize the pipeline end‑to‑end.

---

# **Challenges we ran into**
- **Gemini LLM latency**: 50–60 seconds per analysis, dominating 95% of total runtime  
- **DNS + HTTPS deployment**: DuckDNS and Dynu failed for ACME challenges; solved via FreeDNS + HTTP‑01  
- **Containerd vs Docker**: Local images weren’t visible to k3s until we rebuilt the pipeline  
- **Multimodal extraction**: Video‑to‑text required careful frame handling and fallback logic  
- **Prompt engineering**: Ensuring structured, deterministic outputs from Gemini  
- **State management**: Coordinating multiple async steps inside LangGraph  

Every challenge forced us to rethink architecture, improve instrumentation, and build a more resilient system.

---

# **Accomplishments that we're proud of**
- Built a **fully autonomous multimodal agent** in under 48 hours  
- Achieved **sub‑2‑second performance** for everything except LLM calls  
- Designed a **production‑grade HTTPS deployment** on a homelab cluster  
- Created a **transparent latency dashboard** exposing real bottlenecks  
- Delivered a **complete job application package** from raw inputs  
- Built a system that feels like a **career co‑pilot**, not just a chatbot  

And the best part — it’s live and testable by anyone.

---

# **What we learned**
- Instrumentation beats intuition — **measure first, optimize second**  
- RAG pipelines are only as fast as their LLM bottleneck  
- Multimodal workflows require careful state design  
- Caching transforms user experience  
- Deployment is half the battle  
- Gemini is powerful, but long‑form reasoning latency needs serious improvement  

This project taught us how to build **real AI products**, not just demos.

---

# **What's next for CareerPilot — Autonomous Multimodal Job Application Agent**
CareerPilot is just getting started. Next steps include:

- **Autonomous job search**: Scan job boards and auto‑match roles  
- **Auto‑apply workflows**: Fill forms, rewrite resumes, and submit applications  
- **Video interview agent**: Real‑time feedback during mock interviews  
- **Portfolio builder**: Auto‑generate GitHub projects based on JD gaps  
- **Skill gap learning paths**: Personalized upskilling recommendations  
- **Faster LLM pipeline**: Model distillation, streaming, and hybrid reasoning  
- **Mobile app** for on‑the‑go career coaching  
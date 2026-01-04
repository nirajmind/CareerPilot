# CareerPilot - Copilot Instructions

This document provides guidance for AI coding agents to effectively contribute to the CareerPilot codebase.

## Project Overview

CareerPilot is a cloud-native, agentic AI system powered by Gemini, LangGraph, Redis, MongoDB Vector Search, and Streamlit. It analyzes resumes, job descriptions, and video scrolls to provide a FitGraph skill-match visualization and generate tailored insights for job seekers.

The application is architected as a set of containerized microservices:
- **UI (`app/ui`)**: A Streamlit application that serves as the user interface.
- **API (`app/api`)**: A FastAPI backend that exposes endpoints for analysis, evaluation, and RAG search.
- **Agent (`app/agent`)**: A LangGraph-based agent for planning, RAG retrieval, and FitGraph logic. (Note: `workflow.py` is currently empty, so the agent's implementation is not yet defined).
- **RAG (`app/rag`)**: A Retrieval-Augmented Generation pipeline using MongoDB Atlas Vector Search for grounding resume rewriting.

## Key Technologies

- **Python 3.10+**: The core programming language.
- **Streamlit**: For the UI.
- **FastAPI**: For the backend API.
- **LangGraph**: For the agent workflow and state machine.
- **Gemini API**: For multimodal reasoning.
- **MongoDB Atlas Vector Search**: For the RAG pipeline.
- **Redis**: For agent state persistence, caching, and task queuing.
- **Docker & Docker Compose**: For containerization and local development.
- **Kubernetes**: For production deployment.

## Getting Started

The project can be run locally using Docker Compose. The `infra/docker/docker-compose.yml` file defines the services and their configurations.

To run the application locally:
1. Ensure you have Docker and Docker Compose installed.
2. Create a `.env` file in the root of the project with your `GEMINI_API_KEY`.
3. Run `docker-compose up --build` from the `infra/docker` directory.

This will start the following services:
- `ui`: Streamlit UI on port `8501`.
- `api`: FastAPI backend on port `8000`.
- `agent`: The agent worker (currently does nothing).
- `mongo`: MongoDB database on port `27017`.
- `redis`: Redis server on port `6379`.

## Development Guidelines

### API (`app/api/server.py`)

- The API is built with FastAPI.
- Endpoints are defined for:
  - `/health`: Health check.
  - `/analyze`: Analyzes a resume and job description.
  - `/evaluate_answer`: Evaluates a user's answer to a question.
  - `/rag/search`: Performs a RAG search.
  - `/stream/analyze`: Streams the analysis of a resume and job description.
  - `/stream/evaluate`: Streams the evaluation of a user's answer.
- The API interacts with the Gemini API via the `GeminiService` in `app/gemini/service.py`.
- It uses Redis for caching.

### UI (`app/ui/main.py`)

- The UI is built with Streamlit.
- It's a multi-page application with pages for:
  - Resume Input
  - Job Description
  - Run Analysis
- The UI communicates with the FastAPI backend.

### Agent (`app/agent/workflow.py`)

- The agent is intended to be built with LangGraph.
- The `workflow.py` file is currently empty, so the agent's implementation is a key area for development.
- The agent will be responsible for orchestrating the analysis process, including RAG retrieval and FitGraph logic.

### RAG (`app/rag`)

- The RAG pipeline uses MongoDB Atlas Vector Search.
- `ingest.py` is likely for ingesting documents into the vector store.
- `mongo_vector.py` contains the search logic.

### Conventions

- **Logging**: The project uses a custom logger configured in `app/utils/logger.py`. Use this logger for all logging.
- **Schemas**: Pydantic schemas for API requests and responses are defined in `app/api/schemas.py`.
- **Configuration**: API configuration is in `app/api/config.py`.

### How to Contribute

1.  **Implement the Agent**: The agent is the core of the application, and its implementation is the highest priority. Start by defining the LangGraph workflow in `app/agent/workflow.py`.
2.  **Enhance the UI**: Improve the Streamlit UI to be more interactive and user-friendly.
3.  **Add More RAG Sources**: Extend the RAG pipeline to include more data sources.
4.  **Write Tests**: Add unit and integration tests for the API, agent, and RAG pipeline.

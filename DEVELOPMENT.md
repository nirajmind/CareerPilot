# Local Development Setup Guide

This document provides a detailed guide for setting up and running the CareerPilot application on your local machine without using Docker Compose. This is ideal for contributors who want to work on a specific service directly.

## Prerequisites

- Python 3.10+
- Access to a running MongoDB instance.
- Access to a running Redis instance.
- A Gemini API Key.
- A secret key for signing JWTs.

## 1. Clone the Repository

```bash
git clone <repository-url>
cd CareerPilot
```

## 2. Create and Configure the Environment File

Create a `.env` file in the root of the project. This file will hold your secret keys and connection settings.

```bash
GEMINI_API_KEY="your-gemini-api-key"
JWT_SECRET_KEY="your-super-secret-key-for-jwt"

# If running Mongo and Redis locally, these defaults are usually fine
MONGO_URI="mongodb://localhost:27017/careerpilot"
REDIS_HOST="localhost"
REDIS_PORT="6379"
```

*You can generate a strong JWT secret key with `openssl rand -hex 32`.*

## 3. Set Up a Virtual Environment

It is highly recommended to use a virtual environment to manage project dependencies and avoid conflicts with other projects.

### Create the Virtual Environment

```bash
# This creates a directory named '.venv' in your project root
python -m venv .venv
```

#### Activate the Virtual Environment

- **Windows (PowerShell):**

```powershell
    .venv\Scripts\Activate.ps1
    ```
-   **Windows (Command Prompt):**
    ```cmd
    .venv\Scripts\activate.bat
    ```
-   **macOS / Linux (Bash/Zsh):**
    ```bash
    source .venv/bin/activate
    ```
*Your terminal prompt should now be prefixed with `(.venv)`.*

## 4. Install Dependencies

Once the virtual environment is activated, install all the required Python packages using `pip`.

```bash
pip install -r requirements.txt
```

## 5. Run Local Services (MongoDB & Redis)

You will need to have **MongoDB** and **Redis** running. If you don't have them installed locally, the easiest way to run them is with Docker.

```bash
# Run MongoDB in a container
docker run -d -p 27017:27017 --name mongo mongo:6

# Run Redis in a container
docker run -d -p 6379:6379 --name redis redis:7
```

## 6. Run the Application Services

With your environment set up, you can now run the FastAPI backend and the Streamlit UI.

### Run the FastAPI Application

Open a terminal (with the virtual environment activated) and run the following command from the project root:

```bash
uvicorn app.api.server:app --reload --port 8000
```

*The `--reload` flag will automatically restart the server when you make changes to the code.*

#### Run the Streamlit Application

Open a **second terminal** (and activate the virtual environment) to run the Streamlit UI:

```bash
streamlit run app/ui/main.py
```

You should now be able to access the Streamlit UI at `http://localhost:8501`.

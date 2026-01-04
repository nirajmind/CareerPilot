import os
from dotenv import load_dotenv

# Load .env from project root (CareerPilot/.env)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ENV_PATH = os.path.join(BASE_DIR, ".env")
load_dotenv(ENV_PATH)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3-pro-preview")

if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY is not set in .env")

API_TITLE = "CareerPilot API"
API_VERSION = "0.1.0"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
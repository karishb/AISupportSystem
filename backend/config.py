"""Application configuration from environment variables."""
import os
from dotenv import load_dotenv

load_dotenv()

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///support_platform.db")

# AI Providers
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_API_KEYS = [k.strip() for k in os.getenv("GROQ_API_KEYS", "").split(",") if k.strip()]
if GROQ_API_KEY and GROQ_API_KEY not in GROQ_API_KEYS:
    GROQ_API_KEYS.insert(0, GROQ_API_KEY)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
AI_MODE = os.getenv("AI_MODE", "llm").lower()

# Groq config
GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_BASE_URL = "https://api.groq.com/openai/v1"

# OpenAI embeddings config
EMBEDDING_MODEL = "text-embedding-3-small"

# ChromaDB
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")

# Pipeline
DEFAULT_SAMPLE_SIZE = 500
MAX_UPLOAD_SIZE = 50_000

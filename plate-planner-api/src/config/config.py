"""
Centralized configuration for PlatePlanner API.

All settings are read from environment variables with sensible defaults
for local development. In production (Railway, Docker, etc.), set the
relevant env vars in the platform dashboard.

Database-related values (DATABASE_URL, NEO4J_*, SSL settings) are
centralised in ``src.database.cloud_config`` so there is a single place
to handle the local-Docker vs cloud-Neon/AuraDB distinction.  This module
re-exports them for backward compatibility.
"""

import os

from dotenv import load_dotenv

load_dotenv()

# ──────────────────────────────────────────────────────────────────────
# Server
# ──────────────────────────────────────────────────────────────────────
PORT = int(os.getenv("PORT", "8000"))

# ──────────────────────────────────────────────────────────────────────
# PostgreSQL + Neo4j  (delegated to cloud_config for SSL / cloud support)
# ──────────────────────────────────────────────────────────────────────
from src.database.cloud_config import (  # noqa: E402
    DATABASE_URL,
    NEO4J_URI,
    NEO4J_USER,
    NEO4J_PASSWORD,
    NEO4J_ENCRYPTED,
    NEO4J_DRIVER_KWARGS,
    IS_CLOUD_POSTGRES,
    IS_CLOUD_NEO4J,
)

# ──────────────────────────────────────────────────────────────────────
# JWT / Auth  (also available via cloud_config, re-read here for clarity)
# ──────────────────────────────────────────────────────────────────────
SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkeychangeinproduction")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# ──────────────────────────────────────────────────────────────────────
# External API keys
# ──────────────────────────────────────────────────────────────────────
SPOONACULAR_API_KEY = os.getenv("SPOONACULAR_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")

# ──────────────────────────────────────────────────────────────────────
# LLM provider configuration
# ──────────────────────────────────────────────────────────────────────
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "")  # auto-detected if empty
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
GOOGLE_MODEL = os.getenv("GOOGLE_MODEL", "gemini-2.0-flash")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")

# ──────────────────────────────────────────────────────────────────────
# CORS
# ──────────────────────────────────────────────────────────────────────
# Comma-separated origins, or "*" for dev.
# Example for production:
#   ALLOWED_ORIGINS=https://plateplanner.vercel.app,https://www.plateplanner.com
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", os.getenv("CORS_ORIGINS", "*"))

# ──────────────────────────────────────────────────────────────────────
# SQLite recipe DB path  (local FAISS recipe database)
# ──────────────────────────────────────────────────────────────────────
RECIPE_DB_PATH = os.getenv(
    "RECIPE_DB_PATH",
    "src/data/models/recipe_suggestion/recipes.db",
)

"""
Cloud database configuration for PlatePlanner.

Supports two deployment modes:
  - LOCAL (Docker):  PostgreSQL on localhost:5432, Neo4j on bolt://localhost:7687
  - CLOUD:           Neon Postgres (postgresql+psycopg2://...?sslmode=require)
                     Neo4j AuraDB  (neo4j+s://... with encrypted=True)

All values are read from environment variables with safe local-dev fallbacks.
"""

from __future__ import annotations

import os
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_cloud_postgres(url: str) -> bool:
    """Return True when the DATABASE_URL points to a cloud-hosted Postgres
    instance (Neon, Supabase, etc.) rather than a local Docker container."""
    parsed = urlparse(url)
    hostname = parsed.hostname or ""
    # Neon endpoints contain ".neon.tech"; other cloud providers have similar patterns.
    cloud_markers = [".neon.tech", ".supabase.co", ".amazonaws.com", ".azure.com"]
    return any(marker in hostname for marker in cloud_markers)


def _is_cloud_neo4j(uri: str) -> bool:
    """Return True when the NEO4J_URI uses the neo4j+s:// or neo4j+ssc://
    scheme (required by AuraDB) instead of bolt:// (local Docker)."""
    return uri.startswith("neo4j+s://") or uri.startswith("neo4j+ssc://")


def _ensure_sslmode(url: str) -> str:
    """Append ?sslmode=require to a Postgres URL if not already present.

    Neon (and most managed Postgres) requires SSL connections.  This helper
    is idempotent - it leaves the URL alone when sslmode is already set.
    """
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    if "sslmode" not in qs:
        qs["sslmode"] = ["require"]
        new_query = urlencode(qs, doseq=True)
        parsed = parsed._replace(query=new_query)
    return urlunparse(parsed)


def _normalize_pg_scheme(url: str) -> str:
    """Normalise postgres:// -> postgresql:// (SQLAlchemy requirement) and
    keep the psycopg2 driver explicit for sync usage."""
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    # If using asyncpg scheme from Neon dashboard, convert for sync psycopg2
    if url.startswith("postgresql+asyncpg://"):
        url = url.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)
    # Ensure the driver is explicit so psycopg2-binary is used.
    # Only add the driver suffix if no driver is already specified (i.e.
    # the URL starts with bare "postgresql://" without a "+driver" part).
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return url


# ---------------------------------------------------------------------------
# PostgreSQL / Neon
# ---------------------------------------------------------------------------

_raw_database_url = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/plateplanner",
)

DATABASE_URL: str = _normalize_pg_scheme(_raw_database_url)

# Automatically add sslmode=require for cloud-hosted Postgres
if _is_cloud_postgres(DATABASE_URL):
    DATABASE_URL = _ensure_sslmode(DATABASE_URL)

# SQLAlchemy connect_args for SSL when targeting Neon / cloud Postgres.
# For local Docker, no special args are needed.
POSTGRES_CONNECT_ARGS: dict = {}
if _is_cloud_postgres(DATABASE_URL):
    POSTGRES_CONNECT_ARGS = {
        "sslmode": "require",
    }

# SQLAlchemy engine kwargs suitable for cloud-hosted Postgres.
POSTGRES_ENGINE_KWARGS: dict = {
    "pool_pre_ping": True,      # detect stale connections (important for serverless Neon)
    "pool_size": 5,
    "max_overflow": 10,
    "pool_recycle": 300,        # recycle connections every 5 min (Neon idle timeout)
}

# ---------------------------------------------------------------------------
# Neo4j / AuraDB
# ---------------------------------------------------------------------------

NEO4J_URI: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER: str = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD: str = os.getenv("NEO4J_PASSWORD", "12345678")

# AuraDB uses neo4j+s:// which implies TLS.  For local Docker (bolt://)
# encryption is disabled by default.
NEO4J_ENCRYPTED: bool = _is_cloud_neo4j(NEO4J_URI)

# neo4j+s:// already implies TLS — do not pass encrypted/trust kwargs
# (Neo4j driver v5+ raises ConfigurationError if you do).
NEO4J_DRIVER_KWARGS: dict = {}

# ---------------------------------------------------------------------------
# JWT / Auth  (re-exported for convenience; originals stay in config.py)
# ---------------------------------------------------------------------------

SECRET_KEY: str = os.getenv(
    "SECRET_KEY", "supersecretkeychangeinproduction"
)
ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
    os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
)

# ---------------------------------------------------------------------------
# Deployment mode flag
# ---------------------------------------------------------------------------

IS_CLOUD_POSTGRES: bool = _is_cloud_postgres(DATABASE_URL)
IS_CLOUD_NEO4J: bool = _is_cloud_neo4j(NEO4J_URI)


def summary() -> str:
    """Return a human-readable summary of the active database configuration.
    Useful for startup logging."""
    pg_mode = "Neon (cloud)" if IS_CLOUD_POSTGRES else "Local Docker"
    neo_mode = "AuraDB (cloud)" if IS_CLOUD_NEO4J else "Local Docker"
    parsed = urlparse(DATABASE_URL)
    pg_host = parsed.hostname or "unknown"
    return (
        f"Postgres: {pg_mode} ({pg_host}) | "
        f"Neo4j: {neo_mode} ({NEO4J_URI.split('//')[1].split(':')[0] if '//' in NEO4J_URI else NEO4J_URI})"
    )

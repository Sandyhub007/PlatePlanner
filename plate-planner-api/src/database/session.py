"""
SQLAlchemy engine and session factory.

Supports both local Docker PostgreSQL and cloud-hosted Neon Postgres.
SSL, connection pooling, and pool-recycling settings are automatically
applied when the DATABASE_URL points to a cloud host (see cloud_config.py).
"""

import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from src.database.cloud_config import (
    DATABASE_URL,
    POSTGRES_CONNECT_ARGS,
    POSTGRES_ENGINE_KWARGS,
    IS_CLOUD_POSTGRES,
    summary as db_summary,
)

logger = logging.getLogger("plate_planner.db")

# Build engine kwargs ---------------------------------------------------------
_engine_kwargs: dict = {**POSTGRES_ENGINE_KWARGS}
if POSTGRES_CONNECT_ARGS:
    _engine_kwargs["connect_args"] = POSTGRES_CONNECT_ARGS

engine = create_engine(DATABASE_URL, **_engine_kwargs)

logger.info("Database config: %s", db_summary())

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency that yields a SQLAlchemy session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

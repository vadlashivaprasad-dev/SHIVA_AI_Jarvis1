"""Database engine/session utilities.

Enterprise-grade requirements:
- Singleton engine
- Singleton SessionLocal factory
- Dependency injection helpers
- Pool best practices

NOTE: This module is additive; it does not modify existing models.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool, QueuePool

from .config import get_settings


@lru_cache(maxsize=1)
def get_db_engine() -> Engine:
    """Return a singleton SQLAlchemy engine."""
    settings = get_settings()

    is_postgres = "postgresql" in (settings.database_url or "")

    if is_postgres:
        poolclass = QueuePool
        pool_kwargs = {
            "pool_size": settings.database_pool_size,
            "max_overflow": 20,
            "pool_recycle": settings.database_pool_recycle,
            "pool_pre_ping": True,
        }
    else:
        # SQLite + multi-threading: keep pool disabled.
        poolclass = NullPool
        pool_kwargs = {}

    return create_engine(
        settings.database_url,
        echo=settings.database_echo,
        poolclass=poolclass,
        connect_args={"check_same_thread": False} if not is_postgres else {},
        **pool_kwargs,
    )


@lru_cache(maxsize=1)
def get_session_local() -> sessionmaker[Session]:
    """Return a singleton SessionLocal factory."""
    engine = get_db_engine()
    return sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        future=True,
    )


def get_db_session() -> Generator[Session, None, None]:
    """FastAPI dependency to provide a request-scoped session."""
    SessionLocal = get_session_local()
    db: Session = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


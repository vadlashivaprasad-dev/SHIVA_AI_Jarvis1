"""services.gateway.src.db

SQLAlchemy database engine/session utilities.

Hardening goals:
- Explicit engine lifecycle management (dispose on shutdown)
- Early DATABASE_URL validation + clearer errors
- SQLite connection timeout to prevent hangs
- Structured logging with sensitive data masking

Public API is preserved:
- get_db_engine()
- get_session_local()
- get_db_session()
- shutdown_db_engine()
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Generator, Optional

import structlog
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.exc import ArgumentError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool, QueuePool

from .config import get_settings

logger = structlog.get_logger("db")


def _mask_database_url(url: str) -> str:
    """Mask credentials in database URLs (best-effort)."""
    # e.g. postgresql://user:pass@host/db -> postgresql://user:***@host/db
    return re.sub(r"(://[^:/?#]+):([^@/]+)@", r"\1:***@", url)


@dataclass(frozen=True)
class _EngineConfig:
    database_url: str
    echo: bool
    pool_size: int
    pool_recycle: int
    sqlite_timeout_seconds: int = 20


class DatabaseEngine:
    """Class-based engine manager with explicit disposal."""

    _engine: Optional[Engine] = None
    _SessionLocal: Optional[sessionmaker[Session]] = None

    @classmethod
    def _get_config(cls) -> _EngineConfig:
        settings = get_settings()
        database_url = settings.database_url
        if not database_url:
            raise ValueError("DATABASE_URL environment variable is not set")

        return _EngineConfig(
            database_url=database_url,
            echo=settings.database_echo,
            pool_size=settings.database_pool_size,
            pool_recycle=settings.database_pool_recycle,
        )

    @classmethod
    def get_engine(cls) -> Engine:
        if cls._engine is not None:
            return cls._engine

        config = cls._get_config()
        is_postgres = config.database_url.startswith("postgresql")

        try:
            if is_postgres:
                poolclass = QueuePool
                pool_kwargs = {
                    "pool_size": config.pool_size,
                    "max_overflow": 20,
                    "pool_recycle": config.pool_recycle,
                    "pool_pre_ping": True,
                }
                connect_args = {}
            else:
                # SQLite: keep pool disabled and set timeout.
                poolclass = NullPool
                pool_kwargs = {}
                connect_args = {
                    "check_same_thread": False,
                    "timeout": config.sqlite_timeout_seconds,
                }

            engine = create_engine(
                config.database_url,
                echo=config.echo,
                poolclass=poolclass,
                connect_args=connect_args,
                **pool_kwargs,
            )
        except ArgumentError as e:
            masked = _mask_database_url(config.database_url)
            raise ValueError(f"Invalid database URL: {masked}") from e

        cls._engine = engine
        logger.info(
            "database_engine_initialized",
            url_masked=_mask_database_url(config.database_url),
            is_postgres=is_postgres,
            echo=config.echo,
        )
        return engine

    @classmethod
    def get_session_local(cls) -> sessionmaker[Session]:
        if cls._SessionLocal is not None:
            return cls._SessionLocal

        engine = cls.get_engine()
        cls._SessionLocal = sessionmaker(
            bind=engine,
            autocommit=False,
            autoflush=False,
            future=True,
        )
        logger.info("session_factory_initialized")
        return cls._SessionLocal

    @classmethod
    def dispose(cls) -> None:
        """Dispose the engine/pool and clear cached factories."""
        if cls._engine is None:
            return

        try:
            cls._engine.dispose()
        finally:
            cls._engine = None
            cls._SessionLocal = None
            logger.info("database_engine_disposed")


def get_db_engine() -> Engine:
    """Return a singleton SQLAlchemy engine."""
    return DatabaseEngine.get_engine()


def get_session_local() -> sessionmaker[Session]:
    """Return a singleton SessionLocal factory."""
    return DatabaseEngine.get_session_local()


def shutdown_db_engine() -> None:
    """Dispose the database engine/pool (call on application shutdown)."""
    DatabaseEngine.dispose()


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


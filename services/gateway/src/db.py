"""
services.gateway.src.db

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
from threading import Lock
from typing import Generator, Optional

import structlog
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.engine.url import make_url
from sqlalchemy.exc import ArgumentError, OperationalError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool, QueuePool

from .config import get_settings

logger = structlog.get_logger("db")


def _mask_database_url(url: str) -> str:
    """Mask credentials in database URLs (best-effort)."""
    return re.sub(r"(://[^:/?#]+):([^@/]+)@", r"\1:***@", url)


@dataclass(frozen=True)
class _EngineConfig:
    database_url: str
    echo: bool
    pool_size: int
    pool_recycle: int
    sqlite_timeout_seconds: int = 20
    pool_timeout_seconds: int = 30


class DatabaseEngine:
    """Class-based engine manager with explicit disposal."""

    _engine: Optional[Engine] = None
    _SessionLocal: Optional[sessionmaker[Session]] = None
    _lock = Lock()

    @classmethod
    def _get_config(cls) -> _EngineConfig:
        settings = get_settings()

        database_url = settings.database_url

        if not database_url:
            raise ValueError("DATABASE_URL environment variable is not set")

        try:
            make_url(database_url)
        except Exception as exc:
            raise ValueError(
                f"Invalid DATABASE_URL: {_mask_database_url(database_url)}"
            ) from exc

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

        with cls._lock:
            if cls._engine is not None:
                return cls._engine

            config = cls._get_config()

            url_obj = make_url(config.database_url)
            driver = url_obj.drivername

            try:
                if driver.startswith("postgresql"):
                    poolclass = QueuePool

                    pool_kwargs = {
                        "pool_size": config.pool_size,
                        "max_overflow": 20,
                        "pool_recycle": config.pool_recycle,
                        "pool_pre_ping": True,
                        "pool_timeout": config.pool_timeout_seconds,
                    }

                    connect_args = {}

                elif driver.startswith("sqlite"):
                    poolclass = NullPool

                    pool_kwargs = {}

                    connect_args = {
                        "check_same_thread": False,
                        "timeout": config.sqlite_timeout_seconds,
                    }

                else:
                    poolclass = QueuePool

                    pool_kwargs = {
                        "pool_size": config.pool_size,
                        "max_overflow": 10,
                        "pool_recycle": config.pool_recycle,
                        "pool_pre_ping": True,
                        "pool_timeout": config.pool_timeout_seconds,
                    }

                    connect_args = {}

                engine = create_engine(
                    config.database_url,
                    echo=config.echo,
                    poolclass=poolclass,
                    connect_args=connect_args,
                    future=True,
                    **pool_kwargs,
                )

                #
                # Verify connection during startup
                #
                try:
                    with engine.connect() as conn:
                        conn.execute(text("SELECT 1"))
                except Exception:
                    engine.dispose()
                    raise

            except ArgumentError as exc:
                masked = _mask_database_url(config.database_url)

                raise ValueError(
                    f"Invalid database URL: {masked}"
                ) from exc

            cls._engine = engine

            logger.info(
                "database_engine_initialized",
                url_masked=_mask_database_url(config.database_url),
                driver=driver,
                echo=config.echo,
            )

            return cls._engine

    @classmethod
    def get_session_local(cls) -> sessionmaker[Session]:
        if cls._SessionLocal is not None:
            return cls._SessionLocal

        with cls._lock:
            if cls._SessionLocal is not None:
                return cls._SessionLocal

            engine = cls.get_engine()

            cls._SessionLocal = sessionmaker(
                bind=engine,
                autocommit=False,
                autoflush=False,
                future=True,
                expire_on_commit=False,  # performance improvement
            )

            logger.info("session_factory_initialized")

            return cls._SessionLocal

    @classmethod
    def dispose(cls) -> None:
        """Dispose the engine/pool and clear cached factories."""

        with cls._lock:
            if cls._engine is None:
                return

            try:
                cls._engine.dispose()

            finally:
                cls._engine = None
                cls._SessionLocal = None

                logger.info("database_engine_disposed")


def get_db_engine() -> Engine:
    """
    Return singleton SQLAlchemy engine.

    Preserved compatibility block:
    If legacy configuration references `shivaai`
    but deployment created `shivaai_db`,
    log a clear warning instead of creating
    unmanaged engines.
    """

    try:
        return DatabaseEngine.get_engine()

    except OperationalError as exc:
        msg = str(exc).lower()

        if (
            "database \"shivaai\" does not exist" in msg
            or "database 'shivaai' does not exist" in msg
        ):
            logger.error(
                "database_shivaai_missing",
                recommendation="Update DATABASE_URL to use shivaai_db",
            )

        raise


def get_session_local() -> sessionmaker[Session]:
    """Return a singleton SessionLocal factory."""
    return DatabaseEngine.get_session_local()


def shutdown_db_engine() -> None:
    """Dispose the database engine/pool (call on application shutdown)."""
    DatabaseEngine.dispose()


def get_db_session() -> Generator[Session, None, None]:
    """
    FastAPI dependency to provide a request-scoped session.

    Existing behavior preserved:
    - automatic commit
    - rollback on error
    """

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
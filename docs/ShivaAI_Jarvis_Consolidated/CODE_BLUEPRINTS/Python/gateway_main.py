# services/gateway/src/main.py
"""
ShivaAI Jarvis Gateway - Main FastAPI Application
Cognitive Operating System Kernel - API Gateway
"""

import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from src.config import settings
from src.middleware.auth import AuthMiddleware
from src.middleware.rbac import RBACMiddleware
from src.middleware.ratelimit import RateLimitMiddleware
from src.middleware.telemetry import TelemetryMiddleware
from src.routers import (
    auth,
    chat,
    memory,
    knowledge,
    agents,
    voice,
    workflows,
    trading,
    code,
    predictions,
    learning,
    health,
)
from src.exceptions import ShivaAIException
from src.db import engine, Base
from src.logger import setup_logging

# Setup logging
logger = setup_logging(__name__)


# ============================================================================
# STARTUP / SHUTDOWN EVENTS
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan - startup and shutdown events
    """
    # STARTUP
    logger.info("🚀 ShivaAI Jarvis Kernel initializing...")
    
    # Create database tables
    Base.metadata.create_all(bind=engine)
    logger.info("✅ Database initialized")
    
    # Initialize services
    logger.info("✅ Services initialized")
    
    # Check health of external services
    await check_external_services()
    
    logger.info("✨ ShivaAI Jarvis Kernel ready - operating system online")
    
    yield
    
    # SHUTDOWN
    logger.info("🛑 ShivaAI Jarvis Kernel shutting down...")
    logger.info("✅ All services stopped gracefully")


async def check_external_services():
    """Check health of Redis, Qdrant, Neo4j, etc."""
    try:
        from src.services.redis_client import redis_client
        await redis_client.ping()
        logger.info("✅ Redis connected")
    except Exception as e:
        logger.warning(f"⚠️  Redis health check failed: {e}")
    
    try:
        from src.services.qdrant_client import qdrant_client
        health = await qdrant_client.get_health()
        logger.info("✅ Qdrant connected")
    except Exception as e:
        logger.warning(f"⚠️  Qdrant health check failed: {e}")
    
    try:
        from src.services.neo4j_client import neo4j_client
        await neo4j_client.verify_connectivity()
        logger.info("✅ Neo4j connected")
    except Exception as e:
        logger.warning(f"⚠️  Neo4j health check failed: {e}")


# ============================================================================
# APPLICATION FACTORY
# ============================================================================

def create_app() -> FastAPI:
    """
    Create and configure FastAPI application
    """
    app = FastAPI(
        title="ShivaAI Jarvis",
        description="Cognitive Operating System Kernel - API Gateway",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # ========================================================================
    # MIDDLEWARE STACK
    # ========================================================================
    
    # Trust hosts
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.ALLOWED_HOSTS,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Custom middleware (order matters!)
    app.add_middleware(TelemetryMiddleware)  # Metrics collection
    app.add_middleware(RateLimitMiddleware)   # Rate limiting
    app.add_middleware(RBACMiddleware)        # Authorization
    app.add_middleware(AuthMiddleware)        # Authentication

    # ========================================================================
    # EXCEPTION HANDLERS
    # ========================================================================

    @app.exception_handler(ShivaAIException)
    async def shivaai_exception_handler(request: Request, exc: ShivaAIException):
        """Handle ShivaAI custom exceptions"""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.error_code,
                    "message": exc.message,
                    "details": exc.details,
                }
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle unexpected exceptions"""
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected error occurred",
                }
            },
        )

    # ========================================================================
    # ROUTES
    # ========================================================================

    # Health & Status
    app.include_router(health.router, prefix="/api/v1", tags=["health"])

    # Authentication
    app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])

    # Chat & Conversations
    app.include_router(chat.router, prefix="/api/v1/chat", tags=["chat"])

    # Memory System
    app.include_router(memory.router, prefix="/api/v1/memory", tags=["memory"])

    # Knowledge & RAG
    app.include_router(
        knowledge.router, prefix="/api/v1/knowledge", tags=["knowledge"]
    )

    # Agents
    app.include_router(agents.router, prefix="/api/v1/agents", tags=["agents"])

    # Voice Interface
    app.include_router(voice.router, prefix="/api/v1/voice", tags=["voice"])

    # Workflows
    app.include_router(
        workflows.router, prefix="/api/v1/workflows", tags=["workflows"]
    )

    # Trading AI
    app.include_router(trading.router, prefix="/api/v1/trading", tags=["trading"])

    # Code Assistant
    app.include_router(code.router, prefix="/api/v1/code", tags=["code"])

    # Predictions
    app.include_router(
        predictions.router, prefix="/api/v1/predictions", tags=["predictions"]
    )

    # Learning
    app.include_router(
        learning.router, prefix="/api/v1/learning", tags=["learning"]
    )

    # ========================================================================
    # ROOT ROUTE
    # ========================================================================

    @app.get("/")
    async def root():
        """Root endpoint - API information"""
        return {
            "name": "ShivaAI Jarvis",
            "type": "Cognitive Operating System Kernel",
            "version": "1.0.0",
            "status": "operational",
            "docs": "/docs",
            "openapi": "/openapi.json",
        }

    return app


# ============================================================================
# APPLICATION INSTANCE
# ============================================================================

app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )

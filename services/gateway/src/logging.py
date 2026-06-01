"""
Structured logging configuration for ShivaAI Jarvis.
Uses structlog with JSON output for production environments.
"""

import logging
import logging.config
import os
import sys
from typing import Any

import structlog


def configure_logging(
    log_level: str = "INFO",
    log_format: str = "json",
    environment: str = "development",
) -> None:
    """Configure structured logging for the application."""
    
    # Convert string log level to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Configure standard library logging
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "plain": {
                "()": structlog.stdlib.ProcessorFormatter,
                "processor": structlog.dev.ConsoleRenderer(),
            },
            "json": {
                "()": structlog.stdlib.ProcessorFormatter,
                "processor": structlog.processors.JSONRenderer(),
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": numeric_level,
                "formatter": log_format,
                "stream": sys.stdout,
            },
        },
        "root": {
            "level": numeric_level,
            "handlers": ["console"],
        },
        "loggers": {
            "uvicorn": {
                "level": numeric_level,
                "propagate": True,
            },
            "fastapi": {
                "level": numeric_level,
                "propagate": True,
            },
        },
    }
    
    logging.config.dictConfig(logging_config)
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Set up request ID context variable
    if hasattr(structlog, "contextvars"):
        structlog.contextvars.clear_contextvars()


def get_logger(name: str = __name__) -> structlog.typing.FilteringBoundLogger:
    """Get a logger instance with proper configuration."""
    return structlog.get_logger(name)


class RequestIDMiddleware:
    """Middleware to add request ID to logs and headers."""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            from uuid import uuid4
            
            request_id = str(uuid4())
            
            # Add to scope for access in handlers
            scope["request_id"] = request_id
            
            # Add to response headers
            async def send_wrapper(message):
                if message["type"] == "http.response.start":
                    headers = list(message.get("headers", []))
                    headers.append(
                        (b"x-request-id", request_id.encode())
                    )
                    message["headers"] = headers
                await send(message)
            
            # Bind request ID to structlog context
            structlog.contextvars.bind_contextvars(request_id=request_id)
            
            await self.app(scope, receive, send_wrapper)
        else:
            await self.app(scope, receive, send)


# Middleware for cleaner logging
class LoggingMiddleware:
    """Middleware to log HTTP requests and responses."""
    
    def __init__(self, app):
        self.app = app
        self.logger = get_logger(__name__)
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        import time
        from uuid import uuid4
        
        request_id = scope.get("request_id", str(uuid4()))
        start_time = time.time()
        
        # Log request
        self.logger.info(
            "HTTP request",
            method=scope["method"],
            path=scope["path"],
            request_id=request_id,
        )
        
        # Capture response status
        response_status = 500
        
        async def send_wrapper(message):
            nonlocal response_status
            if message["type"] == "http.response.start":
                response_status = message["status"]
            await send(message)
        
        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            # Log response
            duration_ms = (time.time() - start_time) * 1000
            self.logger.info(
                "HTTP response",
                method=scope["method"],
                path=scope["path"],
                status_code=response_status,
                duration_ms=round(duration_ms, 2),
                request_id=request_id,
            )

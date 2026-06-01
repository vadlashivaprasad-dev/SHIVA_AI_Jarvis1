"""
Standardized error handling and exception hierarchy for ShivaAI Jarvis.
Provides consistent error responses, logging, and categorization.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from fastapi import HTTPException, Request, Response, status
from pydantic import BaseModel
import structlog


logger = structlog.get_logger(__name__)


class ErrorCode(str, Enum):
    """Standardized error codes for API responses."""
    # Authentication errors (4000-4099)
    AUTH_INVALID_CREDENTIALS = "AUTH_001"
    AUTH_TOKEN_EXPIRED = "AUTH_002"
    AUTH_TOKEN_INVALID = "AUTH_003"
    AUTH_INSUFFICIENT_PERMISSIONS = "AUTH_004"
    AUTH_ACCOUNT_LOCKED = "AUTH_005"
    AUTH_MISSING_TOKEN = "AUTH_006"
    
    # Validation errors (4100-4199)
    VALIDATION_ERROR = "VAL_001"
    VALIDATION_INVALID_INPUT = "VAL_002"
    VALIDATION_MISSING_FIELD = "VAL_003"
    
    # Resource errors (4200-4299)
    RESOURCE_NOT_FOUND = "RES_001"
    RESOURCE_ALREADY_EXISTS = "RES_002"
    RESOURCE_CONFLICT = "RES_003"
    
    # Rate limiting errors (4300-4399)
    RATE_LIMIT_EXCEEDED = "RATE_001"
    RATE_LIMIT_QUOTA_EXCEEDED = "RATE_002"
    
    # LLM/External service errors (5000-5099)
    LLM_PROVIDER_ERROR = "LLM_001"
    LLM_TIMEOUT = "LLM_002"
    LLM_RATE_LIMIT = "LLM_003"
    
    # Database errors (5100-5199)
    DATABASE_ERROR = "DB_001"
    DATABASE_CONSTRAINT_VIOLATION = "DB_002"
    
    # Vector DB errors (5200-5299)
    VECTOR_DB_ERROR = "VDB_001"
    
    # Internal errors (5300-5399)
    INTERNAL_SERVER_ERROR = "INT_001"
    SERVICE_UNAVAILABLE = "INT_002"
    OPERATION_TIMEOUT = "INT_003"


class ErrorSeverity(str, Enum):
    """Error severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ErrorDetail:
    """Internal representation of an error."""
    code: ErrorCode
    message: str
    severity: ErrorSeverity
    status_code: int
    user_message: Optional[str] = None
    details: Optional[dict[str, Any]] = None
    request_id: Optional[str] = None
    timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        if self.request_id is None:
            self.request_id = str(uuid4())
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)


class ErrorResponse(BaseModel):
    """Standardized API error response."""
    code: str
    message: str
    severity: str
    request_id: str
    timestamp: str
    status_code: int
    user_message: Optional[str] = None
    details: Optional[dict[str, Any]] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "code": "AUTH_002",
                "message": "JWT token has expired",
                "severity": "error",
                "request_id": "550e8400-e29b-41d4-a716-446655440000",
                "timestamp": "2024-01-15T10:30:00Z",
                "status_code": 401,
                "user_message": "Your session has expired. Please log in again."
            }
        }


class ShivaAIException(Exception):
    """Base exception for ShivaAI Jarvis."""
    
    def __init__(
        self,
        code: ErrorCode,
        message: str,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        status_code: int = 500,
        user_message: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        self.code = code
        self.message = message
        self.severity = severity
        self.status_code = status_code
        self.user_message = user_message or message
        self.details = details or {}
        self.request_id = str(uuid4())
        super().__init__(self.message)
    
    def to_error_detail(self) -> ErrorDetail:
        return ErrorDetail(
            code=self.code,
            message=self.message,
            severity=self.severity,
            status_code=self.status_code,
            user_message=self.user_message,
            details=self.details,
            request_id=self.request_id,
        )


# Specific exception classes
class AuthenticationError(ShivaAIException):
    """Authentication/authorization errors."""
    def __init__(
        self,
        code: ErrorCode = ErrorCode.AUTH_INVALID_CREDENTIALS,
        message: str = "Authentication failed",
        **kwargs
    ):
        super().__init__(
            code=code,
            message=message,
            severity=ErrorSeverity.WARNING,
            status_code=401,
            **kwargs
        )


class ValidationError(ShivaAIException):
    """Input validation errors."""
    def __init__(
        self,
        code: ErrorCode = ErrorCode.VALIDATION_ERROR,
        message: str = "Validation failed",
        **kwargs
    ):
        super().__init__(
            code=code,
            message=message,
            severity=ErrorSeverity.WARNING,
            status_code=400,
            **kwargs
        )


class NotFoundError(ShivaAIException):
    """Resource not found errors."""
    def __init__(
        self,
        code: ErrorCode = ErrorCode.RESOURCE_NOT_FOUND,
        message: str = "Resource not found",
        **kwargs
    ):
        super().__init__(
            code=code,
            message=message,
            severity=ErrorSeverity.INFO,
            status_code=404,
            **kwargs
        )


class ConflictError(ShivaAIException):
    """Resource conflict errors."""
    def __init__(
        self,
        code: ErrorCode = ErrorCode.RESOURCE_CONFLICT,
        message: str = "Resource conflict",
        **kwargs
    ):
        super().__init__(
            code=code,
            message=message,
            severity=ErrorSeverity.WARNING,
            status_code=409,
            **kwargs
        )


class RateLimitError(ShivaAIException):
    """Rate limiting errors."""
    def __init__(
        self,
        code: ErrorCode = ErrorCode.RATE_LIMIT_EXCEEDED,
        message: str = "Rate limit exceeded",
        **kwargs
    ):
        super().__init__(
            code=code,
            message=message,
            severity=ErrorSeverity.WARNING,
            status_code=429,
            **kwargs
        )


class ExternalServiceError(ShivaAIException):
    """External service integration errors (LLM, Vector DB, etc)."""
    def __init__(
        self,
        code: ErrorCode = ErrorCode.LLM_PROVIDER_ERROR,
        message: str = "External service error",
        **kwargs
    ):
        super().__init__(
            code=code,
            message=message,
            severity=ErrorSeverity.ERROR,
            status_code=503,
            **kwargs
        )


class DatabaseError(ShivaAIException):
    """Database operation errors."""
    def __init__(
        self,
        code: ErrorCode = ErrorCode.DATABASE_ERROR,
        message: str = "Database error",
        **kwargs
    ):
        super().__init__(
            code=code,
            message=message,
            severity=ErrorSeverity.ERROR,
            status_code=500,
            **kwargs
        )


class InternalServerError(ShivaAIException):
    """Unexpected internal errors."""
    def __init__(
        self,
        code: ErrorCode = ErrorCode.INTERNAL_SERVER_ERROR,
        message: str = "Internal server error",
        **kwargs
    ):
        super().__init__(
            code=code,
            message=message,
            severity=ErrorSeverity.CRITICAL,
            status_code=500,
            **kwargs
        )


async def shivaai_exception_handler(request: Request, exc: ShivaAIException) -> Response:
    """Handle ShivaAIException and return standardized error response."""
    error_detail = exc.to_error_detail()
    
    # Log the error
    log_context = {
        "error_code": error_detail.code.value,
        "request_id": error_detail.request_id,
        "path": request.url.path,
        "method": request.method,
        "status_code": error_detail.status_code,
        "severity": error_detail.severity.value,
    }
    
    if error_detail.severity == ErrorSeverity.CRITICAL:
        logger.critical("Critical error", **log_context)
    elif error_detail.severity == ErrorSeverity.ERROR:
        logger.error("Error occurred", **log_context)
    elif error_detail.severity == ErrorSeverity.WARNING:
        logger.warning("Warning", **log_context)
    else:
        logger.info("Info", **log_context)
    
    response = ErrorResponse(
        code=error_detail.code.value,
        message=error_detail.message,
        severity=error_detail.severity.value,
        request_id=error_detail.request_id,
        timestamp=error_detail.timestamp.isoformat(),
        status_code=error_detail.status_code,
        user_message=error_detail.user_message,
        details=error_detail.details if error_detail.details else None,
    )
    
    return Response(
        content=response.model_dump_json(exclude_none=True),
        status_code=error_detail.status_code,
        media_type="application/json",
    )


async def generic_exception_handler(request: Request, exc: Exception) -> Response:
    """Handle unexpected exceptions and convert to standardized errors."""
    request_id = str(uuid4())
    
    logger.error(
        "Unhandled exception",
        error_type=type(exc).__name__,
        error_message=str(exc),
        request_id=request_id,
        path=request.url.path,
        method=request.method,
    )
    
    response = ErrorResponse(
        code=ErrorCode.INTERNAL_SERVER_ERROR.value,
        message="An unexpected error occurred",
        severity=ErrorSeverity.CRITICAL.value,
        request_id=request_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
        status_code=500,
        user_message="An unexpected error occurred. Please try again later.",
    )
    
    return Response(
        content=response.model_dump_json(exclude_none=True),
        status_code=500,
        media_type="application/json",
    )

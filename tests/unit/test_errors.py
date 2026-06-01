"""
Unit tests for error handling module.
Tests error codes, exception hierarchy, and error responses.
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4

from services.gateway.src.errors import (
    AuthenticationError,
    ConflictError,
    DatabaseError,
    ErrorCode,
    ErrorResponse,
    ErrorSeverity,
    ExternalServiceError,
    InternalServerError,
    NotFoundError,
    RateLimitError,
    ShivaAIException,
    ValidationError,
)


class TestErrorCodeEnum:
    """Test error code enumeration."""
    
    def test_all_error_codes_are_unique(self):
        """All error codes should be unique."""
        codes = [e.value for e in ErrorCode]
        assert len(codes) == len(set(codes)), "Duplicate error codes found"
    
    def test_error_codes_follow_naming_convention(self):
        """Error codes should follow CATEGORY_XXX pattern."""
        for code in ErrorCode:
            assert "_" in code.value, f"Code {code.value} doesn't follow naming convention"
            assert len(code.value.split("_")[1]) == 3, f"Code {code.value} has invalid suffix"


class TestShivaAIException:
    """Test base exception class."""
    
    def test_exception_initialization(self):
        """Exception should initialize with all required fields."""
        exc = ShivaAIException(
            code=ErrorCode.INTERNAL_SERVER_ERROR,
            message="Test error",
            severity=ErrorSeverity.ERROR,
            status_code=500,
            user_message="Something went wrong",
        )
        
        assert exc.code == ErrorCode.INTERNAL_SERVER_ERROR
        assert exc.message == "Test error"
        assert exc.severity == ErrorSeverity.ERROR
        assert exc.status_code == 500
        assert exc.user_message == "Something went wrong"
        assert exc.request_id is not None
    
    def test_exception_to_error_detail(self):
        """Exception should convert to ErrorDetail correctly."""
        exc = ShivaAIException(
            code=ErrorCode.VALIDATION_ERROR,
            message="Invalid input",
            status_code=400,
        )
        
        detail = exc.to_error_detail()
        
        assert detail.code == ErrorCode.VALIDATION_ERROR
        assert detail.message == "Invalid input"
        assert detail.status_code == 400
        assert detail.request_id == exc.request_id
        assert detail.timestamp is not None


class TestSpecificExceptions:
    """Test specific exception subclasses."""
    
    def test_authentication_error_defaults(self):
        """AuthenticationError should have correct defaults."""
        exc = AuthenticationError()
        
        assert exc.code == ErrorCode.AUTH_INVALID_CREDENTIALS
        assert exc.status_code == 401
        assert exc.severity == ErrorSeverity.WARNING
    
    def test_authentication_error_custom_code(self):
        """AuthenticationError should accept custom code."""
        exc = AuthenticationError(
            code=ErrorCode.AUTH_TOKEN_EXPIRED,
            message="Token expired",
        )
        
        assert exc.code == ErrorCode.AUTH_TOKEN_EXPIRED
        assert exc.status_code == 401
    
    def test_validation_error_defaults(self):
        """ValidationError should have correct defaults."""
        exc = ValidationError(message="Invalid email format")
        
        assert exc.code == ErrorCode.VALIDATION_ERROR
        assert exc.status_code == 400
        assert exc.severity == ErrorSeverity.WARNING
    
    def test_not_found_error_defaults(self):
        """NotFoundError should have correct defaults."""
        exc = NotFoundError(message="User not found")
        
        assert exc.code == ErrorCode.RESOURCE_NOT_FOUND
        assert exc.status_code == 404
        assert exc.severity == ErrorSeverity.INFO
    
    def test_conflict_error_defaults(self):
        """ConflictError should have correct defaults."""
        exc = ConflictError(message="Email already exists")
        
        assert exc.code == ErrorCode.RESOURCE_CONFLICT
        assert exc.status_code == 409
        assert exc.severity == ErrorSeverity.WARNING
    
    def test_rate_limit_error_defaults(self):
        """RateLimitError should have correct defaults."""
        exc = RateLimitError(message="Too many requests")
        
        assert exc.code == ErrorCode.RATE_LIMIT_EXCEEDED
        assert exc.status_code == 429
        assert exc.severity == ErrorSeverity.WARNING
    
    def test_external_service_error_defaults(self):
        """ExternalServiceError should have correct defaults."""
        exc = ExternalServiceError(message="LLM service unavailable")
        
        assert exc.code == ErrorCode.LLM_PROVIDER_ERROR
        assert exc.status_code == 503
        assert exc.severity == ErrorSeverity.ERROR
    
    def test_database_error_defaults(self):
        """DatabaseError should have correct defaults."""
        exc = DatabaseError(message="Connection failed")
        
        assert exc.code == ErrorCode.DATABASE_ERROR
        assert exc.status_code == 500
        assert exc.severity == ErrorSeverity.ERROR
    
    def test_internal_server_error_defaults(self):
        """InternalServerError should have correct defaults."""
        exc = InternalServerError(message="Unexpected error")
        
        assert exc.code == ErrorCode.INTERNAL_SERVER_ERROR
        assert exc.status_code == 500
        assert exc.severity == ErrorSeverity.CRITICAL


class TestErrorResponse:
    """Test error response formatting."""
    
    def test_error_response_model_validation(self):
        """ErrorResponse should validate all required fields."""
        response = ErrorResponse(
            code="AUTH_001",
            message="Authentication failed",
            severity="error",
            request_id=str(uuid4()),
            timestamp=datetime.now(timezone.utc).isoformat(),
            status_code=401,
            user_message="Please log in again",
        )
        
        assert response.code == "AUTH_001"
        assert response.message == "Authentication failed"
        assert response.severity == "error"
        assert response.status_code == 401
    
    def test_error_response_json_serialization(self):
        """ErrorResponse should serialize to JSON correctly."""
        response = ErrorResponse(
            code="VAL_001",
            message="Validation failed",
            severity="warning",
            request_id=str(uuid4()),
            timestamp=datetime.now(timezone.utc).isoformat(),
            status_code=400,
        )
        
        json_str = response.model_dump_json()
        assert "VAL_001" in json_str
        assert "Validation failed" in json_str
        assert "warning" in json_str
    
    def test_error_response_exclude_none(self):
        """ErrorResponse should exclude None values."""
        response = ErrorResponse(
            code="RES_001",
            message="Not found",
            severity="info",
            request_id=str(uuid4()),
            timestamp=datetime.now(timezone.utc).isoformat(),
            status_code=404,
            user_message=None,
            details=None,
        )
        
        json_dict = response.model_dump(exclude_none=True)
        assert "user_message" not in json_dict
        assert "details" not in json_dict
        assert "code" in json_dict
        assert "request_id" in json_dict


class TestErrorHierarchy:
    """Test exception inheritance hierarchy."""
    
    def test_all_specific_exceptions_inherit_from_shivaai_exception(self):
        """All specific exceptions should inherit from ShivaAIException."""
        specific_exceptions = [
            AuthenticationError,
            ValidationError,
            NotFoundError,
            ConflictError,
            RateLimitError,
            ExternalServiceError,
            DatabaseError,
            InternalServerError,
        ]
        
        for exc_class in specific_exceptions:
            exc = exc_class()
            assert isinstance(exc, ShivaAIException)
            assert isinstance(exc, Exception)
    
    def test_exception_hierarchy_message_inheritance(self):
        """Exceptions should properly pass message to parent."""
        message = "Custom error message"
        exc = ValidationError(message=message)
        
        assert str(exc) == message
        assert exc.message == message


class TestErrorDetails:
    """Test error detail field handling."""
    
    def test_error_with_details_dict(self):
        """Exception should accept and preserve details."""
        details = {
            "field": "email",
            "reason": "Invalid format",
            "suggestion": "Use valid email address",
        }
        exc = ValidationError(
            message="Validation failed",
            details=details,
        )
        
        assert exc.details == details
    
    def test_error_response_includes_details(self):
        """ErrorResponse should include details if provided."""
        details = {"field": "username", "error": "Too short"}
        exc = ValidationError(
            message="Validation failed",
            details=details,
        )
        
        detail = exc.to_error_detail()
        assert detail.details == details


class TestErrorSeverityLevels:
    """Test error severity levels."""
    
    def test_severity_enum_values(self):
        """Severity levels should be valid strings."""
        assert ErrorSeverity.INFO.value == "info"
        assert ErrorSeverity.WARNING.value == "warning"
        assert ErrorSeverity.ERROR.value == "error"
        assert ErrorSeverity.CRITICAL.value == "critical"
    
    def test_error_severity_by_type(self):
        """Different error types should have appropriate severity."""
        severity_tests = [
            (AuthenticationError(), ErrorSeverity.WARNING),
            (ValidationError(), ErrorSeverity.WARNING),
            (NotFoundError(), ErrorSeverity.INFO),
            (RateLimitError(), ErrorSeverity.WARNING),
            (DatabaseError(), ErrorSeverity.ERROR),
            (InternalServerError(), ErrorSeverity.CRITICAL),
        ]
        
        for exc, expected_severity in severity_tests:
            assert exc.severity == expected_severity


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

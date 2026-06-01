"""
Unit tests for authentication module.
Tests JWT token generation, validation, and error handling.
"""

import pytest
from datetime import datetime, timedelta, timezone

from services.gateway.src.auth import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from services.gateway.src.config import Settings
from services.gateway.src.errors import AuthenticationError, ErrorCode
from services.gateway.src.schemas import UserPublic


@pytest.fixture
def test_settings():
    """Test settings with secure JWT secret."""
    return Settings(
        jwt_secret="test-secret-key-for-unit-tests-only",
        access_token_minutes=60,
        environment="test",
    )


@pytest.fixture
def test_user():
    """Test user for authentication tests."""
    return UserPublic(
        id="test-user-123",
        email="test@example.com",
        full_name="Test User",
        role="user",
        created_at=datetime.now(timezone.utc).isoformat(),
    )


class TestPasswordHashing:
    """Test password hashing and verification."""
    
    def test_hash_password_creates_valid_hash(self):
        """Hash should create a bcrypt-compatible hash."""
        password = "my-secure-password-123"
        hashed = hash_password(password)
        
        assert hashed != password
        assert "$" in hashed  # Bcrypt format check
        assert len(hashed) > 20
    
    def test_verify_password_success(self):
        """Verify password should match correct password."""
        password = "my-secure-password-123"
        hashed = hash_password(password)
        
        assert verify_password(password, hashed) is True
    
    def test_verify_password_failure(self):
        """Verify password should fail for incorrect password."""
        password = "my-secure-password-123"
        wrong_password = "wrong-password"
        hashed = hash_password(password)
        
        assert verify_password(wrong_password, hashed) is False
    
    def test_hash_changes_per_password(self):
        """Each password hash should be unique (due to salt)."""
        password = "same-password"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        
        assert hash1 != hash2  # Different salts
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True


class TestJWTTokens:
    """Test JWT token creation and validation."""
    
    def test_create_access_token_valid(self, test_user, test_settings):
        """Token creation should produce valid JWT."""
        token = create_access_token(test_user, test_settings)
        
        assert token is not None
        assert isinstance(token, str)
        assert token.count(".") == 2  # JWT has 3 parts
    
    def test_decode_access_token_valid(self, test_user, test_settings):
        """Decoding valid token should return payload."""
        token = create_access_token(test_user, test_settings)
        payload = decode_access_token(token, test_settings)
        
        assert payload["sub"] == test_user.id
        assert payload["email"] == test_user.email
        assert payload["role"] == test_user.role
        assert "exp" in payload
        assert "iat" in payload
        assert "jti" in payload
    
    def test_decode_access_token_invalid_signature(self, test_user, test_settings):
        """Decoding token with wrong secret should raise error."""
        token = create_access_token(test_user, test_settings)
        wrong_settings = Settings(
            jwt_secret="different-secret",
            access_token_minutes=60,
            environment="test",
        )
        
        with pytest.raises(AuthenticationError) as exc_info:
            decode_access_token(token, wrong_settings)
        
        assert exc_info.value.code == ErrorCode.AUTH_TOKEN_INVALID
    
    def test_decode_access_token_expired(self, test_user, test_settings):
        """Decoding expired token should raise error."""
        # Create settings with past expiration
        from services.gateway.src.auth import _b64encode
        import json
        import hashlib
        import hmac
        
        # Create token manually with past expiration
        header = {"alg": "HS256", "typ": "JWT"}
        expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        payload = {
            "sub": test_user.id,
            "email": test_user.email,
            "role": test_user.role,
            "exp": int(expires_at.timestamp()),
            "iat": int(datetime.now(timezone.utc).timestamp()),
            "jti": "test-jti",
        }
        
        encoded_header = _b64encode(json.dumps(header, separators=(",", ":")).encode())
        encoded_payload = _b64encode(json.dumps(payload, separators=(",", ":")).encode())
        signing_input = f"{encoded_header}.{encoded_payload}".encode()
        signature = hmac.new(
            test_settings.jwt_secret.encode(),
            signing_input,
            hashlib.sha256,
        ).digest()
        expired_token = f"{encoded_header}.{encoded_payload}.{_b64encode(signature)}"
        
        with pytest.raises(AuthenticationError) as exc_info:
            decode_access_token(expired_token, test_settings)
        
        assert exc_info.value.code == ErrorCode.AUTH_TOKEN_EXPIRED
    
    def test_decode_access_token_malformed(self, test_settings):
        """Decoding malformed token should raise error."""
        malformed_token = "not.a.valid.jwt.token.structure"
        
        with pytest.raises(AuthenticationError) as exc_info:
            decode_access_token(malformed_token, test_settings)
        
        assert exc_info.value.code == ErrorCode.AUTH_TOKEN_INVALID


class TestTokenClaims:
    """Test JWT claim validation."""
    
    def test_token_contains_required_claims(self, test_user, test_settings):
        """Token should contain all required claims."""
        token = create_access_token(test_user, test_settings)
        payload = decode_access_token(token, test_settings)
        
        required_claims = ["sub", "email", "role", "exp", "iat", "jti"]
        for claim in required_claims:
            assert claim in payload, f"Missing required claim: {claim}"
    
    def test_token_subject_matches_user_id(self, test_user, test_settings):
        """Token 'sub' claim should match user ID."""
        token = create_access_token(test_user, test_settings)
        payload = decode_access_token(token, test_settings)
        
        assert payload["sub"] == test_user.id
    
    def test_token_expiration_in_future(self, test_user, test_settings):
        """Token expiration should be in the future."""
        token = create_access_token(test_user, test_settings)
        payload = decode_access_token(token, test_settings)
        
        exp_time = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        now = datetime.now(timezone.utc)
        
        assert exp_time > now


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

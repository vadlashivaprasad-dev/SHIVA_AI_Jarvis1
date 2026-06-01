# services/gateway/src/middleware/auth.py
"""
Authentication middleware - JWT validation and user context
"""

import logging
from datetime import datetime, timedelta
from typing import Optional
from uuid import uuid4

import jwt
from fastapi import HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from src.config import settings

logger = logging.getLogger(__name__)

security = HTTPBearer()


class TokenPayload:
    """JWT token payload"""
    def __init__(self, user_id: str, role: str, email: str, exp: int):
        self.user_id = user_id
        self.role = role
        self.email = email
        self.exp = exp


class JWTManager:
    """JWT token management"""
    
    @staticmethod
    def create_access_token(user_id: str, role: str, email: str, expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token"""
        if expires_delta is None:
            expires_delta = timedelta(hours=settings.JWT_EXPIRATION_HOURS)
        
        expire = datetime.utcnow() + expires_delta
        payload = {
            "sub": user_id,
            "role": role,
            "email": email,
            "exp": int(expire.timestamp()),
            "iat": int(datetime.utcnow().timestamp()),
            "jti": str(uuid4()),  # JWT ID for revocation
        }
        
        token = jwt.encode(
            payload,
            settings.JWT_SECRET,
            algorithm=settings.JWT_ALGORITHM
        )
        return token
    
    @staticmethod
    def create_refresh_token(user_id: str) -> str:
        """Create JWT refresh token"""
        expires_delta = timedelta(days=settings.JWT_REFRESH_EXPIRATION_DAYS)
        expire = datetime.utcnow() + expires_delta
        
        payload = {
            "sub": user_id,
            "type": "refresh",
            "exp": int(expire.timestamp()),
            "iat": int(datetime.utcnow().timestamp()),
        }
        
        token = jwt.encode(
            payload,
            settings.JWT_SECRET,
            algorithm=settings.JWT_ALGORITHM
        )
        return token
    
    @staticmethod
    def decode_token(token: str) -> TokenPayload:
        """Decode and validate JWT token"""
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET,
                algorithms=[settings.JWT_ALGORITHM]
            )
            
            user_id: str = payload.get("sub")
            role: str = payload.get("role", "user")
            email: str = payload.get("email")
            exp: int = payload.get("exp")
            
            if user_id is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token: missing user ID",
                )
            
            return TokenPayload(user_id=user_id, role=role, email=email, exp=exp)
        
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
            )
        except jwt.InvalidTokenError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}",
            )


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Authentication middleware - validates JWT tokens
    Adds user context to request
    """
    
    # Public routes that don't require auth
    PUBLIC_ROUTES = {
        "/docs",
        "/redoc",
        "/openapi.json",
        "/",
        "/api/v1/auth/signup",
        "/api/v1/auth/login",
        "/api/v1/auth/refresh",
        "/api/v1/health",
        "/health",
        "/health/live",
        "/health/ready",
    }
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request and validate authentication"""
        
        # Skip auth for public routes
        if request.url.path in self.PUBLIC_ROUTES or request.url.path.startswith("/docs"):
            return await call_next(request)
        
        # Extract token from Authorization header
        token = self._extract_token(request)
        
        if not token:
            return self._unauthorized_response("Missing authentication token")
        
        try:
            # Validate token
            payload = JWTManager.decode_token(token)
            
            # Add user context to request
            request.state.user_id = payload.user_id
            request.state.user_role = payload.role
            request.state.user_email = payload.email
            
            logger.debug(f"Authenticated user: {payload.user_id} ({payload.role})")
            
        except HTTPException as e:
            return self._unauthorized_response(e.detail)
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return self._unauthorized_response("Authentication failed")
        
        return await call_next(request)
    
    @staticmethod
    def _extract_token(request: Request) -> Optional[str]:
        """Extract JWT token from Authorization header"""
        auth_header = request.headers.get("Authorization", "")
        
        if not auth_header.startswith("Bearer "):
            return None
        
        return auth_header.replace("Bearer ", "")
    
    @staticmethod
    def _unauthorized_response(detail: str) -> Response:
        """Return 401 unauthorized response"""
        return Response(
            content=f'{{"error": "{detail}"}}',
            status_code=status.HTTP_401_UNAUTHORIZED,
            media_type="application/json",
        )


def get_current_user(request: Request) -> dict:
    """Dependency to get current user from request context"""
    user_id = getattr(request.state, "user_id", None)
    user_role = getattr(request.state, "user_role", None)
    user_email = getattr(request.state, "user_email", None)
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    
    return {
        "user_id": user_id,
        "role": user_role,
        "email": user_email,
    }

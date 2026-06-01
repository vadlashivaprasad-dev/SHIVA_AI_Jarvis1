"""
Enhanced validation schemas with sanitization and security.
"""

import html
import re
from typing import Any, Optional

from pydantic import BaseModel, Field, EmailStr, field_validator


# Email validation regex (RFC 5322 simplified)
EMAIL_REGEX = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"


class EnhancedUserCreate(BaseModel):
    """User registration with enhanced validation."""
    
    email: EmailStr = Field(description="User email address")
    password: str = Field(
        min_length=8,
        max_length=128,
        description="Password (8-128 chars, must include uppercase, lowercase, digit, special char)"
    )
    full_name: Optional[str] = Field(
        None,
        max_length=200,
        description="User full name"
    )
    
    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength."""
        errors = []
        
        if len(v) < 8:
            errors.append("At least 8 characters")
        if not any(c.isupper() for c in v):
            errors.append("At least one uppercase letter")
        if not any(c.islower() for c in v):
            errors.append("At least one lowercase letter")
        if not any(c.isdigit() for c in v):
            errors.append("At least one digit")
        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in v):
            errors.append("At least one special character")
        
        if errors:
            raise ValueError(f"Password must have: {', '.join(errors)}")
        
        return v
    
    @field_validator("full_name")
    @classmethod
    def sanitize_full_name(cls, v: Optional[str]) -> Optional[str]:
        """Sanitize full name."""
        if v is None:
            return None
        
        # Remove HTML and limit length
        v = html.escape(v)[:200]
        
        # Only allow alphanumeric, spaces, hyphens, apostrophes
        if not re.match(r"^[a-zA-Z0-9\s\-']*$", v):
            raise ValueError("Name contains invalid characters")
        
        return v


class EnhancedUserLogin(BaseModel):
    """User login with validation."""
    
    email: EmailStr
    password: str = Field(min_length=1)


class EnhancedMessageRequest(BaseModel):
    """Chat message with validation and sanitization."""
    
    conversation_id: str = Field(min_length=1, max_length=100)
    content: str = Field(
        min_length=1,
        max_length=8000,
        description="Message content"
    )
    model: Optional[str] = None
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, ge=1, le=4096)
    
    @field_validator("content")
    @classmethod
    def sanitize_content(cls, v: str) -> str:
        """Sanitize message content to prevent XSS."""
        # Escape HTML entities
        v = html.escape(v)
        
        # Remove null bytes
        v = v.replace("\x00", "")
        
        # Limit length
        return v[:8000]
    
    @field_validator("conversation_id")
    @classmethod
    def validate_conversation_id(cls, v: str) -> str:
        """Validate conversation ID format."""
        if not re.match(r"^[a-zA-Z0-9\-_]{1,100}$", v):
            raise ValueError("Invalid conversation ID format")
        return v


class EnhancedDocumentCreate(BaseModel):
    """Document upload with validation."""
    
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=1_000_000)  # 1MB
    source: str = Field(default="manual", max_length=120)
    tags: list[str] = Field(default_factory=list, max_length=10)
    add_to_memory: bool = True
    
    @field_validator("title")
    @classmethod
    def sanitize_title(cls, v: str) -> str:
        """Sanitize title."""
        v = html.escape(v)[:200]
        
        # Remove special characters
        if not re.match(r"^[a-zA-Z0-9\s\-_.,:;]+$", v):
            raise ValueError("Title contains invalid characters")
        
        return v
    
    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        """Validate and sanitize content."""
        if len(v.encode("utf-8")) > 1_000_000:
            raise ValueError("Content exceeds 1MB limit")
        
        return v[:1_000_000]
    
    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: list[str]) -> list[str]:
        """Validate tags."""
        if len(v) > 10:
            raise ValueError("Maximum 10 tags allowed")
        
        validated = []
        for tag in v:
            if not tag or len(tag) > 50:
                continue
            
            # Sanitize tag
            tag = html.escape(tag)
            if re.match(r"^[a-zA-Z0-9\-_]+$", tag):
                validated.append(tag)
        
        return validated


class EnhancedMemoryCreate(BaseModel):
    """Memory entry with validation."""
    
    content: str = Field(min_length=1, max_length=5000)
    category: str = Field(
        default="semantic",
        regex="^(semantic|episodic|procedural)$"
    )
    source: str = Field(
        default="manual",
        max_length=120
    )
    conversation_id: Optional[str] = None
    
    @field_validator("content")
    @classmethod
    def sanitize_content(cls, v: str) -> str:
        """Sanitize memory content."""
        return html.escape(v)[:5000]


class EnhancedConversationCreate(BaseModel):
    """Conversation with validation."""
    
    title: Optional[str] = Field(None, max_length=200)
    system_prompt: Optional[str] = Field(None, max_length=2000)
    model: Optional[str] = None
    
    @field_validator("title")
    @classmethod
    def sanitize_title(cls, v: Optional[str]) -> Optional[str]:
        """Sanitize conversation title."""
        if v is None:
            return None
        return html.escape(v)[:200]
    
    @field_validator("system_prompt")
    @classmethod
    def sanitize_system_prompt(cls, v: Optional[str]) -> Optional[str]:
        """Sanitize system prompt."""
        if v is None:
            return None
        return html.escape(v)[:2000]


class RateLimitInfo(BaseModel):
    """Rate limit information response."""
    
    limit: int
    remaining: int
    reset_at: str
    retry_after: Optional[int] = None


class ErrorResponse(BaseModel):
    """Standardized error response."""
    
    code: str
    message: str
    severity: str
    request_id: str
    timestamp: str
    status_code: int
    user_message: Optional[str] = None
    details: Optional[dict[str, Any]] = None


class HealthResponse(BaseModel):
    """Health check response."""
    
    status: str
    version: str
    timestamp: str
    database: str
    cache: str
    dependencies: dict[str, str]

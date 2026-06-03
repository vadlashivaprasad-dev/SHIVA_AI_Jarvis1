import os
from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Application metadata
    app_name: str = "ShivaAI Jarvis"
    app_version: str = "1.0.0"
    
    # Environment and deployment
    environment: str = Field(default="development", alias="ENVIRONMENT")
    debug: bool = Field(default=False, alias="DEBUG")
    
    # Database configuration (PostgreSQL required for production)
    database_url: str = Field(
        default="sqlite:///./data/gateway.db", 
        alias="DATABASE_URL",
        description="PostgreSQL connection string for production"
    )
    database_pool_size: int = Field(default=20, alias="DATABASE_POOL_SIZE")
    database_pool_recycle: int = Field(default=3600, alias="DATABASE_POOL_RECYCLE")
    database_echo: bool = Field(default=False, alias="DATABASE_ECHO")
    
    # Security - MUST be set in environment for production
    jwt_secret: str = Field(alias="JWT_SECRET", description="CRITICAL: Must be set in .env")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_minutes: int = Field(default=60, alias="ACCESS_TOKEN_MINUTES")
    refresh_token_days: int = Field(default=7, alias="REFRESH_TOKEN_DAYS")
    
    # Session and rate limiting
    session_timeout_minutes: int = Field(default=30, alias="SESSION_TIMEOUT_MINUTES")
    max_login_attempts: int = Field(default=5, alias="MAX_LOGIN_ATTEMPTS")
    lockout_duration_minutes: int = Field(default=15, alias="LOCKOUT_DURATION_MINUTES")
    
    # Chat and public access
    allow_public_chat: bool = Field(default=False, alias="ALLOW_PUBLIC_CHAT")
    max_message_length: int = Field(default=8000, alias="MAX_MESSAGE_LENGTH")
    
    # LLM provider configuration
    llm_provider: str = Field(default="local", alias="LLM_PROVIDER")
    llm_timeout_seconds: float = Field(default=45.0, alias="LLM_TIMEOUT_SECONDS")
    llm_max_retries: int = Field(default=3, alias="LLM_MAX_RETRIES")

    # Ollama configuration (open-source local LLMs)
    ollama_base_url: str = Field(default="http://localhost:11434", alias="OLLAMA_BASE_URL")
    ollama_model: str = Field(default="llama3", alias="OLLAMA_MODEL")

    
    # OpenAI configuration
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_api_base: str = Field(default="https://api.openai.com/v1", alias="OPENAI_API_BASE")
    openai_model: str = Field(default="gpt-4-turbo", alias="OPENAI_MODEL")
    openai_timeout: float = Field(default=45.0, alias="OPENAI_TIMEOUT")
    
    # Vector database (Qdrant)
    qdrant_url: str = Field(default="http://localhost:6333", alias="QDRANT_URL")
    qdrant_api_key: str = Field(default="", alias="QDRANT_API_KEY")
    
    # Redis cache
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    
    # CORS and API configuration
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173"],
        alias="CORS_ORIGINS",
    )
    api_prefix: str = Field(default="/api/v1", alias="API_PREFIX")
    
    # Logging configuration
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_format: str = Field(default="json", alias="LOG_FORMAT")
    
    # Security headers
    enable_cors: bool = Field(default=True, alias="ENABLE_CORS")
    enable_https_redirect: bool = Field(default=False, alias="ENABLE_HTTPS_REDIRECT")
    allowed_hosts: List[str] = Field(default=["*"], alias="ALLOWED_HOSTS")
    
    # Feature flags
    enable_vector_search: bool = Field(default=True, alias="ENABLE_VECTOR_SEARCH")
    enable_audit_logging: bool = Field(default=True, alias="ENABLE_AUDIT_LOGGING")
    enable_request_signing: bool = Field(default=False, alias="ENABLE_REQUEST_SIGNING")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        populate_by_name=True,
        case_sensitive=False,
        extra="ignore",
    )
    
    @field_validator("jwt_secret")
    @classmethod
    def validate_jwt_secret(cls, v: str) -> str:
        """Ensure JWT secret is secure for production."""
        if not v or v == "dev-secret-change-me":
            if os.getenv("ENVIRONMENT") == "production":
                raise ValueError(
                    "JWT_SECRET must be set to a secure value in production. "
                    "Generate a secure secret with: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
                )
        return v
    
    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: any) -> List[str]:
        """Parse CORS origins from comma-separated string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Validate database URL for production usage."""
        if "production" in str(os.getenv("ENVIRONMENT", "")):
            if not v.startswith("postgresql"):
                raise ValueError(
                    "Production environment requires PostgreSQL. "
                    "Set DATABASE_URL=postgresql://user:password@host/dbname"
                )
        return v


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()

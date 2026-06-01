# services/gateway/src/config.py
"""
Configuration management for ShivaAI Jarvis
Handles environment variables and settings
"""

from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables
    """

    # ========================================================================
    # APPLICATION
    # ========================================================================

    APP_NAME: str = "ShivaAI Jarvis"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    DEBUG: bool = Field(default=True, env="DEBUG")
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")

    # ========================================================================
    # SERVER
    # ========================================================================

    HOST: str = Field(default="0.0.0.0", env="HOST")
    PORT: int = Field(default=8000, env="PORT")
    RELOAD: bool = Field(default=True, env="RELOAD")
    WORKERS: int = Field(default=4, env="WORKERS")

    # ========================================================================
    # DATABASE
    # ========================================================================

    DATABASE_URL: str = Field(
        default="postgresql://shivaai:shivaai_dev_pass@localhost:5432/shivaai_db",
        env="DATABASE_URL",
    )
    SQLALCHEMY_ECHO: bool = Field(default=False, env="SQLALCHEMY_ECHO")
    SQLALCHEMY_POOL_SIZE: int = Field(default=20, env="SQLALCHEMY_POOL_SIZE")
    SQLALCHEMY_POOL_RECYCLE: int = Field(default=3600, env="SQLALCHEMY_POOL_RECYCLE")

    # ========================================================================
    # CACHE & SESSION
    # ========================================================================

    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        env="REDIS_URL",
    )
    REDIS_MAX_CONNECTIONS: int = Field(default=50, env="REDIS_MAX_CONNECTIONS")
    SESSION_EXPIRE_SECONDS: int = Field(default=604800, env="SESSION_EXPIRE_SECONDS")  # 7 days

    # ========================================================================
    # VECTOR & GRAPH DATABASES
    # ========================================================================

    QDRANT_URL: str = Field(
        default="http://localhost:6333",
        env="QDRANT_URL",
    )
    QDRANT_API_KEY: str = Field(default="", env="QDRANT_API_KEY")
    QDRANT_TIMEOUT: int = Field(default=30, env="QDRANT_TIMEOUT")

    NEO4J_URI: str = Field(
        default="bolt://localhost:7687",
        env="NEO4J_URI",
    )
    NEO4J_AUTH: str = Field(
        default="neo4j/password",
        env="NEO4J_AUTH",
    )

    # ========================================================================
    # MESSAGE QUEUE
    # ========================================================================

    KAFKA_BOOTSTRAP_SERVERS: str = Field(
        default="localhost:9092",
        env="KAFKA_BOOTSTRAP_SERVERS",
    )
    KAFKA_TOPIC_PREFIX: str = Field(default="shivaai", env="KAFKA_TOPIC_PREFIX")

    # ========================================================================
    # SECURITY & AUTHENTICATION
    # ========================================================================

    JWT_SECRET: str = Field(
        default="dev-secret-change-in-production",
        env="JWT_SECRET",
    )
    JWT_ALGORITHM: str = Field(default="HS256", env="JWT_ALGORITHM")
    JWT_EXPIRATION_HOURS: int = Field(default=1, env="JWT_EXPIRATION_HOURS")
    JWT_REFRESH_EXPIRATION_DAYS: int = Field(
        default=7, env="JWT_REFRESH_EXPIRATION_DAYS"
    )

    # CORS
    ALLOWED_HOSTS: List[str] = Field(
        default=["*"],
        env="ALLOWED_HOSTS",
    )
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:3001"],
        env="CORS_ORIGINS",
    )

    # ========================================================================
    # EXTERNAL APIS
    # ========================================================================

    # OpenAI
    OPENAI_API_KEY: str = Field(default="", env="OPENAI_API_KEY")
    OPENAI_ORG_ID: str = Field(default="", env="OPENAI_ORG_ID")
    OPENAI_API_BASE: str = Field(
        default="https://api.openai.com/v1",
        env="OPENAI_API_BASE",
    )
    OPENAI_REQUEST_TIMEOUT: int = Field(default=60, env="OPENAI_REQUEST_TIMEOUT")

    # Anthropic
    ANTHROPIC_API_KEY: str = Field(default="", env="ANTHROPIC_API_KEY")
    ANTHROPIC_API_BASE: str = Field(
        default="https://api.anthropic.com",
        env="ANTHROPIC_API_BASE",
    )

    # Ollama (Local)
    OLLAMA_BASE_URL: str = Field(
        default="http://localhost:11434",
        env="OLLAMA_BASE_URL",
    )

    # vLLM (Local)
    VLLM_BASE_URL: str = Field(
        default="http://localhost:8000",
        env="VLLM_BASE_URL",
    )

    # ========================================================================
    # LLM CONFIGURATION
    # ========================================================================

    DEFAULT_LLM_MODEL: str = Field(default="gpt-4", env="DEFAULT_LLM_MODEL")
    DEFAULT_TEMPERATURE: float = Field(default=0.7, env="DEFAULT_TEMPERATURE")
    DEFAULT_MAX_TOKENS: int = Field(default=2000, env="DEFAULT_MAX_TOKENS")
    CONTEXT_WINDOW_SIZE: int = Field(default=4096, env="CONTEXT_WINDOW_SIZE")

    # ========================================================================
    # EMBEDDINGS
    # ========================================================================

    EMBEDDINGS_MODEL: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        env="EMBEDDINGS_MODEL",
    )
    EMBEDDINGS_DIMENSION: int = Field(default=384, env="EMBEDDINGS_DIMENSION")
    EMBEDDINGS_BATCH_SIZE: int = Field(default=32, env="EMBEDDINGS_BATCH_SIZE")

    # ========================================================================
    # VOICE
    # ========================================================================

    SPEECH_PROVIDER: str = Field(default="openai", env="SPEECH_PROVIDER")  # openai, elevenlabs
    VOICE_SAMPLE_RATE: int = Field(default=16000, env="VOICE_SAMPLE_RATE")
    VOICE_CHUNK_SIZE: int = Field(default=2048, env="VOICE_CHUNK_SIZE")
    VAD_THRESHOLD: float = Field(default=0.5, env="VAD_THRESHOLD")

    # ========================================================================
    # RATE LIMITING
    # ========================================================================

    RATE_LIMIT_ENABLED: bool = Field(default=True, env="RATE_LIMIT_ENABLED")
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = Field(
        default=100, env="RATE_LIMIT_REQUESTS_PER_MINUTE"
    )
    RATE_LIMIT_REQUESTS_PER_HOUR: int = Field(
        default=5000, env="RATE_LIMIT_REQUESTS_PER_HOUR"
    )

    # ========================================================================
    # MONITORING & OBSERVABILITY
    # ========================================================================

    PROMETHEUS_ENABLED: bool = Field(default=True, env="PROMETHEUS_ENABLED")
    PROMETHEUS_PORT: int = Field(default=8001, env="PROMETHEUS_PORT")
    SENTRY_DSN: str = Field(default="", env="SENTRY_DSN")
    OTEL_ENABLED: bool = Field(default=False, env="OTEL_ENABLED")

    # ========================================================================
    # FEATURES
    # ========================================================================

    FEATURE_TRADING: bool = Field(default=True, env="FEATURE_TRADING")
    FEATURE_CODE_EXECUTION: bool = Field(default=True, env="FEATURE_CODE_EXECUTION")
    FEATURE_VOICE: bool = Field(default=True, env="FEATURE_VOICE")
    FEATURE_LEARNING: bool = Field(default=True, env="FEATURE_LEARNING")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Global settings instance
settings = Settings()

# ============================================================================
# ENVIRONMENT-SPECIFIC CONFIGURATIONS
# ============================================================================


def get_settings() -> Settings:
    """Get current settings"""
    return settings


def is_production() -> bool:
    """Check if running in production"""
    return settings.ENVIRONMENT == "production"


def is_development() -> bool:
    """Check if running in development"""
    return settings.ENVIRONMENT == "development"


def is_testing() -> bool:
    """Check if running in test mode"""
    return settings.ENVIRONMENT == "testing"

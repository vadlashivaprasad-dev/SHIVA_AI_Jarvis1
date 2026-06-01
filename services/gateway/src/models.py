"""
SQLAlchemy database models for ShivaAI Jarvis.
Supports both PostgreSQL (production) and SQLite (development).
"""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    create_engine,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.pool import NullPool, QueuePool

from .config import get_settings

Base = declarative_base()


def get_db_engine():
    """Create database engine based on environment configuration."""
    settings = get_settings()
    
    # Use NullPool for SQLite in development to avoid threading issues
    # Use QueuePool for PostgreSQL in production
    if "postgresql" in settings.database_url:
        pool_class = QueuePool
        pool_kwargs = {
            "pool_size": settings.database_pool_size,
            "max_overflow": 20,
            "pool_recycle": settings.database_pool_recycle,
            "pool_pre_ping": True,  # Test connections before using
        }
    else:
        pool_class = NullPool
        pool_kwargs = {}
    
    engine = create_engine(
        settings.database_url,
        echo=settings.database_echo,
        poolclass=pool_class,
        **pool_kwargs,
    )
    
    return engine


def get_db_session():
    """Create database session factory."""
    engine = get_db_engine()
    return sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )


# Models
class User(Base):
    """User account model."""
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255))
    role = Column(String(50), default="user", nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    
    # Relationships
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_users_email", "email"),
        Index("idx_users_role", "role"),
        Index("idx_users_created_at", "created_at"),
    )


class UserSession(Base):
    """User session tracking for authentication."""
    __tablename__ = "user_sessions"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    token_jti = Column(String(36), unique=True, nullable=False)
    ip_address = Column(String(45))  # IPv6 support
    user_agent = Column(String(500))
    device_fingerprint = Column(String(255))
    is_valid = Column(Boolean, default=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    
    # Relationships
    user = relationship("User", back_populates="sessions")
    
    __table_args__ = (
        Index("idx_sessions_user_id", "user_id"),
        Index("idx_sessions_expires_at", "expires_at"),
    )


class Conversation(Base):
    """Chat conversation/session model."""
    __tablename__ = "conversations"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    system_prompt = Column(Text)
    model = Column(String(100))
    metadata = Column(JSON, default=dict)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    
    # Relationships
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_conversations_user_id", "user_id"),
        Index("idx_conversations_created_at", "created_at"),
    )


class Message(Base):
    """Chat message model."""
    __tablename__ = "messages"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    conversation_id = Column(String(36), ForeignKey("conversations.id"), nullable=False)
    role = Column(String(20), nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=False)
    metadata = Column(JSON, default=dict)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    
    __table_args__ = (
        Index("idx_messages_conversation_id", "conversation_id"),
        Index("idx_messages_created_at", "created_at"),
    )


class MemoryEntry(Base):
    """Semantic memory store."""
    __tablename__ = "memory_entries"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"))
    content = Column(Text, nullable=False)
    category = Column(String(100), nullable=False)
    source = Column(String(100), nullable=False)
    embedding_vector = Column(String(50000))  # Stored as JSON for simplicity
    relevance_score = Column(String(10))
    metadata = Column(JSON, default=dict)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    
    __table_args__ = (
        Index("idx_memory_category", "category"),
        Index("idx_memory_source", "source"),
        Index("idx_memory_created_at", "created_at"),
    )


class Document(Base):
    """Ingested documents for knowledge base."""
    __tablename__ = "documents"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    title = Column(String(255), nullable=False)
    source = Column(String(500), nullable=False)
    file_path = Column(String(500))
    file_type = Column(String(50))
    metadata = Column(JSON, default=dict)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    
    # Relationships
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_documents_source", "source"),
        Index("idx_documents_created_at", "created_at"),
    )


class DocumentChunk(Base):
    """Document chunks for vector search."""
    __tablename__ = "document_chunks"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    document_id = Column(String(36), ForeignKey("documents.id"), nullable=False)
    chunk_index = Column(String(10), nullable=False)
    content = Column(Text, nullable=False)
    embedding_vector = Column(String(50000))  # Qdrant will store actual vectors
    metadata = Column(JSON, default=dict)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    
    # Relationships
    document = relationship("Document", back_populates="chunks")
    
    __table_args__ = (
        Index("idx_chunks_document_id", "document_id"),
    )


class AuditLog(Base):
    """Audit logging for compliance and debugging."""
    __tablename__ = "audit_logs"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"))
    action = Column(String(100), nullable=False)
    resource_type = Column(String(100))
    resource_id = Column(String(36))
    changes = Column(JSON, default=dict)
    ip_address = Column(String(45))
    user_agent = Column(String(500))
    status = Column(String(20))  # "success" or "failure"
    error_message = Column(Text)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    
    __table_args__ = (
        Index("idx_audit_user_id", "user_id"),
        Index("idx_audit_action", "action"),
        Index("idx_audit_created_at", "created_at"),
    )

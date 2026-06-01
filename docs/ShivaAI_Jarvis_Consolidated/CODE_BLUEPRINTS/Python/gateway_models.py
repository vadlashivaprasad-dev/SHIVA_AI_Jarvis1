# services/gateway/src/models.py
"""
SQLAlchemy ORM models for ShivaAI Jarvis
Database schema definitions
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    ARRAY,
    Numeric,
    Enum as SQLEnum,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import enum

Base = declarative_base()


# ============================================================================
# ENUMS
# ============================================================================

class UserRole(str, enum.Enum):
    """User role enumeration"""
    ADMIN = "admin"
    USER = "user"
    ANALYST = "analyst"
    TRADER = "trader"


class MessageRole(str, enum.Enum):
    """Chat message role"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class WorkflowStatus(str, enum.Enum):
    """Workflow execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TradeStatus(str, enum.Enum):
    """Trade status"""
    PENDING = "pending"
    APPROVED = "approved"
    EXECUTED = "executed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


# ============================================================================
# USERS & AUTHENTICATION
# ============================================================================

class User(Base):
    """User model"""
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=True, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    role = Column(SQLEnum(UserRole), default=UserRole.USER, nullable=False)
    
    # Profile and preferences
    profile = Column(JSON, nullable=True)  # {communication_style, expertise, preferences}
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_login = Column(DateTime, nullable=True)
    
    # Relationships
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    memory_entries = relationship("MemoryEntry", back_populates="user", cascade="all, delete-orphan")
    feedback = relationship("UserFeedback", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User {self.email}>"


class Session(Base):
    """User session model"""
    __tablename__ = "sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    token = Column(String(1024), unique=True, nullable=False)
    refresh_token = Column(String(1024), nullable=True)
    
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    user = relationship("User")


# ============================================================================
# CONVERSATIONS & MESSAGES
# ============================================================================

class Conversation(Base):
    """Conversation/chat session model"""
    __tablename__ = "conversations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    
    title = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    
    # Configuration
    system_prompt = Column(Text, nullable=True)
    model_config = Column(JSON, nullable=True)  # {model, temperature, max_tokens}
    memory_ids = Column(ARRAY(String), nullable=True)  # Related memory entries
    
    # Status
    is_archived = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Conversation {self.id}>"


class Message(Base):
    """Chat message model"""
    __tablename__ = "messages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    conversation_id = Column(String(36), ForeignKey("conversations.id"), nullable=False, index=True)
    
    role = Column(SQLEnum(MessageRole), nullable=False)
    content = Column(Text, nullable=False)
    
    # Metadata
    metadata = Column(JSON, nullable=True)  # tokens, model, latency, embedding
    artifacts = Column(ARRAY(String), nullable=True)  # Artifact IDs
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    feedback = relationship("UserFeedback", back_populates="message", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Message {self.id}>"


# ============================================================================
# MEMORY & KNOWLEDGE
# ============================================================================

class MemoryEntry(Base):
    """Semantic/episodic memory entry"""
    __tablename__ = "memory_entries"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    
    category = Column(String(50), nullable=False)  # semantic, episodic, relationship, strategic
    content = Column(Text, nullable=False)
    
    # Metadata
    metadata = Column(JSON, nullable=True)  # source, domain, confidence
    
    # TTL - Automatic expiration
    expires_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="memory_entries")
    
    def __repr__(self):
        return f"<MemoryEntry {self.id}>"


class Document(Base):
    """Uploaded document for knowledge base"""
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    file_type = Column(String(50), nullable=False)  # pdf, docx, txt, etc
    content = Column(Text, nullable=True)
    
    chunks = Column(Integer, nullable=True)  # Number of text chunks
    metadata = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


# ============================================================================
# TRADING
# ============================================================================

class Portfolio(Base):
    """Trading portfolio"""
    __tablename__ = "portfolios"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Financial
    initial_balance = Column(Numeric(15, 2), nullable=False)
    current_balance = Column(Numeric(15, 2), nullable=False)
    risk_profile = Column(String(50), nullable=True)  # conservative, moderate, aggressive
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class Trade(Base):
    """Individual trade record"""
    __tablename__ = "trades"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    portfolio_id = Column(String(36), ForeignKey("portfolios.id"), nullable=False, index=True)
    
    symbol = Column(String(20), nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    side = Column(String(10), nullable=False)  # buy, sell
    
    # Strategy reference
    strategy_id = Column(String(36), nullable=True)
    
    # Approval
    approved_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    status = Column(SQLEnum(TradeStatus), default=TradeStatus.PENDING, nullable=False)
    
    # Results
    p_and_l = Column(Numeric(15, 2), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    executed_at = Column(DateTime, nullable=True)


# ============================================================================
# CODE & EXECUTION
# ============================================================================

class CodeSnippet(Base):
    """Code snippet execution history"""
    __tablename__ = "code_snippets"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    
    language = Column(String(50), nullable=False)  # python, javascript, etc
    code = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    
    tags = Column(ARRAY(String), nullable=True)
    
    # Metadata
    metadata = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


# ============================================================================
# WORKFLOWS
# ============================================================================

class Workflow(Base):
    """Automation workflow"""
    __tablename__ = "workflows"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Definition as JSON
    definition = Column(JSON, nullable=False)  # {triggers, nodes, edges}
    
    enabled = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class WorkflowExecution(Base):
    """Workflow execution record"""
    __tablename__ = "workflow_executions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    workflow_id = Column(String(36), ForeignKey("workflows.id"), nullable=False, index=True)
    
    status = Column(SQLEnum(WorkflowStatus), default=WorkflowStatus.PENDING, nullable=False)
    
    input_data = Column(JSON, nullable=True)
    output_data = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)


# ============================================================================
# AUDIT & FEEDBACK
# ============================================================================

class AuditLog(Base):
    """Immutable audit log - all system operations"""
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    
    action = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(50), nullable=False, index=True)
    resource_id = Column(String(36), nullable=True, index=True)
    
    changes = Column(JSON, nullable=True)  # {before, after}
    
    # Client info
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6
    user_agent = Column(Text, nullable=True)
    
    # Timestamp (cannot be changed once inserted)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    user = relationship("User", back_populates="audit_logs")
    
    def __repr__(self):
        return f"<AuditLog {self.action} {self.resource_type}>"


class UserFeedback(Base):
    """User feedback on AI responses"""
    __tablename__ = "user_feedback"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    message_id = Column(String(36), ForeignKey("messages.id"), nullable=True, index=True)
    
    # Feedback
    rating = Column(Integer, nullable=True)  # 1-5 or thumbs up/down
    correction = Column(Text, nullable=True)  # User's correction
    tags = Column(ARRAY(String), nullable=True)  # factually_wrong, unhelpful, etc
    
    # Context
    domain = Column(String(50), nullable=True)  # chat, trading, code, etc
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    user = relationship("User", back_populates="feedback")
    message = relationship("Message", back_populates="feedback")


# ============================================================================
# INDEXES FOR PERFORMANCE
# ============================================================================

# Most queries will need these indexes
__all__ = [
    "Base",
    "User",
    "Session",
    "Conversation",
    "Message",
    "MemoryEntry",
    "Document",
    "Portfolio",
    "Trade",
    "CodeSnippet",
    "Workflow",
    "WorkflowExecution",
    "AuditLog",
    "UserFeedback",
]

# services/gateway/src/routers/chat.py
"""
Chat router - conversation management and messaging API
Endpoint: /api/v1/chat
"""

import logging
from typing import Optional, List
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from src.db import get_db
from src.middleware.auth import get_current_user
from src.models import Conversation, Message, MessageRole, User
from src.services.llm_service import LLMService
from src.services.memory_service import MemoryService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])

# Service instances
llm_service = LLMService()
memory_service = MemoryService()


# ============================================================================
# PYDANTIC SCHEMAS
# ============================================================================

from pydantic import BaseModel


class MessageRequest(BaseModel):
    """Request schema for sending a message"""
    conversation_id: str
    content: str
    model: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "conversation_id": "conv-123",
                "content": "What is the weather like?",
                "model": "gpt-4",
                "temperature": 0.7,
                "max_tokens": 2000,
            }
        }


class MessageResponse(BaseModel):
    """Response schema for a message"""
    id: str
    conversation_id: str
    role: str
    content: str
    created_at: str
    metadata: Optional[dict] = None
    
    class Config:
        from_attributes = True


class ConversationCreate(BaseModel):
    """Request schema to create a conversation"""
    title: Optional[str] = None
    system_prompt: Optional[str] = None
    model: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "title": "Trading Strategy Discussion",
                "system_prompt": "You are an expert trading advisor",
                "model": "gpt-4",
            }
        }


class ConversationResponse(BaseModel):
    """Response schema for a conversation"""
    id: str
    user_id: str
    title: Optional[str]
    created_at: str
    updated_at: str
    message_count: Optional[int] = 0
    
    class Config:
        from_attributes = True


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post(
    "/sessions",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new conversation",
    description="Start a new chat conversation/session",
)
async def create_conversation(
    request: ConversationCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a new conversation session
    
    - **title**: Optional conversation title
    - **system_prompt**: Optional system prompt for the AI
    - **model**: Optional model selection (defaults to config)
    """
    try:
        conversation = Conversation(
            id=str(uuid4()),
            user_id=current_user["user_id"],
            title=request.title,
            system_prompt=request.system_prompt or "",
            model_config={
                "model": request.model,
            },
        )
        
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        
        logger.info(f"Created conversation {conversation.id} for user {current_user['user_id']}")
        
        return ConversationResponse(
            id=conversation.id,
            user_id=conversation.user_id,
            title=conversation.title,
            created_at=conversation.created_at.isoformat(),
            updated_at=conversation.updated_at.isoformat(),
            message_count=0,
        )
    
    except Exception as e:
        logger.error(f"Error creating conversation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create conversation",
        )


@router.get(
    "/sessions",
    response_model=List[ConversationResponse],
    summary="List user conversations",
    description="Get all conversations for the current user",
)
async def list_conversations(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List user's conversations with pagination
    
    - **skip**: Number of conversations to skip (default: 0)
    - **limit**: Maximum conversations to return (default: 20, max: 100)
    """
    try:
        conversations = db.query(Conversation).filter(
            Conversation.user_id == current_user["user_id"],
            Conversation.is_archived == False,
        ).order_by(
            Conversation.updated_at.desc()
        ).offset(skip).limit(limit).all()
        
        return [
            ConversationResponse(
                id=conv.id,
                user_id=conv.user_id,
                title=conv.title,
                created_at=conv.created_at.isoformat(),
                updated_at=conv.updated_at.isoformat(),
                message_count=len(conv.messages),
            )
            for conv in conversations
        ]
    
    except Exception as e:
        logger.error(f"Error listing conversations: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list conversations",
        )


@router.get(
    "/sessions/{conversation_id}",
    response_model=dict,
    summary="Get conversation details",
    description="Get a specific conversation with all its messages",
)
async def get_conversation(
    conversation_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get specific conversation with all messages"""
    try:
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user["user_id"],
        ).first()
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found",
            )
        
        messages = [
            {
                "id": msg.id,
                "role": msg.role.value,
                "content": msg.content,
                "created_at": msg.created_at.isoformat(),
            }
            for msg in conversation.messages
        ]
        
        return {
            "id": conversation.id,
            "user_id": conversation.user_id,
            "title": conversation.title,
            "messages": messages,
            "created_at": conversation.created_at.isoformat(),
            "updated_at": conversation.updated_at.isoformat(),
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting conversation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get conversation",
        )


@router.post(
    "/completions",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Send a message and get AI response",
    description="Send a message to the AI and receive a completion",
)
async def send_message(
    request: MessageRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Send a message and get AI response
    
    - **conversation_id**: ID of the conversation
    - **content**: The message content
    - **model**: Optional model override
    - **temperature**: Optional temperature (0-1)
    - **max_tokens**: Optional token limit
    """
    try:
        # Verify conversation exists and belongs to user
        conversation = db.query(Conversation).filter(
            Conversation.id == request.conversation_id,
            Conversation.user_id == current_user["user_id"],
        ).first()
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found",
            )
        
        # Store user message
        user_message = Message(
            id=str(uuid4()),
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content=request.content,
            metadata={
                "tokens": len(request.content.split()),
            },
        )
        db.add(user_message)
        db.commit()
        
        # Get AI response
        context_messages = [
            {
                "role": msg.role.value,
                "content": msg.content,
            }
            for msg in conversation.messages[-10:]  # Last 10 messages for context
        ]
        
        ai_response = await llm_service.generate_response(
            messages=context_messages,
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )
        
        # Store AI response
        assistant_message = Message(
            id=str(uuid4()),
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content=ai_response["content"],
            metadata={
                "model": ai_response.get("model"),
                "tokens": ai_response.get("tokens"),
                "latency": ai_response.get("latency"),
            },
        )
        db.add(assistant_message)
        db.commit()
        db.refresh(assistant_message)
        
        # Store in memory
        await memory_service.store_interaction(
            user_id=current_user["user_id"],
            user_input=request.content,
            ai_response=ai_response["content"],
            conversation_id=conversation.id,
        )
        
        logger.info(f"Processed message in conversation {conversation.id}")
        
        return MessageResponse(
            id=assistant_message.id,
            conversation_id=assistant_message.conversation_id,
            role=assistant_message.role.value,
            content=assistant_message.content,
            created_at=assistant_message.created_at.isoformat(),
            metadata=assistant_message.metadata,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process message",
        )


@router.delete(
    "/sessions/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a conversation",
    description="Delete/archive a conversation",
)
async def delete_conversation(
    conversation_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a conversation"""
    try:
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user["user_id"],
        ).first()
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found",
            )
        
        # Soft delete - mark as archived
        conversation.is_archived = True
        db.commit()
        
        logger.info(f"Archived conversation {conversation_id}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting conversation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete conversation",
        )

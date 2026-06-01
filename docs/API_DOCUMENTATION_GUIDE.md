# API Documentation & OpenAPI Guide

## Overview
This document shows how to set up comprehensive API documentation using FastAPI's built-in OpenAPI support.

## Automatic Documentation

FastAPI automatically generates OpenAPI (Swagger) documentation. Access it at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## Documenting Endpoints

### Basic Endpoint Documentation

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])

class LoginRequest(BaseModel):
    """User login credentials."""
    email: str
    password: str

class AuthToken(BaseModel):
    """Authentication token response."""
    access_token: str
    token_type: str
    user_id: str

@router.post(
    "/login",
    response_model=AuthToken,
    status_code=200,
    summary="User Login",
    description="Authenticate user with email and password",
    responses={
        200: {"description": "Login successful"},
        401: {"description": "Invalid credentials"},
        429: {"description": "Too many login attempts"},
    }
)
async def login(request: LoginRequest) -> AuthToken:
    """
    Login endpoint for user authentication.
    
    - **email**: User email address
    - **password**: User password
    
    Returns authentication token for subsequent API calls.
    
    Example:
        ```python
        curl -X POST "http://localhost:8000/api/v1/auth/login" \\
          -H "Content-Type: application/json" \\
          -d '{"email":"user@example.com","password":"secure_pass"}'
        ```
    """
    # Implementation
    pass
```

### Endpoint with Query Parameters

```python
@router.get(
    "/search",
    summary="Search Memory",
    description="Search semantic memory by query",
    tags=["memory"]
)
async def search_memory(
    query: str,
    limit: int = 10,
    threshold: float = 0.7,
) -> List[MemoryEntry]:
    """
    Search semantic memory entries.
    
    Query parameters:
    - **query** (required): Search query string
    - **limit**: Maximum results (default: 10)
    - **threshold**: Relevance threshold 0-1 (default: 0.7)
    
    Returns list of relevant memory entries ordered by relevance.
    """
    pass
```

### Endpoint with Path Parameters

```python
@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationDetail,
    summary="Get Conversation",
    description="Retrieve a specific conversation with all messages"
)
async def get_conversation(
    conversation_id: str,
) -> ConversationDetail:
    """
    Get detailed conversation with message history.
    
    Parameters:
    - **conversation_id**: Unique conversation identifier
    
    Returns:
        Complete conversation object with all messages in chronological order.
    
    Raises:
        HTTPException (404): Conversation not found
    """
    pass
```

## Request/Response Examples

### Adding Examples to Models

```python
from pydantic import BaseModel, Field

class MessageCreate(BaseModel):
    """Create new message."""
    conversation_id: str = Field(..., description="Conversation ID")
    content: str = Field(..., min_length=1, max_length=8000, description="Message content")
    
    class Config:
        json_schema_extra = {
            "example": {
                "conversation_id": "conv-123",
                "content": "What's the weather today?"
            }
        }

class Message(BaseModel):
    """Chat message."""
    id: str
    conversation_id: str
    role: str  # "user" or "assistant"
    content: str
    created_at: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "msg-456",
                "conversation_id": "conv-123",
                "role": "assistant",
                "content": "The weather is sunny with a high of 72°F.",
                "created_at": "2024-01-15T10:30:00Z"
            }
        }
```

## Error Documentation

### Standard Error Responses

All errors follow this format:

```json
{
  "code": "AUTH_002",
  "message": "JWT token has expired",
  "severity": "error",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2024-01-15T10:30:00Z",
  "status_code": 401,
  "user_message": "Your session has expired. Please log in again."
}
```

### Documenting Error Codes

```python
from enum import Enum

class AuthErrorCodes(str, Enum):
    """Authentication error codes."""
    INVALID_CREDENTIALS = "AUTH_001"  # Wrong email/password
    TOKEN_EXPIRED = "AUTH_002"        # JWT token expired
    TOKEN_INVALID = "AUTH_003"        # Invalid token format
    INSUFFICIENT_PERMISSIONS = "AUTH_004"  # Lack required role
```

## Tags and Organization

Use tags to organize endpoints by feature:

```python
# In main.py
from fastapi import FastAPI

app = FastAPI(
    title="ShivaAI Jarvis API",
    description="Enterprise AI Assistant API",
    version="1.0.0",
    openapi_tags=[
        {
            "name": "authentication",
            "description": "User authentication and authorization",
        },
        {
            "name": "chat",
            "description": "Chat and conversation management",
        },
        {
            "name": "memory",
            "description": "Semantic memory operations",
        },
        {
            "name": "documents",
            "description": "Document ingestion and search",
        },
    ]
)

# Then use in routers:
@router.post("/login", tags=["authentication"])
async def login(request: LoginRequest) -> AuthToken:
    pass

@router.post("/chat/completions", tags=["chat"])
async def send_message(request: MessageRequest) -> Message:
    pass
```

## Security Documentation

### Bearer Token Authentication

```python
from fastapi.security import HTTPBearer, HTTPAuthCredentials

security = HTTPBearer()

@router.get("/me", security=security)
async def get_current_user(credentials: HTTPAuthCredentials):
    """
    Get current authenticated user.
    
    Security: Requires Bearer token in Authorization header.
    
    Example:
        ```
        curl -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc..." \\
          http://localhost:8000/api/v1/auth/me
        ```
    """
    pass
```

## Testing Documentation

Include test examples in docstrings:

```python
async def send_message(request: MessageRequest) -> Message:
    """
    Send message in conversation.
    
    Example (curl):
        ```bash
        curl -X POST "http://localhost:8000/api/v1/chat/completions" \\
          -H "Authorization: Bearer YOUR_TOKEN" \\
          -H "Content-Type: application/json" \\
          -d '{
            "conversation_id": "conv-123",
            "content": "Hello, how are you?"
          }'
        ```
    
    Example (Python):
        ```python
        import requests
        
        response = requests.post(
            "http://localhost:8000/api/v1/chat/completions",
            headers={"Authorization": "Bearer YOUR_TOKEN"},
            json={
                "conversation_id": "conv-123",
                "content": "Hello, how are you?"
            }
        )
        message = response.json()
        print(message["content"])
        ```
    
    Example (JavaScript):
        ```javascript
        const response = await fetch(
          'http://localhost:8000/api/v1/chat/completions',
          {
            method: 'POST',
            headers: {
              'Authorization': 'Bearer YOUR_TOKEN',
              'Content-Type': 'application/json'
            },
            body: JSON.stringify({
              conversation_id: 'conv-123',
              content: 'Hello, how are you?'
            })
          }
        );
        const message = await response.json();
        console.log(message.content);
        ```
    """
    pass
```

## Rate Limiting Documentation

```python
@router.post(
    "/chat/completions",
    summary="Send Chat Message",
    description="Send message and get AI response"
)
async def send_message(request: MessageRequest) -> Message:
    """
    Send message in conversation.
    
    Rate limiting:
    - 60 requests per minute for regular users
    - 300 requests per minute for premium users
    
    Returns 429 Too Many Requests if limit exceeded.
    """
    pass
```

## Async Streaming Documentation

```python
@router.post(
    "/chat/completions/stream",
    summary="Stream Chat Response",
    description="Get streaming AI response for better UX"
)
async def stream_message(request: MessageRequest):
    """
    Stream message response using Server-Sent Events.
    
    Response format (Server-Sent Events):
        ```
        event: message
        data: {"id":"msg-1","role":"assistant","content":"First chunk"}
        
        event: message
        data: {"id":"msg-1","role":"assistant","content":" of response"}
        
        event: done
        data: {"id":"msg-1"}
        ```
    
    Example (JavaScript):
        ```javascript
        const eventSource = new EventSource(
          '/api/v1/chat/completions/stream?conversation_id=conv-123&content=Hello'
        );
        
        let response = '';
        eventSource.addEventListener('message', (event) => {
          const data = JSON.parse(event.data);
          response += data.content;
          console.log(response);
        });
        
        eventSource.addEventListener('done', () => {
          eventSource.close();
        });
        ```
    """
    pass
```

## Custom OpenAPI Schema

### Customizing OpenAPI Output

```python
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="ShivaAI Jarvis API",
        version="1.0.0",
        description="Enterprise AI Assistant API with cognitive OS architecture",
        routes=app.routes,
    )
    
    openapi_schema["info"]["x-logo"] = {
        "url": "https://example.com/logo.png"
    }
    
    openapi_schema["servers"] = [
        {"url": "https://api.example.com", "description": "Production"},
        {"url": "https://staging.example.com", "description": "Staging"},
        {"url": "http://localhost:8000", "description": "Development"},
    ]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi
```

## Deployment Considerations

### Environment-Specific Documentation

```python
import os
from fastapi import FastAPI

app = FastAPI(
    title="ShivaAI Jarvis API",
    version="1.0.0",
    docs_url="/docs" if os.getenv("ENVIRONMENT") == "development" else None,
    redoc_url="/redoc" if os.getenv("ENVIRONMENT") == "development" else None,
)
```

### API Versioning

Use version in OpenAPI schema:

```python
app = FastAPI(
    title="ShivaAI Jarvis API",
    version="1.0.0",
    openapi_url="/openapi.json",
    docs_url="/docs",
)

# Versioned routers
from fastapi import APIRouter

v1_router = APIRouter(prefix="/api/v1")
v2_router = APIRouter(prefix="/api/v2")
```

## Best Practices

1. **Be Descriptive**: Use clear summary and description fields
2. **Include Examples**: Show request/response examples
3. **Document Errors**: Explain possible HTTP status codes
4. **Add Security**: Document authentication requirements
5. **Use Tags**: Organize endpoints logically
6. **Version API**: Support multiple API versions
7. **Rate Limiting**: Document rate limits
8. **Deprecation**: Mark deprecated endpoints
9. **Type Hints**: Use proper Python type hints
10. **Schema Examples**: Provide realistic model examples

## Automated Testing from Documentation

Use the Swagger UI to test endpoints directly, or export OpenAPI schema for testing frameworks:

```bash
# Get OpenAPI schema
curl http://localhost:8000/openapi.json > openapi.json

# Use with code generation tools
openapi-generator-cli generate \
  -i openapi.json \
  -g python \
  -o ./generated-client
```

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [OpenAPI Specification](https://spec.openapis.org/oas/latest.html)
- [JSON Schema](https://json-schema.org/)
- [Swagger Editor](https://editor.swagger.io/)

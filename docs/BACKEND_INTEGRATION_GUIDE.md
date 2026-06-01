# Integration Guide for main.py - Error Handling & Logging

## How to Integrate Error Handlers

Add this near the top of `main.py` after imports:

```python
# At the top with other imports
from .errors import (
    shivaai_exception_handler,
    generic_exception_handler,
    ShivaAIException,
    rate_limit_response,
)
from .logging import RequestIDMiddleware, LoggingMiddleware, configure_logging

# Create FastAPI app
app = FastAPI(
    title="ShivaAI Jarvis Gateway",
    description="Enterprise AI Assistant Platform",
    version="1.0.0",
)

# Configure logging FIRST
configure_logging()
logger = get_logger(__name__)

# Register error handlers BEFORE middleware
app.add_exception_handler(ShivaAIException, shivaai_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Add middleware (order matters - add these before CORS)
app.add_middleware(LoggingMiddleware)
app.add_middleware(RequestIDMiddleware)

# Then add CORS as usual
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Startup & Shutdown Events

```python
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger = get_logger(__name__)
    logger.info("Application starting up", event="startup")
    
    # Initialize database connection
    # Initialize caches
    # Connect to external services
    # etc.

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown"""
    logger = get_logger(__name__)
    logger.info("Application shutting down", event="shutdown")
    
    # Close database connections
    # Clear caches
    # Disconnect from services
    # etc.
```

## Health Check Endpoint

```python
@app.get("/health", tags=["System"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
```

## Example: Error Handling in Action

### Before (Current Code)
```python
@app.post("/api/v1/chat/completions")
async def send_message(req: MessageRequest):
    try:
        # Some code
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### After (With Error Handler)
```python
from .errors import ValidationError, ShivaAIException

@app.post("/api/v1/chat/completions")
async def send_message(
    req: MessageRequest,
    request: Request,
):
    """Send a message and get a completion"""
    logger = get_logger(__name__)
    request_id = request.headers.get("X-Request-ID", str(uuid4()))
    
    logger.info(
        "message_sent",
        user_id=req.user_id,
        conversation_id=req.conversation_id,
        request_id=request_id,
    )
    
    # Validate input
    if not req.content.strip():
        raise ValidationError(
            code="VAL_001",
            message="Message content cannot be empty",
            user_message="Please enter a message",
        )
    
    try:
        # Process message
        response = await llm_provider.complete(req.content)
        
        logger.info(
            "completion_success",
            response_id=response.id,
            request_id=request_id,
        )
        
        return response
        
    except TimeoutError as e:
        logger.warning(
            "llm_timeout",
            error=str(e),
            request_id=request_id,
        )
        raise ShivaAIException(
            code="LLM_001",
            message="LLM provider timeout",
            user_message="The AI service is taking too long. Please try again.",
            severity="warning",
        )
    except Exception as e:
        logger.error(
            "completion_failed",
            error=str(e),
            error_type=type(e).__name__,
            request_id=request_id,
            exc_info=True,
        )
        raise
```

## Response Examples

### Success Response
```json
{
  "id": "msg_123",
  "role": "assistant",
  "content": "Here's my response...",
  "created_at": "2024-01-15T10:30:00Z"
}
```

### Error Response
```json
{
  "code": "LLM_001",
  "message": "LLM provider timeout",
  "user_message": "The AI service is taking too long. Please try again.",
  "severity": "warning",
  "status_code": 502,
  "request_id": "req_abc123xyz",
  "timestamp": "2024-01-15T10:30:00Z",
  "details": {
    "original_error": "Connection timeout after 30s",
    "retry_after": 60
  }
}
```

## Logging Output Examples

### Request Logging
```json
{
  "timestamp": "2024-01-15T10:30:00.000Z",
  "level": "info",
  "event": "request_started",
  "request_id": "req_abc123xyz",
  "method": "POST",
  "path": "/api/v1/chat/completions",
  "client_ip": "192.168.1.1",
  "user_id": "user_123"
}
```

### Response Logging
```json
{
  "timestamp": "2024-01-15T10:30:00.500Z",
  "level": "info",
  "event": "request_completed",
  "request_id": "req_abc123xyz",
  "method": "POST",
  "path": "/api/v1/chat/completions",
  "status_code": 200,
  "duration_ms": 450,
  "user_id": "user_123"
}
```

### Error Logging
```json
{
  "timestamp": "2024-01-15T10:30:00.100Z",
  "level": "error",
  "event": "completion_failed",
  "request_id": "req_abc123xyz",
  "error": "Connection timeout",
  "error_type": "TimeoutError",
  "severity": "warning",
  "user_id": "user_123",
  "exc_info": "Traceback (most recent call last)..."
}
```

## Testing the Integration

### Unit Test
```python
import pytest
from fastapi.testclient import TestClient
from .errors import ShivaAIException

def test_validation_error_returns_proper_response(client: TestClient):
    """Test that validation errors return correct error format"""
    response = client.post(
        "/api/v1/chat/completions",
        json={"conversation_id": "123", "content": ""}  # Empty content
    )
    
    assert response.status_code == 422
    data = response.json()
    assert data["code"] == "VAL_001"
    assert "request_id" in data
    assert "timestamp" in data
    assert data["user_message"]  # User-friendly message
```

### Integration Test
```python
def test_error_handler_logs_request_id(client: TestClient, caplog):
    """Test that error handler includes request ID in response"""
    response = client.get("/nonexistent")
    
    assert response.status_code == 404
    data = response.json()
    assert "request_id" in data
    # Verify request_id is in logs too
    assert data["request_id"] in caplog.text
```

## File Organization After Integration

```
services/gateway/src/
├── main.py                  # App creation, routes, startup/shutdown
├── config.py               # Configuration management
├── errors.py               # Error definitions (already exists)
├── logging.py              # Logging setup (already exists)
├── auth.py                 # Authentication
├── schemas.py              # Request/response models
├── models.py               # SQLAlchemy ORM models
├── llm.py                  # LLM provider integration
├── storage.py              # Data storage/retrieval
├── capabilities.py         # Capability execution
└── routers/                # API route groups (NEW)
    ├── __init__.py
    ├── chat.py             # Chat endpoints
    ├── memory.py           # Memory endpoints
    ├── documents.py        # Document endpoints
    ├── capabilities.py     # Capability endpoints
    ├── workflows.py        # Workflow endpoints
    ├── decisions.py        # Decision/reflection endpoints
    ├── connectors.py       # Enterprise connectors
    ├── intelligence.py     # Domain intelligence
    ├── profile.py          # User profile
    ├── auth.py             # Auth endpoints
    └── admin.py            # Admin endpoints
```

## Next: Endpoint Grouping with APIRouter

Once error handlers and logging are integrated, refactor endpoints into routers:

```python
# main.py
from .routers import chat, memory, documents, capabilities, auth

app = FastAPI()

# Register routers
app.include_router(chat.router, prefix="/api/v1", tags=["Chat"])
app.include_router(memory.router, prefix="/api/v1", tags=["Memory"])
app.include_router(documents.router, prefix="/api/v1", tags=["Documents"])
app.include_router(capabilities.router, prefix="/api/v1", tags=["Capabilities"])
app.include_router(auth.router, prefix="/api/v1", tags=["Auth"])

# Each router has:
# - Proper imports
# - Consistent error handling
# - Request logging
# - Type-safe schemas
```


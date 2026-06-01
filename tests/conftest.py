"""
Pytest configuration and shared fixtures for all tests.
Provides database session, test client, and common test data.
"""

import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

# Set up temporary database for tests
TEST_DB_DIR = Path(tempfile.gettempdir()) / "shivaai_tests"
TEST_DB_DIR.mkdir(exist_ok=True)
TEST_DB_PATH = f"sqlite:///{TEST_DB_DIR / f'test-{uuid4()}.db'}"

# Configure environment for testing
os.environ["ENVIRONMENT"] = "test"
os.environ["DATABASE_URL"] = TEST_DB_PATH
os.environ["JWT_SECRET"] = "test-secret-key-for-unit-tests-only"
os.environ["LOG_LEVEL"] = "DEBUG"


# Import after environment setup
from services.gateway.src.main import app
from services.gateway.src.config import get_settings
from services.gateway.src.models import Base, get_db_engine, User, UserSession


@pytest.fixture(scope="session")
def test_settings():
    """Get test settings."""
    return get_settings()


@pytest.fixture(scope="session")
def db_engine():
    """Create test database engine."""
    engine = create_engine(TEST_DB_PATH, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def db_session(db_engine) -> Session:
    """Get database session for test."""
    connection = db_engine.connect()
    transaction = connection.begin()
    session = sessionmaker(autocommit=False, autoflush=False, bind=connection)()
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client():
    """Get FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def test_user_data():
    """Test user creation data."""
    return {
        "email": f"test-{uuid4()}@example.com",
        "password": "SecurePassword123!",
        "full_name": "Test User",
        "role": "user",
    }


@pytest.fixture
def test_admin_data():
    """Test admin user creation data."""
    return {
        "email": f"admin-{uuid4()}@example.com",
        "password": "AdminPassword123!",
        "full_name": "Admin User",
        "role": "admin",
    }


@pytest.fixture
def test_user(db_session, test_user_data) -> User:
    """Create test user in database."""
    from services.gateway.src.auth import hash_password
    
    user = User(
        id=str(uuid4()),
        email=test_user_data["email"],
        password_hash=hash_password(test_user_data["password"]),
        full_name=test_user_data["full_name"],
        role=test_user_data["role"],
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def test_user_session(db_session, test_user: User) -> UserSession:
    """Create test user session."""
    from services.gateway.src.auth import create_access_token
    from services.gateway.src.schemas import UserPublic
    
    user_public = UserPublic(
        id=test_user.id,
        email=test_user.email,
        full_name=test_user.full_name,
        role=test_user.role,
        created_at=test_user.created_at.isoformat(),
    )
    
    token = create_access_token(user_public)
    
    session = UserSession(
        id=str(uuid4()),
        user_id=test_user.id,
        token_jti=str(uuid4()),
        ip_address="127.0.0.1",
        user_agent="test-client",
        is_valid=True,
        expires_at=datetime.now(timezone.utc),
    )
    db_session.add(session)
    db_session.commit()
    return session


@pytest.fixture
def auth_headers(test_user_session) -> dict:
    """Get authorization headers with test token."""
    from services.gateway.src.auth import create_access_token
    from services.gateway.src.schemas import UserPublic
    from services.gateway.src.config import get_settings
    from services.gateway.src.models import User
    
    # Fetch the user from database
    # For now, return a mock bearer token
    return {"Authorization": f"Bearer test-token-{test_user_session.token_jti}"}


@pytest.fixture
def authenticated_client(client, auth_headers):
    """Get test client with authentication headers."""
    client.headers.update(auth_headers)
    return client


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "slow: marks test as slow")
    config.addinivalue_line("markers", "integration: marks test as integration test")
    config.addinivalue_line("markers", "unit: marks test as unit test")
    config.addinivalue_line("markers", "db: marks test as requiring database")


@pytest.fixture
def mock_http_client():
    """Mock HTTP client for external service calls."""
    import httpx
    from unittest.mock import AsyncMock, MagicMock
    
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    return mock_client


@pytest.fixture
def mock_llm_provider():
    """Mock LLM provider for testing."""
    from unittest.mock import AsyncMock
    
    mock = AsyncMock()
    mock.generate = AsyncMock(return_value={"content": "Test response", "metadata": {}})
    return mock


@pytest.fixture
def mock_vector_db():
    """Mock vector database for testing."""
    from unittest.mock import AsyncMock
    
    mock = AsyncMock()
    mock.search = AsyncMock(return_value=[
        {"id": "doc-1", "score": 0.95, "content": "Test content"}
    ])
    return mock


# Cleanup
@pytest.fixture(autouse=True)
def cleanup_test_db():
    """Clean up test database after each test session."""
    yield
    # Cleanup happens automatically with fixtures


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

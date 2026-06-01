#!/usr/bin/env python3
"""
Test script to verify error handler integration in main.py
Run with: python tests/test_error_integration.py
"""

import pytest
from fastapi.testclient import TestClient
import json
import sys
from pathlib import Path

# Add services/gateway to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "services" / "gateway"))

from src.main import create_app


@pytest.fixture
def app():
    """Create test app instance"""
    return create_app()


@pytest.fixture
def client(app):
    """Create test client"""
    return TestClient(app)


class TestErrorHandlerIntegration:
    """Test error handler integration"""

    def test_health_endpoint_works(self, client):
        """Test that health endpoint is accessible"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        print("✅ Health check endpoint works")

    def test_404_returns_error_response(self, client):
        """Test that 404 errors return structured error response"""
        response = client.get("/nonexistent/endpoint")
        assert response.status_code == 404
        data = response.json()
        
        # Check error response has required fields
        assert "request_id" in data, "Error response missing request_id"
        assert "timestamp" in data, "Error response missing timestamp"
        assert "status_code" in data, "Error response missing status_code"
        
        print("✅ 404 errors return structured response with request_id")
        print(f"   Response: {json.dumps(data, indent=2)}")

    def test_request_id_header_present(self, client):
        """Test that response includes X-Request-ID header"""
        response = client.get("/health")
        assert "x-request-id" in response.headers, "X-Request-ID header missing"
        
        request_id = response.headers["x-request-id"]
        assert len(request_id) > 0, "X-Request-ID header is empty"
        
        print(f"✅ X-Request-ID header present: {request_id}")

    def test_invalid_request_returns_validation_error(self, client):
        """Test that invalid requests return validation errors"""
        # Try POST without required fields
        response = client.post(
            "/api/v1/auth/login",
            json={"invalid": "data"}  # Missing required fields
        )
        
        # FastAPI returns 422 for validation errors
        assert response.status_code == 422
        data = response.json()
        
        # Should have request_id for tracing
        if isinstance(data, dict) and "detail" in data:
            print(f"✅ Validation error returned: {data['detail']}")
        else:
            print(f"✅ Validation error returned with status 422")

    def test_cors_headers_present(self, client):
        """Test that CORS and security headers are set"""
        response = client.get("/health")
        
        # Check security headers
        assert "x-content-type-options" in response.headers
        assert "x-frame-options" in response.headers
        assert "referrer-policy" in response.headers
        
        print("✅ Security headers present:")
        print(f"   X-Content-Type-Options: {response.headers.get('x-content-type-options')}")
        print(f"   X-Frame-Options: {response.headers.get('x-frame-options')}")
        print(f"   Referrer-Policy: {response.headers.get('referrer-policy')}")

    def test_root_endpoint(self, client):
        """Test that root endpoint returns app info"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        
        assert "name" in data
        assert "version" in data
        assert "docs" in data
        assert "health" in data
        
        print("✅ Root endpoint returns:")
        print(f"   {json.dumps(data, indent=2)}")


def run_integration_tests():
    """Run all tests and print results"""
    print("\n" + "="*60)
    print("ERROR HANDLER INTEGRATION TESTS")
    print("="*60 + "\n")
    
    # Import test functions
    test_instance = TestErrorHandlerIntegration()
    app = create_app()
    client = TestClient(app)
    
    tests = [
        ("Health endpoint", lambda: test_instance.test_health_endpoint_works(client)),
        ("404 error handling", lambda: test_instance.test_404_returns_error_response(client)),
        ("Request ID header", lambda: test_instance.test_request_id_header_present(client)),
        ("Security headers", lambda: test_instance.test_cors_headers_present(client)),
        ("Root endpoint", lambda: test_instance.test_root_endpoint(client)),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            print(f"\nTesting: {test_name}")
            print("-" * 50)
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"❌ FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"❌ ERROR: {e}")
            failed += 1
    
    print("\n" + "="*60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("="*60 + "\n")
    
    return failed == 0


if __name__ == "__main__":
    success = run_integration_tests()
    sys.exit(0 if success else 1)

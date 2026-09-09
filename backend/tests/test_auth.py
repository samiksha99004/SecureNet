"""
SecureNet Backend — Authentication Tests

Basic test suite for authentication endpoints.
"""

import pytest
from httpx import AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_signup_success():
    """Test successful user registration"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/auth/signup",
            json={
                "fullName": "Test User",
                "email": "test@example.com",
                "password": "Test1234",
                "confirmPassword": "Test1234"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data


@pytest.mark.asyncio
async def test_signup_duplicate_email():
    """Test registration with existing email"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # First registration
        await client.post(
            "/api/auth/signup",
            json={
                "fullName": "Test User",
                "email": "duplicate@example.com",
                "password": "Test1234",
                "confirmPassword": "Test1234"
            }
        )
        
        # Duplicate registration
        response = await client.post(
            "/api/auth/signup",
            json={
                "fullName": "Test User 2",
                "email": "duplicate@example.com",
                "password": "Test1234",
                "confirmPassword": "Test1234"
            }
        )
        
        assert response.status_code == 400


@pytest.mark.asyncio
async def test_login_invalid_credentials():
    """Test login with invalid credentials"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "wrongpassword"
            }
        )
        
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_health_check():
    """Test health endpoint"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "database" in data

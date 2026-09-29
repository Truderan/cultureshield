"""
Test suite for CultureShield Auth endpoints
Tests: POST /api/auth/register, POST /api/auth/login, GET /api/auth/me
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestAuthRegistration:
    """Test registration flow - focus of current bug verification"""
    
    def test_register_new_account_success(self):
        """Test that registration creates account and returns valid token"""
        unique_id = int(time.time() * 1000)
        payload = {
            "company_name": f"TestCompany_{unique_id}",
            "email": f"test_register_{unique_id}@example.com",
            "password": "TestPassword123"
        }
        
        response = requests.post(f"{BASE_URL}/api/auth/register", json=payload)
        
        # Status code check
        assert response.status_code == 200, f"Registration failed with status {response.status_code}: {response.text}"
        
        # Data validation
        data = response.json()
        assert "access_token" in data, "Missing access_token in response"
        assert "company" in data, "Missing company in response"
        assert data["company"]["email"] == payload["email"], "Email mismatch"
        assert data["company"]["company_name"] == payload["company_name"], "Company name mismatch"
        assert "id" in data["company"], "Missing company id"
        assert data["token_type"] == "bearer", "Token type should be bearer"
        
        # Verify token is a valid JWT format (has 3 parts separated by dots)
        token = data["access_token"]
        assert len(token.split('.')) == 3, "Token should be valid JWT format"
        
        print(f"✓ Registration successful for {payload['email']}")
        
    def test_register_duplicate_email_fails(self):
        """Test that registering with existing email returns error"""
        unique_id = int(time.time() * 1000)
        payload = {
            "company_name": f"TestCompanyDup_{unique_id}",
            "email": f"test_dup_{unique_id}@example.com",
            "password": "TestPassword123"
        }
        
        # First registration
        response1 = requests.post(f"{BASE_URL}/api/auth/register", json=payload)
        assert response1.status_code == 200, "First registration should succeed"
        
        # Duplicate registration
        response2 = requests.post(f"{BASE_URL}/api/auth/register", json=payload)
        assert response2.status_code == 400, f"Duplicate registration should fail with 400, got {response2.status_code}"
        
        data = response2.json()
        assert "detail" in data, "Error response should have detail"
        assert "already registered" in data["detail"].lower() or "email" in data["detail"].lower()
        
        print("✓ Duplicate email registration correctly rejected")
        
    def test_register_invalid_email_format(self):
        """Test that invalid email format is rejected"""
        payload = {
            "company_name": "TestCompany",
            "email": "invalid-email-format",
            "password": "TestPassword123"
        }
        
        response = requests.post(f"{BASE_URL}/api/auth/register", json=payload)
        assert response.status_code == 422, f"Invalid email should return 422, got {response.status_code}"
        
        print("✓ Invalid email format correctly rejected")
        
    def test_register_missing_fields(self):
        """Test that missing required fields are rejected"""
        # Missing password
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "company_name": "Test",
            "email": "test@example.com"
        })
        assert response.status_code == 422, "Missing password should return 422"
        
        # Missing email
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "company_name": "Test",
            "password": "password123"
        })
        assert response.status_code == 422, "Missing email should return 422"
        
        print("✓ Missing fields correctly rejected")


class TestAuthLogin:
    """Test login flow"""
    
    @pytest.fixture(scope="class")
    def registered_user(self):
        """Create a test user for login tests"""
        unique_id = int(time.time() * 1000)
        payload = {
            "company_name": f"LoginTestCompany_{unique_id}",
            "email": f"test_login_{unique_id}@example.com",
            "password": "LoginPassword123"
        }
        
        response = requests.post(f"{BASE_URL}/api/auth/register", json=payload)
        assert response.status_code == 200, "Setup: Registration failed"
        
        return {
            "email": payload["email"],
            "password": payload["password"],
            "company_name": payload["company_name"],
            "token": response.json()["access_token"]
        }
    
    def test_login_success(self, registered_user):
        """Test successful login with valid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": registered_user["email"],
            "password": registered_user["password"]
        })
        
        assert response.status_code == 200, f"Login failed with status {response.status_code}: {response.text}"
        
        data = response.json()
        assert "access_token" in data, "Missing access_token"
        assert "company" in data, "Missing company"
        assert data["company"]["email"] == registered_user["email"]
        
        print(f"✓ Login successful for {registered_user['email']}")
        
    def test_login_invalid_password(self, registered_user):
        """Test login with wrong password returns 401"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": registered_user["email"],
            "password": "WrongPassword123"
        })
        
        assert response.status_code == 401, f"Invalid password should return 401, got {response.status_code}"
        
        data = response.json()
        assert "detail" in data
        
        print("✓ Invalid password correctly rejected with 401")
        
    def test_login_nonexistent_email(self):
        """Test login with non-existent email returns 401"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "nonexistent_user_12345@example.com",
            "password": "SomePassword123"
        })
        
        assert response.status_code == 401, f"Non-existent email should return 401, got {response.status_code}"
        
        print("✓ Non-existent email correctly rejected with 401")


class TestAuthMe:
    """Test authenticated user info endpoint"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Create a test user and return token"""
        unique_id = int(time.time() * 1000)
        payload = {
            "company_name": f"MeTestCompany_{unique_id}",
            "email": f"test_me_{unique_id}@example.com",
            "password": "MePassword123"
        }
        
        response = requests.post(f"{BASE_URL}/api/auth/register", json=payload)
        assert response.status_code == 200, "Setup: Registration failed"
        
        return {
            "token": response.json()["access_token"],
            "email": payload["email"],
            "company_name": payload["company_name"]
        }
    
    def test_get_me_with_valid_token(self, auth_token):
        """Test GET /api/auth/me with valid token returns user info"""
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {auth_token['token']}"}
        )
        
        assert response.status_code == 200, f"GET /me failed with status {response.status_code}: {response.text}"
        
        data = response.json()
        assert "id" in data, "Missing id in response"
        assert data["email"] == auth_token["email"], "Email mismatch"
        assert data["company_name"] == auth_token["company_name"], "Company name mismatch"
        
        print(f"✓ GET /me successful for {auth_token['email']}")
        
    def test_get_me_without_token(self):
        """Test GET /api/auth/me without token returns 403"""
        response = requests.get(f"{BASE_URL}/api/auth/me")
        
        assert response.status_code == 403, f"Missing token should return 403, got {response.status_code}"
        
        print("✓ Missing token correctly rejected with 403")
        
    def test_get_me_with_invalid_token(self):
        """Test GET /api/auth/me with invalid token returns 401"""
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": "Bearer invalid_token_12345"}
        )
        
        assert response.status_code == 401, f"Invalid token should return 401, got {response.status_code}"
        
        print("✓ Invalid token correctly rejected with 401")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

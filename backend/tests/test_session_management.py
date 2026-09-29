"""
Test suite for Trusted Devices / Active Sessions feature
Tests session tracking, revocation, and token invalidation
"""
import pytest
import requests
import os
import uuid
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials provided
TEST_EMAIL = "session_f8d3fc6e@example.com"
TEST_PASSWORD = "StrongPass!234"


class TestSessionManagement:
    """Tests for session tracking and revocation APIs"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})

    def _create_test_account(self):
        """Create a fresh test account for session testing"""
        unique_id = str(uuid.uuid4())[:8]
        email = f"session_test_{unique_id}@example.com"
        password = "StrongPass!234"
        company_name = f"Session Test Co {unique_id}"
        
        response = self.session.post(f"{BASE_URL}/api/auth/register", json={
            "company_name": company_name,
            "email": email,
            "password": password
        })
        
        if response.status_code == 201 or response.status_code == 200:
            data = response.json()
            return {
                "email": email,
                "password": password,
                "token": data.get("access_token"),
                "company": data.get("company")
            }
        return None

    def _login(self, email, password):
        """Login and return token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": email,
            "password": password
        })
        if response.status_code == 200:
            data = response.json()
            return data.get("access_token")
        return None

    # ==================== Session Creation Tests ====================

    def test_register_creates_session(self):
        """Test that registration creates a server-side auth session"""
        account = self._create_test_account()
        assert account is not None, "Failed to create test account"
        assert account["token"] is not None, "No token returned on registration"
        
        # Verify session exists via /auth/sessions
        response = self.session.get(
            f"{BASE_URL}/api/auth/sessions",
            headers={"Authorization": f"Bearer {account['token']}"}
        )
        assert response.status_code == 200, f"Failed to get sessions: {response.text}"
        
        data = response.json()
        assert "items" in data, "Response missing 'items' field"
        assert "current_session_id" in data, "Response missing 'current_session_id' field"
        assert len(data["items"]) >= 1, "No sessions found after registration"
        
        # Verify current session is marked
        current_session = next((s for s in data["items"] if s["is_current"]), None)
        assert current_session is not None, "No current session marked"
        print(f"✓ Registration creates session: {current_session['id']}")

    def test_login_creates_session(self):
        """Test that login creates a new server-side auth session"""
        # First create an account
        account = self._create_test_account()
        assert account is not None, "Failed to create test account"
        
        # Login again to create a second session
        token2 = self._login(account["email"], account["password"])
        assert token2 is not None, "Failed to login"
        
        # Get sessions with new token
        response = self.session.get(
            f"{BASE_URL}/api/auth/sessions",
            headers={"Authorization": f"Bearer {token2}"}
        )
        assert response.status_code == 200, f"Failed to get sessions: {response.text}"
        
        data = response.json()
        # Should have at least 2 sessions (registration + login)
        assert len(data["items"]) >= 2, f"Expected at least 2 sessions, got {len(data['items'])}"
        print(f"✓ Login creates new session. Total sessions: {len(data['items'])}")

    # ==================== GET /auth/sessions Tests ====================

    def test_get_sessions_returns_metadata(self):
        """Test that GET /auth/sessions returns proper session metadata"""
        account = self._create_test_account()
        assert account is not None, "Failed to create test account"
        
        response = self.session.get(
            f"{BASE_URL}/api/auth/sessions",
            headers={"Authorization": f"Bearer {account['token']}"}
        )
        assert response.status_code == 200, f"Failed to get sessions: {response.text}"
        
        data = response.json()
        assert "items" in data
        assert "current_session_id" in data
        
        session = data["items"][0]
        # Verify required fields
        required_fields = ["id", "device_name", "browser", "os", "ip_address", 
                          "mfa_verified", "created_at", "last_active_at", "is_current"]
        for field in required_fields:
            assert field in session, f"Session missing field: {field}"
        
        print(f"✓ Session metadata complete: {list(session.keys())}")

    def test_get_sessions_requires_auth(self):
        """Test that GET /auth/sessions requires authentication"""
        response = self.session.get(f"{BASE_URL}/api/auth/sessions")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ GET /auth/sessions requires authentication")

    # ==================== POST /auth/logout Tests ====================

    def test_logout_revokes_current_session(self):
        """Test that POST /auth/logout revokes the current session"""
        account = self._create_test_account()
        assert account is not None, "Failed to create test account"
        token = account["token"]
        
        # Logout
        response = self.session.post(
            f"{BASE_URL}/api/auth/logout",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"Logout failed: {response.text}"
        
        data = response.json()
        assert "message" in data, "Logout response missing message"
        print(f"✓ Logout successful: {data['message']}")
        
        # Verify token is now invalid
        response = self.session.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 401, f"Expected 401 after logout, got {response.status_code}"
        print("✓ Token invalidated after logout")

    # ==================== POST /auth/sessions/{session_id}/revoke Tests ====================

    def test_revoke_specific_session(self):
        """Test that POST /auth/sessions/{session_id}/revoke revokes a selected session"""
        account = self._create_test_account()
        assert account is not None, "Failed to create test account"
        token1 = account["token"]
        
        # Create a second session by logging in again
        token2 = self._login(account["email"], account["password"])
        assert token2 is not None, "Failed to create second session"
        
        # Get sessions from token2's perspective
        response = self.session.get(
            f"{BASE_URL}/api/auth/sessions",
            headers={"Authorization": f"Bearer {token2}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        current_session_id = data["current_session_id"]
        
        # Find a non-current session to revoke
        other_session = next((s for s in data["items"] if not s["is_current"]), None)
        assert other_session is not None, "No other session to revoke"
        
        # Revoke the other session
        response = self.session.post(
            f"{BASE_URL}/api/auth/sessions/{other_session['id']}/revoke",
            headers={"Authorization": f"Bearer {token2}"}
        )
        assert response.status_code == 200, f"Failed to revoke session: {response.text}"
        print(f"✓ Revoked session: {other_session['id']}")
        
        # Verify the revoked session's token no longer works
        response = self.session.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {token1}"}
        )
        assert response.status_code == 401, f"Expected 401 for revoked session, got {response.status_code}"
        print("✓ Revoked session token is invalidated")

    def test_revoke_nonexistent_session_returns_404(self):
        """Test that revoking a non-existent session returns 404"""
        account = self._create_test_account()
        assert account is not None, "Failed to create test account"
        
        fake_session_id = str(uuid.uuid4())
        response = self.session.post(
            f"{BASE_URL}/api/auth/sessions/{fake_session_id}/revoke",
            headers={"Authorization": f"Bearer {account['token']}"}
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Revoking non-existent session returns 404")

    # ==================== POST /auth/sessions/revoke-all Tests ====================

    def test_revoke_all_other_sessions(self):
        """Test that POST /auth/sessions/revoke-all revokes all other sessions"""
        account = self._create_test_account()
        assert account is not None, "Failed to create test account"
        token1 = account["token"]
        
        # Create multiple additional sessions
        token2 = self._login(account["email"], account["password"])
        token3 = self._login(account["email"], account["password"])
        assert token2 is not None and token3 is not None, "Failed to create additional sessions"
        
        # Verify we have multiple sessions
        response = self.session.get(
            f"{BASE_URL}/api/auth/sessions",
            headers={"Authorization": f"Bearer {token3}"}
        )
        assert response.status_code == 200
        initial_count = len(response.json()["items"])
        assert initial_count >= 3, f"Expected at least 3 sessions, got {initial_count}"
        print(f"✓ Created {initial_count} sessions")
        
        # Revoke all other sessions from token3
        response = self.session.post(
            f"{BASE_URL}/api/auth/sessions/revoke-all",
            headers={"Authorization": f"Bearer {token3}"}
        )
        assert response.status_code == 200, f"Failed to revoke all: {response.text}"
        print("✓ Revoke-all successful")
        
        # Verify current session (token3) still works
        response = self.session.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {token3}"}
        )
        assert response.status_code == 200, "Current session should still work after revoke-all"
        print("✓ Current session still valid after revoke-all")
        
        # Verify other sessions are revoked
        response = self.session.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {token1}"}
        )
        assert response.status_code == 401, f"Expected 401 for revoked token1, got {response.status_code}"
        
        response = self.session.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {token2}"}
        )
        assert response.status_code == 401, f"Expected 401 for revoked token2, got {response.status_code}"
        print("✓ Other sessions invalidated after revoke-all")
        
        # Verify only 1 session remains
        response = self.session.get(
            f"{BASE_URL}/api/auth/sessions",
            headers={"Authorization": f"Bearer {token3}"}
        )
        assert response.status_code == 200
        final_count = len(response.json()["items"])
        assert final_count == 1, f"Expected 1 session after revoke-all, got {final_count}"
        print(f"✓ Only current session remains: {final_count} session(s)")

    # ==================== Token Invalidation Tests ====================

    def test_revoked_session_token_fails_auth_me(self):
        """Test that /auth/me fails for a revoked session token"""
        account = self._create_test_account()
        assert account is not None, "Failed to create test account"
        token = account["token"]
        
        # Verify token works initially
        response = self.session.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, "Token should work initially"
        
        # Logout to revoke session
        response = self.session.post(
            f"{BASE_URL}/api/auth/logout",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        
        # Verify /auth/me now fails
        response = self.session.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        
        data = response.json()
        assert "detail" in data
        print(f"✓ Revoked token error message: {data['detail']}")

    # ==================== Existing Auth Flow Regression Tests ====================

    def test_login_still_works(self):
        """Regression: Verify basic login still works with session tracking"""
        account = self._create_test_account()
        assert account is not None, "Failed to create test account"
        
        token = self._login(account["email"], account["password"])
        assert token is not None, "Login failed"
        
        # Verify token works
        response = self.session.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        print("✓ Login flow works correctly with session tracking")

    def test_register_still_works(self):
        """Regression: Verify registration still works with session tracking"""
        account = self._create_test_account()
        assert account is not None, "Registration failed"
        assert account["token"] is not None, "No token returned"
        assert account["company"] is not None, "No company data returned"
        
        # Verify token works
        response = self.session.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {account['token']}"}
        )
        assert response.status_code == 200
        print("✓ Registration flow works correctly with session tracking")


class TestSessionWithProvidedCredentials:
    """Tests using the provided test credentials"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})

    def test_provided_account_login(self):
        """Test login with provided test credentials"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        
        # Account may or may not exist, handle both cases
        if response.status_code == 200:
            data = response.json()
            # Check if MFA is required
            if data.get("mfa_required"):
                print(f"✓ Login requires MFA for {TEST_EMAIL}")
            else:
                token = data.get("access_token")
                assert token is not None, "No token returned"
                
                # Verify sessions endpoint works
                response = self.session.get(
                    f"{BASE_URL}/api/auth/sessions",
                    headers={"Authorization": f"Bearer {token}"}
                )
                assert response.status_code == 200
                print(f"✓ Provided account login successful, sessions accessible")
        elif response.status_code == 401:
            print(f"⚠ Provided account {TEST_EMAIL} credentials invalid or account doesn't exist")
            pytest.skip("Test account not available")
        else:
            pytest.fail(f"Unexpected status: {response.status_code} - {response.text}")


class TestPasswordResetSessionRevocation:
    """Test that password reset revokes all sessions"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})

    def _create_test_account(self):
        """Create a fresh test account"""
        unique_id = str(uuid.uuid4())[:8]
        email = f"pwreset_test_{unique_id}@example.com"
        password = "StrongPass!234"
        company_name = f"PW Reset Test Co {unique_id}"
        
        response = self.session.post(f"{BASE_URL}/api/auth/register", json={
            "company_name": company_name,
            "email": email,
            "password": password
        })
        
        if response.status_code in [200, 201]:
            data = response.json()
            return {
                "email": email,
                "password": password,
                "token": data.get("access_token"),
                "company": data.get("company")
            }
        return None

    def test_forgot_password_endpoint_works(self):
        """Test that forgot password endpoint works"""
        account = self._create_test_account()
        assert account is not None, "Failed to create test account"
        
        response = self.session.post(f"{BASE_URL}/api/auth/forgot-password", json={
            "email": account["email"]
        })
        assert response.status_code == 200, f"Forgot password failed: {response.text}"
        
        data = response.json()
        assert "message" in data
        print(f"✓ Forgot password endpoint works: {data['message']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

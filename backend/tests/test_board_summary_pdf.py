"""
Test Board Summary PDF Export Endpoint
Tests the GET /api/board-summary/pdf endpoint for authenticated users
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')

# Test credentials from iteration_13
TEST_EMAIL = "alignment_bbe272c9@example.com"
TEST_PASSWORD = "StrongPass!234"


class TestBoardSummaryPdfExport:
    """Tests for the board summary PDF export feature"""

    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token for test user"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        if response.status_code == 200:
            data = response.json()
            # Handle MFA if required
            if data.get("mfa_required"):
                pytest.skip("MFA required - skipping authenticated tests")
            return data.get("access_token")
        pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")

    def test_board_summary_pdf_returns_200_for_authenticated_user(self, auth_token):
        """GET /api/board-summary/pdf returns 200 for authenticated user"""
        response = requests.get(
            f"{BASE_URL}/api/board-summary/pdf",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print(f"✓ Board summary PDF endpoint returned 200")

    def test_board_summary_pdf_returns_pdf_content_type(self, auth_token):
        """GET /api/board-summary/pdf returns application/pdf content type"""
        response = requests.get(
            f"{BASE_URL}/api/board-summary/pdf",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        content_type = response.headers.get("Content-Type", "")
        assert "application/pdf" in content_type, f"Expected application/pdf, got {content_type}"
        print(f"✓ Content-Type is application/pdf")

    def test_board_summary_pdf_has_content_disposition_header(self, auth_token):
        """GET /api/board-summary/pdf returns Content-Disposition header for download"""
        response = requests.get(
            f"{BASE_URL}/api/board-summary/pdf",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        content_disposition = response.headers.get("Content-Disposition", "")
        assert "attachment" in content_disposition, f"Expected attachment in Content-Disposition, got {content_disposition}"
        assert "filename=" in content_disposition, f"Expected filename in Content-Disposition, got {content_disposition}"
        assert ".pdf" in content_disposition, f"Expected .pdf in filename, got {content_disposition}"
        print(f"✓ Content-Disposition header is correct: {content_disposition}")

    def test_board_summary_pdf_returns_non_empty_content(self, auth_token):
        """GET /api/board-summary/pdf returns non-empty PDF content"""
        response = requests.get(
            f"{BASE_URL}/api/board-summary/pdf",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        content = response.content
        assert len(content) > 0, "PDF content should not be empty"
        # PDF files start with %PDF
        assert content[:4] == b'%PDF', f"Content should start with PDF magic bytes, got {content[:10]}"
        print(f"✓ PDF content is valid ({len(content)} bytes)")

    def test_board_summary_pdf_requires_authentication(self):
        """GET /api/board-summary/pdf returns 401/403 without authentication"""
        response = requests.get(f"{BASE_URL}/api/board-summary/pdf")
        
        assert response.status_code in [401, 403], f"Expected 401 or 403 without auth, got {response.status_code}"
        print(f"✓ Endpoint requires authentication (returned {response.status_code})")

    def test_board_summary_pdf_rejects_invalid_token(self):
        """GET /api/board-summary/pdf returns 401 with invalid token"""
        response = requests.get(
            f"{BASE_URL}/api/board-summary/pdf",
            headers={"Authorization": "Bearer invalid_token_12345"}
        )
        
        assert response.status_code == 401, f"Expected 401 with invalid token, got {response.status_code}"
        print(f"✓ Endpoint rejects invalid token (returned 401)")


class TestPrintSummaryNoRegression:
    """Verify no regression to existing print functionality - just check page loads"""

    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token for test user"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        if response.status_code == 200:
            data = response.json()
            if data.get("mfa_required"):
                pytest.skip("MFA required - skipping authenticated tests")
            return data.get("access_token")
        pytest.skip(f"Authentication failed: {response.status_code}")

    def test_dashboard_stats_endpoint_still_works(self, auth_token):
        """GET /api/dashboard/stats still returns data (used by standards summary page)"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/stats",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        # Verify key fields exist
        assert "overall_score" in data, "Missing overall_score in dashboard stats"
        assert "maturity_level" in data, "Missing maturity_level in dashboard stats"
        assert "aligned_domains" in data, "Missing aligned_domains in dashboard stats"
        print(f"✓ Dashboard stats endpoint works correctly")

    def test_reports_endpoint_still_works(self, auth_token):
        """GET /api/reports still returns data (used by standards summary page)"""
        response = requests.get(
            f"{BASE_URL}/api/reports",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        # Response should be a list
        data = response.json()
        assert isinstance(data, list), "Reports endpoint should return a list"
        print(f"✓ Reports endpoint works correctly ({len(data)} reports)")

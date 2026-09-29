"""
Phishing Simulation Feature Tests
Tests for campaign creation, employee targeting, email templates, tracked opens/clicks/reports,
safe internal training landing page, and results dashboard with employee-level outcomes.
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials from the review request
TEST_EMAIL = f"phishui_98a3f0db@example.com"
TEST_PASSWORD = "StrongPass!234"
EXISTING_SIMULATION_TOKEN = "WN0SBmadQGiJePoeU4y8Mw"


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def auth_token(api_client):
    """Get authentication token for the test account"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    if response.status_code == 200:
        data = response.json()
        if data.get("mfa_required"):
            pytest.skip("MFA required - cannot proceed with automated tests")
        return data.get("access_token")
    pytest.skip(f"Authentication failed with status {response.status_code}: {response.text}")


@pytest.fixture(scope="module")
def authenticated_client(api_client, auth_token):
    """Session with auth header"""
    api_client.headers.update({"Authorization": f"Bearer {auth_token}"})
    return api_client


class TestPhishingTemplates:
    """Tests for GET /api/phishing/templates"""
    
    def test_get_templates_requires_auth(self, api_client):
        """Templates endpoint should require authentication"""
        # Use a fresh session without auth
        response = requests.get(f"{BASE_URL}/api/phishing/templates")
        assert response.status_code == 401 or response.status_code == 403
        print("✓ Templates endpoint correctly requires authentication")
    
    def test_get_templates_returns_list(self, authenticated_client):
        """GET /api/phishing/templates should return a list of templates"""
        response = authenticated_client.get(f"{BASE_URL}/api/phishing/templates")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1, "Should have at least one phishing template"
        print(f"✓ Templates endpoint returned {len(data)} templates")
    
    def test_template_structure(self, authenticated_client):
        """Each template should have required fields"""
        response = authenticated_client.get(f"{BASE_URL}/api/phishing/templates")
        assert response.status_code == 200
        
        data = response.json()
        required_fields = ["id", "name", "category", "difficulty", "subject", "preview_text", "scenario", "cta_label"]
        
        for template in data:
            for field in required_fields:
                assert field in template, f"Template missing required field: {field}"
            
            # Validate difficulty is one of expected values
            assert template["difficulty"] in ["easy", "medium", "hard"], f"Invalid difficulty: {template['difficulty']}"
            print(f"✓ Template '{template['name']}' has all required fields")


class TestPhishingCampaigns:
    """Tests for campaign CRUD operations"""
    
    def test_list_campaigns_requires_auth(self, api_client):
        """Campaigns list endpoint should require authentication"""
        response = requests.get(f"{BASE_URL}/api/phishing/campaigns")
        assert response.status_code == 401 or response.status_code == 403
        print("✓ Campaigns list endpoint correctly requires authentication")
    
    def test_list_campaigns_returns_list(self, authenticated_client):
        """GET /api/phishing/campaigns should return a list"""
        response = authenticated_client.get(f"{BASE_URL}/api/phishing/campaigns")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Campaigns list returned {len(data)} campaigns")
    
    def test_create_campaign_requires_name(self, authenticated_client):
        """Campaign creation should require a name"""
        response = authenticated_client.post(f"{BASE_URL}/api/phishing/campaigns", json={
            "name": "",
            "template_id": "password_reset_urgent",
            "target_employee_ids": []
        })
        # Should fail validation - either 400 or 422
        assert response.status_code in [400, 422]
        print("✓ Campaign creation correctly validates name requirement")
    
    def test_create_campaign_requires_employees(self, authenticated_client):
        """Campaign creation should require at least one employee"""
        response = authenticated_client.post(f"{BASE_URL}/api/phishing/campaigns", json={
            "name": "Test Campaign",
            "template_id": "password_reset_urgent",
            "target_employee_ids": []
        })
        assert response.status_code == 400
        data = response.json()
        assert "employee" in data.get("detail", "").lower() or "select" in data.get("detail", "").lower()
        print("✓ Campaign creation correctly requires at least one employee")
    
    def test_create_campaign_validates_template(self, authenticated_client):
        """Campaign creation should validate template ID"""
        response = authenticated_client.post(f"{BASE_URL}/api/phishing/campaigns", json={
            "name": "Test Campaign",
            "template_id": "invalid_template_id_xyz",
            "target_employee_ids": ["some-id"]
        })
        assert response.status_code == 400
        print("✓ Campaign creation correctly validates template ID")


class TestCampaignCreationWithEmployees:
    """Tests for creating campaigns with actual employees"""
    
    @pytest.fixture(scope="class")
    def test_employee(self, authenticated_client):
        """Get an existing employee for campaign testing"""
        # First try to get existing employees
        response = authenticated_client.get(f"{BASE_URL}/api/employees")
        if response.status_code == 200:
            employees = response.json()
            if employees:
                return employees[0]
        
        # If no employees exist, try to create one
        unique_id = str(uuid.uuid4())[:8]
        employee_data = {
            "name": f"TEST_Phishing_Employee_{unique_id}",
            "email": f"test_phishing_{unique_id}@example.com",
            "department": "Security Testing"
        }
        response = authenticated_client.post(f"{BASE_URL}/api/employees", json=employee_data)
        if response.status_code == 201:
            return response.json()
        elif response.status_code == 403:
            pytest.skip("Employee limit reached on current plan and no existing employees")
        pytest.skip(f"Could not get or create test employee: {response.status_code} - {response.text}")
    
    def test_create_draft_campaign(self, authenticated_client, test_employee):
        """Create a draft campaign without sending immediately"""
        unique_id = str(uuid.uuid4())[:8]
        campaign_data = {
            "name": f"TEST_Draft_Campaign_{unique_id}",
            "template_id": "password_reset_urgent",
            "target_employee_ids": [test_employee["id"]],
            "send_immediately": False
        }
        
        response = authenticated_client.post(f"{BASE_URL}/api/phishing/campaigns", json=campaign_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["name"] == campaign_data["name"]
        assert data["template_id"] == "password_reset_urgent"
        assert data["status"] == "draft"
        assert data["total_targets"] == 1
        assert data["delivered_count"] == 0
        assert data["clicked_count"] == 0
        assert data["reported_count"] == 0
        assert "id" in data
        assert "created_at" in data
        assert "recipients" in data
        assert len(data["recipients"]) == 1
        
        # Verify recipient structure
        recipient = data["recipients"][0]
        assert recipient["employee_id"] == test_employee["id"]
        assert recipient["employee_name"] == test_employee["name"]
        assert recipient["delivery_status"] == "pending"
        
        print(f"✓ Draft campaign created successfully with ID: {data['id']}")
        return data
    
    def test_create_and_send_campaign(self, authenticated_client, test_employee):
        """Create a campaign with send_immediately=true"""
        unique_id = str(uuid.uuid4())[:8]
        campaign_data = {
            "name": f"TEST_Send_Campaign_{unique_id}",
            "template_id": "invoice_review",
            "target_employee_ids": [test_employee["id"]],
            "send_immediately": True
        }
        
        response = authenticated_client.post(f"{BASE_URL}/api/phishing/campaigns", json=campaign_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["name"] == campaign_data["name"]
        # Status should be sent, partially_sent, or failed (Resend sandbox may reject)
        assert data["status"] in ["sent", "partially_sent", "failed"]
        assert data["sent_at"] is not None
        
        # Verify recipient has delivery status updated
        recipient = data["recipients"][0]
        assert recipient["delivery_status"] in ["sent", "failed"]
        
        print(f"✓ Campaign created and sent with status: {data['status']}")
        print(f"  Delivery status: {recipient['delivery_status']}")
        if recipient.get("delivery_error"):
            print(f"  Delivery error (expected in sandbox): {recipient['delivery_error']}")
    
    def test_get_campaign_detail(self, authenticated_client, test_employee):
        """GET /api/phishing/campaigns/{id} returns recipient-level outcomes"""
        # First create a campaign
        unique_id = str(uuid.uuid4())[:8]
        campaign_data = {
            "name": f"TEST_Detail_Campaign_{unique_id}",
            "template_id": "shared_document",
            "target_employee_ids": [test_employee["id"]],
            "send_immediately": False
        }
        
        create_response = authenticated_client.post(f"{BASE_URL}/api/phishing/campaigns", json=campaign_data)
        assert create_response.status_code == 200
        campaign_id = create_response.json()["id"]
        
        # Now get the campaign detail
        detail_response = authenticated_client.get(f"{BASE_URL}/api/phishing/campaigns/{campaign_id}")
        assert detail_response.status_code == 200
        
        data = detail_response.json()
        assert data["id"] == campaign_id
        assert "recipients" in data
        assert len(data["recipients"]) == 1
        
        # Verify recipient-level outcome fields
        recipient = data["recipients"][0]
        required_recipient_fields = [
            "id", "employee_id", "employee_name", "employee_email", "department",
            "delivery_status", "opened_at", "clicked_at", "reported_at"
        ]
        for field in required_recipient_fields:
            assert field in recipient, f"Recipient missing field: {field}"
        
        print(f"✓ Campaign detail returned with recipient-level outcomes")
    
    def test_campaign_not_found(self, authenticated_client):
        """GET /api/phishing/campaigns/{id} returns 404 for non-existent campaign"""
        response = authenticated_client.get(f"{BASE_URL}/api/phishing/campaigns/non-existent-id-xyz")
        assert response.status_code == 404
        print("✓ Non-existent campaign correctly returns 404")


class TestPhishingSimulationLanding:
    """Tests for the public simulation landing page and tracking"""
    
    def test_simulation_landing_marks_click(self):
        """GET /api/phishing/simulations/{token} marks click and returns training content"""
        response = requests.get(f"{BASE_URL}/api/phishing/simulations/{EXISTING_SIMULATION_TOKEN}")
        
        if response.status_code == 404:
            pytest.skip("Existing simulation token not found - may have been cleaned up")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify training content structure
        required_fields = [
            "campaign_name", "template_name", "employee_name", "company_name",
            "difficulty", "category", "scenario", "red_flags", "learning_points",
            "already_reported"
        ]
        for field in required_fields:
            assert field in data, f"Training content missing field: {field}"
        
        assert isinstance(data["red_flags"], list)
        assert isinstance(data["learning_points"], list)
        assert len(data["red_flags"]) >= 1
        assert len(data["learning_points"]) >= 1
        
        print(f"✓ Simulation landing returned training content for {data['employee_name']}")
        print(f"  Campaign: {data['campaign_name']}")
        print(f"  Template: {data['template_name']}")
        print(f"  Already reported: {data['already_reported']}")
    
    def test_simulation_report_action(self):
        """POST /api/phishing/simulations/{token}/report logs the report action"""
        response = requests.post(f"{BASE_URL}/api/phishing/simulations/{EXISTING_SIMULATION_TOKEN}/report")
        
        if response.status_code == 404:
            pytest.skip("Existing simulation token not found")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "message" in data
        assert "reported" in data
        assert data["reported"] == True
        
        print(f"✓ Report action logged: {data['message']}")
    
    def test_simulation_invalid_token(self):
        """Invalid simulation token returns 404"""
        response = requests.get(f"{BASE_URL}/api/phishing/simulations/invalid-token-xyz")
        assert response.status_code == 404
        print("✓ Invalid simulation token correctly returns 404")
    
    def test_report_invalid_token(self):
        """Report with invalid token returns 404"""
        response = requests.post(f"{BASE_URL}/api/phishing/simulations/invalid-token-xyz/report")
        assert response.status_code == 404
        print("✓ Report with invalid token correctly returns 404")


class TestCampaignAggregatedResults:
    """Tests for campaign list with aggregated results"""
    
    def test_campaigns_have_aggregated_counts(self, authenticated_client):
        """GET /api/phishing/campaigns returns campaigns with aggregated results"""
        response = authenticated_client.get(f"{BASE_URL}/api/phishing/campaigns")
        assert response.status_code == 200
        
        data = response.json()
        if len(data) == 0:
            pytest.skip("No campaigns exist to verify aggregated results")
        
        campaign = data[0]
        aggregated_fields = [
            "total_targets", "delivered_count", "opened_count", 
            "clicked_count", "reported_count"
        ]
        
        for field in aggregated_fields:
            assert field in campaign, f"Campaign missing aggregated field: {field}"
            assert isinstance(campaign[field], int), f"{field} should be an integer"
        
        print(f"✓ Campaign '{campaign['name']}' has aggregated results:")
        print(f"  Total targets: {campaign['total_targets']}")
        print(f"  Delivered: {campaign['delivered_count']}")
        print(f"  Opened: {campaign['opened_count']}")
        print(f"  Clicked: {campaign['clicked_count']}")
        print(f"  Reported: {campaign['reported_count']}")


class TestOpenPixelTracking:
    """Tests for email open tracking pixel"""
    
    def test_open_tracking_returns_gif(self):
        """GET /api/phishing/track/open/{token} returns a transparent GIF"""
        response = requests.get(f"{BASE_URL}/api/phishing/track/open/{EXISTING_SIMULATION_TOKEN}")
        
        # Should return 200 with image/gif content type
        assert response.status_code == 200
        assert "image/gif" in response.headers.get("content-type", "")
        
        # Verify it's a valid GIF (starts with GIF magic bytes)
        assert response.content[:3] == b"GIF"
        
        print("✓ Open tracking pixel returns valid transparent GIF")
    
    def test_open_tracking_invalid_token(self):
        """Open tracking with invalid token still returns GIF (silent tracking)"""
        response = requests.get(f"{BASE_URL}/api/phishing/track/open/invalid-token-xyz")
        
        # Should still return 200 with GIF (silent failure for tracking)
        assert response.status_code == 200
        assert "image/gif" in response.headers.get("content-type", "")
        
        print("✓ Open tracking with invalid token returns GIF (silent tracking)")


class TestCoreAuthDashboardRegression:
    """Regression tests to ensure core auth/dashboard flows still work"""
    
    def test_auth_me_still_works(self, authenticated_client):
        """GET /api/auth/me should still work after phishing additions"""
        response = authenticated_client.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 200
        
        data = response.json()
        assert "id" in data
        assert "email" in data
        assert "company_name" in data
        
        print(f"✓ Auth /me endpoint works: {data['email']}")
    
    def test_employees_list_still_works(self, authenticated_client):
        """GET /api/employees should still work"""
        response = authenticated_client.get(f"{BASE_URL}/api/employees")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        
        print(f"✓ Employees list works: {len(data)} employees")
    
    def test_dashboard_stats_still_works(self, authenticated_client):
        """GET /api/dashboard/stats should still work"""
        response = authenticated_client.get(f"{BASE_URL}/api/dashboard/stats")
        assert response.status_code == 200
        
        data = response.json()
        assert "overall_score" in data or "total_employees" in data
        
        print("✓ Dashboard stats endpoint works")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

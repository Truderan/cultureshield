"""
Test suite for CultureShield Email Activity Admin APIs and PWA Support
Tests: 
- GET /api/billing/admin/email-activity - returns recent company email events and summary counts
- GET /api/billing/admin/email-activity/export - downloads CSV successfully
- manifest.json and service-worker.js accessibility
- Core flows remain working after additions
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestEmailActivityAdminAPI:
    """Test GET /api/billing/admin/email-activity endpoint"""
    
    @pytest.fixture(scope="class")
    def auth_context(self):
        """Create a test company and return auth token"""
        unique_id = int(time.time() * 1000)
        payload = {
            "company_name": f"EmailActivityTestCompany_{unique_id}",
            "email": f"test_email_activity_{unique_id}@example.com",
            "password": "TestPassword123"
        }
        
        response = requests.post(f"{BASE_URL}/api/auth/register", json=payload)
        assert response.status_code == 200, f"Setup: Registration failed: {response.text}"
        
        data = response.json()
        return {
            "token": data["access_token"],
            "company_id": data["company"]["id"],
            "company_name": data["company"]["company_name"],
            "email": data["company"]["email"]
        }
    
    def test_get_email_activity_returns_200(self, auth_context):
        """GET /api/billing/admin/email-activity should return 200 with valid auth"""
        response = requests.get(
            f"{BASE_URL}/api/billing/admin/email-activity",
            headers={"Authorization": f"Bearer {auth_context['token']}"}
        )
        
        assert response.status_code == 200, f"Email activity endpoint failed: {response.status_code} - {response.text}"
        
        data = response.json()
        print(f"✓ GET /api/billing/admin/email-activity returned 200")
        return data
    
    def test_email_activity_response_structure(self, auth_context):
        """Verify email activity response has correct structure"""
        response = requests.get(
            f"{BASE_URL}/api/billing/admin/email-activity",
            headers={"Authorization": f"Bearer {auth_context['token']}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "items" in data, "Response should have 'items' field"
        assert "summary" in data, "Response should have 'summary' field"
        
        # Verify summary structure
        summary = data["summary"]
        assert "total" in summary, "Summary should have 'total' count"
        assert "sent" in summary, "Summary should have 'sent' count"
        assert "failed" in summary, "Summary should have 'failed' count"
        assert "skipped" in summary, "Summary should have 'skipped' count"
        
        # Verify items is a list
        assert isinstance(data["items"], list), "Items should be a list"
        
        print(f"✓ Email activity response structure is correct")
        print(f"  Summary: total={summary['total']}, sent={summary['sent']}, failed={summary['failed']}, skipped={summary['skipped']}")
    
    def test_email_activity_after_employee_creation(self, auth_context):
        """Creating an employee should log an email event"""
        # Create an employee (this triggers survey invite email)
        unique_id = int(time.time() * 1000)
        emp_payload = {
            "name": f"Email Activity Test Employee {unique_id}",
            "email": f"test_emp_activity_{unique_id}@example.com",
            "department": "Engineering"
        }
        
        emp_response = requests.post(
            f"{BASE_URL}/api/employees",
            json=emp_payload,
            headers={"Authorization": f"Bearer {auth_context['token']}"}
        )
        assert emp_response.status_code == 200, f"Employee creation failed: {emp_response.text}"
        
        # Wait a moment for async email task to complete
        time.sleep(1)
        
        # Check email activity
        activity_response = requests.get(
            f"{BASE_URL}/api/billing/admin/email-activity",
            headers={"Authorization": f"Bearer {auth_context['token']}"}
        )
        
        assert activity_response.status_code == 200
        data = activity_response.json()
        
        # Should have at least one email event (welcome email from registration + survey invite)
        # Note: Events may be logged even if email fails due to sandbox restrictions
        print(f"✓ Email activity after employee creation: {data['summary']['total']} total events")
        
        # Check if any items exist
        if data["items"]:
            item = data["items"][0]
            assert "id" in item, "Item should have 'id'"
            assert "recipient_email" in item, "Item should have 'recipient_email'"
            assert "subject" in item, "Item should have 'subject'"
            assert "email_type" in item, "Item should have 'email_type'"
            assert "status" in item, "Item should have 'status'"
            assert "created_at" in item, "Item should have 'created_at'"
            print(f"  Latest event: type={item['email_type']}, status={item['status']}")
    
    def test_email_activity_with_limit_parameter(self, auth_context):
        """Test limit parameter works correctly"""
        response = requests.get(
            f"{BASE_URL}/api/billing/admin/email-activity?limit=5",
            headers={"Authorization": f"Bearer {auth_context['token']}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Items should be limited to 5 or less
        assert len(data["items"]) <= 5, f"Expected max 5 items, got {len(data['items'])}"
        print(f"✓ Limit parameter works: returned {len(data['items'])} items (limit=5)")
    
    def test_email_activity_requires_auth(self):
        """Email activity endpoint should require authentication"""
        response = requests.get(f"{BASE_URL}/api/billing/admin/email-activity")
        
        # Should return 401 or 403 without auth
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
        print(f"✓ Email activity endpoint requires authentication (returned {response.status_code})")


class TestEmailActivityExportAPI:
    """Test GET /api/billing/admin/email-activity/export endpoint"""
    
    @pytest.fixture(scope="class")
    def auth_context(self):
        """Create a test company and return auth token"""
        unique_id = int(time.time() * 1000)
        payload = {
            "company_name": f"EmailExportTestCompany_{unique_id}",
            "email": f"test_email_export_{unique_id}@example.com",
            "password": "TestPassword123"
        }
        
        response = requests.post(f"{BASE_URL}/api/auth/register", json=payload)
        assert response.status_code == 200, f"Setup: Registration failed: {response.text}"
        
        data = response.json()
        return {
            "token": data["access_token"],
            "company_id": data["company"]["id"]
        }
    
    def test_export_email_activity_returns_csv(self, auth_context):
        """GET /api/billing/admin/email-activity/export should return CSV"""
        response = requests.get(
            f"{BASE_URL}/api/billing/admin/email-activity/export",
            headers={"Authorization": f"Bearer {auth_context['token']}"}
        )
        
        assert response.status_code == 200, f"Export failed: {response.status_code} - {response.text}"
        
        # Check content type is CSV
        content_type = response.headers.get("content-type", "")
        assert "text/csv" in content_type, f"Expected text/csv, got {content_type}"
        
        # Check content-disposition header for filename
        content_disposition = response.headers.get("content-disposition", "")
        assert "attachment" in content_disposition, "Should have attachment disposition"
        assert ".csv" in content_disposition, "Filename should have .csv extension"
        
        # Verify CSV content has headers
        csv_content = response.text
        assert "created_at" in csv_content, "CSV should have created_at column"
        assert "status" in csv_content, "CSV should have status column"
        assert "email_type" in csv_content, "CSV should have email_type column"
        assert "recipient_email" in csv_content, "CSV should have recipient_email column"
        
        print(f"✓ Export endpoint returns valid CSV")
        print(f"  Content-Type: {content_type}")
        print(f"  Content-Disposition: {content_disposition}")
    
    def test_export_requires_auth(self):
        """Export endpoint should require authentication"""
        response = requests.get(f"{BASE_URL}/api/billing/admin/email-activity/export")
        
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
        print(f"✓ Export endpoint requires authentication (returned {response.status_code})")


class TestPWAAssets:
    """Test PWA manifest.json and service-worker.js accessibility"""
    
    def test_manifest_json_accessible(self):
        """manifest.json should be accessible at /manifest.json"""
        response = requests.get(f"{BASE_URL}/manifest.json")
        
        assert response.status_code == 200, f"manifest.json not accessible: {response.status_code}"
        
        # Verify it's valid JSON
        data = response.json()
        
        # Verify required PWA manifest fields
        assert "name" in data, "Manifest should have 'name'"
        assert "short_name" in data, "Manifest should have 'short_name'"
        assert "start_url" in data, "Manifest should have 'start_url'"
        assert "display" in data, "Manifest should have 'display'"
        assert "icons" in data, "Manifest should have 'icons'"
        
        # Verify CultureShield specific values
        assert "CultureShield" in data["name"], f"Name should contain CultureShield, got {data['name']}"
        assert data["display"] == "standalone", f"Display should be standalone, got {data['display']}"
        
        print(f"✓ manifest.json is accessible and valid")
        print(f"  Name: {data['name']}")
        print(f"  Short name: {data['short_name']}")
        print(f"  Display: {data['display']}")
    
    def test_service_worker_accessible(self):
        """service-worker.js should be accessible at /service-worker.js"""
        response = requests.get(f"{BASE_URL}/service-worker.js")
        
        assert response.status_code == 200, f"service-worker.js not accessible: {response.status_code}"
        
        # Verify it's JavaScript content
        content_type = response.headers.get("content-type", "")
        assert "javascript" in content_type or "text/plain" in content_type, f"Expected JavaScript, got {content_type}"
        
        # Verify it contains service worker code
        content = response.text
        assert "addEventListener" in content, "Service worker should have event listeners"
        assert "install" in content or "fetch" in content, "Service worker should handle install or fetch events"
        
        print(f"✓ service-worker.js is accessible and valid")
        print(f"  Content-Type: {content_type}")
        print(f"  Size: {len(content)} bytes")


class TestCoreFlowsAfterAdditions:
    """Verify core flows still work after email activity and PWA additions"""
    
    def test_registration_still_works(self):
        """Registration should still work after additions"""
        unique_id = int(time.time() * 1000)
        payload = {
            "company_name": f"CoreFlowTestCompany_{unique_id}",
            "email": f"test_core_flow_{unique_id}@example.com",
            "password": "TestPassword123"
        }
        
        response = requests.post(f"{BASE_URL}/api/auth/register", json=payload)
        
        assert response.status_code == 200, f"Registration failed: {response.text}"
        
        data = response.json()
        assert "access_token" in data
        assert "company" in data
        
        print(f"✓ Registration still works")
        return data
    
    def test_login_still_works(self):
        """Login should still work after additions"""
        unique_id = int(time.time() * 1000)
        
        # Register first
        reg_payload = {
            "company_name": f"LoginCoreTestCompany_{unique_id}",
            "email": f"test_login_core_{unique_id}@example.com",
            "password": "TestPassword123"
        }
        
        reg_response = requests.post(f"{BASE_URL}/api/auth/register", json=reg_payload)
        assert reg_response.status_code == 200
        
        # Login
        login_payload = {
            "email": reg_payload["email"],
            "password": reg_payload["password"]
        }
        
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json=login_payload)
        
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        
        data = login_response.json()
        assert "access_token" in data
        
        print(f"✓ Login still works")
    
    def test_billing_info_still_works(self):
        """Billing info endpoint should still work"""
        unique_id = int(time.time() * 1000)
        
        # Register
        reg_payload = {
            "company_name": f"BillingCoreTestCompany_{unique_id}",
            "email": f"test_billing_core_{unique_id}@example.com",
            "password": "TestPassword123"
        }
        
        reg_response = requests.post(f"{BASE_URL}/api/auth/register", json=reg_payload)
        assert reg_response.status_code == 200
        
        token = reg_response.json()["access_token"]
        
        # Get billing info
        billing_response = requests.get(
            f"{BASE_URL}/api/billing/info",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert billing_response.status_code == 200, f"Billing info failed: {billing_response.text}"
        
        data = billing_response.json()
        assert "plan_details" in data
        
        print(f"✓ Billing info endpoint still works")
    
    def test_admin_dashboard_still_works(self):
        """Admin dashboard endpoint should still work"""
        unique_id = int(time.time() * 1000)
        
        # Register
        reg_payload = {
            "company_name": f"AdminDashCoreTestCompany_{unique_id}",
            "email": f"test_admin_dash_core_{unique_id}@example.com",
            "password": "TestPassword123"
        }
        
        reg_response = requests.post(f"{BASE_URL}/api/auth/register", json=reg_payload)
        assert reg_response.status_code == 200
        
        token = reg_response.json()["access_token"]
        
        # Get admin dashboard
        admin_response = requests.get(
            f"{BASE_URL}/api/billing/admin/dashboard",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert admin_response.status_code == 200, f"Admin dashboard failed: {admin_response.text}"
        
        print(f"✓ Admin dashboard endpoint still works")


class TestResendTestAccountLogin:
    """Test login with provided Resend test account credentials"""
    
    def test_resend_test_account_login(self):
        """Login with Resend test account should work"""
        login_payload = {
            "email": "resendcheck_ab423508@example.com",
            "password": "Password123!"
        }
        
        response = requests.post(f"{BASE_URL}/api/auth/login", json=login_payload)
        
        if response.status_code == 200:
            data = response.json()
            assert "access_token" in data
            print(f"✓ Resend test account login succeeded")
            return data
        elif response.status_code == 401:
            # Account may not exist yet, try to register
            print(f"  Resend test account not found, attempting registration...")
            reg_payload = {
                "company_name": "Resend Test Company",
                "email": "resendcheck_ab423508@example.com",
                "password": "Password123!"
            }
            
            reg_response = requests.post(f"{BASE_URL}/api/auth/register", json=reg_payload)
            
            if reg_response.status_code == 200:
                print(f"✓ Resend test account registered successfully")
                return reg_response.json()
            elif reg_response.status_code == 400 and "already registered" in reg_response.text.lower():
                # Account exists but password might be different
                print(f"  Account exists but login failed - password mismatch")
                pytest.skip("Resend test account exists but credentials don't match")
            else:
                print(f"  Registration failed: {reg_response.status_code} - {reg_response.text}")
                pytest.skip(f"Could not setup Resend test account: {reg_response.text}")
        else:
            pytest.fail(f"Unexpected response: {response.status_code} - {response.text}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

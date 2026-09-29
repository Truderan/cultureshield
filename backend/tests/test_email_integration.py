"""
Test suite for CultureShield Email Integration with Resend
Tests: Registration (welcome email), Employee creation (survey invite), Billing checkout
Focus: Verify core app flows work even when Resend returns sandbox errors for unverified recipients
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestRegistrationWithEmailIntegration:
    """Test POST /api/auth/register still succeeds after email integration"""
    
    def test_register_succeeds_with_email_integration(self):
        """Registration should succeed even if welcome email fails due to Resend sandbox restrictions"""
        unique_id = int(time.time() * 1000)
        payload = {
            "company_name": f"EmailTestCompany_{unique_id}",
            "email": f"test_email_reg_{unique_id}@example.com",
            "password": "TestPassword123"
        }
        
        response = requests.post(f"{BASE_URL}/api/auth/register", json=payload)
        
        # Core assertion: Registration must succeed regardless of email delivery status
        assert response.status_code == 200, f"Registration failed with status {response.status_code}: {response.text}"
        
        data = response.json()
        assert "access_token" in data, "Missing access_token in response"
        assert "company" in data, "Missing company in response"
        assert data["company"]["email"] == payload["email"], "Email mismatch"
        assert data["company"]["company_name"] == payload["company_name"], "Company name mismatch"
        assert "id" in data["company"], "Missing company id"
        
        print(f"✓ Registration succeeded for {payload['email']} (email integration did not break flow)")
        return data
    
    def test_register_multiple_accounts_sequentially(self):
        """Multiple registrations should all succeed without email integration blocking"""
        for i in range(3):
            unique_id = int(time.time() * 1000) + i
            payload = {
                "company_name": f"MultiRegCompany_{unique_id}",
                "email": f"test_multi_reg_{unique_id}@example.com",
                "password": "TestPassword123"
            }
            
            response = requests.post(f"{BASE_URL}/api/auth/register", json=payload)
            assert response.status_code == 200, f"Registration {i+1} failed: {response.text}"
            
            data = response.json()
            assert "access_token" in data
            print(f"✓ Registration {i+1}/3 succeeded")
        
        print("✓ All 3 sequential registrations succeeded")


class TestEmployeeCreationWithEmailIntegration:
    """Test POST /api/employees still succeeds after survey invite email integration"""
    
    @pytest.fixture(scope="class")
    def auth_context(self):
        """Create a test company and return auth token"""
        unique_id = int(time.time() * 1000)
        payload = {
            "company_name": f"EmployeeTestCompany_{unique_id}",
            "email": f"test_emp_company_{unique_id}@example.com",
            "password": "TestPassword123"
        }
        
        response = requests.post(f"{BASE_URL}/api/auth/register", json=payload)
        assert response.status_code == 200, f"Setup: Registration failed: {response.text}"
        
        data = response.json()
        return {
            "token": data["access_token"],
            "company_id": data["company"]["id"],
            "company_name": data["company"]["company_name"]
        }
    
    def test_create_employee_succeeds_with_email_integration(self, auth_context):
        """Employee creation should succeed even if survey invite email fails"""
        unique_id = int(time.time() * 1000)
        payload = {
            "name": f"Test Employee {unique_id}",
            "email": f"test_employee_{unique_id}@example.com",
            "department": "Engineering"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/employees",
            json=payload,
            headers={"Authorization": f"Bearer {auth_context['token']}"}
        )
        
        # Core assertion: Employee creation must succeed regardless of email delivery
        assert response.status_code == 200, f"Employee creation failed with status {response.status_code}: {response.text}"
        
        data = response.json()
        assert "id" in data, "Missing employee id"
        assert data["name"] == payload["name"], "Name mismatch"
        assert data["email"] == payload["email"], "Email mismatch"
        assert data["department"] == payload["department"], "Department mismatch"
        assert "survey_link" in data, "Missing survey_link"
        assert data["survey_completed"] == False, "New employee should have survey_completed=False"
        
        print(f"✓ Employee creation succeeded for {payload['email']} (email integration did not break flow)")
        return data
    
    def test_create_multiple_employees_sequentially(self, auth_context):
        """Multiple employee creations should all succeed without email integration blocking"""
        for i in range(3):
            unique_id = int(time.time() * 1000) + i
            payload = {
                "name": f"Multi Employee {unique_id}",
                "email": f"test_multi_emp_{unique_id}@example.com",
                "department": "Sales"
            }
            
            response = requests.post(
                f"{BASE_URL}/api/employees",
                json=payload,
                headers={"Authorization": f"Bearer {auth_context['token']}"}
            )
            assert response.status_code == 200, f"Employee creation {i+1} failed: {response.text}"
            
            data = response.json()
            assert "id" in data
            print(f"✓ Employee creation {i+1}/3 succeeded")
        
        print("✓ All 3 sequential employee creations succeeded")
    
    def test_get_employees_after_creation(self, auth_context):
        """Verify employees are persisted correctly after creation with email integration"""
        response = requests.get(
            f"{BASE_URL}/api/employees",
            headers={"Authorization": f"Bearer {auth_context['token']}"}
        )
        
        assert response.status_code == 200, f"GET employees failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        # We created at least 4 employees in previous tests
        assert len(data) >= 4, f"Expected at least 4 employees, got {len(data)}"
        
        print(f"✓ GET /employees returned {len(data)} employees")


class TestBulkImportWithEmailIntegration:
    """Test POST /api/employees/bulk-import still succeeds after email integration"""
    
    @pytest.fixture(scope="class")
    def auth_context(self):
        """Create a test company and return auth token"""
        unique_id = int(time.time() * 1000)
        payload = {
            "company_name": f"BulkImportTestCompany_{unique_id}",
            "email": f"test_bulk_company_{unique_id}@example.com",
            "password": "TestPassword123"
        }
        
        response = requests.post(f"{BASE_URL}/api/auth/register", json=payload)
        assert response.status_code == 200, f"Setup: Registration failed: {response.text}"
        
        data = response.json()
        return {
            "token": data["access_token"],
            "company_id": data["company"]["id"]
        }
    
    def test_bulk_import_succeeds_with_email_integration(self, auth_context):
        """Bulk import should succeed even if survey invite emails fail"""
        unique_id = int(time.time() * 1000)
        payload = {
            "employees": [
                {"name": f"Bulk Emp 1 {unique_id}", "email": f"bulk1_{unique_id}@example.com", "department": "HR"},
                {"name": f"Bulk Emp 2 {unique_id}", "email": f"bulk2_{unique_id}@example.com", "department": "Finance"},
                {"name": f"Bulk Emp 3 {unique_id}", "email": f"bulk3_{unique_id}@example.com", "department": "IT"}
            ]
        }
        
        response = requests.post(
            f"{BASE_URL}/api/employees/bulk-import",
            json=payload,
            headers={"Authorization": f"Bearer {auth_context['token']}"}
        )
        
        # Core assertion: Bulk import must succeed regardless of email delivery
        assert response.status_code == 200, f"Bulk import failed with status {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["total_processed"] == 3, "Should process 3 employees"
        assert data["successful"] == 3, f"All 3 should succeed, got {data['successful']}"
        assert data["failed"] == 0, f"None should fail, got {data['failed']}"
        assert len(data["employees_created"]) == 3, "Should return 3 created employees"
        
        print(f"✓ Bulk import succeeded: {data['successful']}/{data['total_processed']} employees created")


class TestBillingCheckoutWithEmailIntegration:
    """Test POST /api/billing/checkout/subscribe still succeeds after billing email integration"""
    
    @pytest.fixture(scope="class")
    def auth_context(self):
        """Create a test company and return auth token"""
        unique_id = int(time.time() * 1000)
        payload = {
            "company_name": f"BillingTestCompany_{unique_id}",
            "email": f"test_billing_company_{unique_id}@example.com",
            "password": "TestPassword123"
        }
        
        response = requests.post(f"{BASE_URL}/api/auth/register", json=payload)
        assert response.status_code == 200, f"Setup: Registration failed: {response.text}"
        
        data = response.json()
        return {
            "token": data["access_token"],
            "company_id": data["company"]["id"],
            "email": data["company"]["email"]
        }
    
    def test_checkout_subscribe_succeeds_with_email_integration(self, auth_context):
        """Billing checkout should succeed even if billing notification email fails"""
        payload = {
            "plan_id": "starter",
            "callback_url": "https://shield-billing-demo.preview.emergentagent.com/billing/callback",
            "currency": "NGN"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/billing/checkout/subscribe",
            json=payload,
            headers={"Authorization": f"Bearer {auth_context['token']}"}
        )
        
        # Core assertion: Checkout must succeed regardless of email delivery
        assert response.status_code == 200, f"Checkout failed with status {response.status_code}: {response.text}"
        
        data = response.json()
        assert "authorization_url" in data, "Missing authorization_url"
        assert "reference" in data, "Missing reference"
        assert "access_code" in data, "Missing access_code"
        
        # Verify the authorization URL is a valid Paystack URL
        assert "paystack.co" in data["authorization_url"], "Authorization URL should be Paystack"
        
        print(f"✓ Billing checkout succeeded with reference: {data['reference']}")
        return data
    
    def test_get_billing_info_after_checkout(self, auth_context):
        """Verify billing info endpoint works after checkout"""
        response = requests.get(
            f"{BASE_URL}/api/billing/info",
            headers={"Authorization": f"Bearer {auth_context['token']}"}
        )
        
        assert response.status_code == 200, f"GET billing info failed: {response.text}"
        
        data = response.json()
        assert "subscription" in data or data.get("subscription") is None, "Response should have subscription field"
        assert "plan_details" in data, "Response should have plan_details"
        
        print(f"✓ GET /billing/info returned valid response")
    
    def test_get_pricing_plans(self, auth_context):
        """Verify pricing plans endpoint works"""
        response = requests.get(
            f"{BASE_URL}/api/billing/plans",
            headers={"Authorization": f"Bearer {auth_context['token']}"}
        )
        
        assert response.status_code == 200, f"GET plans failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list of plans"
        assert len(data) >= 4, f"Expected at least 4 plans, got {len(data)}"
        
        # Verify plan structure
        plan_ids = [p["id"] for p in data]
        assert "free" in plan_ids, "Should have free plan"
        assert "starter" in plan_ids, "Should have starter plan"
        
        print(f"✓ GET /billing/plans returned {len(data)} plans")


class TestLoginFlowWithEmailIntegration:
    """Test login flow still works after email integration changes"""
    
    def test_login_after_registration_with_email(self):
        """Login should work for accounts created with email integration"""
        unique_id = int(time.time() * 1000)
        
        # Register
        reg_payload = {
            "company_name": f"LoginTestCompany_{unique_id}",
            "email": f"test_login_email_{unique_id}@example.com",
            "password": "TestPassword123"
        }
        
        reg_response = requests.post(f"{BASE_URL}/api/auth/register", json=reg_payload)
        assert reg_response.status_code == 200, f"Registration failed: {reg_response.text}"
        
        # Login
        login_payload = {
            "email": reg_payload["email"],
            "password": reg_payload["password"]
        }
        
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json=login_payload)
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        
        data = login_response.json()
        assert "access_token" in data, "Missing access_token"
        assert data["company"]["email"] == reg_payload["email"]
        
        print(f"✓ Login succeeded for account created with email integration")


class TestSurveySubmissionWithEmailIntegration:
    """Test survey submission triggers completion email without breaking flow"""
    
    @pytest.fixture(scope="class")
    def survey_context(self):
        """Create company, employee, and return context for survey testing"""
        unique_id = int(time.time() * 1000)
        
        # Register company
        reg_payload = {
            "company_name": f"SurveyTestCompany_{unique_id}",
            "email": f"test_survey_company_{unique_id}@example.com",
            "password": "TestPassword123"
        }
        
        reg_response = requests.post(f"{BASE_URL}/api/auth/register", json=reg_payload)
        assert reg_response.status_code == 200, f"Setup: Registration failed: {reg_response.text}"
        
        token = reg_response.json()["access_token"]
        
        # Create employee
        emp_payload = {
            "name": f"Survey Employee {unique_id}",
            "email": f"test_survey_emp_{unique_id}@example.com",
            "department": "Engineering"
        }
        
        emp_response = requests.post(
            f"{BASE_URL}/api/employees",
            json=emp_payload,
            headers={"Authorization": f"Bearer {token}"}
        )
        assert emp_response.status_code == 200, f"Setup: Employee creation failed: {emp_response.text}"
        
        employee = emp_response.json()
        
        return {
            "token": token,
            "employee_id": employee["id"],
            "employee_email": employee["email"]
        }
    
    def test_survey_submission_succeeds_with_email_integration(self, survey_context):
        """Survey submission should succeed even if completion email fails"""
        # Get survey questions first
        questions_response = requests.get(f"{BASE_URL}/api/survey/questions")
        assert questions_response.status_code == 200, "Failed to get survey questions"
        
        questions = questions_response.json()
        
        # Create responses (all middle-ground answers)
        responses = {q["id"]: 2 for q in questions}
        
        # Submit survey
        submit_response = requests.post(
            f"{BASE_URL}/api/survey/submit/{survey_context['employee_id']}",
            json={"responses": responses}
        )
        
        # Core assertion: Survey submission must succeed regardless of email delivery
        assert submit_response.status_code == 200, f"Survey submission failed: {submit_response.text}"
        
        data = submit_response.json()
        assert "id" in data, "Missing response id"
        assert "overall_score" in data, "Missing overall_score"
        assert "risk_level" in data, "Missing risk_level"
        assert data["employee_id"] == survey_context["employee_id"]
        
        print(f"✓ Survey submission succeeded with score: {data['overall_score']}, risk: {data['risk_level']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

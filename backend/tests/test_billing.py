"""
CultureShield AI - Billing System API Tests
Tests for Paystack billing, subscriptions, feature gating, and admin dashboard
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://shield-billing-demo.preview.emergentagent.com')

# Test credentials
TEST_EMAIL = "billingtest_06ebb117@example.com"
TEST_PASSWORD = "Password123!"

class TestBillingPlans:
    """Tests for public billing plans endpoint"""
    
    def test_get_plans_usd(self):
        """GET /api/billing/plans returns all plans in USD"""
        response = requests.get(f"{BASE_URL}/api/billing/plans")
        assert response.status_code == 200
        
        plans = response.json()
        assert len(plans) == 5
        
        plan_ids = [p["id"] for p in plans]
        assert "free" in plan_ids
        assert "starter" in plan_ids
        assert "business" in plan_ids
        assert "pro" in plan_ids
        assert "pay_per_audit" in plan_ids
    
    def test_get_plans_ngn(self):
        """GET /api/billing/plans?currency=NGN returns NGN prices"""
        response = requests.get(f"{BASE_URL}/api/billing/plans?currency=NGN")
        assert response.status_code == 200
        
        plans = response.json()
        for plan in plans:
            if plan["id"] != "free":
                assert plan["currency"] == "NGN"
                assert plan["display_price"] > 0
    
    def test_plan_structure(self):
        """Plans have required fields"""
        response = requests.get(f"{BASE_URL}/api/billing/plans")
        plans = response.json()
        
        for plan in plans:
            assert "id" in plan
            assert "name" in plan
            assert "price_usd" in plan
            assert "price_ngn" in plan
            assert "interval" in plan
            assert "max_employees" in plan
            assert "features" in plan
            assert isinstance(plan["features"], list)


class TestAuthentication:
    """Tests for auth endpoints (regression check)"""
    
    def test_login_success(self):
        """POST /api/auth/login succeeds with valid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200
        
        data = response.json()
        assert "access_token" in data
        assert "company" in data
        assert data["company"]["email"] == TEST_EMAIL
    
    def test_login_invalid_credentials(self):
        """POST /api/auth/login fails with invalid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "invalid@test.com",
            "password": "wrongpassword"
        })
        assert response.status_code == 401
    
    def test_me_endpoint_authenticated(self):
        """GET /api/auth/me returns user info when authenticated"""
        # Login first
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        token = login_response.json()["access_token"]
        
        # Test me endpoint
        response = requests.get(f"{BASE_URL}/api/auth/me", headers={
            "Authorization": f"Bearer {token}"
        })
        assert response.status_code == 200
        assert response.json()["email"] == TEST_EMAIL


class TestBillingInfo:
    """Tests for billing info and portal endpoints"""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        return response.json()["access_token"]
    
    def test_billing_info_returns_data(self, auth_token):
        """GET /api/billing/info returns billing portal data"""
        response = requests.get(f"{BASE_URL}/api/billing/info", headers={
            "Authorization": f"Bearer {auth_token}"
        })
        assert response.status_code == 200
        
        data = response.json()
        assert "subscription" in data
        assert "invoices" in data
        assert "payment_methods" in data
        assert "usage_this_period" in data
        assert "plan_details" in data
    
    def test_billing_info_subscription_structure(self, auth_token):
        """Billing info subscription has required fields"""
        response = requests.get(f"{BASE_URL}/api/billing/info", headers={
            "Authorization": f"Bearer {auth_token}"
        })
        data = response.json()
        
        if data["subscription"]:
            sub = data["subscription"]
            assert "plan_id" in sub
            assert "status" in sub
            assert "current_period_start" in sub
            assert "current_period_end" in sub
    
    def test_billing_portal_returns_url(self, auth_token):
        """GET /api/billing/portal returns in-app portal path"""
        response = requests.get(f"{BASE_URL}/api/billing/portal", headers={
            "Authorization": f"Bearer {auth_token}"
        })
        assert response.status_code == 200
        
        data = response.json()
        assert "portal_url" in data
        assert data["portal_url"] == "/billing?view=portal"
        assert data["status"] == "available"


class TestCheckout:
    """Tests for Paystack checkout initialization"""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        return response.json()["access_token"]
    
    def test_checkout_subscribe_initializes_paystack(self, auth_token):
        """POST /api/billing/checkout/subscribe returns Paystack authorization URL"""
        response = requests.post(
            f"{BASE_URL}/api/billing/checkout/subscribe",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "plan_id": "starter",
                "callback_url": "https://shield-billing-demo.preview.emergentagent.com/billing/callback",
                "currency": "NGN"
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "authorization_url" in data
        assert data["authorization_url"].startswith("https://checkout.paystack.com/")
        assert "reference" in data
        assert data["reference"].startswith("cs_")
        assert "access_code" in data
        assert data["amount"] == 43500  # Starter plan in kobo
        assert data["currency"] == "NGN"
    
    def test_checkout_subscribe_business_plan(self, auth_token):
        """Checkout for business plan returns correct amount"""
        response = requests.post(
            f"{BASE_URL}/api/billing/checkout/subscribe",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "plan_id": "business",
                "callback_url": "https://shield-billing-demo.preview.emergentagent.com/billing/callback",
                "currency": "NGN"
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["amount"] == 118500  # Business plan in NGN
    
    def test_checkout_invalid_plan(self, auth_token):
        """Checkout with invalid plan returns error"""
        response = requests.post(
            f"{BASE_URL}/api/billing/checkout/subscribe",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "plan_id": "invalid_plan",
                "callback_url": "https://example.com/callback",
                "currency": "NGN"
            }
        )
        assert response.status_code == 400 or response.status_code == 404


class TestFeatureGating:
    """Tests for subscription-based feature gating"""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token for free plan user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        return response.json()["access_token"]
    
    def test_free_plan_report_gating(self, auth_token):
        """Free plan users are blocked from report generation with 403"""
        response = requests.post(
            f"{BASE_URL}/api/reports/generate",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 403
        
        data = response.json()
        assert "detail" in data
        assert "plan" in data["detail"].lower() or "audit" in data["detail"].lower()
    
    def test_employee_limit_gating(self, auth_token):
        """Free plan users blocked when exceeding 5 employee limit"""
        # First check current employee count
        employees_response = requests.get(
            f"{BASE_URL}/api/employees",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert employees_response.status_code == 200
        current_count = len(employees_response.json())
        
        if current_count >= 5:
            # Try to add another employee
            response = requests.post(
                f"{BASE_URL}/api/employees",
                headers={"Authorization": f"Bearer {auth_token}"},
                json={
                    "name": "Over Limit Test",
                    "email": f"overlimit{current_count}@test.com",
                    "department": "Engineering"
                }
            )
            assert response.status_code == 403
            assert "5 employees" in response.json()["detail"]


class TestAdminBillingDashboard:
    """Tests for admin billing dashboard endpoint"""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        return response.json()["access_token"]
    
    def test_admin_dashboard_returns_metrics(self, auth_token):
        """GET /api/billing/admin/dashboard returns billing metrics"""
        response = requests.get(
            f"{BASE_URL}/api/billing/admin/dashboard",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "mrr" in data
        assert "arr" in data
        assert "total_customers" in data
        assert "active_subscriptions" in data
        assert "churn_rate" in data
        assert "revenue_by_plan" in data
        assert "at_risk_customers" in data
        assert "forecast_30_day_revenue" in data
    
    def test_admin_dashboard_has_numerical_metrics(self, auth_token):
        """Admin dashboard metrics are numeric"""
        response = requests.get(
            f"{BASE_URL}/api/billing/admin/dashboard",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        data = response.json()
        
        assert isinstance(data["mrr"], (int, float))
        assert isinstance(data["arr"], (int, float))
        assert isinstance(data["total_customers"], int)
        assert isinstance(data["churn_rate"], (int, float))


class TestBillingSubscription:
    """Tests for subscription management endpoints"""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        return response.json()["access_token"]
    
    def test_get_current_subscription(self, auth_token):
        """GET /api/billing/subscription returns current subscription"""
        response = requests.get(
            f"{BASE_URL}/api/billing/subscription",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "subscription" in data
        assert "plan" in data
    
    def test_get_invoices(self, auth_token):
        """GET /api/billing/invoices returns invoice list"""
        response = requests.get(
            f"{BASE_URL}/api/billing/invoices",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "invoices" in data
        assert isinstance(data["invoices"], list)
    
    def test_get_payment_methods(self, auth_token):
        """GET /api/billing/payment-methods returns payment methods"""
        response = requests.get(
            f"{BASE_URL}/api/billing/payment-methods",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "payment_methods" in data
        assert isinstance(data["payment_methods"], list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

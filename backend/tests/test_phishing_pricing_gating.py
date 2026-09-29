"""
CultureShield AI - Phishing Simulation Pricing & Feature Gating Tests
Tests that phishing simulation features are correctly gated to Business and Pro plans
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials for free account
FREE_ACCOUNT_EMAIL = "alignment_bbe272c9@example.com"
FREE_ACCOUNT_PASSWORD = "StrongPass!234"


class TestBillingPlansPhishingFeature:
    """Tests for GET /api/billing/plans - verify phishing simulation in plan features"""

    def test_billing_plans_returns_200(self):
        """Billing plans endpoint should return 200"""
        response = requests.get(f"{BASE_URL}/api/billing/plans")
        assert response.status_code == 200
        print("SUCCESS: GET /api/billing/plans returns 200")

    def test_free_plan_no_phishing(self):
        """Free plan should NOT include phishing simulations"""
        response = requests.get(f"{BASE_URL}/api/billing/plans")
        plans = response.json()
        free_plan = next((p for p in plans if p["id"] == "free"), None)
        
        assert free_plan is not None, "Free plan not found"
        features_lower = [f.lower() for f in free_plan.get("features", [])]
        has_phishing = any("phishing" in f for f in features_lower)
        
        assert not has_phishing, f"Free plan should NOT have phishing feature, but found: {free_plan['features']}"
        print(f"SUCCESS: Free plan features: {free_plan['features']} - No phishing")

    def test_starter_plan_no_phishing(self):
        """Starter plan should NOT include phishing simulations"""
        response = requests.get(f"{BASE_URL}/api/billing/plans")
        plans = response.json()
        starter_plan = next((p for p in plans if p["id"] == "starter"), None)
        
        assert starter_plan is not None, "Starter plan not found"
        features_lower = [f.lower() for f in starter_plan.get("features", [])]
        has_phishing = any("phishing" in f for f in features_lower)
        
        assert not has_phishing, f"Starter plan should NOT have phishing feature, but found: {starter_plan['features']}"
        print(f"SUCCESS: Starter plan features: {starter_plan['features']} - No phishing")

    def test_business_plan_has_phishing(self):
        """Business plan SHOULD include phishing simulations"""
        response = requests.get(f"{BASE_URL}/api/billing/plans")
        plans = response.json()
        business_plan = next((p for p in plans if p["id"] == "business"), None)
        
        assert business_plan is not None, "Business plan not found"
        features_lower = [f.lower() for f in business_plan.get("features", [])]
        has_phishing = any("phishing" in f for f in features_lower)
        
        assert has_phishing, f"Business plan SHOULD have phishing feature, but features are: {business_plan['features']}"
        print(f"SUCCESS: Business plan features: {business_plan['features']} - Has phishing")

    def test_pro_plan_has_phishing(self):
        """Pro plan SHOULD include phishing simulations (advanced)"""
        response = requests.get(f"{BASE_URL}/api/billing/plans")
        plans = response.json()
        pro_plan = next((p for p in plans if p["id"] == "pro"), None)
        
        assert pro_plan is not None, "Pro plan not found"
        features_lower = [f.lower() for f in pro_plan.get("features", [])]
        has_phishing = any("phishing" in f for f in features_lower)
        
        assert has_phishing, f"Pro plan SHOULD have phishing feature, but features are: {pro_plan['features']}"
        print(f"SUCCESS: Pro plan features: {pro_plan['features']} - Has phishing")

    def test_pay_per_audit_no_phishing(self):
        """Pay Per Audit plan should NOT include phishing simulations"""
        response = requests.get(f"{BASE_URL}/api/billing/plans")
        plans = response.json()
        ppa_plan = next((p for p in plans if p["id"] == "pay_per_audit"), None)
        
        assert ppa_plan is not None, "Pay Per Audit plan not found"
        features_lower = [f.lower() for f in ppa_plan.get("features", [])]
        has_phishing = any("phishing" in f for f in features_lower)
        
        assert not has_phishing, f"Pay Per Audit plan should NOT have phishing feature, but found: {ppa_plan['features']}"
        print(f"SUCCESS: Pay Per Audit plan features: {ppa_plan['features']} - No phishing")


class TestPhishingAccessGating:
    """Tests for phishing feature access gating for free accounts"""

    @pytest.fixture
    def free_account_token(self):
        """Login with free account and get token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": FREE_ACCOUNT_EMAIL, "password": FREE_ACCOUNT_PASSWORD}
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        return data.get("access_token")

    def test_billing_access_phishing_denied_for_free(self, free_account_token):
        """GET /api/billing/access/phishing_simulation should deny free account"""
        response = requests.get(
            f"{BASE_URL}/api/billing/access/phishing_simulation",
            headers={"Authorization": f"Bearer {free_account_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data.get("allowed") == False, f"Free account should NOT be allowed, got: {data}"
        assert "business" in data.get("message", "").lower() or "pro" in data.get("message", "").lower(), \
            f"Message should mention business/pro plans, got: {data.get('message')}"
        print(f"SUCCESS: Phishing access denied for free account: {data}")

    def test_phishing_templates_403_for_free(self, free_account_token):
        """GET /api/phishing/templates should return 403 for free account"""
        response = requests.get(
            f"{BASE_URL}/api/phishing/templates",
            headers={"Authorization": f"Bearer {free_account_token}"}
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "business" in data.get("detail", "").lower() or "pro" in data.get("detail", "").lower(), \
            f"Error message should mention business/pro plans, got: {data.get('detail')}"
        print(f"SUCCESS: Phishing templates returns 403 for free account: {data}")

    def test_phishing_campaigns_403_for_free(self, free_account_token):
        """GET /api/phishing/campaigns should return 403 for free account"""
        response = requests.get(
            f"{BASE_URL}/api/phishing/campaigns",
            headers={"Authorization": f"Bearer {free_account_token}"}
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        print(f"SUCCESS: Phishing campaigns returns 403 for free account")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

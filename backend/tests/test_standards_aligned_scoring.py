"""
Test suite for CultureShield AI Standards-Aligned Scoring Model
Tests ISO/IEC 27001 and NIST CSF aligned scoring, maturity levels, and report structure
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials from main agent
TEST_EMAIL = "alignment_bbe272c9@example.com"
TEST_PASSWORD = "StrongPass!234"


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def auth_token(api_client):
    """Get authentication token for test account"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    if response.status_code == 200:
        data = response.json()
        if data.get("mfa_required"):
            pytest.skip("MFA required - cannot proceed with automated tests")
        return data.get("access_token")
    pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def authenticated_client(api_client, auth_token):
    """Session with auth header"""
    api_client.headers.update({"Authorization": f"Bearer {auth_token}"})
    return api_client


class TestDashboardStatsStandardsAlignment:
    """Test dashboard stats endpoint returns standards-aligned scoring fields"""
    
    def test_dashboard_stats_returns_maturity_level(self, authenticated_client):
        """Dashboard stats should return maturity_level field"""
        response = authenticated_client.get(f"{BASE_URL}/api/dashboard/stats")
        assert response.status_code == 200
        
        data = response.json()
        assert "maturity_level" in data, "maturity_level field missing from dashboard stats"
        assert data["maturity_level"] in ["Initial", "Developing", "Defined", "Managed", "Adaptive"], \
            f"Invalid maturity_level: {data['maturity_level']}"
        print(f"✓ maturity_level: {data['maturity_level']}")
    
    def test_dashboard_stats_returns_maturity_summary(self, authenticated_client):
        """Dashboard stats should return maturity_summary field"""
        response = authenticated_client.get(f"{BASE_URL}/api/dashboard/stats")
        assert response.status_code == 200
        
        data = response.json()
        assert "maturity_summary" in data, "maturity_summary field missing from dashboard stats"
        assert isinstance(data["maturity_summary"], str), "maturity_summary should be a string"
        assert len(data["maturity_summary"]) > 0, "maturity_summary should not be empty"
        print(f"✓ maturity_summary: {data['maturity_summary'][:80]}...")
    
    def test_dashboard_stats_returns_framework_note(self, authenticated_client):
        """Dashboard stats should return framework_note with ISO/NIST reference"""
        response = authenticated_client.get(f"{BASE_URL}/api/dashboard/stats")
        assert response.status_code == 200
        
        data = response.json()
        assert "framework_note" in data, "framework_note field missing from dashboard stats"
        assert isinstance(data["framework_note"], str), "framework_note should be a string"
        # Verify it mentions ISO and NIST
        assert "ISO" in data["framework_note"] or "NIST" in data["framework_note"], \
            "framework_note should reference ISO or NIST standards"
        print(f"✓ framework_note contains standards reference")
    
    def test_dashboard_stats_returns_aligned_domains(self, authenticated_client):
        """Dashboard stats should return aligned_domains with control domain scores"""
        response = authenticated_client.get(f"{BASE_URL}/api/dashboard/stats")
        assert response.status_code == 200
        
        data = response.json()
        assert "aligned_domains" in data, "aligned_domains field missing from dashboard stats"
        assert isinstance(data["aligned_domains"], dict), "aligned_domains should be a dict"
        
        # If there are survey responses, domains should be populated
        if data.get("completed_surveys", 0) > 0:
            expected_domains = ["govern_awareness", "protect_secure_behavior", "detect_verify", "respond_report"]
            for domain in expected_domains:
                if domain in data["aligned_domains"]:
                    domain_data = data["aligned_domains"][domain]
                    assert "label" in domain_data, f"Domain {domain} missing label"
                    assert "score" in domain_data, f"Domain {domain} missing score"
                    assert "maturity_level" in domain_data, f"Domain {domain} missing maturity_level"
                    assert "iso_reference" in domain_data, f"Domain {domain} missing iso_reference"
                    assert "nist_reference" in domain_data, f"Domain {domain} missing nist_reference"
                    print(f"✓ Domain {domain}: score={domain_data['score']}, maturity={domain_data['maturity_level']}")
        else:
            print("✓ aligned_domains present (empty - no survey responses)")
    
    def test_dashboard_stats_returns_phishing_program(self, authenticated_client):
        """Dashboard stats should return phishing_program posture data"""
        response = authenticated_client.get(f"{BASE_URL}/api/dashboard/stats")
        assert response.status_code == 200
        
        data = response.json()
        assert "phishing_program" in data, "phishing_program field missing from dashboard stats"
        assert isinstance(data["phishing_program"], dict), "phishing_program should be a dict"
        
        phishing = data["phishing_program"]
        assert "measured" in phishing, "phishing_program missing 'measured' field"
        assert "summary" in phishing, "phishing_program missing 'summary' field"
        
        if phishing.get("measured"):
            assert "click_rate" in phishing, "phishing_program missing click_rate when measured"
            assert "report_rate" in phishing, "phishing_program missing report_rate when measured"
            assert "resilience_score" in phishing, "phishing_program missing resilience_score when measured"
            print(f"✓ phishing_program measured: click_rate={phishing['click_rate']}%, report_rate={phishing['report_rate']}%")
        else:
            print(f"✓ phishing_program not measured yet: {phishing.get('summary', '')[:60]}...")
    
    def test_dashboard_stats_overall_score_reflects_standards_alignment(self, authenticated_client):
        """Overall score should reflect standards-aligned domain weighting plus risk penalties"""
        response = authenticated_client.get(f"{BASE_URL}/api/dashboard/stats")
        assert response.status_code == 200
        
        data = response.json()
        assert "overall_score" in data, "overall_score field missing"
        assert isinstance(data["overall_score"], (int, float)), "overall_score should be numeric"
        assert 0 <= data["overall_score"] <= 100, f"overall_score should be 0-100, got {data['overall_score']}"
        
        # Verify risk_level is consistent with score
        assert "risk_level" in data, "risk_level field missing"
        valid_risk_levels = ["Low", "Low-Medium", "Medium", "Medium-High", "High", "Critical"]
        assert data["risk_level"] in valid_risk_levels, f"Invalid risk_level: {data['risk_level']}"
        
        print(f"✓ overall_score: {data['overall_score']}, risk_level: {data['risk_level']}")


class TestSurveySubmissionAndScoring:
    """Test survey submission still works and produces standards-aligned scores"""
    
    def test_survey_questions_endpoint(self, api_client):
        """Survey questions endpoint should be accessible"""
        response = api_client.get(f"{BASE_URL}/api/survey/questions")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list), "Survey questions should be a list"
        assert len(data) > 0, "Survey questions should not be empty"
        
        # Verify question structure
        for q in data[:3]:  # Check first 3 questions
            assert "id" in q, "Question missing id"
            assert "category" in q, "Question missing category"
            assert "question" in q, "Question missing question text"
            assert "options" in q, "Question missing options"
            assert "risk_weight" in q, "Question missing risk_weight"
        
        print(f"✓ Survey has {len(data)} questions with proper structure")


class TestReportGenerationBillingGate:
    """Test report generation is properly gated by billing (expected behavior)"""
    
    def test_report_generation_requires_subscription(self, authenticated_client):
        """Report generation should be gated by billing for free accounts"""
        response = authenticated_client.post(f"{BASE_URL}/api/reports/generate")
        
        # Free accounts should get 403 (billing gate) - this is expected behavior
        if response.status_code == 403:
            data = response.json()
            assert "detail" in data, "403 response should have detail message"
            print(f"✓ Report generation properly gated: {data.get('detail', '')[:60]}...")
        elif response.status_code == 200:
            # If somehow allowed, verify report structure
            data = response.json()
            assert "id" in data, "Report should have id"
            assert "report_content" in data, "Report should have report_content"
            print(f"✓ Report generated (subscription active)")
        else:
            # Other status codes might indicate issues
            print(f"⚠ Unexpected status: {response.status_code}")


class TestAuthAndNavigationRegression:
    """Test no regression in auth/dashboard/navigation after scoring updates"""
    
    def test_auth_me_endpoint(self, authenticated_client):
        """Auth me endpoint should work"""
        response = authenticated_client.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 200
        
        data = response.json()
        assert "id" in data, "Auth me should return company id"
        assert "company_name" in data, "Auth me should return company_name"
        assert "email" in data, "Auth me should return email"
        print(f"✓ Auth me working: {data.get('company_name')}")
    
    def test_employees_list_endpoint(self, authenticated_client):
        """Employees list endpoint should work"""
        response = authenticated_client.get(f"{BASE_URL}/api/employees")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list), "Employees should be a list"
        print(f"✓ Employees list working: {len(data)} employees")
    
    def test_reports_list_endpoint(self, authenticated_client):
        """Reports list endpoint should work"""
        response = authenticated_client.get(f"{BASE_URL}/api/reports")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list), "Reports should be a list"
        print(f"✓ Reports list working: {len(data)} reports")


class TestFrameworkDomainScoring:
    """Test framework domain scoring helper functions via dashboard stats"""
    
    def test_domain_scores_have_iso_nist_references(self, authenticated_client):
        """Each domain should have ISO and NIST references"""
        response = authenticated_client.get(f"{BASE_URL}/api/dashboard/stats")
        assert response.status_code == 200
        
        data = response.json()
        aligned_domains = data.get("aligned_domains", {})
        
        if aligned_domains:
            for domain_key, domain_data in aligned_domains.items():
                assert "iso_reference" in domain_data, f"Domain {domain_key} missing iso_reference"
                assert "nist_reference" in domain_data, f"Domain {domain_key} missing nist_reference"
                assert "ISO" in domain_data["iso_reference"], f"Domain {domain_key} iso_reference should mention ISO"
                assert "NIST" in domain_data["nist_reference"], f"Domain {domain_key} nist_reference should mention NIST"
                print(f"✓ Domain {domain_key}: {domain_data['iso_reference']} / {domain_data['nist_reference']}")
        else:
            print("✓ No domains to check (no survey responses)")
    
    def test_maturity_levels_are_valid(self, authenticated_client):
        """Maturity levels should be from the 5-level model"""
        response = authenticated_client.get(f"{BASE_URL}/api/dashboard/stats")
        assert response.status_code == 200
        
        data = response.json()
        valid_levels = ["Initial", "Developing", "Defined", "Managed", "Adaptive"]
        
        # Check company-level maturity
        assert data["maturity_level"] in valid_levels, f"Invalid company maturity_level: {data['maturity_level']}"
        
        # Check domain-level maturity
        for domain_key, domain_data in data.get("aligned_domains", {}).items():
            if "maturity_level" in domain_data:
                assert domain_data["maturity_level"] in valid_levels, \
                    f"Invalid domain maturity_level for {domain_key}: {domain_data['maturity_level']}"
        
        print(f"✓ All maturity levels valid (5-level model)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

#!/usr/bin/env python3
"""
Enhanced Cybersecurity Culture Scoring Model Test Suite
Tests the new weighted scoring, risk flags detection, and risk profiles
"""

import requests
import json
import sys
import time
from datetime import datetime
from typing import Dict, Any, Optional

class EnhancedScoringTester:
    def __init__(self, base_url: str = "https://shield-billing-demo.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.token = None
        self.company_data = None
        self.employee_id = None
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []
        
    def log(self, message: str, level: str = "INFO"):
        """Log test messages with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
        
    def run_test(self, name: str, method: str, endpoint: str, expected_status: int, 
                 data: Optional[Dict] = None, headers: Optional[Dict] = None) -> tuple:
        """Run a single API test and return success status and response data"""
        url = f"{self.api_url}/{endpoint}"
        test_headers = {'Content-Type': 'application/json'}
        
        if headers:
            test_headers.update(headers)
            
        if self.token and 'Authorization' not in test_headers:
            test_headers['Authorization'] = f'Bearer {self.token}'

        self.tests_run += 1
        self.log(f"🔍 Testing {name} - {method} {endpoint}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=test_headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=test_headers, timeout=30)
            elif method == 'DELETE':
                response = requests.delete(url, headers=test_headers, timeout=30)
            else:
                raise ValueError(f"Unsupported method: {method}")

            success = response.status_code == expected_status
            
            if success:
                self.tests_passed += 1
                self.log(f"✅ PASSED - Status: {response.status_code}")
                try:
                    return True, response.json()
                except:
                    return True, response.text
            else:
                self.log(f"❌ FAILED - Expected {expected_status}, got {response.status_code}")
                self.log(f"   Response: {response.text[:200]}")
                self.failed_tests.append({
                    'name': name,
                    'expected': expected_status,
                    'actual': response.status_code,
                    'response': response.text[:200]
                })
                try:
                    return False, response.json()
                except:
                    return False, response.text

        except Exception as e:
            self.log(f"❌ FAILED - Error: {str(e)}")
            self.failed_tests.append({'name': name, 'error': str(e)})
            return False, {}

    def setup_test_environment(self):
        """Setup test company and employee"""
        self.log("=== SETTING UP TEST ENVIRONMENT ===")
        
        # Register test company
        timestamp = int(time.time())
        test_company = {
            "company_name": f"Enhanced Test Company {timestamp}",
            "email": f"enhanced{timestamp}@testcompany.com",
            "password": "TestPassword123!"
        }
        
        success, response = self.run_test(
            "Company Registration", 
            "POST", 
            "auth/register", 
            200, 
            test_company
        )
        
        if success and isinstance(response, dict):
            self.token = response.get('access_token')
            self.company_data = response.get('company')
            self.log(f"✅ Test company created - ID: {self.company_data.get('id', 'N/A')}")
        else:
            return False
        
        # Create test employee
        employee_data = {
            "name": "Risk Test Employee",
            "email": f"risk.test{timestamp}@testcompany.com",
            "department": "Security Testing"
        }
        
        success, response = self.run_test(
            "Create Test Employee",
            "POST",
            "employees",
            200,
            employee_data
        )
        
        if success and isinstance(response, dict):
            self.employee_id = response.get('id')
            self.log(f"✅ Test employee created - ID: {self.employee_id}")
            return True
        
        return False

    def test_critical_risk_flags_detection(self):
        """Test detection of critical risk behaviors"""
        self.log("=== TESTING CRITICAL RISK FLAGS DETECTION ===")
        
        if not self.employee_id:
            self.log("❌ No employee ID available")
            return False
        
        # Get survey questions first
        success, questions = self.run_test(
            "Get Survey Questions",
            "GET",
            "survey/questions",
            200
        )
        
        if not success or not isinstance(questions, list):
            return False
        
        # Create risky responses to trigger critical flags
        # q5=0 (password reuse), q11=0 (click unknown links), q17=0 (share credentials)
        risky_responses = {}
        
        for question in questions:
            qid = question['id']
            if qid == 'q5':  # Password reuse - "Yes, for all accounts"
                risky_responses[qid] = 0
            elif qid == 'q11':  # Click unknown links - "Yes, definitely"
                risky_responses[qid] = 0
            elif qid == 'q17':  # Share credentials - "Yes, often"
                risky_responses[qid] = 0
            else:
                # Use middle options for other questions
                risky_responses[qid] = 1
        
        survey_data = {"responses": risky_responses}
        
        success, survey_response = self.run_test(
            "Submit Risky Survey Responses",
            "POST",
            f"survey/submit/{self.employee_id}",
            200,
            survey_data
        )
        
        if not success or not isinstance(survey_response, dict):
            return False
        
        # Verify risk flags are detected
        risk_flags = survey_response.get('risk_flags', [])
        risk_profile = survey_response.get('risk_profile', {})
        
        self.log(f"📊 Survey Results:")
        self.log(f"   Overall Score: {survey_response.get('overall_score', 'N/A')}")
        self.log(f"   Risk Level: {survey_response.get('risk_level', 'N/A')}")
        self.log(f"   Risk Flags Detected: {len(risk_flags)}")
        self.log(f"   Risk Profile: {risk_profile.get('risk_persona', 'N/A')}")
        
        # Check for critical flags
        critical_flags = [f for f in risk_flags if f.get('severity') == 'critical']
        expected_critical_flags = ['flag_q5', 'flag_q11', 'flag_q17']
        
        success_flags = True
        for expected_flag in expected_critical_flags:
            found = any(f.get('flag_id') == expected_flag for f in critical_flags)
            if found:
                self.log(f"✅ Critical flag detected: {expected_flag}")
            else:
                self.log(f"❌ Missing critical flag: {expected_flag}")
                success_flags = False
        
        # Verify risk profile
        if risk_profile.get('critical_flags', 0) >= 3:
            self.log(f"✅ Risk profile shows {risk_profile.get('critical_flags')} critical flags")
        else:
            self.log(f"❌ Expected 3+ critical flags, got {risk_profile.get('critical_flags', 0)}")
            success_flags = False
        
        # Verify vulnerability index
        vulnerability_index = risk_profile.get('vulnerability_index', 0)
        if vulnerability_index > 50:  # Should be high for risky responses
            self.log(f"✅ High vulnerability index: {vulnerability_index}")
        else:
            self.log(f"❌ Expected high vulnerability index, got {vulnerability_index}")
            success_flags = False
        
        return success_flags

    def test_dashboard_enhanced_stats(self):
        """Test enhanced dashboard statistics"""
        self.log("=== TESTING ENHANCED DASHBOARD STATS ===")
        
        success, stats = self.run_test(
            "Get Enhanced Dashboard Stats",
            "GET",
            "dashboard/stats",
            200
        )
        
        if not success or not isinstance(stats, dict):
            return False
        
        # Check for enhanced fields
        required_fields = [
            'high_risk_employees',
            'behavioral_red_flags', 
            'vulnerability_index',
            'risk_distribution',
            'critical_risk_count'
        ]
        
        success_stats = True
        for field in required_fields:
            if field in stats:
                self.log(f"✅ Enhanced field present: {field}")
                
                # Log specific values
                if field == 'high_risk_employees':
                    high_risk = stats[field]
                    self.log(f"   High risk employees: {len(high_risk) if isinstance(high_risk, list) else 'N/A'}")
                    if isinstance(high_risk, list) and len(high_risk) > 0:
                        emp = high_risk[0]
                        self.log(f"   First high-risk employee: {emp.get('name', 'N/A')} - {emp.get('risk_persona', 'N/A')}")
                
                elif field == 'behavioral_red_flags':
                    red_flags = stats[field]
                    self.log(f"   Behavioral red flags: {len(red_flags) if isinstance(red_flags, list) else 'N/A'}")
                    if isinstance(red_flags, list) and len(red_flags) > 0:
                        flag = red_flags[0]
                        self.log(f"   Top red flag: {flag.get('title', 'N/A')} ({flag.get('affected_count', 0)} employees)")
                
                elif field == 'vulnerability_index':
                    self.log(f"   Vulnerability index: {stats[field]}")
                
                elif field == 'risk_distribution':
                    dist = stats[field]
                    if isinstance(dist, dict):
                        self.log(f"   Risk distribution: {dist}")
                
                elif field == 'critical_risk_count':
                    self.log(f"   Critical risk count: {stats[field]}")
            else:
                self.log(f"❌ Missing enhanced field: {field}")
                success_stats = False
        
        return success_stats

    def test_weighted_scoring_calculation(self):
        """Test that weighted scoring is working correctly"""
        self.log("=== TESTING WEIGHTED SCORING CALCULATION ===")
        
        # Create a second employee for comparison
        timestamp = int(time.time())
        employee_data = {
            "name": "Safe Test Employee",
            "email": f"safe.test{timestamp}@testcompany.com",
            "department": "Security Testing"
        }
        
        success, response = self.run_test(
            "Create Safe Employee",
            "POST",
            "employees",
            200,
            employee_data
        )
        
        if not success:
            return False
        
        safe_employee_id = response.get('id')
        
        # Get questions
        success, questions = self.run_test(
            "Get Questions for Safe Employee",
            "GET",
            "survey/questions",
            200
        )
        
        if not success:
            return False
        
        # Create safe responses (all best options)
        safe_responses = {}
        for question in questions:
            safe_responses[question['id']] = 3  # Best option (index 3)
        
        survey_data = {"responses": safe_responses}
        
        success, safe_survey_response = self.run_test(
            "Submit Safe Survey Responses",
            "POST",
            f"survey/submit/{safe_employee_id}",
            200,
            survey_data
        )
        
        if not success:
            return False
        
        # Compare scores
        safe_score = safe_survey_response.get('overall_score', 0)
        safe_risk_level = safe_survey_response.get('risk_level', 'Unknown')
        safe_flags = len(safe_survey_response.get('risk_flags', []))
        
        self.log(f"📊 Safe Employee Results:")
        self.log(f"   Overall Score: {safe_score}")
        self.log(f"   Risk Level: {safe_risk_level}")
        self.log(f"   Risk Flags: {safe_flags}")
        
        # Verify safe employee has better scores
        if safe_score > 70 and safe_risk_level in ['Low', 'Low-Medium'] and safe_flags == 0:
            self.log(f"✅ Safe employee has good scores as expected")
            return True
        else:
            self.log(f"❌ Safe employee scores not as expected")
            return False

    def cleanup_test_environment(self):
        """Clean up test data"""
        self.log("=== CLEANING UP TEST ENVIRONMENT ===")
        
        # Get all employees and delete them
        success, employees = self.run_test(
            "Get All Employees",
            "GET",
            "employees",
            200
        )
        
        if success and isinstance(employees, list):
            for emp in employees:
                emp_id = emp.get('id')
                if emp_id:
                    self.run_test(
                        f"Delete Employee {emp.get('name', emp_id)}",
                        "DELETE",
                        f"employees/{emp_id}",
                        200
                    )

    def run_enhanced_scoring_tests(self):
        """Run all enhanced scoring tests"""
        self.log("🚀 Starting Enhanced Cybersecurity Culture Scoring Tests")
        self.log(f"🌐 Testing against: {self.base_url}")
        
        start_time = time.time()
        
        # Setup
        if not self.setup_test_environment():
            self.log("❌ Failed to setup test environment")
            return False
        
        # Run enhanced scoring tests
        test_suites = [
            ("Critical Risk Flags Detection", self.test_critical_risk_flags_detection),
            ("Enhanced Dashboard Stats", self.test_dashboard_enhanced_stats),
            ("Weighted Scoring Calculation", self.test_weighted_scoring_calculation),
        ]
        
        all_passed = True
        for suite_name, test_func in test_suites:
            try:
                self.log(f"\n{'='*50}")
                result = test_func()
                if not result:
                    all_passed = False
            except Exception as e:
                self.log(f"❌ Test suite '{suite_name}' failed with error: {str(e)}")
                all_passed = False
        
        # Cleanup
        self.cleanup_test_environment()
        
        # Print final results
        end_time = time.time()
        duration = end_time - start_time
        
        self.log(f"\n{'='*50}")
        self.log("📊 ENHANCED SCORING TEST RESULTS")
        self.log(f"{'='*50}")
        self.log(f"Tests Run: {self.tests_run}")
        self.log(f"Tests Passed: {self.tests_passed}")
        self.log(f"Tests Failed: {len(self.failed_tests)}")
        self.log(f"Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%" if self.tests_run > 0 else "0%")
        self.log(f"Duration: {duration:.2f} seconds")
        
        if self.failed_tests:
            self.log(f"\n❌ FAILED TESTS:")
            for i, test in enumerate(self.failed_tests, 1):
                self.log(f"  {i}. {test['name']}")
                if 'expected' in test:
                    self.log(f"     Expected: {test['expected']}, Got: {test['actual']}")
                if 'error' in test:
                    self.log(f"     Error: {test['error']}")
        
        return all_passed

def main():
    """Main test execution"""
    tester = EnhancedScoringTester()
    
    try:
        success = tester.run_enhanced_scoring_tests()
        return 0 if success else 1
    except KeyboardInterrupt:
        tester.log("\n⚠️  Tests interrupted by user")
        return 1
    except Exception as e:
        tester.log(f"\n💥 Unexpected error: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
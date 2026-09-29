#!/usr/bin/env python3
"""
CultureShield AI Backend API Testing Suite
Tests all endpoints for the cybersecurity culture audit platform
"""

import requests
import json
import sys
import time
from datetime import datetime
from typing import Dict, Any, Optional

class CultureShieldAPITester:
    def __init__(self, base_url: str = "https://shield-billing-demo.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.token = None
        self.company_data = None
        self.employee_id = None
        self.report_id = None
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

        except requests.exceptions.Timeout:
            self.log(f"❌ FAILED - Request timeout")
            self.failed_tests.append({'name': name, 'error': 'Timeout'})
            return False, {}
        except Exception as e:
            self.log(f"❌ FAILED - Error: {str(e)}")
            self.failed_tests.append({'name': name, 'error': str(e)})
            return False, {}

    def test_health_check(self):
        """Test API health endpoints"""
        self.log("=== HEALTH CHECK TESTS ===")
        
        # Test root endpoint
        success, _ = self.run_test("API Root", "GET", "", 200)
        
        # Test health endpoint
        success, _ = self.run_test("Health Check", "GET", "health", 200)
        
        return success

    def test_company_registration(self):
        """Test company registration"""
        self.log("=== COMPANY REGISTRATION TESTS ===")
        
        # Generate unique test data
        timestamp = int(time.time())
        test_company = {
            "company_name": f"Test Company {timestamp}",
            "email": f"test{timestamp}@testcompany.com",
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
            self.log(f"✅ Registration successful - Company ID: {self.company_data.get('id', 'N/A')}")
        
        return success

    def test_company_login(self):
        """Test company login with registered credentials"""
        self.log("=== COMPANY LOGIN TESTS ===")
        
        if not self.company_data:
            self.log("❌ No company data available for login test")
            return False
            
        login_data = {
            "email": self.company_data['email'],
            "password": "TestPassword123!"
        }
        
        success, response = self.run_test(
            "Company Login",
            "POST",
            "auth/login",
            200,
            login_data
        )
        
        if success and isinstance(response, dict):
            self.token = response.get('access_token')
            self.log(f"✅ Login successful - Token received")
        
        return success

    def test_auth_me(self):
        """Test getting current company info"""
        self.log("=== AUTH ME TEST ===")
        
        if not self.token:
            self.log("❌ No token available for auth test")
            return False
            
        success, response = self.run_test(
            "Get Current Company",
            "GET",
            "auth/me",
            200
        )
        
        return success

    def test_employee_management(self):
        """Test employee CRUD operations"""
        self.log("=== EMPLOYEE MANAGEMENT TESTS ===")
        
        if not self.token:
            self.log("❌ No token available for employee tests")
            return False
        
        # Test getting empty employee list
        success, _ = self.run_test(
            "Get Empty Employee List",
            "GET",
            "employees",
            200
        )
        
        # Test adding an employee
        employee_data = {
            "name": "John Test Employee",
            "email": f"john.test{int(time.time())}@testcompany.com",
            "department": "Engineering"
        }
        
        success, response = self.run_test(
            "Add Employee",
            "POST",
            "employees",
            200,
            employee_data
        )
        
        if success and isinstance(response, dict):
            self.employee_id = response.get('id')
            self.log(f"✅ Employee created - ID: {self.employee_id}")
        
        # Test getting employee list with data
        success, employees = self.run_test(
            "Get Employee List",
            "GET",
            "employees",
            200
        )
        
        if success and isinstance(employees, list) and len(employees) > 0:
            self.log(f"✅ Found {len(employees)} employees")
        
        return success

    def test_survey_functionality(self):
        """Test survey questions and submission"""
        self.log("=== SURVEY FUNCTIONALITY TESTS ===")
        
        # Test getting survey questions
        success, questions = self.run_test(
            "Get Survey Questions",
            "GET",
            "survey/questions",
            200
        )
        
        if not success or not isinstance(questions, list):
            return False
            
        self.log(f"✅ Found {len(questions)} survey questions")
        
        if not self.employee_id:
            self.log("❌ No employee ID available for survey tests")
            return False
        
        # Test getting employee for survey
        success, emp_data = self.run_test(
            "Get Employee for Survey",
            "GET",
            f"survey/employee/{self.employee_id}",
            200
        )
        
        if not success:
            return False
        
        # Test survey submission with sample responses
        # Create responses for all questions (selecting middle options)
        responses = {}
        for i, question in enumerate(questions):
            responses[question['id']] = 1  # Select second option (index 1)
        
        survey_data = {"responses": responses}
        
        success, survey_response = self.run_test(
            "Submit Survey",
            "POST",
            f"survey/submit/{self.employee_id}",
            200,
            survey_data
        )
        
        if success and isinstance(survey_response, dict):
            self.log(f"✅ Survey submitted - Score: {survey_response.get('overall_score', 'N/A')}")
        
        # Test getting survey responses
        success, _ = self.run_test(
            "Get Survey Responses",
            "GET",
            "survey/responses",
            200
        )
        
        return success

    def test_dashboard_stats(self):
        """Test dashboard statistics"""
        self.log("=== DASHBOARD STATS TEST ===")
        
        if not self.token:
            self.log("❌ No token available for dashboard test")
            return False
        
        success, stats = self.run_test(
            "Get Dashboard Stats",
            "GET",
            "dashboard/stats",
            200
        )
        
        if success and isinstance(stats, dict):
            self.log(f"✅ Dashboard stats - Overall Score: {stats.get('overall_score', 'N/A')}")
            self.log(f"   Participation Rate: {stats.get('participation_rate', 'N/A')}%")
        
        return success

    def test_trend_analysis(self):
        """Test trend analysis endpoints"""
        self.log("=== TREND ANALYSIS TESTS ===")
        
        if not self.token:
            self.log("❌ No token available for trend analysis tests")
            return False
        
        # Test GET /api/analytics/trends
        success, response = self.run_test(
            "Get Trend Analysis",
            "GET",
            "analytics/trends",
            200
        )
        
        if not success:
            return False
        
        # Validate response structure
        required_fields = ['weekly_trends', 'monthly_trends', 'score_change_weekly', 
                         'score_change_monthly', 'trend_direction', 'insights']
        
        missing_fields = [field for field in required_fields if field not in response]
        if missing_fields:
            self.log(f"❌ Missing required fields in trend analysis: {missing_fields}")
            return False
        
        # Validate weekly trends (should have 4 periods)
        weekly_trends = response.get('weekly_trends', [])
        if len(weekly_trends) != 4:
            self.log(f"❌ Expected 4 weekly trends, got {len(weekly_trends)}")
            return False
        
        # Validate monthly trends (should have 6 periods)
        monthly_trends = response.get('monthly_trends', [])
        if len(monthly_trends) != 6:
            self.log(f"❌ Expected 6 monthly trends, got {len(monthly_trends)}")
            return False
        
        # Validate trend direction
        trend_direction = response.get('trend_direction')
        if trend_direction not in ['improving', 'declining', 'stable']:
            self.log(f"❌ Invalid trend direction: {trend_direction}")
            return False
        
        # Validate insights is array
        insights = response.get('insights', [])
        if not isinstance(insights, list):
            self.log(f"❌ Insights should be array, got {type(insights)}")
            return False
        
        # Validate trend data point structure
        if weekly_trends:
            trend_point = weekly_trends[0]
            required_trend_fields = ['period', 'date', 'overall_score', 'awareness_score', 
                                   'behavior_score', 'reporting_score', 'participation_rate', 
                                   'responses_count', 'risk_level']
            missing_trend_fields = [field for field in required_trend_fields if field not in trend_point]
            if missing_trend_fields:
                self.log(f"❌ Missing fields in trend data point: {missing_trend_fields}")
                return False
        
        self.log(f"✅ Trend analysis validated")
        self.log(f"   Weekly trends: {len(weekly_trends)} periods")
        self.log(f"   Monthly trends: {len(monthly_trends)} periods")
        self.log(f"   Trend direction: {trend_direction}")
        self.log(f"   Insights count: {len(insights)}")
        self.log(f"   Score change weekly: {response.get('score_change_weekly', 0)}")
        self.log(f"   Score change monthly: {response.get('score_change_monthly', 0)}")
        
        return True

    def test_bulk_import(self):
        """Test bulk import endpoints"""
        self.log("=== BULK IMPORT TESTS ===")
        
        if not self.token:
            self.log("❌ No token available for bulk import tests")
            return False
        
        # Test GET /api/employees/csv-template
        success, response = self.run_test(
            "Get CSV Template",
            "GET",
            "employees/csv-template",
            200
        )
        
        if not success:
            return False
        
        # Validate CSV template structure
        required_fields = ['format', 'required_columns', 'example_rows']
        missing_fields = [field for field in required_fields if field not in response]
        if missing_fields:
            self.log(f"❌ CSV template missing fields: {missing_fields}")
            return False
        
        required_columns = response.get('required_columns', [])
        if 'name' not in required_columns or 'email' not in required_columns:
            self.log(f"❌ CSV template should require 'name' and 'email' columns")
            return False
        
        self.log(f"✅ CSV template validated")
        self.log(f"   Required columns: {required_columns}")
        
        # Test POST /api/employees/bulk-import with valid data
        timestamp = int(time.time())
        bulk_data = {
            "employees": [
                {"name": "John Doe Test", "email": f"john.doe.test.{timestamp}@test.com", "department": "Engineering"},
                {"name": "Jane Smith Test", "email": f"jane.smith.test.{timestamp}@test.com", "department": "Marketing"},
                {"name": "Bob Wilson Test", "email": f"bob.wilson.test.{timestamp}@test.com", "department": "Finance"}
            ]
        }
        
        success, response = self.run_test(
            "Bulk Import Valid Employees",
            "POST",
            "employees/bulk-import",
            200,
            data=bulk_data
        )
        
        if not success:
            return False
        
        # Validate bulk import response structure
        required_fields = ['total_processed', 'successful', 'failed', 'errors', 'employees_created']
        missing_fields = [field for field in required_fields if field not in response]
        if missing_fields:
            self.log(f"❌ Bulk import response missing fields: {missing_fields}")
            return False
        
        if response['total_processed'] != 3:
            self.log(f"❌ Expected 3 processed, got {response['total_processed']}")
            return False
        
        if response['successful'] != 3:
            self.log(f"❌ Expected 3 successful, got {response['successful']}")
            return False
        
        if response['failed'] != 0:
            self.log(f"❌ Expected 0 failed, got {response['failed']}")
            return False
        
        # Store employee IDs for potential cleanup
        bulk_employee_ids = [emp['id'] for emp in response.get('employees_created', [])]
        
        self.log(f"✅ Bulk import successful")
        self.log(f"   Processed: {response['total_processed']}")
        self.log(f"   Successful: {response['successful']}")
        self.log(f"   Failed: {response['failed']}")
        
        # Test bulk import with duplicate emails
        duplicate_data = {
            "employees": [
                {"name": "John Duplicate", "email": bulk_data["employees"][0]["email"], "department": "IT"},
                {"name": "New Employee", "email": f"new.employee.{timestamp}@test.com", "department": "Sales"}
            ]
        }
        
        success, response = self.run_test(
            "Bulk Import with Duplicates",
            "POST",
            "employees/bulk-import",
            200,
            data=duplicate_data
        )
        
        if not success:
            return False
        
        if response['failed'] == 0:
            self.log(f"❌ Expected at least 1 failure due to duplicate email")
            return False
        
        errors = response.get('errors', [])
        duplicate_error_found = any('already exists' in str(error).lower() for error in errors)
        if not duplicate_error_found:
            self.log(f"❌ Expected duplicate email error in: {errors}")
            return False
        
        self.log(f"✅ Duplicate detection working")
        self.log(f"   Errors: {len(errors)}")
        
        # Test bulk import with invalid data
        invalid_data = {
            "employees": [
                {"name": "", "email": "invalid@test.com", "department": "IT"},  # Empty name
                {"name": "Valid Name", "email": "", "department": "Sales"},      # Empty email
                {"name": "Another Valid", "email": "invalid-email", "department": "HR"}  # Invalid email
            ]
        }
        
        success, response = self.run_test(
            "Bulk Import with Invalid Data",
            "POST",
            "employees/bulk-import",
            200,
            data=invalid_data
        )
        
        if not success:
            return False
        
        if response['failed'] == 0:
            self.log(f"❌ Expected failures due to invalid data")
            return False
        
        self.log(f"✅ Validation working")
        self.log(f"   Failed: {response['failed']}")
        self.log(f"   Errors: {len(response.get('errors', []))}")
        
        # Clean up bulk imported employees
        for emp_id in bulk_employee_ids:
            self.run_test(
                f"Delete Bulk Employee",
                "DELETE",
                f"employees/{emp_id}",
                200
            )
        
        return True

    def test_report_generation(self):
        """Test AI report generation and PDF download"""
        self.log("=== REPORT GENERATION TESTS ===")
        
        if not self.token:
            self.log("❌ No token available for report tests")
            return False
        
        # Test generating a report (this may take time due to AI processing)
        self.log("🤖 Generating AI report (this may take 10-30 seconds)...")
        success, report = self.run_test(
            "Generate AI Report",
            "POST",
            "reports/generate",
            200
        )
        
        if success and isinstance(report, dict):
            self.report_id = report.get('id')
            self.log(f"✅ Report generated - ID: {self.report_id}")
        
        # Test getting reports list
        success, reports = self.run_test(
            "Get Reports List",
            "GET",
            "reports",
            200
        )
        
        if success and isinstance(reports, list):
            self.log(f"✅ Found {len(reports)} reports")
        
        # Test getting specific report
        if self.report_id:
            success, report_detail = self.run_test(
                "Get Report Detail",
                "GET",
                f"reports/{self.report_id}",
                200
            )
            
            # Test PDF download
            success_pdf, _ = self.run_test(
                "Download Report PDF",
                "GET",
                f"reports/{self.report_id}/pdf",
                200
            )
        
        return success

    def test_employee_deletion(self):
        """Test employee deletion (cleanup)"""
        self.log("=== EMPLOYEE DELETION TEST ===")
        
        if not self.token or not self.employee_id:
            self.log("❌ No token or employee ID available for deletion test")
            return False
        
        success, _ = self.run_test(
            "Delete Employee",
            "DELETE",
            f"employees/{self.employee_id}",
            200
        )
        
        return success

    def run_all_tests(self):
        """Run all test suites"""
        self.log("🚀 Starting CultureShield AI Backend API Tests")
        self.log(f"🌐 Testing against: {self.base_url}")
        
        start_time = time.time()
        
        # Run test suites in order
        test_suites = [
            ("Health Check", self.test_health_check),
            ("Company Registration", self.test_company_registration),
            ("Company Login", self.test_company_login),
            ("Auth Me", self.test_auth_me),
            ("Employee Management", self.test_employee_management),
            ("Trend Analysis", self.test_trend_analysis),
            ("Bulk Import", self.test_bulk_import),
            ("Survey Functionality", self.test_survey_functionality),
            ("Dashboard Stats", self.test_dashboard_stats),
            ("Report Generation", self.test_report_generation),
            ("Employee Deletion", self.test_employee_deletion),
        ]
        
        for suite_name, test_func in test_suites:
            try:
                self.log(f"\n{'='*50}")
                test_func()
            except Exception as e:
                self.log(f"❌ Test suite '{suite_name}' failed with error: {str(e)}")
        
        # Print final results
        end_time = time.time()
        duration = end_time - start_time
        
        self.log(f"\n{'='*50}")
        self.log("📊 FINAL TEST RESULTS")
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
        
        return self.tests_passed == self.tests_run

def main():
    """Main test execution"""
    tester = CultureShieldAPITester()
    
    try:
        success = tester.run_all_tests()
        return 0 if success else 1
    except KeyboardInterrupt:
        tester.log("\n⚠️  Tests interrupted by user")
        return 1
    except Exception as e:
        tester.log(f"\n💥 Unexpected error: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
"""Unit tests for IILM Academic Advisory Email Alerts."""

import unittest
from fastapi.testclient import TestClient

from src import api
from src.email_alerts import generate_advisory_email_html, dispatch_advisory_email


class EmailAlertsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(api.app)

    def test_generate_html_template_contains_iilm_and_metrics(self):
        html_output = generate_advisory_email_html(
            student_name="Test Student",
            student_email="test.student@iilm.edu",
            predicted_cgpa=1.85,
            major="Computer Science",
            attendance_pct=62.5,
            recovery_plan=[
                {
                    "week": 1,
                    "title": "Week 1",
                    "focus": "Diagnostic Triage",
                    "actionable": "Attend TA clinic",
                    "hours_target": "2.5h/day",
                }
            ],
            advisor_name="Dr. Priya Mehta",
        )
        self.assertIn("IILM University", html_output)
        self.assertIn("Test Student", html_output)
        self.assertIn("1.85", html_output)
        self.assertIn("62.5%", html_output)
        self.assertIn("Diagnostic Triage", html_output)

    def test_dispatch_simulated_mode(self):
        result = dispatch_advisory_email(
            student_name="Aarav Sharma",
            student_email="aarav.sharma@iilm.edu",
            predicted_cgpa=1.75,
            major="Engineering",
            attendance_pct=58.0,
        )
        self.assertIn(result["status"], {"delivered", "delivered_simulated"})
        self.assertEqual(result["recipient"], "aarav.sharma@iilm.edu")
        self.assertIn("subject", result)

    def test_api_send_warning_endpoint(self):
        payload = {
            "student_name": "Rohan Verma",
            "student_email": "rohan.v@iilm.edu",
            "predicted_cgpa": 1.90,
            "major": "Computer Science",
            "attendance_pct": 65.0,
            "advisor_name": "Dr. Priya Mehta",
        }
        res = self.client.post("/api/v1/alerts/send-warning", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("delivered", data["status"])
        self.assertEqual(data["recipient"], "rohan.v@iilm.edu")

    def test_api_preview_warning_endpoint(self):
        payload = {
            "student_name": "Ananya Sen",
            "student_email": "ananya.s@iilm.edu",
            "predicted_cgpa": 1.65,
            "major": "Business",
            "attendance_pct": 52.0,
        }
        res = self.client.post("/api/v1/alerts/preview", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("html", data)
        self.assertIn("IILM University", data["html"])

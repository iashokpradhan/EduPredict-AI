"""Unit tests for Power BI star-schema summary endpoint."""

import unittest
from fastapi.testclient import TestClient

from src import api
from src import db


class PowerBiAnalyticsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(api.app)

    def test_db_get_powerbi_summary_structure(self):
        summary = db.get_powerbi_summary()
        self.assertEqual(summary["status"], "ready")
        self.assertIn("dax_measures", summary)
        self.assertIn("star_schema", summary)
        self.assertIn("attendance_impact", summary)
        self.assertEqual(summary["bi_architect"], "Ashok Pradhan")

        # Test DAX Measures existence
        dax = summary["dax_measures"]
        self.assertIn("Total_Students", dax)
        self.assertIn("Avg_CGPA", dax)
        self.assertIn("At_Risk_Rate_Pct", dax)

    def test_api_powerbi_summary_endpoint(self):
        res = self.client.get("/api/v1/analytics/powerbi-summary")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "ready")
        self.assertIn("star_schema", data)
        self.assertIn("v_powerbi_academic_facts", data["star_schema"]["fact_tables"])
        self.assertIn("v_powerbi_student_dim", data["star_schema"]["dimension_tables"])

"""Unit tests for the relational database layer and enhanced API endpoints."""

import tempfile
import unittest
from pathlib import Path

import httpx

import src.api as api
from src import db


class DatabaseAndApiExtensionsTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_edupredict.db"
        self.db_url = str(self.db_path)
        db.initialize_core_database(self.db_url)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_database_initialization_and_engine_type(self):
        engine = db.get_database_engine_type(self.db_url)
        self.assertEqual(engine, "sqlite")
        self.assertTrue(self.db_path.exists())

    def test_insert_prediction_log_and_retrieval(self):
        features = {
            "Gender": "Female",
            "Age": 21,
            "Major": "Computer Science",
            "Attendance_Pct": 94.0,
            "Study_Hours_Per_Day": 5.0,
            "Previous_CGPA": 3.70,
            "Sleep_Hours": 7.0,
            "Social_Hours_Week": 8.0,
        }
        recs = [
            {"id": "study_schedule", "title": "Maintain focus", "action": "Keep consistent blocks", "why": "Good routine"}
        ]
        log_id = db.insert_prediction_log(
            student_features=features,
            predicted_cgpa=3.75,
            risk_probability=0.04,
            risk_label="not_at_risk",
            recommendations=recs,
            database_url=self.db_url,
        )
        self.assertIsNotNone(log_id)

        history = db.get_recent_predictions(limit=5, database_url=self.db_url)
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["major"], "Computer Science")
        self.assertEqual(history[0]["predicted_cgpa"], 3.75)
        self.assertEqual(history[0]["risk_label"], "not_at_risk")

    def test_cohort_summary_fallback_and_structure(self):
        summary = db.get_cohort_summary(self.db_url)
        self.assertIn("avg_final_cgpa", summary)
        self.assertIn("majors", summary)
        self.assertIn("performance_bands", summary)

    async def test_api_presets_endpoint(self):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=api.app), base_url="http://testserver"
        ) as client:
            res = await client.get("/api/v1/presets")
            self.assertEqual(res.status_code, 200)
            presets = res.json()
            self.assertGreaterEqual(len(presets), 3)
            ids = [p["id"] for p in presets]
            self.assertIn("high_achiever", ids)
            self.assertIn("at_risk_student", ids)

    async def test_api_cohort_analytics_and_history_endpoints(self):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=api.app), base_url="http://testserver"
        ) as client:
            cohort_res = await client.get("/api/v1/analytics/cohort")
            self.assertEqual(cohort_res.status_code, 200)
            data = cohort_res.json()
            self.assertIn("total_records", data)

            history_res = await client.get("/api/v1/analytics/history")
            self.assertEqual(history_res.status_code, 200)
            self.assertIsInstance(history_res.json(), list)

    async def test_api_models_diagnostics_endpoint(self):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=api.app), base_url="http://testserver"
        ) as client:
            res = await client.get("/api/v1/models/diagnostics")
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertIn("regression", data)
            self.assertIn("classification", data)
            self.assertIn("feature_importance_ranking", data)
            self.assertEqual(data["regression"]["chosen_model"], "Gradient Boosting Regressor")

    async def test_api_simulation_endpoint(self):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=api.app), base_url="http://testserver"
        ) as client:
            payload = {
                "base_features": {
                    "Gender": "Female",
                    "Age": 21,
                    "Major": "Computer Science",
                    "Attendance_Pct": 80.0,
                    "Study_Hours_Per_Day": 3.0,
                    "Previous_CGPA": 3.0,
                    "Sleep_Hours": 7.0,
                    "Social_Hours_Week": 10.0,
                },
                "attendance_delta": 10.0,
                "study_hours_delta": 2.0,
                "sleep_hours_delta": 1.0,
            }
            res = await client.post("/api/v1/simulate", json=payload)
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertIn("cgpa_delta", data)
            self.assertIn("interpretation", data)
            self.assertEqual(data["simulated_features"]["Attendance_Pct"], 90.0)
            self.assertEqual(data["simulated_features"]["Study_Hours_Per_Day"], 5.0)


if __name__ == "__main__":
    unittest.main()

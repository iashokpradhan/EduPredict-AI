import unittest

import httpx

from src.api import app
from tests.integration.prerequisites import MODEL_PATHS, require_local_files


VALID_STUDENT = {
    "Gender": "Female",
    "Age": 20,
    "Major": "Engineering",
    "Attendance_Pct": 75.0,
    "Study_Hours_Per_Day": 1.5,
    "Previous_CGPA": 2.7,
    "Sleep_Hours": 5.5,
    "Social_Hours_Week": 8,
}


class ApiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        require_local_files(*MODEL_PATHS)
        self.lifespan = app.router.lifespan_context(app)
        await self.lifespan.__aenter__()
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://testserver"
        )

    async def asyncTearDown(self):
        await self.client.aclose()
        await self.lifespan.__aexit__(None, None, None)

    async def test_health_and_frontend(self):
        self.assertEqual((await self.client.get("/api/v1/health")).json()["status"], "ok")
        page = await self.client.get("/")
        self.assertEqual(page.status_code, 200)
        self.assertIn("EduPredict AI", page.text)

    async def test_prediction_returns_unclipped_number(self):
        response = await self.client.post("/api/v1/predict", json=VALID_STUDENT)
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertIsInstance(result["predicted_cgpa"], float)
        self.assertFalse(result["prediction_is_clipped"])

    async def test_risk_endpoint_identifies_experimental_status(self):
        response = await self.client.post("/api/v1/risk", json=VALID_STUDENT)
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result["model_status"], "experimental_demo_only")
        self.assertFalse(result["threshold_is_official_policy"])
        self.assertGreaterEqual(result["risk_probability"], 0)
        self.assertLessEqual(result["risk_probability"], 1)

    async def test_recommendations_are_distinct_from_model_prediction(self):
        response = await self.client.post("/api/v1/recommendations", json=VALID_STUDENT)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["recommendations"]), 3)

    async def test_missing_invalid_and_target_leaking_inputs_are_rejected(self):
        missing = {key: value for key, value in VALID_STUDENT.items() if key != "Gender"}
        self.assertEqual((await self.client.post("/api/v1/predict", json=missing)).status_code, 422)
        invalid = {**VALID_STUDENT, "Previous_CGPA": 4.1}
        self.assertEqual((await self.client.post("/api/v1/risk", json=invalid)).status_code, 422)
        leaking = {**VALID_STUDENT, "Final_CGPA": 3.2}
        self.assertEqual((await self.client.post("/api/v1/recommendations", json=leaking)).status_code, 422)


if __name__ == "__main__":
    unittest.main()

import tempfile
import unittest
from contextlib import asynccontextmanager
from pathlib import Path
from unittest.mock import Mock, patch

import httpx
import numpy as np

import src.api as api


STUDENT = {
    "Gender": "Female",
    "Age": 20,
    "Major": "Engineering",
    "Attendance_Pct": 75,
    "Study_Hours_Per_Day": 1.5,
    "Previous_CGPA": 2.7,
    "Sleep_Hours": 5.5,
    "Social_Hours_Week": 8,
}


class ApiWithoutArtifactsTests(unittest.IsolatedAsyncioTestCase):
    @asynccontextmanager
    async def client_with_artifacts(
        self,
        artifact_names=(),
        load_side_effect=None,
        database_url=None,
        database_status="disabled",
    ):
        original_directory = api.MODEL_DIRECTORY
        with tempfile.TemporaryDirectory() as temporary:
            model_directory = Path(temporary)
            api.MODEL_DIRECTORY = model_directory
            for name in artifact_names:
                (model_directory / name).touch()
            side_effect = load_side_effect
            if isinstance(load_side_effect, dict):
                side_effect = lambda _path: load_side_effect
            loader = patch.object(api.joblib, "load", side_effect=side_effect)
            try:
                with (
                    patch.dict(
                        "os.environ",
                        {api.analytics_db.DATABASE_URL_ENV: database_url or ""},
                    ),
                    patch.object(api.analytics_db, "probe_database", return_value=database_status),
                    loader,
                ):
                    async with api.app.router.lifespan_context(api.app):
                        async with httpx.AsyncClient(
                            transport=httpx.ASGITransport(app=api.app),
                            base_url="http://testserver",
                        ) as client:
                            yield client
            finally:
                api.MODEL_DIRECTORY = original_directory

    async def test_missing_models_do_not_block_core_routes_or_frontend(self):
        async with self.client_with_artifacts() as client:
            health = (await client.get("/api/v1/health")).json()
            self.assertTrue(health["ready"])
            self.assertEqual(health["status"], "degraded")
            self.assertFalse(health["prediction_available"])
            self.assertFalse(health["risk_available"])
            self.assertEqual(health["prediction_status"], "missing_artifact")
            self.assertEqual(health["risk_status"], "missing_artifact")
            self.assertTrue(health["recommendations_available"])
            self.assertTrue(health["study_plan_available"])
            self.assertFalse(health["analytics_database_configured"])
            self.assertEqual(health["analytics_database_status"], "disabled")

            page = await client.get("/")
            self.assertEqual(page.status_code, 200)
            self.assertIn('id="capability-status"', page.text)
            self.assertIn('aria-live="polite"', page.text)
            self.assertNotIn("innerHTML", page.text)
            prediction = await client.post("/api/v1/predict", json=STUDENT)
            risk = await client.post("/api/v1/risk", json=STUDENT)
            for response, artifact in (
                (prediction, "final_cgpa_regression.joblib"),
                (risk, "experimental_risk_classifier.joblib"),
            ):
                self.assertEqual(response.status_code, 503)
                self.assertIn(artifact, response.json()["detail"])
                self.assertIn("python -m src.build_models", response.json()["detail"])

            recommendations = await client.post("/api/v1/recommendations", json=STUDENT)
            self.assertEqual(recommendations.status_code, 200)
            self.assertTrue(recommendations.json()["recommendations"])
            plan = await client.post(
                "/api/v1/study-plan",
                json={"available_minutes_by_day": {"Monday": 45}},
            )
            self.assertEqual(plan.status_code, 200)

    async def test_each_model_is_loaded_and_reported_independently(self):
        regression = Mock()
        regression.predict.return_value = [3.1]
        risk_model = Mock()
        risk_model.predict_proba.return_value = np.array([[0.8, 0.2]])

        async with self.client_with_artifacts(
            ("final_cgpa_regression.joblib",),
            {"pipeline": regression, "metadata": {"target_range": [0.0, 4.0]}},
        ) as client:
            health = (await client.get("/api/v1/health")).json()
            self.assertTrue(health["prediction_available"])
            self.assertFalse(health["risk_available"])
            self.assertEqual((await client.post("/api/v1/predict", json=STUDENT)).status_code, 200)
            self.assertEqual((await client.post("/api/v1/risk", json=STUDENT)).status_code, 503)

        async with self.client_with_artifacts(
            ("experimental_risk_classifier.joblib",),
            {"pipeline": risk_model, "metadata": {"label_threshold": 2.0}},
        ) as client:
            health = (await client.get("/api/v1/health")).json()
            self.assertFalse(health["prediction_available"])
            self.assertTrue(health["risk_available"])
            self.assertEqual((await client.post("/api/v1/predict", json=STUDENT)).status_code, 503)
            self.assertEqual((await client.post("/api/v1/risk", json=STUDENT)).status_code, 200)

    async def test_corrupt_artifact_is_reported_as_load_error_not_missing(self):
        with patch.object(api.LOGGER, "exception"):
            async with self.client_with_artifacts(
                ("final_cgpa_regression.joblib",), EOFError("broken artifact")
            ) as client:
                health = (await client.get("/api/v1/health")).json()
                self.assertEqual(health["prediction_status"], "load_error")
                self.assertFalse(health["prediction_available"])
                response = await client.post("/api/v1/predict", json=STUDENT)
                self.assertEqual(response.status_code, 503)
                self.assertIn("could not be loaded", response.json()["detail"])
                self.assertIn("API logs", response.json()["detail"])
                self.assertEqual(
                    (await client.post("/api/v1/recommendations", json=STUDENT)).status_code,
                    200,
                )

    async def test_database_outage_does_not_break_recommendations_or_planner(self):
        with patch.object(api.analytics_db, "record_usage_event", side_effect=OSError("offline")):
            async with self.client_with_artifacts(
                database_url="postgresql://not-used",
                database_status="available",
            ) as client:
                health = (await client.get("/api/v1/health")).json()
                self.assertTrue(health["analytics_database_configured"])
                self.assertTrue(health["analytics_database_available"])
                recommendations = await client.post("/api/v1/recommendations", json=STUDENT)
                plan = await client.post(
                    "/api/v1/study-plan",
                    json={"available_minutes_by_day": {"Monday": 30}},
                )
                self.assertEqual(recommendations.status_code, 200)
                self.assertEqual(plan.status_code, 200)
                health_after = (await client.get("/api/v1/health")).json()
                self.assertEqual(health_after["analytics_database_status"], "unavailable")
                self.assertFalse(health_after["analytics_database_available"])


if __name__ == "__main__":
    unittest.main()

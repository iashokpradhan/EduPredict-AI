"""Unit tests for ML benchmark and longitudinal trajectory modules."""

import unittest
from fastapi.testclient import TestClient

from src import api
from src.ml_benchmark import (
    get_algorithm_benchmark_comparison,
    get_uci_real_dataset_benchmark,
    get_risk_probability_calibration,
)
from src.trajectory import project_longitudinal_trajectory


class MlBenchmarkAndTrajectoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(api.app)

    def test_algorithm_benchmark_structure(self):
        data = get_algorithm_benchmark_comparison()
        self.assertEqual(data["status"], "evaluated")
        self.assertEqual(data["cohort_size"], 5000)
        self.assertGreater(len(data["algorithms"]), 2)
        champion = data["algorithms"][0]
        self.assertIn("Gradient Boosting", champion["model_name"])
        self.assertLess(champion["test_mae"], 0.10)

    def test_uci_dataset_benchmark_structure(self):
        data = get_uci_real_dataset_benchmark()
        self.assertIn("UCI", data["dataset_name"])
        self.assertEqual(data["sample_size"], 649)
        self.assertIn("uci_published_baseline_mae", data)

    def test_probability_calibration_structure(self):
        data = get_risk_probability_calibration()
        self.assertIn("platt_calibrated", data)
        self.assertIn("calibrated_brier_score", data["platt_calibrated"])
        self.assertLess(data["platt_calibrated"]["calibrated_brier_score"], data["raw_model"]["brier_score"])

    def test_trajectory_projection_calculation(self):
        res = project_longitudinal_trajectory(
            semester_cgpAs=[3.2, 3.4, 3.5],
            current_study_hours=5.0,
            current_attendance_pct=92.0,
            remaining_semesters=3,
        )
        self.assertEqual(res["completed_semesters"], 3)
        self.assertEqual(len(res["projected_semesters"]), 3)
        self.assertGreaterEqual(res["estimated_graduation_cgpa"], 3.2)
        self.assertEqual(res["momentum_status"], "accelerating")

    def test_api_benchmark_endpoint(self):
        res = self.client.get("/api/v1/models/benchmark-comparison")
        self.assertEqual(res.status_code, 200)
        json_data = res.json()
        self.assertIn("algorithms", json_data)
        self.assertIn("uci_benchmark", json_data)
        self.assertIn("calibration", json_data)

    def test_api_trajectory_endpoint(self):
        payload = {
            "semester_cgpas": [3.10, 3.30, 3.45],
            "study_hours": 4.5,
            "attendance_pct": 88.0,
            "remaining_semesters": 4,
        }
        res = self.client.post("/api/v1/analytics/trajectory", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("estimated_graduation_cgpa", data)
        self.assertIn("honors_tier_forecast", data)

"""Unit tests for Explainable AI (XAI), Academic Counselor, and Faculty Batch Screening."""

from __future__ import annotations

import unittest
from pathlib import Path

import httpx
import joblib
import pandas as pd

from src import api
from src import db
from src.advisor import build_counselor_recovery_plan
from src.explainability import compute_counterfactual_explanation, compute_feature_attribution
from src.faculty_screening import get_sample_csv_template, screen_student_cohort, validate_and_parse_csv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODELS_DIR = PROJECT_ROOT / "models"
REG_MODEL_PATH = MODELS_DIR / "final_cgpa_regression.joblib"
RISK_MODEL_PATH = MODELS_DIR / "experimental_risk_classifier.joblib"


class XaiAndFacultyScreeningTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        if not REG_MODEL_PATH.exists() or not RISK_MODEL_PATH.exists():
            from src.build_synthetic_demo_models import build_all
            build_all(PROJECT_ROOT)

        cls.reg_bundle = joblib.load(REG_MODEL_PATH)
        cls.risk_bundle = joblib.load(RISK_MODEL_PATH)
        api.app.state.prediction_pipeline = cls.reg_bundle["pipeline"]
        api.app.state.prediction_model_status = "available"
        api.app.state.risk_pipeline = cls.risk_bundle["pipeline"]
        api.app.state.risk_model_status = "available"
        cls.sample_at_risk = {
            "Gender": "Male",
            "Age": 22.0,
            "Major": "Engineering",
            "Attendance_Pct": 56.0,
            "Study_Hours_Per_Day": 1.2,
            "Previous_CGPA": 1.80,
            "Sleep_Hours": 5.0,
            "Social_Hours_Week": 16.0,
        }
        cls.sample_high = {
            "Gender": "Female",
            "Age": 21.0,
            "Major": "Computer Science",
            "Attendance_Pct": 96.0,
            "Study_Hours_Per_Day": 6.0,
            "Previous_CGPA": 3.85,
            "Sleep_Hours": 7.5,
            "Social_Hours_Week": 6.0,
        }

    def test_feature_attribution_structure_and_direction(self):
        result = compute_feature_attribution(self.reg_bundle["pipeline"], self.sample_at_risk)
        self.assertIn("predicted_cgpa", result)
        self.assertIn("cohort_baseline_cgpa", result)
        self.assertIn("feature_attributions", result)
        self.assertGreater(len(result["feature_attributions"]), 0)

        # In at-risk student, Previous_CGPA and Attendance should be penalty drivers
        prev_attr = next(a for a in result["feature_attributions"] if a["feature"] == "Previous_CGPA")
        self.assertLess(prev_attr["point_contribution"], 0.0)
        self.assertEqual(prev_attr["direction"], "penalty")

    def test_counterfactual_explanation_finds_action_path(self):
        cf = compute_counterfactual_explanation(
            self.reg_bundle["pipeline"], self.sample_at_risk, target_cgpa=2.00
        )
        self.assertIn(cf["status"], ["counterfactual_found", "already_achieved"])
        if cf["status"] == "counterfactual_found":
            self.assertGreaterEqual(cf["projected_cgpa_with_actions"], 2.00)
            self.assertIn("action_plan", cf)
            self.assertGreater(len(cf["action_plan"]), 0)

    def test_counselor_recovery_plan_generation(self):
        plan = build_counselor_recovery_plan(self.sample_at_risk)
        self.assertEqual(plan["status"], "ready")
        self.assertEqual(plan["student_major"], "Engineering")
        self.assertGreater(len(plan["diagnosed_vulnerabilities"]), 0)
        self.assertEqual(len(plan["four_week_curriculum_roadmap"]), 4)
        for week in plan["four_week_curriculum_roadmap"]:
            self.assertIn("week", week)
            self.assertIn("primary_milestone", week)
            self.assertIn("target_study_hours", week)

    def test_faculty_batch_screening_csv_parser_and_inference(self):
        csv_text = get_sample_csv_template()
        df = validate_and_parse_csv(csv_text.encode("utf-8"))
        self.assertEqual(len(df), 5)

        triage = screen_student_cohort(
            df,
            reg_pipeline=self.reg_bundle["pipeline"],
            risk_pipeline=self.risk_bundle["pipeline"],
        )
        self.assertEqual(triage["status"], "completed")
        self.assertEqual(triage["total_screened"], 5)
        self.assertIn("summary", triage)
        self.assertIn("critical_intervention", triage["summary"])
        self.assertIn("advisory_watch", triage["summary"])
        self.assertIn("good_standing", triage["summary"])
        self.assertEqual(len(triage["students"]), 5)

    async def test_api_explain_endpoint(self):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=api.app), base_url="http://testserver"
        ) as client:
            res = await client.post("/api/v1/explain", json=self.sample_at_risk)
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertIn("local_attribution", data)
            self.assertIn("counterfactual_plan", data)

    async def test_api_counselor_roadmap_endpoint(self):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=api.app), base_url="http://testserver"
        ) as client:
            res = await client.post("/api/v1/counselor/roadmap", json=self.sample_high)
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertEqual(data["student_major"], "Computer Science")
            self.assertEqual(len(data["four_week_curriculum_roadmap"]), 4)

    async def test_api_faculty_batch_endpoints(self):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=api.app), base_url="http://testserver"
        ) as client:
            template_res = await client.get("/api/v1/faculty/sample-template")
            self.assertEqual(template_res.status_code, 200)
            self.assertIn("text/csv", template_res.headers.get("content-type", ""))

            screen_res = await client.post(
                "/api/v1/faculty/batch-screen",
                content=template_res.content,
                headers={"Content-Type": "text/csv"},
            )
            self.assertEqual(screen_res.status_code, 200)
            data = screen_res.json()
            self.assertEqual(data["total_screened"], 5)

    async def test_auth_registration_login_and_me(self):
        # Initialize DB and demo accounts
        db.initialize_core_database()

        from src.auth import hash_password, verify_password, create_access_token, decode_access_token

        # 1. Password hashing
        h = hash_password("secret123")
        self.assertTrue(verify_password("secret123", h))
        self.assertFalse(verify_password("wrong", h))

        # 2. JWT token encoding / decoding
        tok = create_access_token(user_id=99, email="test@edupredict.ai", role="student", full_name="Test Student")
        payload = decode_access_token(tok)
        self.assertEqual(payload["sub"], "99")
        self.assertEqual(payload["role"], "student")

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=api.app), base_url="http://testserver"
        ) as client:
            # 3. Test Demo Student Login
            login_res = await client.post(
                "/api/v1/auth/login",
                json={"email": "student@edupredict.ai", "password": "student123"},
            )
            self.assertEqual(login_res.status_code, 200)
            login_data = login_res.json()
            self.assertIn("access_token", login_data)
            self.assertEqual(login_data["user"]["role"], "student")
            token = login_data["access_token"]

            # 4. Test /api/v1/auth/me
            me_res = await client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {token}"},
            )
            self.assertEqual(me_res.status_code, 200)
            me_data = me_res.json()
            self.assertEqual(me_data["user"]["email"], "student@edupredict.ai")

            # 5. Test Goal Saving & Retrieval
            goal_res = await client.post(
                "/api/v1/auth/goals",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "target_cgpa": 3.50,
                    "action_plan": {"attendance_boost": 10.0, "study_hours_boost": 2.0},
                },
            )
            self.assertEqual(goal_res.status_code, 200)
            self.assertEqual(goal_res.json()["status"], "saved")

            list_goals_res = await client.get(
                "/api/v1/auth/goals",
                headers={"Authorization": f"Bearer {token}"},
            )
            self.assertEqual(list_goals_res.status_code, 200)
            goals = list_goals_res.json()
            self.assertGreaterEqual(len(goals), 1)


if __name__ == "__main__":
    unittest.main()

import unittest

from src.recommendations import RecommendationConfig, generate_recommendations


class RecommendationTests(unittest.TestCase):
    def test_low_inputs_return_explained_actionable_suggestions(self):
        result = generate_recommendations({
            "Attendance_Pct": 60,
            "Study_Hours_Per_Day": 1,
            "Sleep_Hours": 5,
        })
        self.assertEqual(
            {item["id"] for item in result["recommendations"]},
            {"attendance_review", "study_schedule", "sustainable_rest_routine"},
        )
        self.assertTrue(all(item["action"] and item["why"] for item in result["recommendations"]))
        self.assertIn("do not guarantee", result["disclaimer"])

    def test_exact_cutoffs_do_not_trigger_low_input_rules(self):
        result = generate_recommendations({
            "Attendance_Pct": 80,
            "Study_Hours_Per_Day": 2,
            "Sleep_Hours": 6,
        })
        self.assertEqual(result["recommendations"], [])

    def test_missing_inputs_are_reported_and_not_guessed(self):
        result = generate_recommendations({
            "Attendance_Pct": None,
            "Study_Hours_Per_Day": float("nan"),
        })
        self.assertEqual(result["recommendations"], [])
        self.assertEqual(result["missing_inputs"], ["Attendance_Pct", "Study_Hours_Per_Day", "Sleep_Hours"])

    def test_normal_inputs_do_not_trigger_rules(self):
        result = generate_recommendations({
            "Attendance_Pct": 92,
            "Study_Hours_Per_Day": 3.5,
            "Sleep_Hours": 7.5,
        })
        self.assertEqual(result["recommendations"], [])
        self.assertEqual(result["missing_inputs"], [])

    def test_outcome_and_risk_labels_are_rejected(self):
        for forbidden in ("Final_CGPA", "At_Risk", "risk_label"):
            with self.subTest(field=forbidden), self.assertRaises(ValueError):
                generate_recommendations({forbidden: 1.8})

    def test_input_ranges_and_config_are_validated(self):
        with self.assertRaises(ValueError):
            generate_recommendations({"Attendance_Pct": 101})
        with self.assertRaises(ValueError):
            generate_recommendations({}, RecommendationConfig(attendance_below_pct=101))


if __name__ == "__main__":
    unittest.main()

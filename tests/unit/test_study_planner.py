import unittest

from src.study_planner import DAYS, build_weekly_study_plan


class StudyPlannerTests(unittest.TestCase):
    def test_creates_seven_day_plan_with_requested_capacity(self):
        plan = build_weekly_study_plan({"Monday": 60, "Wednesday": 25})
        self.assertEqual([item["day"] for item in plan["schedule"]], list(DAYS))
        monday = plan["schedule"][0]
        self.assertEqual(sum(block["minutes"] for block in monday["blocks"]), 60)
        self.assertEqual(monday["unused_minutes"], 0)
        self.assertEqual(plan["schedule"][1]["blocks"], [])
        self.assertEqual(plan["schedule"][2]["blocks"][0]["minutes"], 25)
        self.assertIn("does not guarantee", plan["disclaimer"])

    def test_custom_focus_areas_are_used_deterministically(self):
        plan = build_weekly_study_plan({"Tuesday": 55}, ["Reading", "Practice"])
        focuses = [block["focus"] for block in plan["schedule"][1]["blocks"]]
        self.assertEqual(focuses, ["Reading", "Short break", "Practice"])

    def test_rejects_invalid_days_and_time(self):
        with self.assertRaises(ValueError):
            build_weekly_study_plan({"Someday": 30})
        with self.assertRaises(ValueError):
            build_weekly_study_plan({"Monday": 481})

    def test_rejects_empty_focus_areas(self):
        with self.assertRaises(ValueError):
            build_weekly_study_plan({}, [])


if __name__ == "__main__":
    unittest.main()

import unittest
from unittest.mock import MagicMock, patch

from src import analytics_db


class AnalyticsDatabaseTests(unittest.TestCase):
    def test_database_is_disabled_without_a_url(self):
        with patch.dict("os.environ", {analytics_db.DATABASE_URL_ENV: ""}):
            self.assertIsNone(analytics_db.database_url_from_environment())
        self.assertEqual(analytics_db.probe_database(None), "disabled")

    def test_event_allowlist_rejects_unknown_types_and_rule_ids(self):
        with self.assertRaisesRegex(ValueError, "Unsupported"):
            analytics_db.validate_event("raw_student_payload", None, True, True)
        with self.assertRaisesRegex(ValueError, "Unknown recommendation"):
            analytics_db.validate_event(
                "recommendation_rule_triggered", "untrusted-rule", True, True
            )
        with self.assertRaisesRegex(ValueError, "only valid"):
            analytics_db.validate_event("study_plan_created", "attendance_review", True, True)
        with self.assertRaisesRegex(ValueError, "booleans"):
            analytics_db.validate_event("study_plan_created", None, 1, False)

    def test_insert_is_parameterized_and_contains_only_allowed_aggregate_values(self):
        connection = MagicMock()
        connection.__enter__.return_value = connection
        with patch.object(analytics_db, "_connect", return_value=connection):
            analytics_db.record_usage_event(
                "postgresql://not-used",
                event_type="recommendation_rule_triggered",
                recommendation_rule_id="attendance_review",
                prediction_available=False,
                risk_available=False,
            )
        sql, parameters = connection.execute.call_args.args
        self.assertIn("VALUES (%s, %s, %s, %s)", sql)
        self.assertEqual(
            parameters,
            ("recommendation_rule_triggered", "attendance_review", False, False),
        )
        self.assertNotIn("student", sql.lower())
        self.assertNotIn("cgpa", sql.lower())

    def test_probe_reports_schema_missing_and_available(self):
        connection = MagicMock()
        connection.__enter__.return_value = connection
        connection.execute.return_value.fetchone.return_value = ("analytics.usage_events",)
        with patch.object(analytics_db, "_connect", return_value=connection):
            self.assertEqual(analytics_db.probe_database("postgresql://not-used"), "available")
        connection.execute.return_value.fetchone.return_value = (None,)
        with patch.object(analytics_db, "_connect", return_value=connection):
            self.assertEqual(analytics_db.probe_database("postgresql://not-used"), "schema_missing")

    def test_probe_degrades_safely_on_connection_failure(self):
        with patch.object(analytics_db, "_connect", side_effect=OSError("connection refused")):
            self.assertEqual(analytics_db.probe_database("postgresql://not-used"), "unavailable")

    def test_probe_reports_missing_optional_driver_without_raising(self):
        with patch.object(
            analytics_db,
            "_connect",
            side_effect=RuntimeError("PostgreSQL analytics is configured but psycopg is not installed."),
        ):
            self.assertEqual(analytics_db.probe_database("postgresql://not-used"), "driver_missing")

    def test_setup_requires_connection_url_and_executes_idempotent_sql(self):
        with patch.dict("os.environ", {analytics_db.DATABASE_URL_ENV: ""}):
            with self.assertRaisesRegex(RuntimeError, analytics_db.DATABASE_URL_ENV):
                analytics_db.setup_schema()

        connection = MagicMock()
        connection.__enter__.return_value = connection
        with patch.object(analytics_db, "_connect", return_value=connection):
            analytics_db.setup_schema("postgresql://not-used")
        statements = [call.args[0] for call in connection.execute.call_args_list]
        self.assertTrue(any("CREATE TABLE IF NOT EXISTS analytics.usage_events" in sql for sql in statements))
        self.assertTrue(any("CREATE OR REPLACE VIEW bi.daily_usage" in sql for sql in statements))
        self.assertTrue(any("CREATE OR REPLACE VIEW bi.daily_recommendation_rules" in sql for sql in statements))
        self.assertTrue(any("CREATE OR REPLACE VIEW bi.daily_model_availability" in sql for sql in statements))

    def test_power_bi_views_expose_only_aggregates(self):
        sql = analytics_db.MIGRATION_PATH.read_text(encoding="utf-8").lower()
        views = sql.split("create or replace view")
        self.assertEqual(len(views), 4)
        for view in views[1:]:
            self.assertIn("group by", view)
            self.assertIn("count(*)", view)
            self.assertNotIn("student_id", view)
            self.assertNotIn("final_cgpa", view)
            self.assertNotIn("predicted_cgpa", view)
            self.assertNotIn("risk_probability", view)


if __name__ == "__main__":
    unittest.main()

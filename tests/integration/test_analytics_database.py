"""Opt-in PostgreSQL check; requires a dedicated disposable test database."""

import importlib.util
import os
import unittest

from src import analytics_db


TEST_DATABASE_URL = os.environ.get("EDUPREDICT_TEST_DATABASE_URL", "").strip()
POSTGRES_TESTS_AVAILABLE = bool(TEST_DATABASE_URL) and importlib.util.find_spec("psycopg") is not None


@unittest.skipUnless(
    POSTGRES_TESTS_AVAILABLE,
    "Set EDUPREDICT_TEST_DATABASE_URL to a dedicated PostgreSQL test database and install psycopg to run this integration check.",
)
class AnalyticsDatabaseIntegrationTests(unittest.TestCase):
    def test_migration_and_aggregate_views(self):
        import psycopg

        analytics_db.setup_schema(TEST_DATABASE_URL)
        with psycopg.connect(TEST_DATABASE_URL, autocommit=False) as connection:
            connection.execute(
                """
                INSERT INTO analytics.usage_events
                    (event_type, recommendation_rule_id, prediction_available, risk_available)
                VALUES (%s, %s, %s, %s)
                """,
                ("recommendation_rule_triggered", "attendance_review", False, False),
            )
            rule_count = connection.execute(
                """
                SELECT event_count FROM bi.daily_recommendation_rules
                WHERE usage_date_utc = (now() AT TIME ZONE 'UTC')::date
                  AND recommendation_rule_id = %s
                """,
                ("attendance_review",),
            ).fetchone()
            usage = connection.execute(
                """
                SELECT event_count FROM bi.daily_usage
                WHERE usage_date_utc = (now() AT TIME ZONE 'UTC')::date
                  AND event_type = %s
                """,
                ("recommendation_rule_triggered",),
            ).fetchone()
            self.assertIsNotNone(rule_count)
            self.assertGreaterEqual(rule_count[0], 1)
            self.assertIsNotNone(usage)
            self.assertGreaterEqual(usage[0], 1)
            connection.rollback()


if __name__ == "__main__":
    unittest.main()

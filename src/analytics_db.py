"""Opt-in, aggregate-only PostgreSQL usage analytics.

No student inputs, identifiers, predictions, or risk scores are accepted by this
module. Database-driver imports happen only when a database URL is configured.
"""

from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path


LOGGER = logging.getLogger(__name__)
DATABASE_URL_ENV = "EDUPREDICT_DATABASE_URL"
MIGRATION_PATH = Path(__file__).resolve().parents[1] / "sql" / "001_aggregate_analytics.sql"

EVENT_TYPES = frozenset({
    "prediction_requested",
    "risk_requested",
    "recommendations_evaluated",
    "recommendation_rule_triggered",
    "study_plan_created",
})
RECOMMENDATION_RULE_IDS = frozenset({
    "attendance_review",
    "study_schedule",
    "sustainable_rest_routine",
})


def database_url_from_environment() -> str | None:
    """Return the optional connection string without logging or exposing it."""

    value = os.environ.get(DATABASE_URL_ENV, "").strip()
    return value or None


def _connect(database_url: str):
    """Import Psycopg lazily so the default app has no database dependency."""

    try:
        import psycopg
    except ImportError as exc:
        raise RuntimeError(
            "PostgreSQL analytics is configured but psycopg is not installed. "
            "Install the project's optional dependency from requirements.txt."
        ) from exc
    return psycopg.connect(database_url, connect_timeout=2, autocommit=False)


def probe_database(database_url: str | None) -> str:
    """Report disabled, ready, schema-missing, driver-missing, or unavailable."""

    if not database_url:
        return "disabled"
    try:
        with _connect(database_url) as connection:
            exists = connection.execute(
                "SELECT to_regclass(%s)", ("analytics.usage_events",)
            ).fetchone()[0]
        return "available" if exists else "schema_missing"
    except RuntimeError as exc:
        if "psycopg is not installed" in str(exc):
            return "driver_missing"
        return "unavailable"
    except Exception:
        # Connection exceptions may include host details. Keep those out of health
        # responses and logs; the server operator can verify their local DSN.
        LOGGER.warning("Optional PostgreSQL analytics connection is unavailable")
        return "unavailable"


def validate_event(
    event_type: str,
    recommendation_rule_id: str | None,
    prediction_available: bool,
    risk_available: bool,
) -> tuple[str, str | None, bool, bool]:
    """Validate the small allow-listed event shape before database access."""

    if event_type not in EVENT_TYPES:
        raise ValueError("Unsupported aggregate analytics event type.")
    if type(prediction_available) is not bool or type(risk_available) is not bool:
        raise ValueError("Model availability values must be booleans.")
    if event_type == "recommendation_rule_triggered":
        if recommendation_rule_id not in RECOMMENDATION_RULE_IDS:
            raise ValueError("Unknown recommendation rule identifier.")
    elif recommendation_rule_id is not None:
        raise ValueError("A recommendation rule identifier is only valid for a rule event.")
    return event_type, recommendation_rule_id, prediction_available, risk_available


def record_usage_event(
    database_url: str,
    *,
    event_type: str,
    prediction_available: bool,
    risk_available: bool,
    recommendation_rule_id: str | None = None,
) -> None:
    """Insert one allow-listed aggregate event with parameterized SQL."""

    event = validate_event(
        event_type,
        recommendation_rule_id,
        prediction_available,
        risk_available,
    )
    with _connect(database_url) as connection:
        connection.execute(
            """
            INSERT INTO analytics.usage_events
                (event_type, recommendation_rule_id, prediction_available, risk_available)
            VALUES (%s, %s, %s, %s)
            """,
            event,
        )


def setup_schema(database_url: str | None = None) -> None:
    """Apply the idempotent SQL schema and reporting-view migration."""

    resolved_url = database_url or database_url_from_environment()
    if not resolved_url:
        raise RuntimeError(
            f"Set {DATABASE_URL_ENV} before setting up the optional analytics database."
        )
    script = MIGRATION_PATH.read_text(encoding="utf-8")
    with _connect(resolved_url) as connection:
        for statement in script.split(";"):
            if statement.strip():
                connection.execute(statement)


def main() -> None:
    parser = argparse.ArgumentParser(description="Set up optional aggregate analytics views.")
    parser.add_argument("command", choices=("setup",), help="Apply the idempotent SQL setup.")
    parser.parse_args()
    setup_schema()
    print("Aggregate analytics schema and Power BI views are ready.")


if __name__ == "__main__":
    main()

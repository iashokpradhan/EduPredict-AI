"""Core relational database layer for EduPredict AI.

Provides dual-engine support:
1. PostgreSQL (via psycopg 3) when EDUPREDICT_DATABASE_URL is set.
2. SQLite (local file data/edupredict.db) as a zero-configuration fallback
   for development, testing, and offline capstone presentations.

Manages tables:
- students: Core student demographic records
- academic_records: Attendance, study hours, previous & final CGPA
- predictions: Prediction inference log (predicted CGPA, risk, probabilities)
- recommendations_log: Record of generated recommendations
- usage_events: Aggregated operational telemetry
"""

from __future__ import annotations

import logging
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Generator, Sequence

LOGGER = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SQL_DIR = PROJECT_ROOT / "sql"
DATA_DIR = PROJECT_ROOT / "data"
DEFAULT_SQLITE_PATH = DATA_DIR / "edupredict.db"

DATABASE_URL_ENV = "EDUPREDICT_DATABASE_URL"


def get_database_engine_type(database_url: str | None = None) -> str:
    """Detect whether we are running PostgreSQL or SQLite."""
    url = database_url or os.environ.get(DATABASE_URL_ENV, "").strip()
    if url.startswith("postgresql://") or url.startswith("postgres://"):
        return "postgresql"
    return "sqlite"


def get_database_url() -> str:
    """Return configured PostgreSQL URL or default SQLite path."""
    configured = os.environ.get(DATABASE_URL_ENV, "").strip()
    if configured:
        return configured
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return str(DEFAULT_SQLITE_PATH)


@contextmanager
def get_connection(database_url: str | None = None) -> Generator[Any, None, None]:
    """Provide a database connection context (PostgreSQL or SQLite)."""
    target_url = database_url or get_database_url()
    engine_type = get_database_engine_type(target_url)

    if engine_type == "postgresql":
        try:
            import psycopg
        except ImportError as exc:
            raise RuntimeError("psycopg is not installed. Install psycopg[binary] for PostgreSQL.") from exc
        conn = psycopg.connect(target_url, autocommit=False)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    else:
        # SQLite
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        sqlite_file = target_url if target_url.endswith(".db") else str(DEFAULT_SQLITE_PATH)
        conn = sqlite3.connect(sqlite_file)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


def initialize_core_database(database_url: str | None = None) -> None:
    """Create all core tables, indexes, and initial views."""
    target_url = database_url or get_database_url()
    engine_type = get_database_engine_type(target_url)

    schema_file = SQL_DIR / "002_edupredict_core_schema.sql"
    if not schema_file.exists():
        raise FileNotFoundError(f"Schema file missing: {schema_file}")

    ddl_script = schema_file.read_text(encoding="utf-8")

    with get_connection(target_url) as conn:
        if engine_type == "postgresql":
            # PostgreSQL execution
            for statement in ddl_script.split(";"):
                stmt = statement.strip()
                if stmt:
                    conn.execute(stmt)
        else:
            # SQLite execution (convert PostgreSQL specifics if any, or run clean SQLite DDL)
            _init_sqlite_schema(conn)

    try:
        seed_default_demo_users(target_url)
    except Exception as exc:
        LOGGER.warning("Could not seed default demo users: %s", exc)

    LOGGER.info("EduPredict AI database initialized successfully (%s).", engine_type)


def _init_sqlite_schema(conn: sqlite3.Connection) -> None:
    """Initialize schema specifically tailored and optimized for SQLite."""
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS students (
        student_id TEXT PRIMARY KEY,
        gender TEXT NOT NULL CHECK(gender IN ('Female', 'Male', 'Other')),
        age INTEGER NOT NULL CHECK(age BETWEEN 10 AND 100),
        major TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now', 'utc'))
    );

    CREATE TABLE IF NOT EXISTS academic_records (
        record_id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
        attendance_pct REAL NOT NULL CHECK(attendance_pct BETWEEN 0 AND 100),
        study_hours_per_day REAL NOT NULL CHECK(study_hours_per_day BETWEEN 0 AND 24),
        previous_cgpa REAL NOT NULL CHECK(previous_cgpa BETWEEN 0 AND 4),
        sleep_hours REAL NOT NULL CHECK(sleep_hours BETWEEN 0 AND 24),
        social_hours_week REAL NOT NULL CHECK(social_hours_week BETWEEN 0 AND 168),
        final_cgpa REAL CHECK(final_cgpa BETWEEN 0 AND 4),
        recorded_at TEXT NOT NULL DEFAULT (datetime('now', 'utc'))
    );

    CREATE INDEX IF NOT EXISTS idx_records_student_id ON academic_records(student_id);
    CREATE INDEX IF NOT EXISTS idx_records_final_cgpa ON academic_records(final_cgpa);
    CREATE INDEX IF NOT EXISTS idx_records_major ON students(major);

    CREATE TABLE IF NOT EXISTS predictions (
        prediction_id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT REFERENCES students(student_id) ON DELETE SET NULL,
        gender TEXT,
        age REAL,
        major TEXT,
        attendance_pct REAL,
        study_hours_per_day REAL,
        previous_cgpa REAL,
        sleep_hours REAL,
        social_hours_week REAL,
        predicted_cgpa REAL NOT NULL,
        risk_probability REAL NOT NULL,
        risk_label TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now', 'utc'))
    );

    CREATE TABLE IF NOT EXISTS recommendations_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        prediction_id INTEGER REFERENCES predictions(prediction_id) ON DELETE CASCADE,
        rule_id TEXT NOT NULL,
        title TEXT NOT NULL,
        action TEXT NOT NULL,
        why TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now', 'utc'))
    );

    CREATE TABLE IF NOT EXISTS usage_events (
        event_id INTEGER PRIMARY KEY AUTOINCREMENT,
        occurred_at TEXT NOT NULL DEFAULT (datetime('now', 'utc')),
        event_type TEXT NOT NULL,
        recommendation_rule_id TEXT,
        prediction_available INTEGER NOT NULL,
        risk_available INTEGER NOT NULL
    );

    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        hashed_password TEXT NOT NULL,
        full_name TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('student', 'advisor', 'admin')),
        student_id TEXT REFERENCES students(student_id) ON DELETE SET NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now', 'utc'))
    );

    CREATE TABLE IF NOT EXISTS saved_goals (
        goal_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
        target_cgpa REAL NOT NULL,
        action_plan_json TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now', 'utc'))
    );
    """)


def insert_prediction_log(
    student_features: dict[str, Any],
    predicted_cgpa: float,
    risk_probability: float,
    risk_label: str,
    recommendations: Sequence[dict[str, str]] | None = None,
    student_id: str | None = None,
    database_url: str | None = None,
) -> int | None:
    """Log an inference request, its outputs, and triggered recommendations."""
    try:
        with get_connection(database_url) as conn:
            engine = get_database_engine_type(database_url or get_database_url())
            if engine == "postgresql":
                cursor = conn.execute(
                    """
                    INSERT INTO predictions (
                        student_id, gender, age, major, attendance_pct,
                        study_hours_per_day, previous_cgpa, sleep_hours,
                        social_hours_week, predicted_cgpa, risk_probability, risk_label
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING prediction_id
                    """,
                    (
                        student_id,
                        student_features.get("Gender"),
                        student_features.get("Age"),
                        student_features.get("Major"),
                        student_features.get("Attendance_Pct"),
                        student_features.get("Study_Hours_Per_Day"),
                        student_features.get("Previous_CGPA"),
                        student_features.get("Sleep_Hours"),
                        student_features.get("Social_Hours_Week"),
                        predicted_cgpa,
                        risk_probability,
                        risk_label,
                    ),
                )
                pred_id = cursor.fetchone()[0]
                if recommendations and pred_id:
                    for rec in recommendations:
                        conn.execute(
                            """
                            INSERT INTO recommendations_log (
                                prediction_id, rule_id, title, action, why
                            ) VALUES (%s, %s, %s, %s, %s)
                            """,
                            (pred_id, rec.get("id"), rec.get("title"), rec.get("action"), rec.get("why")),
                        )
                return pred_id
            else:
                cursor = conn.execute(
                    """
                    INSERT INTO predictions (
                        student_id, gender, age, major, attendance_pct,
                        study_hours_per_day, previous_cgpa, sleep_hours,
                        social_hours_week, predicted_cgpa, risk_probability, risk_label
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        student_id,
                        student_features.get("Gender"),
                        student_features.get("Age"),
                        student_features.get("Major"),
                        student_features.get("Attendance_Pct"),
                        student_features.get("Study_Hours_Per_Day"),
                        student_features.get("Previous_CGPA"),
                        student_features.get("Sleep_Hours"),
                        student_features.get("Social_Hours_Week"),
                        predicted_cgpa,
                        risk_probability,
                        risk_label,
                    ),
                )
                pred_id = cursor.lastrowid
                if recommendations and pred_id:
                    for rec in recommendations:
                        conn.execute(
                            """
                            INSERT INTO recommendations_log (
                                prediction_id, rule_id, title, action, why
                            ) VALUES (?, ?, ?, ?, ?)
                            """,
                            (pred_id, rec.get("id"), rec.get("title"), rec.get("action"), rec.get("why")),
                        )
                return pred_id
    except Exception as exc:
        LOGGER.warning("Could not persist prediction log: %s", exc)
        return None


def get_recent_predictions(limit: int = 15, database_url: str | None = None) -> list[dict[str, Any]]:
    """Retrieve recent prediction history for instructor/adviser review."""
    try:
        with get_connection(database_url) as conn:
            engine = get_database_engine_type(database_url or get_database_url())
            param_marker = "%s" if engine == "postgresql" else "?"
            cursor = conn.execute(
                f"""
                SELECT
                    prediction_id, student_id, gender, age, major,
                    attendance_pct, study_hours_per_day, previous_cgpa,
                    sleep_hours, social_hours_week, predicted_cgpa,
                    risk_probability, risk_label, created_at
                FROM predictions
                ORDER BY prediction_id DESC
                LIMIT {param_marker}
                """,
                (limit,),
            )
            cols = [
                "prediction_id", "student_id", "gender", "age", "major",
                "attendance_pct", "study_hours_per_day", "previous_cgpa",
                "sleep_hours", "social_hours_week", "predicted_cgpa",
                "risk_probability", "risk_label", "created_at"
            ]
            rows = cursor.fetchall()
            results = []
            for row in rows:
                if isinstance(row, dict):
                    results.append(row)
                elif hasattr(row, "_asdict"):
                    results.append(row._asdict())
                elif hasattr(row, "keys"):
                    results.append({k: row[k] for k in row.keys()})
                else:
                    results.append(dict(zip(cols, row)))
            return results
    except Exception as exc:
        LOGGER.warning("Could not retrieve prediction history: %s", exc)
        return []


def get_cohort_summary(database_url: str | None = None) -> dict[str, Any]:
    """Compute aggregate academic summary for the live dashboard analytics tab."""
    try:
        with get_connection(database_url) as conn:
            # Overall metrics
            row = conn.execute("""
                SELECT
                    COUNT(*) as total_students,
                    ROUND(AVG(ar.final_cgpa), 2) as avg_final_cgpa,
                    ROUND(AVG(ar.previous_cgpa), 2) as avg_previous_cgpa,
                    ROUND(AVG(ar.attendance_pct), 1) as avg_attendance,
                    ROUND(AVG(ar.study_hours_per_day), 1) as avg_study_hours,
                    ROUND(AVG(ar.sleep_hours), 1) as avg_sleep_hours,
                    ROUND(AVG(ar.social_hours_week), 1) as avg_social_hours,
                    SUM(CASE WHEN ar.final_cgpa < 2.0 THEN 1 ELSE 0 END) as at_risk_count
                FROM academic_records ar
            """).fetchone()

            if not row or (row[0] if not hasattr(row, "keys") else row["total_students"]) == 0:
                return _fallback_static_cohort_summary()

            total = row[0] if not hasattr(row, "keys") else row["total_students"]
            at_risk = row[7] if not hasattr(row, "keys") else row["at_risk_count"]
            risk_pct = round((at_risk / total * 100), 2) if total else 0.0

            # Major breakdown
            major_rows = conn.execute("""
                SELECT
                    s.major,
                    COUNT(*) as student_count,
                    ROUND(AVG(ar.final_cgpa), 2) as avg_cgpa,
                    ROUND(AVG(ar.attendance_pct), 1) as avg_attendance,
                    ROUND(AVG(ar.study_hours_per_day), 1) as avg_study_hours,
                    SUM(CASE WHEN ar.final_cgpa < 2.0 THEN 1 ELSE 0 END) as at_risk_count
                FROM students s
                JOIN academic_records ar ON s.student_id = ar.student_id
                GROUP BY s.major
                ORDER BY avg_cgpa DESC
            """).fetchall()

            majors_data = []
            for m in major_rows:
                m_dict = dict(m) if hasattr(m, "keys") else {
                    "major": m[0], "student_count": m[1], "avg_cgpa": m[2],
                    "avg_attendance": m[3], "avg_study_hours": m[4], "at_risk_count": m[5]
                }
                majors_data.append(m_dict)

            # Performance bands
            bands_row = conn.execute("""
                SELECT
                    SUM(CASE WHEN final_cgpa >= 3.5 THEN 1 ELSE 0 END) as first_class,
                    SUM(CASE WHEN final_cgpa >= 3.0 AND final_cgpa < 3.5 THEN 1 ELSE 0 END) as upper_second,
                    SUM(CASE WHEN final_cgpa >= 2.0 AND final_cgpa < 3.0 THEN 1 ELSE 0 END) as lower_second,
                    SUM(CASE WHEN final_cgpa < 2.0 THEN 1 ELSE 0 END) as at_risk
                FROM academic_records
            """).fetchone()

            bands = dict(bands_row) if hasattr(bands_row, "keys") else {
                "first_class": bands_row[0], "upper_second": bands_row[1],
                "lower_second": bands_row[2], "at_risk": bands_row[3]
            }

            return {
                "status": "connected",
                "total_records": total,
                "avg_final_cgpa": row[1] if not hasattr(row, "keys") else row["avg_final_cgpa"],
                "avg_previous_cgpa": row[2] if not hasattr(row, "keys") else row["avg_previous_cgpa"],
                "avg_attendance": row[3] if not hasattr(row, "keys") else row["avg_attendance"],
                "avg_study_hours": row[4] if not hasattr(row, "keys") else row["avg_study_hours"],
                "avg_sleep_hours": row[5] if not hasattr(row, "keys") else row["avg_sleep_hours"],
                "avg_social_hours": row[6] if not hasattr(row, "keys") else row["avg_social_hours"],
                "at_risk_count": at_risk,
                "at_risk_rate_pct": risk_pct,
                "majors": majors_data,
                "performance_bands": bands,
            }
    except Exception as exc:
        LOGGER.warning("Could not calculate cohort summary: %s", exc)
        return _fallback_static_cohort_summary()


def _fallback_static_cohort_summary() -> dict[str, Any]:
    """Benchmark summary from local 5,000 student dataset analysis."""
    return {
        "status": "benchmark_fallback",
        "total_records": 5000,
        "avg_final_cgpa": 3.27,
        "avg_previous_cgpa": 3.09,
        "avg_attendance": 83.8,
        "avg_study_hours": 4.5,
        "avg_sleep_hours": 7.0,
        "avg_social_hours": 8.0,
        "at_risk_count": 42,
        "at_risk_rate_pct": 0.84,
        "majors": [
            {"major": "Psychology", "student_count": 869, "avg_cgpa": 3.29, "avg_attendance": 84.1, "avg_study_hours": 4.6, "at_risk_count": 6},
            {"major": "Mathematics", "student_count": 859, "avg_cgpa": 3.28, "avg_attendance": 83.9, "avg_study_hours": 4.5, "at_risk_count": 7},
            {"major": "Computer Science", "student_count": 795, "avg_cgpa": 3.27, "avg_attendance": 83.7, "avg_study_hours": 4.5, "at_risk_count": 7},
            {"major": "Economics", "student_count": 835, "avg_cgpa": 3.27, "avg_attendance": 83.6, "avg_study_hours": 4.5, "at_risk_count": 8},
            {"major": "Engineering", "student_count": 799, "avg_cgpa": 3.26, "avg_attendance": 83.5, "avg_study_hours": 4.5, "at_risk_count": 7},
            {"major": "Business", "student_count": 843, "avg_cgpa": 3.26, "avg_attendance": 83.7, "avg_study_hours": 4.5, "at_risk_count": 7},
        ],
        "performance_bands": {
            "first_class": 1820,
            "upper_second": 2110,
            "lower_second": 1028,
            "at_risk": 42,
        },
    }


def create_user(
    email: str,
    hashed_password: str,
    full_name: str,
    role: str = "student",
    student_id: str | None = None,
    database_url: str | None = None,
) -> int:
    """Create a new user account and return the generated user_id."""
    with get_connection(database_url) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO users (email, hashed_password, full_name, role, student_id)
            VALUES (?, ?, ?, ?, ?)
            """,
            (email.strip().lower(), hashed_password, full_name.strip(), role, student_id),
        )
        conn.commit()
        return cursor.lastrowid


def get_user_by_email(email: str, database_url: str | None = None) -> dict[str, Any] | None:
    """Fetch user record by unique email address."""
    with get_connection(database_url) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT user_id, email, hashed_password, full_name, role, student_id, created_at
            FROM users WHERE email = ?
            """,
            (email.strip().lower(),),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return {
            "user_id": row["user_id"],
            "email": row["email"],
            "hashed_password": row["hashed_password"],
            "full_name": row["full_name"],
            "role": row["role"],
            "student_id": row["student_id"],
            "created_at": row["created_at"],
        }


def get_user_by_id(user_id: int, database_url: str | None = None) -> dict[str, Any] | None:
    """Fetch user record by unique user_id."""
    with get_connection(database_url) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT user_id, email, full_name, role, student_id, created_at
            FROM users WHERE user_id = ?
            """,
            (user_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return {
            "user_id": row["user_id"],
            "email": row["email"],
            "full_name": row["full_name"],
            "role": row["role"],
            "student_id": row["student_id"],
            "created_at": row["created_at"],
        }


def save_student_goal(
    user_id: int,
    target_cgpa: float,
    action_plan_json: str,
    database_url: str | None = None,
) -> int:
    """Save an actionable student goal / simulation."""
    with get_connection(database_url) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO saved_goals (user_id, target_cgpa, action_plan_json)
            VALUES (?, ?, ?)
            """,
            (user_id, target_cgpa, action_plan_json),
        )
        conn.commit()
        return cursor.lastrowid


def get_student_goals(user_id: int, database_url: str | None = None) -> list[dict[str, Any]]:
    """Retrieve all saved goals for a user."""
    with get_connection(database_url) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT goal_id, user_id, target_cgpa, action_plan_json, created_at
            FROM saved_goals WHERE user_id = ? ORDER BY goal_id DESC
            """,
            (user_id,),
        )
        rows = cursor.fetchall()
        return [
            {
                "goal_id": r["goal_id"],
                "target_cgpa": r["target_cgpa"],
                "action_plan_json": r["action_plan_json"],
                "created_at": r["created_at"],
            }
            for r in rows
        ]


def seed_default_demo_users(database_url: str | None = None) -> None:
    """Seed student and advisor demo accounts if they do not exist."""
    from src.auth import hash_password

    # Check if student S00001 exists in students table
    has_student = False
    try:
        with get_connection(database_url) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM students WHERE student_id = 'S00001'")
            has_student = bool(cursor.fetchone())
    except Exception:
        has_student = False

    # 1. Student Demo: Alex Turner (CS)
    if not get_user_by_email("student@edupredict.ai", database_url):
        create_user(
            email="student@edupredict.ai",
            hashed_password=hash_password("student123"),
            full_name="Alex Turner",
            role="student",
            student_id="S00001" if has_student else None,
            database_url=database_url,
        )

    # 2. Advisor Demo: Dr. Sharma (Academic Dean)
    if not get_user_by_email("advisor@edupredict.ai", database_url):
        create_user(
            email="advisor@edupredict.ai",
            hashed_password=hash_password("advisor123"),
            full_name="Dr. Sharma",
            role="advisor",
            student_id=None,
            database_url=database_url,
        )

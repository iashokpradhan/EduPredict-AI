"""Database initialization and seeding CLI for EduPredict AI.

Loads student records from data/raw/Student_data.csv into:
- students
- academic_records
and optionally populates initial sample predictions for demonstration.

Usage:
    python -m src.seed_db
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import pandas as pd

from src.db import (
    get_connection,
    get_database_engine_type,
    get_database_url,
    initialize_core_database,
    insert_prediction_log,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
LOGGER = logging.getLogger("seed_db")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = PROJECT_ROOT / "data" / "raw" / "Student_data.csv"


def seed_database(database_url: str | None = None, limit: int | None = None) -> None:
    """Initialize tables and load records from Student_data.csv."""
    target_url = database_url or get_database_url()
    LOGGER.info("Target database: %s", target_url)

    # 1. Initialize schema
    initialize_core_database(target_url)

    # 2. Check if dataset exists
    if not DATA_PATH.is_file():
        LOGGER.warning(
            "Authorized CSV missing at %s; generating 100 synthetic demonstration records.",
            DATA_PATH,
        )
        import numpy as np

        idx = np.arange(100)
        df = pd.DataFrame({
            "Student_ID": [f"ID{10000+i}" for i in idx],
            "Gender": ["Female" if i % 2 == 0 else "Male" for i in idx],
            "Age": 18 + (idx % 7),
            "Major": ["Computer Science", "Engineering", "Business", "Mathematics", "Economics", "Psychology"][idx % 6],
            "Attendance_Pct": 60.0 + (idx % 40) * 1.0,
            "Study_Hours_Per_Day": 1.0 + (idx % 20) * 0.3,
            "Previous_CGPA": 2.0 + (idx % 20) * 0.1,
            "Sleep_Hours": 5.0 + (idx % 10) * 0.5,
            "Social_Hours_Week": 2 + (idx % 15),
            "Final_CGPA": 2.2 + (idx % 18) * 0.1,
        })
    else:
        LOGGER.info("Loading student data from %s...", DATA_PATH)
        df = pd.read_csv(DATA_PATH)
        if limit:
            df = df.head(limit)

    LOGGER.info("Seeding %d student records...", len(df))

    engine_type = get_database_engine_type(target_url)

    with get_connection(target_url) as conn:
        # Check existing count
        existing = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
        if existing > 0:
            LOGGER.info("Database already contains %d students. Skipping duplicate insert.", existing)
        else:
            # Insert students and academic records
            if engine_type == "postgresql":
                student_tuples = [
                    (row["Student_ID"], row["Gender"], int(row["Age"]), row["Major"])
                    for _, row in df.iterrows()
                ]
                with conn.cursor() as cur:
                    cur.executemany(
                        """
                        INSERT INTO students (student_id, gender, age, major)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (student_id) DO NOTHING
                        """,
                        student_tuples,
                    )
                    records_tuples = [
                        (
                            row["Student_ID"],
                            float(row["Attendance_Pct"]),
                            float(row["Study_Hours_Per_Day"]),
                            float(row["Previous_CGPA"]),
                            float(row["Sleep_Hours"]),
                            float(row["Social_Hours_Week"]),
                            float(row["Final_CGPA"]),
                        )
                        for _, row in df.iterrows()
                    ]
                    cur.executemany(
                        """
                        INSERT INTO academic_records (
                            student_id, attendance_pct, study_hours_per_day,
                            previous_cgpa, sleep_hours, social_hours_week, final_cgpa
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """,
                        records_tuples,
                    )
            else:
                # SQLite
                student_tuples = [
                    (row["Student_ID"], row["Gender"], int(row["Age"]), row["Major"])
                    for _, row in df.iterrows()
                ]
                conn.executemany(
                    """
                    INSERT OR IGNORE INTO students (student_id, gender, age, major)
                    VALUES (?, ?, ?, ?)
                    """,
                    student_tuples,
                )
                records_tuples = [
                    (
                        row["Student_ID"],
                        float(row["Attendance_Pct"]),
                        float(row["Study_Hours_Per_Day"]),
                        float(row["Previous_CGPA"]),
                        float(row["Sleep_Hours"]),
                        float(row["Social_Hours_Week"]),
                        float(row["Final_CGPA"]),
                    )
                    for _, row in df.iterrows()
                ]
                conn.executemany(
                    """
                    INSERT INTO academic_records (
                        student_id, attendance_pct, study_hours_per_day,
                        previous_cgpa, sleep_hours, social_hours_week, final_cgpa
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    records_tuples,
                )

            LOGGER.info("Seeded %d student records and academic records.", len(df))

    # Add sample prediction logs for demonstration
    sample_preds = [
        {
            "features": {"Gender": "Female", "Age": 21, "Major": "Computer Science", "Attendance_Pct": 92.5, "Study_Hours_Per_Day": 5.5, "Previous_CGPA": 3.75, "Sleep_Hours": 7.5, "Social_Hours_Week": 6},
            "cgpa": 3.82, "risk": 0.02, "label": "not_at_risk",
            "recs": []
        },
        {
            "features": {"Gender": "Male", "Age": 20, "Major": "Engineering", "Attendance_Pct": 68.0, "Study_Hours_Per_Day": 1.5, "Previous_CGPA": 2.15, "Sleep_Hours": 5.5, "Social_Hours_Week": 18},
            "cgpa": 2.05, "risk": 0.46, "label": "not_at_risk",
            "recs": [{"id": "attendance_review", "title": "Review attendance", "action": "Increase class presence", "why": "Attendance is 68%"}]
        },
        {
            "features": {"Gender": "Female", "Age": 22, "Major": "Business", "Attendance_Pct": 54.0, "Study_Hours_Per_Day": 1.0, "Previous_CGPA": 1.70, "Sleep_Hours": 4.5, "Social_Hours_Week": 14},
            "cgpa": 1.68, "risk": 0.88, "label": "at_risk",
            "recs": [
                {"id": "attendance_review", "title": "Attendance Alert", "action": "Speak to academic advisor immediately", "why": "Attendance is 54%"},
                {"id": "study_schedule", "title": "Structured Study", "action": "Target 2-3 hours daily study blocks", "why": "Study time is 1 hr"}
            ]
        }
    ]

    for p in sample_preds:
        insert_prediction_log(
            student_features=p["features"],
            predicted_cgpa=p["cgpa"],
            risk_probability=p["risk"],
            risk_label=p["label"],
            recommendations=p["recs"],
            database_url=target_url,
        )

    LOGGER.info("Database seeding completed successfully.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed EduPredict AI database.")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of rows to insert.")
    parser.add_argument("--url", type=str, default=None, help="Target database URL.")
    args = parser.parse_args()
    seed_database(database_url=args.url, limit=args.limit)


if __name__ == "__main__":
    main()

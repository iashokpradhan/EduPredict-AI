"""Power BI Data Export Utility for EduPredict AI.

Exports clean, star-schema dimension and fact tables as CSV files into data/powerbi/
ready for direct import into Power BI Desktop or Excel.

Usage:
    python -m src.export_powerbi_data
"""

from __future__ import annotations

import logging
from pathlib import Path
import pandas as pd

from src.db import get_connection, get_database_url

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
LOGGER = logging.getLogger("export_powerbi")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
POWERBI_EXPORT_DIR = PROJECT_ROOT / "data" / "powerbi"


def export_powerbi_datasets() -> None:
    """Generate all dimension and fact CSVs for Power BI."""
    POWERBI_EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    db_url = get_database_url()

    with get_connection(db_url) as conn:
        LOGGER.info("Exporting Dim_Students...")
        dim_students = pd.read_sql_query(
            "SELECT student_id, gender, age, major, created_at AS enrolled_date FROM students",
            conn,
        )
        dim_students.to_csv(POWERBI_EXPORT_DIR / "dim_students.csv", index=False)

        LOGGER.info("Exporting Fact_Academic_Records...")
        fact_records = pd.read_sql_query(
            """
            SELECT
                ar.record_id,
                ar.student_id,
                s.major,
                s.gender,
                ar.attendance_pct,
                ar.study_hours_per_day,
                ar.previous_cgpa,
                ar.sleep_hours,
                ar.social_hours_week,
                ar.final_cgpa,
                ROUND(ar.final_cgpa - ar.previous_cgpa, 2) AS cgpa_growth,
                CASE WHEN ar.final_cgpa < 2.0 THEN 1 ELSE 0 END AS is_at_risk,
                CASE
                    WHEN ar.final_cgpa >= 3.50 THEN 'First Class (3.5+)'
                    WHEN ar.final_cgpa >= 3.00 THEN 'Upper Second (3.00-3.49)'
                    WHEN ar.final_cgpa >= 2.00 THEN 'Lower Second (2.00-2.99)'
                    ELSE 'At-Risk (<2.00)'
                END AS honors_band,
                CASE
                    WHEN ar.attendance_pct >= 90 THEN 'Tier 1 (90%+)'
                    WHEN ar.attendance_pct >= 80 THEN 'Tier 2 (80-89%)'
                    WHEN ar.attendance_pct >= 70 THEN 'Tier 3 (70-79%)'
                    ELSE 'Tier 4 (<70%)'
                END AS attendance_tier,
                CASE
                    WHEN ar.study_hours_per_day >= 6.0 THEN 'High (6+ hrs)'
                    WHEN ar.study_hours_per_day >= 4.0 THEN 'Moderate-High (4-6 hrs)'
                    WHEN ar.study_hours_per_day >= 2.0 THEN 'Moderate (2-4 hrs)'
                    ELSE 'Low (<2 hrs)'
                END AS study_tier,
                CASE
                    WHEN ar.sleep_hours < 6.0 THEN 'Sleep Deprived (<6h)'
                    WHEN ar.sleep_hours <= 8.0 THEN 'Optimal (6-8h)'
                    ELSE 'Extended (>8h)'
                END AS sleep_tier,
                ar.recorded_at
            FROM academic_records ar
            JOIN students s ON ar.student_id = s.student_id
            """,
            conn,
        )
        fact_records.to_csv(POWERBI_EXPORT_DIR / "fact_academic_records.csv", index=False)

        LOGGER.info("Exporting Dim_Majors_Summary...")
        dim_majors = pd.read_sql_query(
            """
            SELECT
                s.major,
                COUNT(*) AS total_enrolled,
                ROUND(AVG(ar.final_cgpa), 2) AS avg_final_cgpa,
                ROUND(AVG(ar.previous_cgpa), 2) AS avg_previous_cgpa,
                ROUND(AVG(ar.attendance_pct), 1) AS avg_attendance,
                ROUND(AVG(ar.study_hours_per_day), 1) AS avg_study_hours,
                SUM(CASE WHEN ar.final_cgpa < 2.0 THEN 1 ELSE 0 END) AS at_risk_count,
                ROUND(SUM(CASE WHEN ar.final_cgpa < 2.0 THEN 1.0 ELSE 0.0 END) / COUNT(*) * 100, 2) AS at_risk_rate_pct
            FROM students s
            JOIN academic_records ar ON s.student_id = ar.student_id
            GROUP BY s.major
            """,
            conn,
        )
        dim_majors.to_csv(POWERBI_EXPORT_DIR / "dim_majors_summary.csv", index=False)

        LOGGER.info("Exporting Fact_Predictions...")
        fact_preds = pd.read_sql_query(
            """
            SELECT
                prediction_id,
                student_id,
                gender,
                age,
                major,
                attendance_pct,
                study_hours_per_day,
                previous_cgpa,
                predicted_cgpa,
                risk_probability,
                risk_label,
                created_at
            FROM predictions
            """,
            conn,
        )
        fact_preds.to_csv(POWERBI_EXPORT_DIR / "fact_predictions.csv", index=False)

    LOGGER.info("Successfully exported 4 Power BI CSV datasets to: %s", POWERBI_EXPORT_DIR)


if __name__ == "__main__":
    export_powerbi_datasets()

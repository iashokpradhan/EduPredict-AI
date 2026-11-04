"""Faculty & Counselor Batch Screening Engine.

Provides:
- Ingestion and schema validation of batch student CSV files.
- High-throughput inference for cohort triage.
- Multi-tier categorization:
    1. Critical Intervention (CGPA < 2.0 or Risk Prob >= 0.5)
    2. Advisory Watch (2.0 <= CGPA < 3.0)
    3. Good Standing (CGPA >= 3.0)
- Sample CSV template generation for faculty counselors.
"""

from __future__ import annotations

import io
from typing import Any
import pandas as pd
from fastapi import HTTPException


REQUIRED_COLUMNS = [
    "Gender",
    "Age",
    "Major",
    "Attendance_Pct",
    "Study_Hours_Per_Day",
    "Previous_CGPA",
    "Sleep_Hours",
    "Social_Hours_Week",
]

SAMPLE_TEMPLATE_CSV = """Student_ID,Gender,Age,Major,Attendance_Pct,Study_Hours_Per_Day,Previous_CGPA,Sleep_Hours,Social_Hours_Week
S1001,Male,21,Computer Science,92.5,5.5,3.75,7.5,8.0
S1002,Female,20,Business,84.0,3.5,3.10,7.0,12.0
S1003,Male,22,Engineering,54.0,1.2,1.85,5.0,18.0
S1004,Female,20,Psychology,76.0,2.5,2.75,5.5,20.0
S1005,Male,21,Economics,88.0,4.0,3.30,7.0,10.0
"""


def get_sample_csv_template() -> str:
    """Return a formatted sample CSV string for faculty testing."""
    return SAMPLE_TEMPLATE_CSV


def validate_and_parse_csv(file_bytes: bytes, max_rows: int = 1000) -> pd.DataFrame:
    """Validate uploaded CSV for size, schema, and realistic values."""
    if len(file_bytes) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File exceeds 5MB size limit.")

    try:
        df = pd.read_csv(io.BytesIO(file_bytes))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid CSV format: {exc}")

    if df.empty:
        raise HTTPException(status_code=400, detail="The uploaded CSV file contains no data rows.")

    if len(df) > max_rows:
        raise HTTPException(status_code=400, detail=f"CSV contains {len(df)} rows. Maximum allowed is {max_rows}.")

    missing_cols = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_cols:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required columns: {', '.join(missing_cols)}. Use the sample template.",
        )

    # Clean numeric fields
    numeric_cols = ["Age", "Attendance_Pct", "Study_Hours_Per_Day", "Previous_CGPA", "Sleep_Hours", "Social_Hours_Week"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
        if df[col].isna().any():
            raise HTTPException(
                status_code=400,
                detail=f"Column '{col}' contains non-numeric or missing values.",
            )

    # Range validations
    if (df["Attendance_Pct"] < 0).any() or (df["Attendance_Pct"] > 100).any():
        raise HTTPException(status_code=400, detail="Attendance_Pct must be between 0 and 100.")

    if (df["Previous_CGPA"] < 0).any() or (df["Previous_CGPA"] > 4.0).any():
        raise HTTPException(status_code=400, detail="Previous_CGPA must be between 0.0 and 4.0.")

    return df


def screen_student_cohort(
    df: pd.DataFrame,
    reg_pipeline: Any,
    risk_pipeline: Any,
) -> dict[str, Any]:
    """Execute high-speed inference across the uploaded cohort dataframe."""
    feature_df = df[REQUIRED_COLUMNS].copy()

    # Vectorized / batch inference
    preds = reg_pipeline.predict(feature_df)
    risk_probs = risk_pipeline.predict_proba(feature_df)[:, 1]

    results: list[dict[str, Any]] = []
    critical_count = 0
    advisory_count = 0
    good_standing_count = 0

    dept_stats: dict[str, dict[str, int]] = {}

    for idx, row in df.iterrows():
        student_id = str(row.get("Student_ID", f"STU-{idx + 1:04d}"))
        major = str(row["Major"])
        cgpa = float(preds[idx])
        risk_prob = float(risk_probs[idx])

        if major not in dept_stats:
            dept_stats[major] = {"total": 0, "critical": 0, "advisory": 0, "good": 0}
        dept_stats[major]["total"] += 1

        if cgpa < 2.00 or risk_prob >= 0.50:
            tier = "Critical Intervention"
            tier_badge = "critical"
            critical_count += 1
            dept_stats[major]["critical"] += 1
            recommended_action = "Schedule urgent academic counselor meeting; review course load"
        elif cgpa < 3.00:
            tier = "Advisory Watch"
            tier_badge = "advisory"
            advisory_count += 1
            dept_stats[major]["advisory"] += 1
            recommended_action = "Recommend peer tutoring and attendance monitoring"
        else:
            tier = "Good Standing"
            tier_badge = "good"
            good_standing_count += 1
            dept_stats[major]["good"] += 1
            recommended_action = "On track; recommend advanced study modules"

        results.append({
            "student_id": student_id,
            "major": major,
            "attendance_pct": round(float(row["Attendance_Pct"]), 1),
            "study_hours": round(float(row["Study_Hours_Per_Day"]), 1),
            "previous_cgpa": round(float(row["Previous_CGPA"]), 2),
            "predicted_cgpa": round(cgpa, 2),
            "risk_probability_pct": round(risk_prob * 100, 1),
            "triage_tier": tier,
            "triage_badge": tier_badge,
            "recommended_action": recommended_action,
        })

    # Sort students by highest risk first
    results.sort(key=lambda s: s["predicted_cgpa"])

    total = len(df)
    return {
        "status": "completed",
        "total_screened": total,
        "summary": {
            "critical_intervention": critical_count,
            "critical_intervention_pct": round((critical_count / total) * 100, 1) if total else 0.0,
            "advisory_watch": advisory_count,
            "advisory_watch_pct": round((advisory_count / total) * 100, 1) if total else 0.0,
            "good_standing": good_standing_count,
            "good_standing_pct": round((good_standing_count / total) * 100, 1) if total else 0.0,
        },
        "department_breakdown": [
            {"major": k, **v} for k, v in dept_stats.items()
        ],
        "students": results,
    }

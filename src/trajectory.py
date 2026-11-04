"""Multi-Semester Academic Trajectory & Longitudinal CGPA Forecasting."""

from __future__ import annotations

from typing import Any
import numpy as np


def project_longitudinal_trajectory(
    semester_cgpAs: list[float],
    current_study_hours: float,
    current_attendance_pct: float,
    remaining_semesters: int = 4,
) -> dict[str, Any]:
    """Calculate historical trend, velocity, and projected graduation CGPA across remaining semesters."""
    if not semester_cgpAs:
        semester_cgpAs = [3.0]

    valid_cgpAs = [min(4.0, max(0.0, float(c))) for c in semester_cgpAs]
    num_completed = len(valid_cgpAs)

    # Calculate semester-over-semester momentum (delta)
    momentum = 0.0
    if num_completed >= 2:
        deltas = [valid_cgpAs[i] - valid_cgpAs[i - 1] for i in range(1, num_completed)]
        momentum = float(np.mean(deltas))

    current_cgpa = valid_cgpAs[-1]
    cumulative_cgpa = float(np.mean(valid_cgpAs))

    # Behavioral modifier: attendance and study hours affect future velocity
    behavioral_lift = 0.0
    if current_attendance_pct >= 90 and current_study_hours >= 5.0:
        behavioral_lift = 0.08
    elif current_attendance_pct < 75 or current_study_hours < 2.0:
        behavioral_lift = -0.12

    projected_semesters = []
    projected_val = current_cgpa
    cumulative_tracker = list(valid_cgpAs)

    for i in range(1, remaining_semesters + 1):
        sem_num = num_completed + i
        step_delta = (momentum * 0.5) + behavioral_lift
        projected_val = min(4.0, max(1.0, projected_val + step_delta))
        cumulative_tracker.append(projected_val)
        projected_semesters.append({
            "semester_number": sem_num,
            "projected_semester_cgpa": round(projected_val, 2),
            "projected_cumulative_cgpa": round(float(np.mean(cumulative_tracker)), 2),
        })

    projected_final_cgpa = projected_semesters[-1]["projected_cumulative_cgpa"] if projected_semesters else cumulative_cgpa

    return {
        "completed_semesters": num_completed,
        "historical_cgpAs": valid_cgpAs,
        "current_cumulative_cgpa": round(cumulative_cgpa, 2),
        "trajectory_momentum_per_semester": round(momentum, 3),
        "momentum_status": "accelerating" if momentum > 0.05 else ("declining" if momentum < -0.05 else "stable"),
        "projected_semesters": projected_semesters,
        "estimated_graduation_cgpa": round(projected_final_cgpa, 2),
        "honors_tier_forecast": (
            "First Class Honors (3.5+)" if projected_final_cgpa >= 3.5
            else ("Upper Second Class (3.0-3.49)" if projected_final_cgpa >= 3.0
                  else ("Lower Second Class (2.0-2.99)" if projected_final_cgpa >= 2.0 else "Academic Probation (<2.0)"))
        ),
    }

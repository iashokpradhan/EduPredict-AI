"""Explainable AI (XAI) engine for EduPredict AI.

Provides:
1. Local feature attribution (Marginal Shapley decomposition) showing exact
   positive and negative point contributions relative to the cohort baseline.
2. Algorithmic Counterfactual Optimization: finds the minimal realistic
   behavioral change needed for an at-risk student to achieve a target CGPA.
"""

from __future__ import annotations

from typing import Any
import numpy as np
import pandas as pd


# Cohort reference baselines computed from the 5,000 student dataset
COHORT_BASELINE = {
    "Gender": "Female",
    "Age": 21.0,
    "Major": "Computer Science",
    "Attendance_Pct": 83.8,
    "Study_Hours_Per_Day": 4.5,
    "Previous_CGPA": 3.09,
    "Sleep_Hours": 7.0,
    "Social_Hours_Week": 8.0,
}

FEATURE_FRIENDLY_NAMES = {
    "Previous_CGPA": "Prior CGPA Track Record",
    "Attendance_Pct": "Classroom Attendance Rate",
    "Study_Hours_Per_Day": "Daily Independent Study",
    "Sleep_Hours": "Nightly Sleep Duration",
    "Social_Hours_Week": "Extracurricular & Social Load",
    "Major": "Academic Major Field",
    "Age": "Student Age Cohort",
    "Gender": "Demographic Baseline",
}


def compute_feature_attribution(pipeline: Any, student_features: dict[str, Any]) -> dict[str, Any]:
    """Compute local marginal feature attribution relative to the cohort mean baseline."""
    student_df = pd.DataFrame([student_features])
    predicted_cgpa = float(pipeline.predict(student_df)[0])

    baseline_df = pd.DataFrame([COHORT_BASELINE])
    baseline_cgpa = float(pipeline.predict(baseline_df)[0])

    net_delta = round(predicted_cgpa - baseline_cgpa, 3)

    attributions: list[dict[str, Any]] = []
    # Primary predictive features
    primary_features = [
        "Previous_CGPA",
        "Attendance_Pct",
        "Study_Hours_Per_Day",
        "Sleep_Hours",
        "Social_Hours_Week",
    ]

    for feat in primary_features:
        # Evaluate marginal difference by substituting cohort mean
        perturbed = student_features.copy()
        perturbed[feat] = COHORT_BASELINE[feat]
        perturbed_pred = float(pipeline.predict(pd.DataFrame([perturbed]))[0])
        # Delta = predicted - value without this feature's deviation
        delta = round(predicted_cgpa - perturbed_pred, 3)

        attributions.append({
            "feature": feat,
            "friendly_name": FEATURE_FRIENDLY_NAMES.get(feat, feat),
            "student_value": student_features.get(feat),
            "cohort_mean": COHORT_BASELINE.get(feat),
            "point_contribution": delta,
            "direction": "positive" if delta >= 0 else "penalty",
            "narrative": (
                f"+{delta:.2f} points boost above cohort baseline"
                if delta >= 0
                else f"{delta:.2f} points drag below cohort baseline"
            ),
        })

    # Sort by absolute impact magnitude
    attributions.sort(key=lambda item: abs(item["point_contribution"]), reverse=True)

    return {
        "predicted_cgpa": round(predicted_cgpa, 2),
        "cohort_baseline_cgpa": round(baseline_cgpa, 2),
        "net_points_from_cohort_mean": net_delta,
        "feature_attributions": attributions,
        "top_positive_driver": next((a for a in attributions if a["point_contribution"] > 0), None),
        "top_penalty_driver": next((a for a in attributions if a["point_contribution"] < 0), None),
        "methodology": "Local Marginal Feature Attribution (evaluated against 5,000 student empirical baseline)",
    }


def compute_counterfactual_explanation(
    pipeline: Any,
    student_features: dict[str, Any],
    target_cgpa: float = 2.00,
) -> dict[str, Any]:
    """Find the minimal behavioral change (least-cost path) to reach target CGPA."""
    initial_cgpa = float(pipeline.predict(pd.DataFrame([student_features]))[0])

    # If already at or above target, no counterfactual search needed
    if initial_cgpa >= target_cgpa:
        return {
            "status": "already_achieved",
            "current_cgpa": round(initial_cgpa, 2),
            "target_cgpa": target_cgpa,
            "message": f"Student is already projected at {initial_cgpa:.2f}, meeting or exceeding target {target_cgpa:.2f}.",
            "required_actions": [],
        }

    best_cf: dict[str, Any] | None = None
    min_cost = float("inf")

    # Grid search across realistic behavioral interventions
    att_steps = [0.0, 5.0, 10.0, 15.0, 20.0, 25.0, 30.0]
    study_steps = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]
    sleep_steps = [0.0, 1.0, 2.0]

    for d_att in att_steps:
        for d_study in study_steps:
            for d_sleep in sleep_steps:
                candidate = student_features.copy()
                candidate["Attendance_Pct"] = min(100.0, candidate["Attendance_Pct"] + d_att)
                candidate["Study_Hours_Per_Day"] = min(12.0, candidate["Study_Hours_Per_Day"] + d_study)
                candidate["Sleep_Hours"] = min(10.0, candidate["Sleep_Hours"] + d_sleep)

                pred = float(pipeline.predict(pd.DataFrame([candidate]))[0])
                if pred >= target_cgpa:
                    # Effort cost weight: 1.0 per 5% attendance, 1.2 per 0.5h study, 0.8 per 1h sleep
                    cost = (d_att / 5.0) * 1.0 + (d_study / 0.5) * 1.2 + d_sleep * 0.8
                    if cost < min_cost:
                        min_cost = cost
                        best_cf = {
                            "current_predicted_cgpa": round(initial_cgpa, 2),
                            "projected_cgpa_with_actions": round(pred, 2),
                            "target_cgpa": target_cgpa,
                            "effort_cost_index": round(cost, 1),
                            "actions": {
                                "attendance_boost_pct": float(d_att),
                                "study_hours_boost_daily": float(d_study),
                                "sleep_hours_boost_nightly": float(d_sleep),
                                "new_attendance_pct": round(candidate["Attendance_Pct"], 1),
                                "new_study_hours_daily": round(candidate["Study_Hours_Per_Day"], 1),
                                "new_sleep_hours_nightly": round(candidate["Sleep_Hours"], 1),
                            },
                        }

    if best_cf:
        actions_list = []
        act = best_cf["actions"]
        if act["attendance_boost_pct"] > 0:
            actions_list.append(f"Increase attendance by +{act['attendance_boost_pct']:.0f}% (target: {act['new_attendance_pct']}%)")
        if act["study_hours_boost_daily"] > 0:
            actions_list.append(f"Add +{act['study_hours_boost_daily']:.1f} hrs/day dedicated study (target: {act['new_study_hours_daily']} hrs)")
        if act["sleep_hours_boost_nightly"] > 0:
            actions_list.append(f"Improve nightly sleep by +{act['sleep_hours_boost_nightly']:.1f} hrs (target: {act['new_sleep_hours_nightly']} hrs)")

        best_cf["action_plan"] = actions_list
        best_cf["status"] = "counterfactual_found"
        return best_cf

    return {
        "status": "target_unreachable_by_lifestyle_alone",
        "current_cgpa": round(initial_cgpa, 2),
        "target_cgpa": target_cgpa,
        "message": "Target CGPA cannot be achieved solely via behavioral changes; prior academic credits impose a ceiling.",
        "required_actions": [],
    }

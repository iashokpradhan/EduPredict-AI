"""Transparent, configurable student study-support recommendations.

Recommendations use only current, student-provided routine information. They are
guidance for discussion and planning, not predictions, medical advice, or guarantees.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from collections.abc import Mapping
from typing import Any


@dataclass(frozen=True)
class RecommendationConfig:
    """Editable heuristic cutoffs; these are project assumptions, not policy."""

    attendance_below_pct: float = 80.0
    study_hours_below_per_day: float = 2.0
    sleep_hours_below_per_day: float = 6.0


DISCLAIMER = (
    "These suggestions are optional guidance based on the supplied routine inputs. "
    "They do not guarantee a CGPA outcome and should not replace a conversation "
    "with an instructor or adviser."
)

_FIELDS = {
    "Attendance_Pct": (0.0, 100.0),
    "Study_Hours_Per_Day": (0.0, 24.0),
    "Sleep_Hours": (0.0, 24.0),
}
_FORBIDDEN_FIELDS = {"Final_CGPA", "At_Risk", "risk_label", "risk_target"}


def _optional_number(inputs: Mapping[str, Any], name: str) -> float | None:
    """Read an optional numeric field, rejecting invalid or out-of-range values."""

    value = inputs.get(name)
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a number, not a boolean.")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be numeric or missing.") from exc
    if math.isnan(number):
        return None
    low, high = _FIELDS[name]
    if not math.isfinite(number) or not low <= number <= high:
        raise ValueError(f"{name} must be between {low:g} and {high:g}.")
    return number


def generate_recommendations(
    student_inputs: Mapping[str, Any],
    config: RecommendationConfig | None = None,
) -> dict[str, Any]:
    """Return deterministic suggestions and input-availability notes.

    `Final_CGPA` and target-derived risk labels are rejected to prevent the rules
    from using an outcome that may not yet be known at prediction time. Missing
    routine fields are skipped rather than guessed or imputed.
    """

    if not isinstance(student_inputs, Mapping):
        raise TypeError("student_inputs must be a mapping of field names to values.")
    forbidden = _FORBIDDEN_FIELDS.intersection(student_inputs)
    if forbidden:
        raise ValueError(
            "Outcome-derived fields are not recommendation inputs: "
            + ", ".join(sorted(forbidden))
        )

    settings = config or RecommendationConfig()
    limits = (
        settings.attendance_below_pct,
        settings.study_hours_below_per_day,
        settings.sleep_hours_below_per_day,
    )
    if any(not math.isfinite(float(limit)) for limit in limits):
        raise ValueError("Recommendation thresholds must be finite numbers.")
    if not 0 <= settings.attendance_below_pct <= 100:
        raise ValueError("Attendance cutoff must be between 0 and 100.")
    if not 0 <= settings.study_hours_below_per_day <= 24:
        raise ValueError("Study-hours cutoff must be between 0 and 24.")
    if not 0 <= settings.sleep_hours_below_per_day <= 24:
        raise ValueError("Sleep-hours cutoff must be between 0 and 24.")

    values = {name: _optional_number(student_inputs, name) for name in _FIELDS}
    missing = [name for name, value in values.items() if value is None]
    suggestions: list[dict[str, str]] = []

    attendance = values["Attendance_Pct"]
    if attendance is not None and attendance < settings.attendance_below_pct:
        suggestions.append({
            "id": "attendance_review",
            "title": "Review your attendance routine",
            "action": (
                "Look for a manageable way to attend scheduled classes more regularly; "
                "if barriers are getting in the way, consider discussing them with an adviser."
            ),
            "why": (
                f"The supplied attendance is {attendance:g}%, below the configurable "
                f"{settings.attendance_below_pct:g}% project heuristic."
            ),
        })

    study_hours = values["Study_Hours_Per_Day"]
    if study_hours is not None and study_hours < settings.study_hours_below_per_day:
        suggestions.append({
            "id": "study_schedule",
            "title": "Try a consistent study block",
            "action": (
                "Choose one realistic study period and split larger tasks into shorter, "
                "planned sessions that fit your schedule."
            ),
            "why": (
                f"The supplied study time is {study_hours:g} hours per day, below the "
                f"configurable {settings.study_hours_below_per_day:g}-hour heuristic."
            ),
        })

    sleep_hours = values["Sleep_Hours"]
    if sleep_hours is not None and sleep_hours < settings.sleep_hours_below_per_day:
        suggestions.append({
            "id": "sustainable_rest_routine",
            "title": "Keep a sustainable rest routine",
            "action": (
                "Consider protecting a regular time for rest alongside study and other "
                "commitments; discuss ongoing concerns with appropriate support."
            ),
            "why": (
                f"The supplied sleep time is {sleep_hours:g} hours per day, below the "
                f"configurable {settings.sleep_hours_below_per_day:g}-hour project heuristic."
            ),
        })

    return {
        "recommendations": suggestions,
        "missing_inputs": missing,
        "disclaimer": DISCLAIMER,
    }

"""Deterministic study-plan fallback; intentionally makes no external AI calls."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


DAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
DEFAULT_FOCUS_AREAS = ("Review class notes", "Practice course problems", "Work on an assignment")


def build_weekly_study_plan(
    available_minutes_by_day: Mapping[str, Any],
    focus_areas: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Create a repeatable block schedule within the time a student reports.

    This is a rules-based fallback, not a generative-language-model response.
    Missing days are treated as unavailable and no assumptions are made about
    grades, learning needs, or medical circumstances.
    """

    if not isinstance(available_minutes_by_day, Mapping):
        raise TypeError("available_minutes_by_day must map day names to minutes.")
    unknown_days = set(available_minutes_by_day) - set(DAYS)
    if unknown_days:
        raise ValueError(f"Unknown day name(s): {', '.join(sorted(unknown_days))}.")

    areas = tuple(focus_areas) if focus_areas is not None else DEFAULT_FOCUS_AREAS
    if not areas or any(not isinstance(area, str) or not area.strip() for area in areas):
        raise ValueError("Provide one or more non-empty focus-area names.")

    schedule = []
    block_number = 0
    for day in DAYS:
        raw_minutes = available_minutes_by_day.get(day, 0)
        if isinstance(raw_minutes, bool):
            raise ValueError(f"Available minutes for {day} must be an integer from 0 to 480.")
        try:
            minutes = int(raw_minutes)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Available minutes for {day} must be an integer from 0 to 480.") from exc
        if minutes != raw_minutes or not 0 <= minutes <= 480:
            raise ValueError(f"Available minutes for {day} must be an integer from 0 to 480.")

        blocks = []
        remaining = minutes
        while remaining >= 25:
            duration = min(25, remaining)
            blocks.append({
                "minutes": duration,
                "focus": areas[block_number % len(areas)],
            })
            block_number += 1
            remaining -= duration
            if remaining >= 5:
                blocks.append({"minutes": 5, "focus": "Short break"})
                remaining -= 5
        schedule.append({"day": day, "blocks": blocks, "unused_minutes": remaining})

    return {
        "planner_type": "deterministic rules-based fallback",
        "schedule": schedule,
        "disclaimer": (
            "This is an editable planning template based only on the time and focus "
            "areas supplied. Adjust it to your classes, responsibilities, and wellbeing; "
            "it does not guarantee academic results."
        ),
    }

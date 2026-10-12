"""FastAPI entry point for the local EduPredict AI demonstration."""

from __future__ import annotations

from contextlib import asynccontextmanager
import logging
from pathlib import Path
from typing import Annotated

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, StrictStr, field_validator

from src.recommendations import generate_recommendations
from src.study_planner import DAYS, build_weekly_study_plan
from src import analytics_db


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODEL_DIRECTORY = PROJECT_ROOT / "models"
FRONTEND_DIRECTORY = PROJECT_ROOT / "frontend"
LOGGER = logging.getLogger(__name__)


class StudentFeatures(BaseModel):
    """Prediction-time input schema; target and identifier are deliberately absent."""

    model_config = ConfigDict(extra="forbid")

    Gender: Annotated[str, Field(min_length=1, max_length=40)]
    Age: Annotated[float, Field(ge=10, le=100)]
    Major: Annotated[str, Field(min_length=1, max_length=100)]
    Attendance_Pct: Annotated[float, Field(ge=0, le=100)]
    Study_Hours_Per_Day: Annotated[float, Field(ge=0, le=24)]
    Previous_CGPA: Annotated[float, Field(ge=0, le=4)]
    Sleep_Hours: Annotated[float, Field(ge=0, le=24)]
    Social_Hours_Week: Annotated[float, Field(ge=0, le=168)]


class StudyPlanRequest(BaseModel):
    """Validated, prediction-independent inputs for the weekly planner."""

    model_config = ConfigDict(extra="forbid")

    available_minutes_by_day: dict[str, Annotated[int, Field(strict=True, ge=0, le=480)]]
    focus_areas: list[StrictStr] | None = Field(default=None, min_length=1, max_length=10)

    @field_validator("available_minutes_by_day")
    @classmethod
    def validate_day_names(cls, minutes_by_day: dict[str, int]) -> dict[str, int]:
        unknown_days = set(minutes_by_day) - set(DAYS)
        if unknown_days:
            raise ValueError(
                "Unknown day name(s): " + ", ".join(sorted(unknown_days))
                + ". Use Monday through Sunday."
            )
        return minutes_by_day

    @field_validator("focus_areas")
    @classmethod
    def validate_focus_areas(cls, focus_areas: list[str] | None) -> list[str] | None:
        if focus_areas is None:
            return None
        cleaned = [area.strip() for area in focus_areas]
        if any(not area for area in cleaned):
            raise ValueError("Each focus area must contain non-whitespace text.")
        if any(len(area) > 100 for area in cleaned):
            raise ValueError("Each focus area must be 100 characters or fewer.")
        return cleaned


@asynccontextmanager
async def lifespan(application: FastAPI):
    regression_path = MODEL_DIRECTORY / "final_cgpa_regression.joblib"
    risk_path = MODEL_DIRECTORY / "experimental_risk_classifier.joblib"
    # joblib uses pickle semantics: load only trusted, locally generated artifacts.
    for capability, path, method in (
        ("prediction", regression_path, "predict"),
        ("risk", risk_path, "predict_proba"),
    ):
        pipeline, metadata, status = _load_model_bundle(path, method, capability)
        setattr(application.state, f"{capability}_pipeline", pipeline)
        setattr(application.state, f"{capability}_metadata", metadata)
        setattr(application.state, f"{capability}_model_status", status)
    database_url = analytics_db.database_url_from_environment()
    application.state.analytics_database_url = database_url
    application.state.analytics_database_status = analytics_db.probe_database(database_url)
    yield


def _load_model_bundle(path: Path, method: str, capability: str):
    """Load one local model, distinguishing absent files from unusable artifacts."""
    if not path.exists():
        return None, None, "missing_artifact"
    if not path.is_file():
        LOGGER.error("Expected %s model artifact %s to be a file", capability, path.name)
        return None, None, "load_error"
    try:
        bundle = joblib.load(path)
        if not isinstance(bundle, dict) or not isinstance(bundle.get("metadata"), dict):
            raise ValueError("Expected a model bundle with pipeline and metadata entries")
        pipeline = bundle.get("pipeline")
        if pipeline is None or not callable(getattr(pipeline, method, None)):
            raise ValueError(f"Model pipeline does not provide {method}()")
        metadata = bundle["metadata"]
        if capability == "risk":
            float(metadata["label_threshold"])
        return pipeline, metadata, "available"
    except Exception:
        LOGGER.exception("Could not load %s model artifact %s", capability, path.name)
        return None, None, "load_error"


def _require_model(capability: str, artifact_name: str) -> None:
    status = getattr(app.state, f"{capability}_model_status", "missing_artifact")
    if status == "available":
        return
    if status == "load_error":
        detail = (
            f"The {capability} feature is unavailable because its local artifact exists "
            "but could not be loaded (corrupt or incompatible). Check the API logs. "
            "With an authorized dataset, regenerate artifacts using `python -m src.build_models`."
        )
    else:
        detail = (
            f"The {capability} feature is unavailable because {artifact_name} is missing. "
            "The dashboard, recommendations, and study planner remain available. To enable "
            "model features, provide an authorized dataset at data/raw/Student_data.csv and run "
            "`python -m src.build_models` from the project root."
        )
    raise HTTPException(status_code=503, detail=detail)


def _record_analytics_event(
    event_type: str,
    recommendation_rule_id: str | None = None,
) -> None:
    """Record only allow-listed aggregate data; failures never break app routes."""

    database_url = getattr(app.state, "analytics_database_url", None)
    if not database_url:
        return
    if getattr(app.state, "analytics_database_status", "disabled") in {
        "disabled", "driver_missing", "schema_missing", "unavailable"
    }:
        return
    try:
        analytics_db.record_usage_event(
            database_url,
            event_type=event_type,
            recommendation_rule_id=recommendation_rule_id,
            prediction_available=app.state.prediction_model_status == "available",
            risk_available=app.state.risk_model_status == "available",
        )
        app.state.analytics_database_status = "available"
    except RuntimeError as error:
        # The optional adapter is not installed; preserve the core app behavior.
        app.state.analytics_database_status = (
            "driver_missing" if "psycopg is not installed" in str(error) else "unavailable"
        )
        LOGGER.warning("Optional PostgreSQL analytics event was not recorded")
    except Exception:
        app.state.analytics_database_status = "unavailable"
        # Do not log a driver exception that might contain connection details.
        LOGGER.warning("Optional PostgreSQL analytics event was not recorded")


app = FastAPI(
    title="EduPredict AI",
    description="Local educational decision-support demonstration; estimates are not guarantees.",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/api/v1/health", tags=["health"])
def health() -> dict[str, object]:
    prediction = app.state.prediction_model_status
    risk = app.state.risk_model_status
    both_models = prediction == "available" and risk == "available"
    return {
        "status": "ready" if both_models else "degraded",
        "ready": True,
        "models_loaded": both_models,
        "prediction_available": prediction == "available",
        "prediction_status": prediction,
        "risk_available": risk == "available",
        "risk_status": risk,
        "recommendations_available": True,
        "study_plan_available": True,
        "analytics_database_configured": bool(
            getattr(app.state, "analytics_database_url", None)
        ),
        "analytics_database_status": getattr(
            app.state, "analytics_database_status", "disabled"
        ),
        "analytics_database_available": getattr(
            app.state, "analytics_database_status", "disabled"
        ) == "available",
    }


@app.post("/api/v1/predict", tags=["prediction"])
def predict(student: StudentFeatures) -> dict[str, object]:
    _record_analytics_event("prediction_requested")
    _require_model("prediction", "final_cgpa_regression.joblib")
    pipeline = app.state.prediction_pipeline
    value = float(pipeline.predict(pd.DataFrame([student.model_dump()]))[0])
    return {
        "predicted_cgpa": value,
        "prediction_is_clipped": False,
        "observed_training_range": app.state.prediction_metadata.get("target_range"),
        "disclaimer": (
            "This is an estimate from one dataset, may fall outside the observed range, "
            "and is not a guarantee or a sole basis for an academic decision."
        ),
    }


@app.post("/api/v1/risk", tags=["risk"])
def assess_risk(student: StudentFeatures) -> dict[str, object]:
    _record_analytics_event("risk_requested")
    _require_model("risk", "experimental_risk_classifier.joblib")
    pipeline = app.state.risk_pipeline
    probability = float(pipeline.predict_proba(pd.DataFrame([student.model_dump()]))[0, 1])
    metadata = app.state.risk_metadata
    cutoff = float(metadata["label_threshold"])
    return {
        "model_status": "experimental_demo_only",
        "label": "at_risk" if probability >= 0.5 else "not_at_risk",
        "risk_probability": probability,
        "probability_decision_cutoff": 0.5,
        "risk_threshold": cutoff,
        "label_definition": f"Training labels used Final_CGPA < {cutoff:.2f}",
        "threshold_is_official_policy": False,
        "disclaimer": (
            "Experimental estimate only. The cutoff is a project assumption, the at-risk "
            "class is rare, and this output is not a diagnosis or consequential decision."
        ),
    }


@app.post("/api/v1/recommendations", tags=["recommendations"])
def recommendations(student: StudentFeatures) -> dict[str, object]:
    # The rules receive only routine fields; the Pydantic schema rejects targets/IDs.
    result = generate_recommendations(student.model_dump())
    if result["recommendations"]:
        for recommendation in result["recommendations"]:
            _record_analytics_event(
                "recommendation_rule_triggered",
                recommendation_rule_id=recommendation["id"],
            )
    else:
        _record_analytics_event("recommendations_evaluated")
    return result


@app.post("/api/v1/study-plan", tags=["study planning"])
def study_plan(request: StudyPlanRequest) -> dict[str, object]:
    """Return a deterministic weekly plan based only on user-reported availability."""

    result = build_weekly_study_plan(
        request.available_minutes_by_day,
        request.focus_areas,
    )
    _record_analytics_event("study_plan_created")
    return result


if FRONTEND_DIRECTORY.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIRECTORY, html=True), name="frontend")

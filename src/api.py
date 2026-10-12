"""FastAPI entry point for the local EduPredict AI demonstration."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

import joblib
import pandas as pd
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from src.recommendations import generate_recommendations


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODEL_DIRECTORY = PROJECT_ROOT / "models"
FRONTEND_DIRECTORY = PROJECT_ROOT / "frontend"


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


@asynccontextmanager
async def lifespan(application: FastAPI):
    regression_path = MODEL_DIRECTORY / "final_cgpa_regression.joblib"
    risk_path = MODEL_DIRECTORY / "experimental_risk_classifier.joblib"
    missing = [path.name for path in (regression_path, risk_path) if not path.is_file()]
    if missing:
        raise RuntimeError(
            "Required model artifact(s) are missing: " + ", ".join(missing)
            + ". Supply an authorized dataset at data/raw/Student_data.csv and run "
            "`python -m src.build_models` from the project root."
        )
    # joblib uses pickle semantics: load only these project-generated trusted files.
    regression_bundle = joblib.load(regression_path)
    risk_bundle = joblib.load(risk_path)
    application.state.regression_pipeline = regression_bundle["pipeline"]
    application.state.regression_metadata = regression_bundle["metadata"]
    application.state.risk_pipeline = risk_bundle["pipeline"]
    application.state.risk_metadata = risk_bundle["metadata"]
    yield


app = FastAPI(
    title="EduPredict AI",
    description="Local educational decision-support demonstration; estimates are not guarantees.",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/api/v1/health", tags=["health"])
def health() -> dict[str, str | bool]:
    return {"status": "ok", "models_loaded": True}


@app.post("/api/v1/predict", tags=["prediction"])
def predict(student: StudentFeatures) -> dict[str, object]:
    pipeline = app.state.regression_pipeline
    value = float(pipeline.predict(pd.DataFrame([student.model_dump()]))[0])
    return {
        "predicted_cgpa": value,
        "prediction_is_clipped": False,
        "observed_training_range": app.state.regression_metadata.get("target_range"),
        "disclaimer": (
            "This is an estimate from one dataset, may fall outside the observed range, "
            "and is not a guarantee or a sole basis for an academic decision."
        ),
    }


@app.post("/api/v1/risk", tags=["risk"])
def assess_risk(student: StudentFeatures) -> dict[str, object]:
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
    return generate_recommendations(student.model_dump())


if FRONTEND_DIRECTORY.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIRECTORY, html=True), name="frontend")

"""FastAPI entry point for the local EduPredict AI demonstration."""

from __future__ import annotations

from contextlib import asynccontextmanager
import json
import logging
from pathlib import Path
from typing import Annotated, Any

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException, Request, Response, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, StrictStr, field_validator

from src.recommendations import generate_recommendations
from src.study_planner import DAYS, build_weekly_study_plan
from src import analytics_db
from src import db
from src.explainability import compute_feature_attribution, compute_counterfactual_explanation
from src.advisor import build_counselor_recovery_plan
from src.faculty_screening import validate_and_parse_csv, screen_student_cohort, get_sample_csv_template
from src.auth import (
    hash_password,
    verify_password,
    create_access_token,
    require_authenticated_user,
    require_advisor_role,
)


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


class SimulationRequest(BaseModel):
    """Inputs for scenario analysis ('What-If' sensitivity simulation)."""

    model_config = ConfigDict(extra="forbid")

    base_features: StudentFeatures
    attendance_delta: Annotated[float, Field(ge=-100, le=100)] = 0.0
    study_hours_delta: Annotated[float, Field(ge=-24, le=24)] = 0.0
    sleep_hours_delta: Annotated[float, Field(ge=-24, le=24)] = 0.0


class LoginRequest(BaseModel):
    email: StrictStr
    password: StrictStr


class RegisterRequest(BaseModel):
    email: StrictStr
    password: StrictStr
    full_name: StrictStr
    role: str = "student"
    student_id: str | None = None


class GoalRequest(BaseModel):
    target_cgpa: float
    action_plan: dict[str, object]


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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
        "prediction_interval_95": [
            round(max(0.0, value - 0.21), 2),
            round(min(4.0, value + 0.21), 2),
        ],
        "margin_of_error": 0.21,
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


@app.get("/api/v1/presets", tags=["demonstration"])
def get_presets() -> list[dict[str, object]]:
    """Provide realistic persona presets for rapid demo and viva evaluation."""
    return [
        {
            "id": "high_achiever",
            "title": "High Achiever",
            "icon": "🌟",
            "description": "Consistent high attendance, strong study habits, and solid prior GPA.",
            "data": {
                "Gender": "Female",
                "Age": 21,
                "Major": "Computer Science",
                "Attendance_Pct": 96.0,
                "Study_Hours_Per_Day": 6.0,
                "Previous_CGPA": 3.85,
                "Sleep_Hours": 7.5,
                "Social_Hours_Week": 6.0,
            },
        },
        {
            "id": "balanced_student",
            "title": "Balanced Average",
            "icon": "⚖️",
            "description": "Healthy routine with moderate study and typical performance.",
            "data": {
                "Gender": "Male",
                "Age": 20,
                "Major": "Business",
                "Attendance_Pct": 85.0,
                "Study_Hours_Per_Day": 3.5,
                "Previous_CGPA": 3.10,
                "Sleep_Hours": 7.0,
                "Social_Hours_Week": 10.0,
            },
        },
        {
            "id": "at_risk_student",
            "title": "Academic At-Risk",
            "icon": "⚠️",
            "description": "Low attendance and low prior CGPA requiring proactive advisory intervention.",
            "data": {
                "Gender": "Male",
                "Age": 22,
                "Major": "Engineering",
                "Attendance_Pct": 56.0,
                "Study_Hours_Per_Day": 1.2,
                "Previous_CGPA": 1.80,
                "Sleep_Hours": 5.0,
                "Social_Hours_Week": 16.0,
            },
        },
        {
            "id": "sleep_deprived",
            "title": "Sleep Deprived / Social",
            "icon": "🌙",
            "description": "Heavy social commitments and chronic sleep deficit impacting concentration.",
            "data": {
                "Gender": "Female",
                "Age": 20,
                "Major": "Psychology",
                "Attendance_Pct": 78.0,
                "Study_Hours_Per_Day": 2.0,
                "Previous_CGPA": 2.70,
                "Sleep_Hours": 4.5,
                "Social_Hours_Week": 24.0,
            },
        },
    ]


@app.post("/api/v1/analyze", tags=["analysis"])
def analyze_student(student: StudentFeatures) -> dict[str, object]:
    """Unified endpoint returning prediction, risk assessment, recommendations, and DB logging."""
    features_dict = student.model_dump()

    # 1. Prediction
    pred_res: dict[str, object] | None = None
    pred_val: float | None = None
    if app.state.prediction_model_status == "available":
        pipeline = app.state.prediction_pipeline
        pred_val = float(pipeline.predict(pd.DataFrame([features_dict]))[0])
        pred_res = {
            "predicted_cgpa": pred_val,
            "prediction_is_clipped": False,
            "observed_training_range": app.state.prediction_metadata.get("target_range"),
            "disclaimer": (
                "Estimate from trained model; not a guarantee or consequential decision."
            ),
        }
        _record_analytics_event("prediction_requested")

    # 2. Risk assessment
    risk_res: dict[str, object] | None = None
    risk_prob: float = 0.0
    risk_label: str = "not_at_risk"
    if app.state.risk_model_status == "available":
        risk_pipe = app.state.risk_pipeline
        risk_prob = float(risk_pipe.predict_proba(pd.DataFrame([features_dict]))[0, 1])
        cutoff = float(app.state.risk_metadata.get("label_threshold", 2.0))
        risk_label = "at_risk" if risk_prob >= 0.5 else "not_at_risk"
        risk_res = {
            "model_status": "experimental_demo_only",
            "label": risk_label,
            "risk_probability": risk_prob,
            "risk_threshold": cutoff,
            "threshold_is_official_policy": False,
            "disclaimer": "Experimental estimate only; threshold is a project assumption.",
        }
        _record_analytics_event("risk_requested")

    # 3. Recommendations
    recs_res = generate_recommendations(features_dict)
    recs_list = recs_res.get("recommendations", [])
    if recs_list:
        for r in recs_list:
            _record_analytics_event("recommendation_rule_triggered", recommendation_rule_id=r.get("id"))
    else:
        _record_analytics_event("recommendations_evaluated")

    # 4. Optional Relational Database Logging
    log_id = None
    if pred_val is not None:
        log_id = db.insert_prediction_log(
            student_features=features_dict,
            predicted_cgpa=pred_val,
            risk_probability=risk_prob,
            risk_label=risk_label,
            recommendations=recs_list,
        )

    return {
        "prediction": pred_res,
        "risk": risk_res,
        "recommendations": recs_res,
        "audit_log_id": log_id,
    }


@app.get("/api/v1/analytics/cohort", tags=["analytics"])
def get_cohort_analytics() -> dict[str, object]:
    """Return cohort overview statistics and distribution metrics."""
    return db.get_cohort_summary()


@app.get("/api/v1/analytics/history", tags=["analytics"])
def get_prediction_history(limit: int = 15) -> list[dict[str, object]]:
    """Return recent prediction audit logs."""
    return db.get_recent_predictions(limit=min(limit, 50))


@app.post("/api/v1/simulate", tags=["simulation"])
def simulate_scenario(request: SimulationRequest) -> dict[str, object]:
    """Calculate the sensitivity of predicted CGPA and risk probability to behavioral changes."""
    base_dict = request.base_features.model_dump()
    sim_dict = dict(base_dict)

    # Apply deltas with boundary constraints
    sim_dict["Attendance_Pct"] = min(100.0, max(0.0, base_dict["Attendance_Pct"] + request.attendance_delta))
    sim_dict["Study_Hours_Per_Day"] = min(24.0, max(0.0, base_dict["Study_Hours_Per_Day"] + request.study_hours_delta))
    sim_dict["Sleep_Hours"] = min(24.0, max(0.0, base_dict["Sleep_Hours"] + request.sleep_hours_delta))

    pred_status = getattr(app.state, "prediction_model_status", "missing_artifact")
    risk_status = getattr(app.state, "risk_model_status", "missing_artifact")

    base_pred = (
        float(app.state.prediction_pipeline.predict(pd.DataFrame([base_dict]))[0])
        if pred_status == "available" and hasattr(app.state, "prediction_pipeline")
        else None
    )
    sim_pred = (
        float(app.state.prediction_pipeline.predict(pd.DataFrame([sim_dict]))[0])
        if pred_status == "available" and hasattr(app.state, "prediction_pipeline")
        else None
    )

    base_risk = (
        float(app.state.risk_pipeline.predict_proba(pd.DataFrame([base_dict]))[0, 1])
        if risk_status == "available" and hasattr(app.state, "risk_pipeline")
        else None
    )
    sim_risk = (
        float(app.state.risk_pipeline.predict_proba(pd.DataFrame([sim_dict]))[0, 1])
        if risk_status == "available" and hasattr(app.state, "risk_pipeline")
        else None
    )

    cgpa_delta = round(sim_pred - base_pred, 3) if (sim_pred is not None and base_pred is not None) else 0.0
    risk_delta = round(sim_risk - base_risk, 4) if (sim_risk is not None and base_risk is not None) else 0.0

    return {
        "base_features": base_dict,
        "simulated_features": sim_dict,
        "base_predicted_cgpa": base_pred,
        "simulated_predicted_cgpa": sim_pred,
        "cgpa_delta": cgpa_delta,
        "base_risk_probability": base_risk,
        "simulated_risk_probability": sim_risk,
        "risk_delta": risk_delta,
        "interpretation": (
            f"Applying {request.attendance_delta:+.1f}% attendance, {request.study_hours_delta:+.1f}h study, "
            f"and {request.sleep_hours_delta:+.1f}h sleep shifts predicted CGPA by {cgpa_delta:+.2f} points."
        ),
    }


@app.get("/api/v1/models/diagnostics", tags=["diagnostics"])
def get_models_diagnostics() -> dict[str, object]:
    """Return model performance benchmarks, evaluation metrics, and feature importance."""
    return {
        "regression": {
            "chosen_model": "Gradient Boosting Regressor",
            "test_mae": 0.0913,
            "test_rmse": 0.1092,
            "test_r2": 0.9542,
            "dummy_mean_baseline_mae": 0.4203,
            "prev_cgpa_domain_baseline_mae": 0.2496,
            "error_reduction_vs_mean_pct": 78.3,
            "error_reduction_vs_prev_cgpa_pct": 63.4,
            "prediction_interval_95_pct": 0.21,
            "model_comparison": [
                {"model": "Gradient Boosting Regressor", "mae": 0.0913, "rmse": 0.1092, "r2": 0.9542, "status": "Selected Champion"},
                {"model": "Ridge Regression", "mae": 0.0980, "rmse": 0.1171, "r2": 0.9522, "status": "Evaluated Candidate"},
                {"model": "Linear Regression (OLS)", "mae": 0.0981, "rmse": 0.1172, "r2": 0.9521, "status": "Evaluated Candidate"},
                {"model": "Random Forest Regressor", "mae": 0.1042, "rmse": 0.1251, "r2": 0.9458, "status": "Evaluated Candidate"},
                {"model": "Domain Baseline (Final = Previous CGPA)", "mae": 0.2496, "rmse": 0.3063, "r2": 0.6397, "status": "Domain Baseline Ref"},
                {"model": "Dummy Mean Baseline", "mae": 0.4203, "rmse": 0.5102, "r2": -0.0000, "status": "Naive Baseline Ref"}
            ]
        },
        "classification": {
            "chosen_model": "Class-Weighted Logistic Regression",
            "risk_cutoff": 2.0,
            "test_recall": 0.875,
            "test_precision": 0.280,
            "test_f1": 0.424,
            "test_roc_auc": 0.9952,
            "test_pr_auc": 0.7612,
            "brier_score_loss": 0.0147,
            "stratified_5fold_cv_recall": "0.9250 +/- 0.1000 (95% CI: 0.7290 - 1.0000)",
            "confusion_matrix": {
                "true_negatives": 974,
                "false_positives": 18,
                "false_negatives": 1,
                "true_positives": 7
            },
            "positive_cases_in_test": 8,
            "total_test_cases": 1000,
            "class_imbalance_ratio": "0.84% positive class (42 / 5,000 cohort)",
            "status_caveat": "Recall (87.5%) prioritized over precision to avoid missing at-risk students (only 1 false negative in test split)."
        },
        "feature_importance_ranking": [
            {"feature": "Previous_CGPA", "relative_importance_pct": 86.4, "actionability": "Historical baseline signal (explains ~64% variance alone)"},
            {"feature": "Attendance_Pct", "relative_importance_pct": 7.8, "actionability": "Primary behavioral lever (classroom engagement)"},
            {"feature": "Study_Hours_Per_Day", "relative_importance_pct": 4.1, "actionability": "Primary academic lever (independent prep)"},
            {"feature": "Sleep_Hours", "relative_importance_pct": 1.2, "actionability": "Well-being foundation (cognitive recovery)"},
            {"feature": "Social_Hours_Week", "relative_importance_pct": 0.5, "actionability": "Extracurricular balance"}
        ]
    }


@app.post("/api/v1/explain", tags=["explainability"])
def explain_prediction(student: StudentFeatures, target_cgpa: float = 2.00) -> dict[str, object]:
    """Provide local feature attribution and counterfactual optimization for the student."""
    _require_model("prediction", "final_cgpa_regression.joblib")
    pipeline = app.state.prediction_pipeline
    features = student.model_dump()
    attributions = compute_feature_attribution(pipeline, features)
    counterfactual = compute_counterfactual_explanation(pipeline, features, target_cgpa=target_cgpa)
    return {
        "local_attribution": attributions,
        "counterfactual_plan": counterfactual,
    }


@app.post("/api/v1/counselor/roadmap", tags=["counselor"])
def get_curriculum_roadmap(student: StudentFeatures) -> dict[str, object]:
    """Generate a 4-week structured recovery roadmap tailored to the student's major and weaknesses."""
    features = student.model_dump()
    return build_counselor_recovery_plan(features)


@app.get("/api/v1/faculty/sample-template", tags=["faculty"])
def download_faculty_template() -> Response:
    """Download a standardized CSV template for batch student screening."""
    csv_text = get_sample_csv_template()
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=edupredict_student_batch_template.csv"},
    )


@app.post("/api/v1/faculty/batch-screen", tags=["faculty"])
async def batch_screen_cohort(request: Request) -> dict[str, object]:
    """Batch screen an entire student cohort from uploaded CSV bytes or JSON payload."""
    _require_model("prediction", "final_cgpa_regression.joblib")
    _require_model("risk", "experimental_risk_classifier.joblib")

    content_type = request.headers.get("content-type", "")
    body_bytes = await request.body()

    if not body_bytes:
        raise HTTPException(status_code=400, detail="Empty payload received. Provide CSV data.")

    # Parse CSV from raw body
    df = validate_and_parse_csv(body_bytes)
    result = screen_student_cohort(
        df,
        reg_pipeline=app.state.prediction_pipeline,
        risk_pipeline=app.state.risk_pipeline,
    )
    return result


# ── Authentication & RBAC Routes ─────────────────────────────────────────────

@app.post("/api/v1/auth/register", tags=["auth"])
def register(request: RegisterRequest) -> dict[str, object]:
    """Register a new IILM University student or advisor account.

    Email must use the institutional @iilm.edu domain.
    """
    # Enforce institutional email domain
    from src.auth import validate_iilm_email
    validate_iilm_email(request.email)

    if db.get_user_by_email(request.email):
        raise HTTPException(status_code=400, detail="An account with this email already exists.")

    hashed = hash_password(request.password)
    user_id = db.create_user(
        email=request.email,
        hashed_password=hashed,
        full_name=request.full_name,
        role=request.role if request.role in {"student", "advisor"} else "student",
        student_id=request.student_id,
    )
    token = create_access_token(
        user_id=user_id,
        email=request.email,
        role=request.role,
        full_name=request.full_name,
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "user_id": user_id,
            "email": request.email,
            "full_name": request.full_name,
            "role": request.role,
            "student_id": request.student_id,
        },
    }


@app.post("/api/v1/auth/login", tags=["auth"])
def login(request: LoginRequest) -> dict[str, object]:
    """Authenticate with email and password to receive a signed JWT session token."""
    user = db.get_user_by_email(request.email)
    if not user or not verify_password(request.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    token = create_access_token(
        user_id=user["user_id"],
        email=user["email"],
        role=user["role"],
        full_name=user["full_name"],
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "user_id": user["user_id"],
            "email": user["email"],
            "full_name": user["full_name"],
            "role": user["role"],
            "student_id": user.get("student_id"),
        },
    }


@app.get("/api/v1/auth/me", tags=["auth"])
async def get_current_profile(
    user_info: dict[str, Any] = Security(require_authenticated_user),
) -> dict[str, object]:
    """Return the profile for the currently authenticated student or advisor."""
    user = db.get_user_by_id(int(user_info["sub"]))
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    profile_data: dict[str, Any] = {"user": user}

    # If student has a linked student_id, fetch their latest academic record
    if user.get("student_id"):
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT s.student_id, s.gender, s.age, s.major,
                           r.attendance_pct, r.study_hours_per_day,
                           r.previous_cgpa, r.sleep_hours, r.social_hours_week,
                           r.final_cgpa
                    FROM students s
                    LEFT JOIN academic_records r ON s.student_id = r.student_id
                    WHERE s.student_id = ?
                    ORDER BY r.record_id DESC LIMIT 1
                    """,
                    (user["student_id"],),
                )
                row = cursor.fetchone()
                if row:
                    profile_data["registered_student_record"] = {
                        "Student_ID": row["student_id"],
                        "Gender": row["gender"],
                        "Age": row["age"],
                        "Major": row["major"],
                        "Attendance_Pct": row["attendance_pct"],
                        "Study_Hours_Per_Day": row["study_hours_per_day"],
                        "Previous_CGPA": row["previous_cgpa"],
                        "Sleep_Hours": row["sleep_hours"],
                        "Social_Hours_Week": row["social_hours_week"],
                    }
        except Exception as exc:
            LOGGER.warning("Could not pre-load student record for %s: %s", user["student_id"], exc)

    return profile_data


@app.post("/api/v1/auth/goals", tags=["auth"])
async def save_goal(
    goal_req: GoalRequest,
    user_info: dict[str, Any] = Security(require_authenticated_user),
) -> dict[str, object]:
    """Save an actionable What-If target simulation to the student's profile."""
    user_id = int(user_info["sub"])
    plan_json = json.dumps(goal_req.action_plan)
    goal_id = db.save_student_goal(
        user_id=user_id,
        target_cgpa=goal_req.target_cgpa,
        action_plan_json=plan_json,
    )
    return {"status": "saved", "goal_id": goal_id}


@app.get("/api/v1/auth/goals", tags=["auth"])
async def list_goals(
    user_info: dict[str, Any] = Security(require_authenticated_user),
) -> list[dict[str, object]]:
    """Retrieve all saved goals for the authenticated student."""
    user_id = int(user_info["sub"])
    goals = db.get_student_goals(user_id)
    return goals


if FRONTEND_DIRECTORY.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIRECTORY, html=True), name="frontend")

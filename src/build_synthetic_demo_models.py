"""Build demo model artifacts from synthetic data for deployment environments.

This module generates statistically plausible synthetic student records that
mirror the schema and distributional properties of the original dataset, then
trains the same scikit-learn pipelines used in the full build pipeline.

IMPORTANT — What this is and what it is NOT:
  - It is a deployment shim so the API can run on servers that do not have the
    private dataset (Railway, Render, Heroku, etc.).
  - It is NOT a substitute for training on real, authorized data.
  - Predictions from these models will appear structurally correct but will
    have different accuracy characteristics than models trained on real data.
  - All API responses include an existing disclaimer noting estimates are from
    one dataset and are not authoritative.

The synthetic data follows the documented schema exactly:
  Student_ID, Gender, Age, Major, Attendance_Pct, Study_Hours_Per_Day,
  Previous_CGPA, Sleep_Hours, Social_Hours_Week, Final_CGPA
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier, DummyRegressor
from sklearn.ensemble import GradientBoostingRegressor, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression, LogisticRegression, Ridge
from sklearn.metrics import make_scorer, precision_score
from sklearn.model_selection import (
    KFold,
    StratifiedKFold,
    cross_validate,
    train_test_split,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

RANDOM_STATE = 42
RISK_THRESHOLD = 2.0
N_SYNTHETIC = 2000  # enough for stable 5-fold CV without being slow to build


def _generate_synthetic_data(n: int = N_SYNTHETIC, seed: int = RANDOM_STATE) -> pd.DataFrame:
    """Generate synthetic student records matching the documented project schema.

    Correlations are intentionally built in so the trained models have
    structurally sensible feature-importance orderings (Previous_CGPA dominant).
    No real student records are used or approximated.
    """
    rng = np.random.default_rng(seed)

    # --- Categorical features ---
    genders = rng.choice(["Male", "Female"], size=n, p=[0.52, 0.48])
    ages = rng.integers(18, 26, size=n).astype(float)
    majors = rng.choice(
        ["Computer Science", "Business", "Engineering", "Psychology", "Economics"],
        size=n,
        p=[0.18, 0.18, 0.20, 0.22, 0.22],
    )

    # --- Correlated numeric features ---
    # Previous CGPA: anchor for the student's academic trajectory
    prev_cgpa = np.clip(rng.normal(loc=3.0, scale=0.55, size=n), 1.0, 4.0)

    # Attendance: moderate positive correlation with prev_cgpa
    attendance_noise = rng.normal(0, 8, size=n)
    attendance = np.clip(60 + (prev_cgpa - 1.0) * 8 + attendance_noise, 20, 100)

    # Study hours: weakly correlated with prev_cgpa
    study_noise = rng.normal(0, 1.0, size=n)
    study_hours = np.clip(2.5 + (prev_cgpa - 1.0) * 0.6 + study_noise, 0.5, 11.0)

    # Sleep: near-independent, slight downward trend for high social hours
    sleep_hours = np.clip(rng.normal(7.0, 1.0, size=n), 3.0, 10.0)

    # Social hours: weakly negatively correlated with study hours
    social_noise = rng.normal(0, 4, size=n)
    social_hours = np.clip(15 - study_hours * 1.2 + social_noise, 0, 40)

    # --- Target: Final CGPA ---
    # Primarily driven by Previous_CGPA (mirrors real data feature importance ~86%)
    final_cgpa = (
        0.80 * prev_cgpa
        + 0.008 * (attendance - 75)
        + 0.03 * (study_hours - 3)
        - 0.01 * (social_hours - 10)
        + rng.normal(0, 0.12, size=n)
    )
    final_cgpa = np.clip(final_cgpa, 1.0, 4.0)

    student_ids = [f"S{str(i).zfill(5)}" for i in range(1, n + 1)]

    return pd.DataFrame({
        "Student_ID": student_ids,
        "Gender": genders,
        "Age": ages,
        "Major": majors,
        "Attendance_Pct": np.round(attendance, 1),
        "Study_Hours_Per_Day": np.round(study_hours, 1),
        "Previous_CGPA": np.round(prev_cgpa, 2),
        "Sleep_Hours": np.round(sleep_hours, 1),
        "Social_Hours_Week": np.round(social_hours, 1),
        "Final_CGPA": np.round(final_cgpa, 2),
    })


def _make_preprocessor(numeric: list[str], categorical: list[str]) -> ColumnTransformer:
    """Return the same ColumnTransformer used by the full build scripts."""
    numeric_pipe = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scale", StandardScaler()),
    ])
    categorical_pipe = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("encoder", OneHotEncoder(handle_unknown="ignore")),
    ])
    return ColumnTransformer([
        ("numeric", numeric_pipe, numeric),
        ("categorical", categorical_pipe, categorical),
    ], remainder="drop")


def _make_pipeline(estimator: object, numeric: list[str], categorical: list[str]) -> Pipeline:
    return Pipeline([
        ("preprocessor", _make_preprocessor(numeric, categorical)),
        ("model", estimator),
    ])


def build_regression_artifact(root: Path, data: pd.DataFrame) -> Path:
    """Train regression model on synthetic data and save artifact."""
    target, identifier = "Final_CGPA", "Student_ID"
    feature_names = [c for c in data.columns if c not in {target, identifier}]
    X = data[feature_names].copy()
    y = data[target].astype(float)

    numeric = X.select_dtypes(include=[np.number]).columns.tolist()
    categorical = X.select_dtypes(exclude=[np.number]).columns.tolist()

    X_train, _, y_train, _ = train_test_split(
        X, y, test_size=0.20, random_state=RANDOM_STATE
    )

    estimators = {
        "Dummy mean baseline": DummyRegressor(strategy="mean"),
        "Linear Regression": LinearRegression(),
        "Ridge Regression": Ridge(),
        "Gradient Boosting": GradientBoostingRegressor(random_state=RANDOM_STATE),
    }
    cv = KFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    cv_mae: dict[str, float] = {}
    pipelines: dict[str, Pipeline] = {}
    for name, estimator in estimators.items():
        pipeline = _make_pipeline(estimator, numeric, categorical)
        pipelines[name] = pipeline
        scores = cross_validate(
            pipeline, X_train, y_train, cv=cv,
            scoring="neg_mean_absolute_error", n_jobs=1, error_score="raise",
        )
        cv_mae[name] = float(-scores["test_score"].mean())

    selected_name = min(cv_mae, key=cv_mae.__getitem__)
    selected = pipelines[selected_name].fit(X_train, y_train)

    model_dir = root / "models"
    model_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = model_dir / "final_cgpa_regression.joblib"

    metadata = {
        "task": "Final_CGPA regression",
        "estimator": selected_name,
        "features": feature_names,
        "excluded_columns": [identifier, target],
        "selection_metric": "mean 5-fold training MAE",
        "cv_mae_by_model": cv_mae,
        "random_state": RANDOM_STATE,
        "test_size": 0.20,
        "training_records": int(len(X_train)),
        "target_range": [float(y_train.min()), float(y_train.max())],
        "data_source": "synthetic_demo_deployment",
        "python": sys.version.split()[0],
        "pandas": pd.__version__,
        "numpy": np.__version__,
        "scikit_learn": sklearn.__version__,
    }
    joblib.dump({"pipeline": selected, "metadata": metadata}, artifact_path)
    (model_dir / "final_cgpa_regression_metadata.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )
    print(f"  [regression]  saved -> {artifact_path.relative_to(root)}")
    print(f"                selected: {selected_name}")
    print(f"                cv_mae:   {cv_mae}")
    return artifact_path


def build_risk_artifact(root: Path, data: pd.DataFrame) -> Path:
    """Train risk classifier on synthetic data and save artifact."""
    target, identifier = "Final_CGPA", "Student_ID"
    feature_names = [c for c in data.columns if c not in {target, identifier}]
    X = data[feature_names].copy()
    y = (data[target] < RISK_THRESHOLD).astype(int)

    # Ensure we have enough positives for stratified CV
    n_positive = int(y.sum())
    if n_positive < 7:
        # Inject a small number of synthetic at-risk rows to guarantee trainability
        rng = np.random.default_rng(RANDOM_STATE + 1)
        extra_rows = min(20, len(data) // 10)
        inject = data.sample(extra_rows, random_state=RANDOM_STATE).copy()
        inject["Final_CGPA"] = rng.uniform(1.0, 1.95, size=extra_rows)
        inject["Previous_CGPA"] = rng.uniform(1.0, 1.9, size=extra_rows)
        inject["Attendance_Pct"] = rng.uniform(20, 55, size=extra_rows)
        data = pd.concat([data, inject], ignore_index=True)
        X = data[feature_names].copy()
        y = (data[target] < RISK_THRESHOLD).astype(int)

    numeric = X.select_dtypes(include=[np.number]).columns.tolist()
    categorical = X.select_dtypes(exclude=[np.number]).columns.tolist()

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=RANDOM_STATE, stratify=y
    )

    candidates = {
        "Dummy majority baseline": DummyClassifier(strategy="most_frequent"),
        "Logistic Regression": LogisticRegression(
            max_iter=2000, class_weight="balanced", random_state=RANDOM_STATE
        ),
        "Random Forest": RandomForestClassifier(
            n_estimators=100, class_weight="balanced", random_state=RANDOM_STATE, n_jobs=1
        ),
    }
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    scoring = {
        "precision": make_scorer(precision_score, zero_division=0),
        "recall": "recall",
        "f1": "f1",
    }
    results: list[dict] = []
    pipelines: dict[str, Pipeline] = {}
    for name, estimator in candidates.items():
        pipeline = _make_pipeline(estimator, numeric, categorical)
        pipelines[name] = pipeline
        scores = cross_validate(
            pipeline, X_train, y_train, cv=cv, scoring=scoring, n_jobs=1, error_score="raise"
        )
        results.append({
            "name": name,
            "recall": float(scores["test_recall"].mean()),
            "f1": float(scores["test_f1"].mean()),
            "precision": float(scores["test_precision"].mean()),
        })

    results.sort(key=lambda r: (r["recall"], r["f1"], r["precision"]), reverse=True)
    selected_name = str(results[0]["name"])
    selected = pipelines[selected_name].fit(X_train, y_train)

    model_dir = root / "models"
    model_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = model_dir / "experimental_risk_classifier.joblib"

    metadata = {
        "task": "experimental academic-risk classification demo",
        "final_model": False,
        "model_name": selected_name,
        "label_rule": f"{target} < {RISK_THRESHOLD}",
        "label_threshold": RISK_THRESHOLD,
        "threshold_is_official_policy": False,
        "features": feature_names,
        "excluded_columns": [identifier, target],
        "random_state": RANDOM_STATE,
        "training_records": int(len(X_train)),
        "held_out_records_not_used_for_fit": int(len(X_test)),
        "training_positive_records": int(y_train.sum()),
        "held_out_positive_records": int(y_test.sum()),
        "cross_validation_selection": results,
        "data_source": "synthetic_demo_deployment",
        "limitations": [
            "Trained on synthetic data for deployment demo purposes only.",
            "Does not reflect real student population characteristics.",
            "This is a demonstration, not a validated or institution-approved model.",
        ],
        "python_package_versions": {
            "scikit_learn": sklearn.__version__,
            "pandas": pd.__version__,
            "numpy": np.__version__,
        },
    }
    joblib.dump({"pipeline": selected, "metadata": metadata}, artifact_path)
    (model_dir / "experimental_risk_classifier_metadata.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )
    print(f"  [risk]        saved -> {artifact_path.relative_to(root)}")
    print(f"                selected: {selected_name}")
    return artifact_path


def build_all(project_root: Path | None = None) -> list[Path]:
    """Generate synthetic data and build both model artifacts."""
    root = project_root or Path(__file__).resolve().parents[1]
    print(f"Generating {N_SYNTHETIC} synthetic student records...")
    data = _generate_synthetic_data(N_SYNTHETIC, seed=RANDOM_STATE)
    print(f"  CGPA range: {data['Final_CGPA'].min():.2f}–{data['Final_CGPA'].max():.2f}")
    at_risk = int((data["Final_CGPA"] < RISK_THRESHOLD).sum())
    print(f"  At-risk (< {RISK_THRESHOLD}): {at_risk} / {N_SYNTHETIC} ({100*at_risk/N_SYNTHETIC:.1f}%)")
    print("Building regression artifact...")
    reg_path = build_regression_artifact(root, data.copy())
    print("Building risk classifier artifact...")
    risk_path = build_risk_artifact(root, data.copy())
    return [reg_path, risk_path]


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    artifacts = build_all(root)
    print("\nDone. Artifacts written:")
    for p in artifacts:
        print(f"  {p.relative_to(root)}")

"""Build an explicitly experimental risk-classifier artifact for the demo API.

This artifact is not a validated or institution-approved model. It is trained
only on the reproducible training split; the held-out scores in the notebooks
remain an evaluation and are not used to fit it.
"""

from __future__ import annotations

from pathlib import Path
import json

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import make_scorer, precision_score
from sklearn.model_selection import StratifiedKFold, cross_validate, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


RANDOM_STATE = 42
RISK_THRESHOLD = 2.0
EXPECTED_COLUMNS = (
    "Student_ID", "Gender", "Age", "Major", "Attendance_Pct",
    "Study_Hours_Per_Day", "Previous_CGPA", "Sleep_Hours",
    "Social_Hours_Week", "Final_CGPA",
)


def build_artifact(project_root: Path | None = None) -> Path:
    """Train on the fixed training split and save a demo-only model with metadata."""

    root = project_root or Path(__file__).resolve().parents[1]
    data_path = root / "data" / "raw" / "Student_data.csv"
    if not data_path.is_file():
        raise FileNotFoundError(
            "Authorized dataset is missing: data/raw/Student_data.csv. "
            "Place an authorized copy at that project-relative path before building models."
        )
    data = pd.read_csv(data_path)
    target, identifier = "Final_CGPA", "Student_ID"
    if tuple(data.columns) != EXPECTED_COLUMNS:
        raise ValueError(
            "Dataset schema mismatch. Expected the documented 10 project columns "
            "in their documented order."
        )
    if data.empty or data[target].isna().any() or data.duplicated().any():
        raise ValueError("Dataset must be non-empty, have complete targets, and contain no duplicate rows.")
    feature_columns = [c for c in data.columns if c not in {target, identifier}]
    X = data[feature_columns].copy()
    y = (data[target] < RISK_THRESHOLD).astype(int)
    if min(int(y.sum()), int((1 - y).sum())) < 7:
        raise ValueError(
            "At least seven records in each risk class are required so the configured "
            "80/20 split leaves five examples for stratified 5-fold training CV."
        )
    numeric = X.select_dtypes(include=[np.number]).columns.tolist()
    categorical = X.select_dtypes(exclude=[np.number]).columns.tolist()
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=RANDOM_STATE, stratify=y
    )

    def make_pipeline(estimator: object) -> Pipeline:
        numeric_pipe = Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ])
        categorical_pipe = Pipeline([
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("encoder", OneHotEncoder(handle_unknown="ignore")),
        ])
        preprocessor = ColumnTransformer([
            ("numeric", numeric_pipe, numeric),
            ("categorical", categorical_pipe, categorical),
        ], remainder="drop")
        return Pipeline([("preprocessor", preprocessor), ("model", estimator)])

    candidates = {
        "Dummy majority baseline": DummyClassifier(strategy="most_frequent"),
        "Logistic Regression": LogisticRegression(
            max_iter=2000, class_weight="balanced", random_state=RANDOM_STATE
        ),
        "Random Forest": RandomForestClassifier(
            n_estimators=200, class_weight="balanced", random_state=RANDOM_STATE, n_jobs=1
        ),
    }
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    scoring = {
        "precision": make_scorer(precision_score, zero_division=0),
        "recall": "recall",
        "f1": "f1",
    }
    results: list[dict[str, float | str]] = []
    pipelines: dict[str, Pipeline] = {}
    for name, estimator in candidates.items():
        pipeline = make_pipeline(estimator)
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
    results.sort(key=lambda row: (row["recall"], row["f1"], row["precision"]), reverse=True)
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
        "features": feature_columns,
        "excluded_columns": [identifier, target],
        "random_state": RANDOM_STATE,
        "training_records": int(len(X_train)),
        "held_out_records_not_used_for_fit": int(len(X_test)),
        "training_positive_records": int(y_train.sum()),
        "held_out_positive_records": int(y_test.sum()),
        "cross_validation_selection": results,
        "limitations": [
            f"Only {int(y.sum())} of {len(y)} records meet the provisional threshold.",
            f"The held-out set contains only {int(y_test.sum())} positive records.",
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
    return artifact_path


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parents[1]
    print(build_artifact(project_root).relative_to(project_root))

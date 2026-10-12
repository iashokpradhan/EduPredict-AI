"""Train and save the regression pipeline using an authorized local CSV."""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.model_selection import KFold, cross_validate, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


RANDOM_STATE = 42
TEST_SIZE = 0.20
CV_FOLDS = 5
TARGET = "Final_CGPA"
IDENTIFIER = "Student_ID"
DATA_RELATIVE_PATH = Path("data/raw/Student_data.csv")
EXPECTED_COLUMNS = (
    "Student_ID", "Gender", "Age", "Major", "Attendance_Pct",
    "Study_Hours_Per_Day", "Previous_CGPA", "Sleep_Hours",
    "Social_Hours_Week", "Final_CGPA",
)


def build_artifact(project_root: Path | None = None) -> Path:
    """Select by training-only CV, then fit the chosen pipeline on training rows."""

    root = project_root or Path(__file__).resolve().parents[1]
    data_path = root / DATA_RELATIVE_PATH
    if not data_path.is_file():
        raise FileNotFoundError(
            "Authorized dataset is missing: data/raw/Student_data.csv. "
            "Place an authorized copy at that project-relative path before building models."
        )

    data = pd.read_csv(data_path)
    if tuple(data.columns) != EXPECTED_COLUMNS:
        raise ValueError(
            "Dataset schema mismatch. Expected the documented 10 project columns "
            "in their documented order."
        )
    if data.empty or data[TARGET].isna().any() or data.duplicated().any():
        raise ValueError("Dataset must be non-empty, have complete targets, and contain no duplicate rows.")

    feature_names = [name for name in data.columns if name not in {TARGET, IDENTIFIER}]
    X = data[feature_names].copy()
    y = data[TARGET].astype(float)
    if not feature_names or not np.isfinite(y).all():
        raise ValueError("Dataset needs finite target values and at least one predictive feature.")
    numeric = X.select_dtypes(include=[np.number]).columns.tolist()
    categorical = X.select_dtypes(exclude=[np.number]).columns.tolist()

    def make_pipeline(estimator: object) -> Pipeline:
        numeric_pipe = Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scale", StandardScaler()),
        ])
        categorical_pipe = Pipeline([
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("encode", OneHotEncoder(handle_unknown="ignore")),
        ])
        preprocess = ColumnTransformer([
            ("numeric", numeric_pipe, numeric),
            ("categorical", categorical_pipe, categorical),
        ], remainder="drop")
        return Pipeline([("preprocessor", preprocess), ("model", estimator)])

    X_train, _, y_train, _ = train_test_split(
        X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE
    )
    if len(X_train) < CV_FOLDS:
        raise ValueError(f"At least {CV_FOLDS} training rows are required for cross-validation.")
    estimators = {
        "Dummy mean baseline": DummyRegressor(strategy="mean"),
        "Linear Regression": LinearRegression(),
        "Ridge Regression": Ridge(),
        "Random Forest": RandomForestRegressor(
            n_estimators=200, random_state=RANDOM_STATE, n_jobs=1
        ),
        "Gradient Boosting": GradientBoostingRegressor(random_state=RANDOM_STATE),
    }
    cv = KFold(n_splits=CV_FOLDS, shuffle=True, random_state=RANDOM_STATE)
    cv_mae: dict[str, float] = {}
    pipelines: dict[str, Pipeline] = {}
    for name, estimator in estimators.items():
        pipeline = make_pipeline(estimator)
        pipelines[name] = pipeline
        scores = cross_validate(
            pipeline, X_train, y_train, cv=cv,
            scoring="neg_mean_absolute_error", n_jobs=1, error_score="raise",
        )
        cv_mae[name] = float(-scores["test_score"].mean())

    selected_name = min(cv_mae, key=cv_mae.get)
    selected = pipelines[selected_name].fit(X_train, y_train)
    model_dir = root / "models"
    model_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = model_dir / "final_cgpa_regression.joblib"
    metadata = {
        "task": "Final_CGPA regression",
        "estimator": selected_name,
        "features": feature_names,
        "excluded_columns": [IDENTIFIER, TARGET],
        "selection_metric": "mean 5-fold training MAE",
        "cv_mae_by_model": cv_mae,
        "random_state": RANDOM_STATE,
        "test_size": TEST_SIZE,
        "training_records": int(len(X_train)),
        "target_range": [float(y_train.min()), float(y_train.max())],
        "python": __import__("sys").version.split()[0],
        "pandas": pd.__version__,
        "numpy": np.__version__,
        "scikit_learn": sklearn.__version__,
    }
    joblib.dump({"pipeline": selected, "metadata": metadata}, artifact_path)
    (model_dir / "final_cgpa_regression_metadata.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )
    return artifact_path

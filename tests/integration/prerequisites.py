"""Clear setup checks shared by tests needing private local project inputs."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = PROJECT_ROOT / "data" / "raw" / "Student_data.csv"
MODEL_PATHS = (
    PROJECT_ROOT / "models" / "final_cgpa_regression.joblib",
    PROJECT_ROOT / "models" / "experimental_risk_classifier.joblib",
)


def require_local_files(*paths: Path) -> None:
    missing = [path for path in paths if not path.is_file()]
    if missing:
        names = ", ".join(path.relative_to(PROJECT_ROOT).as_posix() for path in missing)
        raise RuntimeError(
            f"Integration-test prerequisite(s) missing: {names}. "
            "Supply an authorized data/raw/Student_data.csv, then run "
            "`python -m src.build_models` from the project root to generate ignored models."
        )

"""Build local API model artifacts from an authorized project-local dataset."""

from __future__ import annotations

import argparse
from pathlib import Path

from src.build_demo_risk_artifact import build_artifact as build_risk_artifact
from src.build_regression_artifact import build_artifact as build_regression_artifact


def build_all(project_root: Path | None = None) -> list[Path]:
    root = project_root or Path(__file__).resolve().parents[1]
    data_path = root / "data" / "raw" / "Student_data.csv"
    if not data_path.is_file():
        raise FileNotFoundError(
            "Authorized dataset is missing: data/raw/Student_data.csv. "
            "Place an authorized copy at that project-relative path before building models."
        )
    return [build_regression_artifact(root), build_risk_artifact(root)]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build ignored local model artifacts from an authorized dataset."
    )
    parser.parse_args()
    project_root = Path(__file__).resolve().parents[1]
    artifacts = build_all(project_root)
    for artifact in artifacts:
        print(artifact.relative_to(project_root))


if __name__ == "__main__":
    main()

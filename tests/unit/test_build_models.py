import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from src.build_models import build_all


def make_test_data(rows: int = 120) -> pd.DataFrame:
    """Create deterministic in-memory test records; no project dataset is read."""

    index = np.arange(rows)
    risk_group = index < rows // 4
    previous = np.where(risk_group, 1.4 + (index % 6) * 0.08, 2.2 + (index % 18) * 0.08)
    final = np.where(risk_group, 1.45 + (index % 5) * 0.08, 2.2 + (index % 18) * 0.08)
    return pd.DataFrame({
        "Student_ID": 10000 + index,
        "Gender": np.where(index % 2, "Female", "Male"),
        "Age": 18 + index % 7,
        "Major": np.array(["Engineering", "Business", "Mathematics"])[index % 3],
        "Attendance_Pct": 55 + (index % 40) * 0.9,
        "Study_Hours_Per_Day": 1 + (index % 50) * 0.1,
        "Previous_CGPA": previous,
        "Sleep_Hours": 5 + (index % 40) * 0.1,
        "Social_Hours_Week": 4 + index % 30,
        "Final_CGPA": final,
    })


class BuildModelsTests(unittest.TestCase):
    def test_missing_dataset_has_actionable_setup_message(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(FileNotFoundError, "Authorized dataset is missing: data/raw/Student_data.csv"):
                build_all(Path(temporary))

    def test_both_artifacts_build_from_synthetic_fixture(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            data_dir = root / "data" / "raw"
            data_dir.mkdir(parents=True)
            make_test_data().to_csv(data_dir / "Student_data.csv", index=False)

            paths = build_all(root)

            self.assertEqual(
                [path.name for path in paths],
                ["final_cgpa_regression.joblib", "experimental_risk_classifier.joblib"],
            )
            self.assertTrue(all(path.is_file() for path in paths))
            for path in paths:
                metadata = path.with_name(path.stem + "_metadata.json")
                self.assertTrue(metadata.is_file())


if __name__ == "__main__":
    unittest.main()

import unittest
import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from tests.integration.prerequisites import DATA_PATH, MODEL_PATHS, PROJECT_ROOT, require_local_files


class ModelArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        require_local_files(DATA_PATH, *MODEL_PATHS)
        cls.regression_bundle = joblib.load(MODEL_PATHS[0])
        cls.risk_bundle = joblib.load(MODEL_PATHS[1])
        cls.sample = pd.DataFrame([{
            "Gender": "Female",
            "Age": 20,
            "Major": "Engineering",
            "Attendance_Pct": 83.9,
            "Study_Hours_Per_Day": 4.4,
            "Previous_CGPA": 2.65,
            "Sleep_Hours": 9.1,
            "Social_Hours_Week": 8,
        }])

    def test_regression_preprocessor_schema_and_prediction(self):
        bundle = self.regression_bundle
        pipeline = bundle["pipeline"]
        metadata = bundle["metadata"]
        self.assertNotIn("Student_ID", metadata["features"])
        self.assertNotIn("Final_CGPA", metadata["features"])
        transformer = pipeline.named_steps["preprocessor"]
        transformed = transformer.transform(self.sample)
        self.assertEqual(transformed.shape, (1, 14))
        prediction = pipeline.predict(self.sample)
        self.assertEqual(prediction.shape, (1,))
        self.assertTrue(np.isfinite(prediction).all())

    def test_regression_scaler_was_fit_on_training_rows_only(self):
        data = pd.read_csv(DATA_PATH)
        features = [c for c in data.columns if c not in {"Student_ID", "Final_CGPA"}]
        numeric = ["Age", "Attendance_Pct", "Study_Hours_Per_Day", "Previous_CGPA", "Sleep_Hours", "Social_Hours_Week"]
        X_train, _, _, _ = train_test_split(
            data[features], data["Final_CGPA"], test_size=0.20, random_state=42
        )
        scaler = self.regression_bundle["pipeline"].named_steps["preprocessor"].named_transformers_["numeric"].named_steps["scale"]
        np.testing.assert_allclose(scaler.mean_, X_train[numeric].mean().to_numpy())

    def test_risk_artifact_is_marked_experimental_and_target_free(self):
        bundle = self.risk_bundle
        metadata = bundle["metadata"]
        self.assertFalse(metadata["final_model"])
        self.assertFalse(metadata["threshold_is_official_policy"])
        self.assertNotIn("Student_ID", metadata["features"])
        self.assertNotIn("Final_CGPA", metadata["features"])
        probabilities = bundle["pipeline"].predict_proba(self.sample)
        self.assertEqual(probabilities.shape, (1, 2))
        self.assertAlmostEqual(float(probabilities.sum()), 1.0)


if __name__ == "__main__":
    unittest.main()

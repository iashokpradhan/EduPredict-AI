import tempfile
import unittest
from pathlib import Path

import src.api as api


class ApiSetupTests(unittest.IsolatedAsyncioTestCase):
    async def test_missing_models_name_required_artifacts_and_build_command(self):
        original_directory = api.MODEL_DIRECTORY
        with tempfile.TemporaryDirectory() as temporary:
            api.MODEL_DIRECTORY = Path(temporary)
            try:
                lifespan = api.app.router.lifespan_context(api.app)
                with self.assertRaisesRegex(
                    RuntimeError,
                    "final_cgpa_regression.joblib.*experimental_risk_classifier.joblib.*python -m src.build_models",
                ):
                    await lifespan.__aenter__()
            finally:
                api.MODEL_DIRECTORY = original_directory


if __name__ == "__main__":
    unittest.main()

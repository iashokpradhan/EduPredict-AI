# EduPredict AI

EduPredict AI is a local capstone demonstration for student CGPA estimation, an experimental academic-risk classifier, and transparent study-support suggestions. It uses scikit-learn pipelines and a FastAPI dashboard. Estimates are decision-support outputs, not diagnoses, guarantees, or the sole basis for consequential academic decisions.

## Privacy and data provenance

The dataset source URL, license, collection process, and redistribution permission have not been verified. The original CSV is not included. Keep it private until its owner and applicable permissions are confirmed. To run data-dependent project workflows, place an authorized file at `data/raw/Student_data.csv` with the project schema:

`Student_ID`, `Gender`, `Age`, `Major`, `Attendance_Pct`, `Study_Hours_Per_Day`, `Previous_CGPA`, `Sleep_Hours`, `Social_Hours_Week`, `Final_CGPA`.

Do not substitute data unless you have permission to use it. Notebooks 01-05 are prepared with saved cell outputs cleared; model metadata and evaluation figures generated from local data are ignored. Notebook execution will create data-derived outputs locally. Do not commit those outputs unless the dataset rights and disclosure implications have been reviewed. Aggregate results in prior local runs are deliberately omitted from this code-only release because dataset rights remain unresolved.

## Environment setup (Windows PowerShell)

The direct dependencies are pinned in `requirements.txt`; the project was verified with Python 3.14.6. These commands describe a fresh setup and were not run as part of this release-preparation phase:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

The existing environment is local and excluded from version control. No packages were installed during release preparation. The requirements file pins direct dependencies, not every transitive package; use a generated lock file if byte-for-byte environment recreation is required.

## Tests

Unit tests use code-only behavior and deterministic synthetic test data. They do not require the private CSV or saved model files:

```powershell
python -m unittest discover -s tests/unit -v
```

Integration tests read the authorized local CSV and generated model artifacts:

```powershell
python -m src.build_models
python -m unittest discover -s tests/integration -v
```

The build command requires `data/raw/Student_data.csv`. If it is missing, it stops with an actionable setup message. Generated `.joblib` models and their JSON metadata are local artifacts and are ignored by Git. The experimental risk classifier is for demonstration only; its cutoff defaults to a provisional project assumption of `Final_CGPA < 2.0`, not official policy.

## Notebooks

Open notebooks 01-05 in VS Code/Jupyter. They load the CSV from the project-relative `data/raw/Student_data.csv` path. To execute a notebook locally from PowerShell:

```powershell
python -m nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=300 notebooks_data_understanding.ipynb
```

Repeat with the desired notebook filename. Executing a notebook writes its data-derived outputs into the notebook; clear those outputs before including it in a public code-only release unless disclosure rights have been confirmed. Notebooks 04-05 perform model comparison and evaluation; the separate model-building command trains the pipelines used by the API without writing notebook outputs.

## Local API and dashboard

After supplying authorized data and building local artifacts:

```powershell
python -m uvicorn src.api:app --reload
```

Open `http://127.0.0.1:8000/`. API routes are `GET /api/v1/health`, `POST /api/v1/predict`, `POST /api/v1/risk`, and `POST /api/v1/recommendations`. Missing artifacts report the exact build command. The API rejects missing, invalid, target-leaking, and extra input fields. The risk response identifies itself as experimental. Dashboard and API are local demonstration components and are not deployed.

## Method safeguards and limitations

- `Final_CGPA` is the regression target; `Student_ID` is excluded from model inputs.
- `Previous_CGPA` is used only if it is known before the prediction period.
- Preprocessing is inside scikit-learn pipelines and is fitted on training data within cross-validation.
- Risk labels are derived from the target only for training; neither the target nor its derivative is an input.
- The recommendation rules use student-provided routine fields and do not imply causal effects.
- SHAP is not a dependency; evaluation notebooks use permutation importance.
- The dataset may be synthetic or otherwise non-representative. No external-cohort validation is claimed.

See [the viva and methodology guide](docs/viva_guide.md), [portfolio summary](docs/portfolio_summary.md), and [optional integration notes](docs/optional_integrations.md). Dataset provenance and redistribution rights must be resolved before publishing dataset-derived outputs or the original CSV.

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

Dataset/model integration tests read the authorized local CSV and generated model artifacts. They require a supplied authorized CSV and a model build:

```powershell
python -m src.build_models
python -m unittest discover -s tests/integration -v
```

The build command requires `data/raw/Student_data.csv`. If it is missing, it stops with an actionable setup message. Generated `.joblib` models and their JSON metadata are local artifacts and are ignored by Git. The API-only integration tests can be run separately with existing local model artifacts using `python -m unittest tests.integration.test_api -v`; they do not read the CSV. The optional PostgreSQL integration check is separate, uses only `EDUPREDICT_TEST_DATABASE_URL`, and is skipped unless that dedicated test database and Psycopg are available. Never point it at a production database. The experimental risk classifier is for demonstration only; its cutoff defaults to a provisional project assumption of `Final_CGPA < 2.0`, not official policy.

Optional PostgreSQL integration tests use only `EDUPREDICT_TEST_DATABASE_URL`, a separate disposable test database, and are skipped when it is unset or Psycopg is unavailable. Never point integration tests at a production database.

## Notebooks

Open notebooks 01-05 in VS Code/Jupyter. They load the CSV from the project-relative `data/raw/Student_data.csv` path. To execute a notebook locally from PowerShell:

```powershell
python -m nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=300 notebooks/01_data_understanding.ipynb
```

Repeat with the desired notebook filename. Executing a notebook writes its data-derived outputs into the notebook; clear those outputs before including it in a public code-only release unless disclosure rights have been confirmed. Notebooks 04-05 perform model comparison and evaluation; the separate model-building command trains the pipelines used by the API without writing notebook outputs.

## Local API and dashboard

The dashboard, health endpoint, rule-based recommendations, and deterministic weekly study planner can run without the private CSV or generated model artifacts. Start the app directly:

```powershell
python -m uvicorn src.api:app --reload
```

Open `http://127.0.0.1:8000/`. API routes are `GET /api/v1/health`, `POST /api/v1/predict`, `POST /api/v1/risk`, `POST /api/v1/recommendations`, and `POST /api/v1/study-plan`. Health reports app readiness and prediction/risk artifact status independently. When a model artifact is absent, its endpoint returns HTTP 503 with setup guidance; the dashboard still serves the app and displays a capability-specific message while other results remain usable. A present but corrupt or incompatible artifact is reported as a load error in health and the API logs, not as a missing file.

Prediction and risk require their corresponding local model artifacts. To generate both, first confirm that you are authorized to use the dataset, place it at `data/raw/Student_data.csv`, then run `python -m src.build_models` from the project root. This command reads the local CSV and writes ignored model files under `models/`. The source, license, and redistribution rights for the original dataset remain unverified; do not obtain or use a copy without permission. The student endpoints reject missing, invalid, target-leaking, and extra input fields. The risk response identifies itself as experimental. Dashboard and API are local demonstration components and are not deployed.

### Weekly study planner

The dashboard includes a local weekly planner. Enter whole-number availability from 0 to 480 minutes for each weekday and optionally enter comma-separated focus areas. The planner uses only those inputs; if focus areas are omitted, it uses its documented default activities. It is deterministic and does not call an LLM or external service.

The API endpoint is `POST /api/v1/study-plan`. Example request:

```json
{
  "available_minutes_by_day": {"Monday": 60, "Wednesday": 30},
  "focus_areas": ["Review notes", "Practice problems"]
}
```

Day names must be Monday through Sunday with this capitalization. Each supplied value must be an integer from 0 to 480; omitted days are treated as unavailable. `focus_areas` may be omitted, or contain 1 to 10 non-empty strings of at most 100 characters each. Invalid requests return HTTP 422 with validation details. The returned schedule is an editable template, not a promise of academic results.

## Optional PostgreSQL analytics and Power BI

The app works without PostgreSQL. Aggregate analytics are enabled only when `EDUPREDICT_DATABASE_URL` is set and Psycopg is installed. See [the database and Power BI guide](docs/optional_integrations.md) for idempotent setup, least-privilege roles, aggregate-only views, and Power BI Desktop connection steps. The application stores only allow-listed event types, recommendation rule IDs, model-availability booleans, and server timestamps. It does not store student identifiers, input payloads, predictions, risk scores, CSV rows, or model artifacts. A database outage does not disable the dashboard, planner, recommendations, or prediction endpoints.

## Method safeguards and limitations

- `Final_CGPA` is the regression target; `Student_ID` is excluded from model inputs.
- `Previous_CGPA` is used only if it is known before the prediction period.
- Preprocessing is inside scikit-learn pipelines and is fitted on training data within cross-validation.
- Risk labels are derived from the target only for training; neither the target nor its derivative is an input.
- The recommendation rules use student-provided routine fields and do not imply causal effects.
- SHAP is not a dependency; evaluation notebooks use permutation importance.
- The dataset may be synthetic or otherwise non-representative. No external-cohort validation is claimed.

See [the viva and methodology guide](docs/viva_guide.md), [portfolio summary](docs/portfolio_summary.md), and [optional integration notes](docs/optional_integrations.md). Dataset provenance and redistribution rights must be resolved before publishing dataset-derived outputs or the original CSV.

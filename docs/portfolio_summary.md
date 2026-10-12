# Portfolio summary and local demo

## Honest portfolio description

> Built EduPredict AI, a local student-support prototype with leakage-aware scikit-learn pipelines, regression and experimental risk-classification workflows, permutation-importance evaluation, transparent recommendations, and a FastAPI dashboard. Dataset provenance and usage rights remain unverified, so the public code-only version contains no dataset-derived results or model artifacts.

Avoid performance claims until the data source and permissions are established and results are independently reviewed. Do not describe associations as causes or the experimental risk estimate as a diagnosis.

## Local demo flow (requires authorized private data and generated artifacts)

1. Activate the existing Python environment and run `python -m uvicorn src.api:app --reload`.
2. Open `http://127.0.0.1:8000/` and use clearly synthetic example inputs.
3. Show the CGPA estimate separately from the experimental risk estimate and rule-based suggestions.
4. Explain the provisional 2.0 threshold assumption and the need for human review.
5. Show the regression residual/permutation plots and note `Previous_CGPA` dominance.

## Before any public release

- Verify the dataset's source, license, and permitted redistribution. They are currently unknown; `data/raw/` is git-ignored.
- Notebook outputs 01-05 are cleared in the code-only release; notebook code and Markdown remain. The source URL, license, and redistribution rights remain unverified. Keep the raw dataset, generated model metadata, and evaluation figures private until permissions are confirmed.
- Review the tracked-file list after initializing Git; this workspace currently has no `.git` directory or remote repository.
- Regenerate and validate model artifacts locally; `.joblib` files and generated metadata are git-ignored because they are derived local artifacts; joblib files also use pickle semantics. Do not load untrusted artifacts.
- Keep the academic-risk artifact clearly marked experimental and retain the rare-class caveats in every demo description.
- Do not publish or push this project without explicit approval.

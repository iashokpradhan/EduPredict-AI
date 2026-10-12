# Optional database and BI integrations

## Current audit

No database URL/host configuration, PostgreSQL client executable, or PostgreSQL Python driver was found in the workspace/environment. No Power BI project, configuration, or local CLI was found. Credential variable names were checked without reading credential values. No integration was added.

## PostgreSQL proposal (future, only if approved)

Start with a minimal schema:

- `prediction_request`: generated request ID, created timestamp, model version, and permitted feature snapshot only when data retention is approved.
- `prediction_result`: request ID, predicted CGPA, experimental risk score/status, and threshold version.
- `recommendation`: request ID, deterministic rule ID, and display text/version.

Use parameterized queries and a least-privilege database role. Store credentials in an environment variable or approved secret manager, never in source control. Decide consent, retention, deletion, access control, and whether student-level information needs persistence before implementing storage. The current demo is stateless and does not need a database.

## Power BI proposal (future, optional)

Only publish aggregate, de-identified measures after data-use approval. Possible measures include regression MAE/RMSE by evaluation cohort, counts of at-risk labels by the explicitly documented cutoff, precision/recall with positive support counts, and recommendation rule frequency. Dashboards should show sample sizes, model version, threshold, evaluation date, and disclaimers; suppress small groups to reduce re-identification risk. Keep model evaluation separate from operational student records. No Power BI software or external service has been accessed or configured.

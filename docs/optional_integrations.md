# Optional PostgreSQL analytics and Power BI

PostgreSQL is disabled by default. The local dashboard, model endpoints, recommendations, and weekly planner continue to work without a configured database. If PostgreSQL is configured but unavailable, writes are skipped after the failure is detected and the API reports the database capability as unavailable; core responses still succeed.

## What is stored

The optional table is `analytics.usage_events`. Its allow-listed fields are:

- event type: a valid prediction or risk request, recommendations evaluated, one recommendation rule triggered, or a study plan created
- recommendation rule ID, only for a triggered rule (`attendance_review`, `study_schedule`, or `sustainable_rest_routine`)
- prediction-model and experimental-risk-model availability booleans
- server-generated UTC-capable timestamp

No student identifier, input value, request body, recommendation text, predicted CGPA, risk probability, CSV row, or model artifact is written. The timestamped event log is operational telemetry, not a student record. Before enabling it in a real setting, obtain the appropriate institutional approval, limit database access, and set a retention policy. The public reporting views aggregate events by UTC date and contain no student-level rows.

## Configure and initialize PostgreSQL

Psycopg 3 is an optional runtime dependency pinned in `requirements.txt`. It is imported only when `EDUPREDICT_DATABASE_URL` is configured. No package was installed as part of this code change. For a new environment, install the project's requirements through its normal approved setup process.

Set the connection string in the process environment; `.env.example` contains only a placeholder and the app does not automatically parse `.env` files. In PowerShell:

```powershell
$env:EDUPREDICT_DATABASE_URL = "postgresql://edupredict_app:YOUR_SECRET@localhost:5432/edupredict"
python -m src.analytics_db setup
python -m uvicorn src.api:app --reload
```

Run `python -m src.analytics_db setup` as a database owner with permission to create the `analytics` and `bi` schemas. The migration at `sql/001_aggregate_analytics.sql` is idempotent and can be run again safely. It creates the event table and three reporting views. It does not create database roles or store credentials.

Use separate least-privilege accounts after setup. The application role needs `USAGE` on the `analytics` schema and `INSERT` on `analytics.usage_events`. It does not need read permission on the event table. The Power BI role needs `CONNECT` on the database, `USAGE` on schema `bi`, and `SELECT` on the three views only. Create credentials in PostgreSQL/Power BI's credential manager or a protected local environment variable; never put real secrets in source control. The API's `/api/v1/health` response reports whether analytics is disabled, connected, missing its schema, missing the Psycopg driver, or unavailable. It never returns the connection string.

If database setup or connectivity fails, the API remains usable. Analytics events may be skipped; they are not buffered locally or retried in the background. `GET /api/v1/health` reflects the most recent startup connection check or write failure. After fixing connectivity or applying the schema, restart the API to recheck and resume analytics writes.

## Power BI Desktop

Power BI is a read-only consumer of the aggregate views; this project does not create or publish a `.pbix` file.

1. Configure the Power BI role as described above, then in Power BI Desktop choose **Get data → PostgreSQL database**.
2. Enter the PostgreSQL server and database. Choose Import mode for a small local demonstration, or DirectQuery if the deployment's PostgreSQL connectivity and refresh policy support it.
3. Authenticate using the read-only Power BI account. Select only `bi.daily_usage`, `bi.daily_recommendation_rules`, and `bi.daily_model_availability`.
4. Use `usage_date_utc` as the date axis. Relate the views to a calendar table by that column if a shared date slicer is needed.
5. Configure refresh in Power BI Desktop for a local report. A published Power BI Service dataset may require an on-premises data gateway; that external setup is outside this project and has not been performed.

Suggested report pages:

- **Usage trend:** line chart by `usage_date_utc`, with event counts split by `event_type` from `bi.daily_usage`.
- **Recommendation rules:** bar chart by `recommendation_rule_id`, with `event_count`, and a date slicer from `bi.daily_recommendation_rules`.
- **Capability availability:** line chart of prediction/risk available-event counts against total event counts from `bi.daily_model_availability`.

Example DAX measures (adjust table names to the names assigned by Power BI):

```DAX
Usage Events = SUM('daily_usage'[event_count])

Triggered Rule Events = SUM('daily_recommendation_rules'[event_count])

Prediction Availability Rate =
    DIVIDE(
        SUM('daily_model_availability'[prediction_available_events]),
        SUM('daily_model_availability'[event_count])
    )

Risk Model Availability Rate =
    DIVIDE(
        SUM('daily_model_availability'[risk_available_events]),
        SUM('daily_model_availability'[event_count])
    )
```

These measures describe demo usage and whether model capabilities were available. They are not model accuracy, student outcomes, or evidence that a rule caused a result. Empty views mean no events were recorded during the selected period; they do not imply zero student need.

## Views

| View | Grain | Main columns |
| --- | --- | --- |
| `bi.daily_usage` | UTC date × event type | `usage_date_utc`, `event_type`, `event_count`, model-available event counts |
| `bi.daily_recommendation_rules` | UTC date × rule ID | `usage_date_utc`, `recommendation_rule_id`, `event_count` |
| `bi.daily_model_availability` | UTC date | `usage_date_utc`, `event_count`, prediction/risk available-event counts |

The views expose aggregates only. Counts can still be small, so avoid public dashboards or narrow time filters that might allow someone to infer who used the local demo. Dataset provenance and redistribution rights remain unverified; the analytics path neither imports the CSV nor resolves those rights.

## Optional database integration test

Unit tests use mocks and do not need PostgreSQL. A live integration check exists but is skipped unless both Psycopg is installed and `EDUPREDICT_TEST_DATABASE_URL` points to a dedicated disposable test database. It creates the schema if needed, inserts one synthetic event inside a transaction, validates aggregate views, then rolls the event back. Do not point it at a production database.

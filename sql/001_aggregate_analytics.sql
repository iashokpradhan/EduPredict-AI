-- Aggregate-only operational telemetry. Never add student inputs or outcomes here.
CREATE SCHEMA IF NOT EXISTS analytics;
CREATE SCHEMA IF NOT EXISTS bi;

CREATE TABLE IF NOT EXISTS analytics.usage_events (
    occurred_at timestamptz NOT NULL DEFAULT now(),
    event_type text NOT NULL CHECK (event_type IN (
        'prediction_requested',
        'risk_requested',
        'recommendations_evaluated',
        'recommendation_rule_triggered',
        'study_plan_created'
    )),
    recommendation_rule_id text NULL CHECK (
        recommendation_rule_id IS NULL OR recommendation_rule_id IN (
            'attendance_review',
            'study_schedule',
            'sustainable_rest_routine'
        )
    ),
    prediction_available boolean NOT NULL,
    risk_available boolean NOT NULL,
    CHECK (
        (event_type = 'recommendation_rule_triggered' AND recommendation_rule_id IS NOT NULL)
        OR (event_type <> 'recommendation_rule_triggered' AND recommendation_rule_id IS NULL)
    )
);

CREATE INDEX IF NOT EXISTS usage_events_occurred_at_idx
    ON analytics.usage_events (occurred_at);

CREATE OR REPLACE VIEW bi.daily_usage AS
SELECT
    (occurred_at AT TIME ZONE 'UTC')::date AS usage_date_utc,
    event_type,
    count(*)::bigint AS event_count,
    count(*) FILTER (WHERE prediction_available)::bigint AS prediction_available_events,
    count(*) FILTER (WHERE risk_available)::bigint AS risk_available_events
FROM analytics.usage_events
GROUP BY (occurred_at AT TIME ZONE 'UTC')::date, event_type;

CREATE OR REPLACE VIEW bi.daily_recommendation_rules AS
SELECT
    (occurred_at AT TIME ZONE 'UTC')::date AS usage_date_utc,
    recommendation_rule_id,
    count(*)::bigint AS event_count
FROM analytics.usage_events
WHERE event_type = 'recommendation_rule_triggered'
GROUP BY (occurred_at AT TIME ZONE 'UTC')::date, recommendation_rule_id;

CREATE OR REPLACE VIEW bi.daily_model_availability AS
SELECT
    (occurred_at AT TIME ZONE 'UTC')::date AS usage_date_utc,
    count(*)::bigint AS event_count,
    count(*) FILTER (WHERE prediction_available)::bigint AS prediction_available_events,
    count(*) FILTER (WHERE risk_available)::bigint AS risk_available_events
FROM analytics.usage_events
GROUP BY (occurred_at AT TIME ZONE 'UTC')::date;

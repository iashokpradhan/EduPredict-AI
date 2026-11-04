-- =====================================================================
-- EduPredict AI — Dedicated Power BI Reporting Views (Phase 3)
-- =====================================================================
-- These views simplify Star Schema modeling in Power BI Desktop.
-- Compatible with PostgreSQL and SQLite.
-- =====================================================================

-- 1. Student Dimension View
CREATE VIEW IF NOT EXISTS v_powerbi_student_dim AS
SELECT
    student_id,
    gender,
    age,
    major,
    created_at AS enrolled_date
FROM students;

-- 2. Academic Facts View (Metrics, Performance Bands, Tiers)
CREATE VIEW IF NOT EXISTS v_powerbi_academic_facts AS
SELECT
    ar.record_id,
    ar.student_id,
    s.major,
    s.gender,
    ar.attendance_pct,
    ar.study_hours_per_day,
    ar.previous_cgpa,
    ar.sleep_hours,
    ar.social_hours_week,
    ar.final_cgpa,
    ROUND(ar.final_cgpa - ar.previous_cgpa, 2) AS cgpa_growth,
    CASE
        WHEN ar.final_cgpa < 2.0 THEN 1
        ELSE 0
    END AS is_at_risk,
    CASE
        WHEN ar.final_cgpa >= 3.5 THEN 'First Class (3.5+)'
        WHEN ar.final_cgpa >= 3.0 THEN 'Upper Second (3.0-3.49)'
        WHEN ar.final_cgpa >= 2.0 THEN 'Lower Second (2.0-2.99)'
        ELSE 'At Risk (<2.0)'
    END AS honors_band,
    CASE
        WHEN ar.attendance_pct >= 90 THEN '90%+'
        WHEN ar.attendance_pct >= 80 THEN '80-89%'
        WHEN ar.attendance_pct >= 70 THEN '70-79%'
        ELSE '<70%'
    END AS attendance_bracket,
    CASE
        WHEN ar.study_hours_per_day >= 6.0 THEN '6+ Hours'
        WHEN ar.study_hours_per_day >= 4.0 THEN '4-6 Hours'
        WHEN ar.study_hours_per_day >= 2.0 THEN '2-4 Hours'
        ELSE '<2 Hours'
    END AS study_bracket,
    CASE
        WHEN ar.sleep_hours < 6.0 THEN 'Sleep Deprived (<6h)'
        WHEN ar.sleep_hours <= 8.0 THEN 'Healthy (6-8h)'
        ELSE 'Extended (>8h)'
    END AS sleep_bracket,
    ar.recorded_at
FROM academic_records ar
JOIN students s ON ar.student_id = s.student_id;

-- 3. Major Aggregates Summary View
CREATE VIEW IF NOT EXISTS v_powerbi_major_aggregates AS
SELECT
    s.major,
    COUNT(*) AS total_students,
    ROUND(AVG(ar.final_cgpa), 2) AS avg_cgpa,
    ROUND(AVG(ar.previous_cgpa), 2) AS avg_prior_cgpa,
    ROUND(AVG(ar.attendance_pct), 1) AS avg_attendance,
    ROUND(AVG(ar.study_hours_per_day), 1) AS avg_study_hours,
    ROUND(AVG(ar.sleep_hours), 1) AS avg_sleep_hours,
    SUM(CASE WHEN ar.final_cgpa < 2.0 THEN 1 ELSE 0 END) AS at_risk_count,
    ROUND(SUM(CASE WHEN ar.final_cgpa < 2.0 THEN 1.0 ELSE 0.0 END) / COUNT(*) * 100, 2) AS at_risk_pct
FROM students s
JOIN academic_records ar ON s.student_id = ar.student_id
GROUP BY s.major;

-- 4. Academic Risk Early Intervention Cohort View
CREATE VIEW IF NOT EXISTS v_powerbi_risk_summary AS
SELECT
    ar.record_id,
    ar.student_id,
    s.major,
    s.gender,
    ar.attendance_pct,
    ar.study_hours_per_day,
    ar.previous_cgpa,
    ar.final_cgpa,
    CASE
        WHEN ar.final_cgpa < 2.0 THEN 'Confirmed Risk'
        WHEN ar.previous_cgpa < 2.5 AND ar.attendance_pct < 75 THEN 'High Vulnerability'
        ELSE 'Satisfactory'
    END AS risk_tier
FROM academic_records ar
JOIN students s ON ar.student_id = s.student_id
WHERE ar.final_cgpa < 2.0 OR (ar.previous_cgpa < 2.5 AND ar.attendance_pct < 75);

-- 5. Prediction History View (Live Auditing)
CREATE VIEW IF NOT EXISTS v_powerbi_prediction_history AS
SELECT
    prediction_id,
    student_id,
    major,
    gender,
    attendance_pct,
    study_hours_per_day,
    previous_cgpa,
    predicted_cgpa,
    risk_probability,
    risk_label,
    created_at AS prediction_timestamp
FROM predictions;

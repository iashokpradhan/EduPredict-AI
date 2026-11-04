-- =====================================================================
-- EduPredict AI — Phase 2 SQL Analytics & Reporting Queries Suite
-- =====================================================================
-- These queries directly answer the research and business questions
-- outlined in the Capstone Roadmap. Tested on PostgreSQL and SQLite.
-- =====================================================================

-- ---------------------------------------------------------------------
-- QUERY 1: Overall Academic Performance KPIs
-- Purpose: Executive summary KPIs for university leadership dashboard.
-- ---------------------------------------------------------------------
SELECT
    COUNT(*) AS total_students,
    ROUND(AVG(ar.final_cgpa), 2) AS avg_final_cgpa,
    ROUND(AVG(ar.previous_cgpa), 2) AS avg_previous_cgpa,
    ROUND(AVG(ar.attendance_pct), 1) AS avg_attendance_pct,
    ROUND(AVG(ar.study_hours_per_day), 1) AS avg_study_hours_per_day,
    ROUND(AVG(ar.sleep_hours), 1) AS avg_sleep_hours,
    ROUND(AVG(ar.social_hours_week), 1) AS avg_social_hours_week,
    SUM(CASE WHEN ar.final_cgpa < 2.0 THEN 1 ELSE 0 END) AS at_risk_count,
    ROUND(SUM(CASE WHEN ar.final_cgpa < 2.0 THEN 1.0 ELSE 0.0 END) / COUNT(*) * 100, 2) AS at_risk_rate_pct
FROM students s
JOIN academic_records ar ON s.student_id = ar.student_id;


-- ---------------------------------------------------------------------
-- QUERY 2: Academic Performance Breakdown by Major
-- Purpose: Identify which academic majors achieve the highest CGPA,
-- attendance rates, and where intervention may be needed.
-- ---------------------------------------------------------------------
SELECT
    s.major,
    COUNT(*) AS student_count,
    ROUND(AVG(ar.final_cgpa), 2) AS avg_final_cgpa,
    ROUND(MIN(ar.final_cgpa), 2) AS min_final_cgpa,
    ROUND(MAX(ar.final_cgpa), 2) AS max_final_cgpa,
    ROUND(AVG(ar.attendance_pct), 1) AS avg_attendance_pct,
    ROUND(AVG(ar.study_hours_per_day), 1) AS avg_study_hours,
    SUM(CASE WHEN ar.final_cgpa < 2.0 THEN 1 ELSE 0 END) AS at_risk_count,
    ROUND(SUM(CASE WHEN ar.final_cgpa < 2.0 THEN 1.0 ELSE 0.0 END) / COUNT(*) * 100, 2) AS at_risk_rate_pct
FROM students s
JOIN academic_records ar ON s.student_id = ar.student_id
GROUP BY s.major
ORDER BY avg_final_cgpa DESC;


-- ---------------------------------------------------------------------
-- QUERY 3: Attendance Quartiles vs Academic Performance
-- Purpose: Measure the direct empirical relationship between attendance
-- tiers and student grade outcomes.
-- ---------------------------------------------------------------------
SELECT
    CASE
        WHEN ar.attendance_pct >= 90 THEN 'Tier 1: High Attendance (90-100%)'
        WHEN ar.attendance_pct >= 80 THEN 'Tier 2: Good Attendance (80-89%)'
        WHEN ar.attendance_pct >= 70 THEN 'Tier 3: Moderate Attendance (70-79%)'
        ELSE 'Tier 4: Chronic Absenteeism (<70%)'
    END AS attendance_tier,
    COUNT(*) AS student_count,
    ROUND(AVG(ar.final_cgpa), 2) AS avg_final_cgpa,
    ROUND(AVG(ar.previous_cgpa), 2) AS avg_previous_cgpa,
    ROUND(AVG(ar.study_hours_per_day), 1) AS avg_study_hours,
    SUM(CASE WHEN ar.final_cgpa < 2.0 THEN 1 ELSE 0 END) AS at_risk_count,
    ROUND(SUM(CASE WHEN ar.final_cgpa < 2.0 THEN 1.0 ELSE 0.0 END) / COUNT(*) * 100, 2) AS at_risk_rate_pct
FROM academic_records ar
GROUP BY attendance_tier
ORDER BY avg_final_cgpa DESC;


-- ---------------------------------------------------------------------
-- QUERY 4: Study Hours Buckets vs Academic CGPA
-- Purpose: Evaluate whether increased independent study time correlates
-- with higher CGPA and whether diminishing returns exist.
-- ---------------------------------------------------------------------
SELECT
    CASE
        WHEN ar.study_hours_per_day < 2.0 THEN 'Low (<2 hrs/day)'
        WHEN ar.study_hours_per_day < 4.0 THEN 'Moderate (2-4 hrs/day)'
        WHEN ar.study_hours_per_day < 6.0 THEN 'High (4-6 hrs/day)'
        ELSE 'Very High (6+ hrs/day)'
    END AS study_intensity,
    COUNT(*) AS student_count,
    ROUND(AVG(ar.final_cgpa), 2) AS avg_final_cgpa,
    ROUND(AVG(ar.attendance_pct), 1) AS avg_attendance_pct,
    ROUND(AVG(ar.sleep_hours), 1) AS avg_sleep_hours,
    SUM(CASE WHEN ar.final_cgpa < 2.0 THEN 1 ELSE 0 END) AS at_risk_count
FROM academic_records ar
GROUP BY study_intensity
ORDER BY avg_final_cgpa DESC;


-- ---------------------------------------------------------------------
-- QUERY 5: Sleep Duration & Student Well-being vs CGPA
-- Purpose: Analyze optimal sleep window (7-8 hours) vs sleep deprivation (<6 hours).
-- ---------------------------------------------------------------------
SELECT
    CASE
        WHEN ar.sleep_hours < 6.0 THEN 'Sleep Deprived (<6 hrs)'
        WHEN ar.sleep_hours <= 8.0 THEN 'Optimal Sleep (6-8 hrs)'
        ELSE 'Long Sleep (>8 hrs)'
    END AS sleep_category,
    COUNT(*) AS student_count,
    ROUND(AVG(ar.final_cgpa), 2) AS avg_final_cgpa,
    ROUND(AVG(ar.study_hours_per_day), 1) AS avg_study_hours,
    ROUND(AVG(ar.attendance_pct), 1) AS avg_attendance_pct,
    SUM(CASE WHEN ar.final_cgpa < 2.0 THEN 1 ELSE 0 END) AS at_risk_count
FROM academic_records ar
GROUP BY sleep_category
ORDER BY avg_final_cgpa DESC;


-- ---------------------------------------------------------------------
-- QUERY 6: Social Hours per Week vs Academic Outcome
-- Purpose: Explore whether social engagement impacts student performance.
-- ---------------------------------------------------------------------
SELECT
    CASE
        WHEN ar.social_hours_week <= 5 THEN 'Low Social (0-5 hrs/wk)'
        WHEN ar.social_hours_week <= 10 THEN 'Moderate Social (6-10 hrs/wk)'
        WHEN ar.social_hours_week <= 15 THEN 'High Social (11-15 hrs/wk)'
        ELSE 'Excessive Social (16+ hrs/wk)'
    END AS social_engagement_level,
    COUNT(*) AS student_count,
    ROUND(AVG(ar.final_cgpa), 2) AS avg_final_cgpa,
    ROUND(AVG(ar.study_hours_per_day), 1) AS avg_study_hours,
    ROUND(AVG(ar.attendance_pct), 1) AS avg_attendance_pct
FROM academic_records ar
GROUP BY social_engagement_level
ORDER BY avg_final_cgpa DESC;


-- ---------------------------------------------------------------------
-- QUERY 7: Student Academic Honors Bands (Academic Distribution)
-- Purpose: Count how many students fall into formal degree classifications.
-- ---------------------------------------------------------------------
SELECT
    CASE
        WHEN ar.final_cgpa >= 3.50 THEN 'First Class Honors (3.50 - 4.00)'
        WHEN ar.final_cgpa >= 3.00 THEN 'Upper Second Class (3.00 - 3.49)'
        WHEN ar.final_cgpa >= 2.00 THEN 'Lower Second Class (2.00 - 2.99)'
        ELSE 'At-Risk / Warning (< 2.00)'
    END AS performance_band,
    COUNT(*) AS student_count,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM academic_records), 2) AS percentage_of_cohort,
    ROUND(AVG(ar.attendance_pct), 1) AS avg_attendance,
    ROUND(AVG(ar.study_hours_per_day), 1) AS avg_study_hours,
    ROUND(AVG(ar.previous_cgpa), 2) AS avg_previous_cgpa
FROM academic_records ar
GROUP BY performance_band
ORDER BY MIN(ar.final_cgpa) DESC;


-- ---------------------------------------------------------------------
-- QUERY 8: Academic Progression & Growth Analysis (CGPA Delta)
-- Purpose: Find students who improved significantly vs those whose grades dropped.
-- ---------------------------------------------------------------------
SELECT
    CASE
        WHEN (ar.final_cgpa - ar.previous_cgpa) >= 0.2 THEN 'Improved (+0.20 or more)'
        WHEN (ar.final_cgpa - ar.previous_cgpa) <= -0.2 THEN 'Declined (-0.20 or more)'
        ELSE 'Stable (-0.19 to +0.19)'
    END AS performance_trajectory,
    COUNT(*) AS student_count,
    ROUND(AVG(ar.final_cgpa - ar.previous_cgpa), 2) AS avg_cgpa_change,
    ROUND(AVG(ar.attendance_pct), 1) AS avg_attendance,
    ROUND(AVG(ar.study_hours_per_day), 1) AS avg_study_hours
FROM academic_records ar
GROUP BY performance_trajectory
ORDER BY avg_cgpa_change DESC;


-- ---------------------------------------------------------------------
-- QUERY 9: Demographic & Subgroup Parity Check
-- Purpose: Fairness audit comparing gender cohorts on attendance and outcomes.
-- ---------------------------------------------------------------------
SELECT
    s.gender,
    COUNT(*) AS student_count,
    ROUND(AVG(ar.final_cgpa), 2) AS avg_final_cgpa,
    ROUND(AVG(ar.previous_cgpa), 2) AS avg_previous_cgpa,
    ROUND(AVG(ar.attendance_pct), 1) AS avg_attendance_pct,
    ROUND(AVG(ar.study_hours_per_day), 1) AS avg_study_hours,
    SUM(CASE WHEN ar.final_cgpa < 2.0 THEN 1 ELSE 0 END) AS at_risk_count,
    ROUND(SUM(CASE WHEN ar.final_cgpa < 2.0 THEN 1.0 ELSE 0.0 END) / COUNT(*) * 100, 2) AS at_risk_pct
FROM students s
JOIN academic_records ar ON s.student_id = ar.student_id
GROUP BY s.gender;


-- ---------------------------------------------------------------------
-- QUERY 10: Early Warning Intervention Priority List
-- Purpose: Filter students in urgent need of academic advising
-- (Attendance < 75% AND Previous CGPA < 2.50).
-- ---------------------------------------------------------------------
SELECT
    s.student_id,
    s.major,
    s.gender,
    ar.previous_cgpa,
    ar.attendance_pct,
    ar.study_hours_per_day,
    ar.sleep_hours,
    ar.final_cgpa,
    CASE WHEN ar.final_cgpa < 2.0 THEN 'CONFIRMED_AT_RISK' ELSE 'VULNERABLE' END AS risk_status
FROM students s
JOIN academic_records ar ON s.student_id = ar.student_id
WHERE ar.attendance_pct < 75.0 AND ar.previous_cgpa < 2.50
ORDER BY ar.previous_cgpa ASC, ar.attendance_pct ASC
LIMIT 20;


-- ---------------------------------------------------------------------
-- QUERY 11: Habit Comparison: Top 10% vs Bottom 10%
-- Purpose: Clear comparative benchmark between highest and lowest performers.
-- ---------------------------------------------------------------------
WITH ranked_students AS (
    SELECT
        student_id,
        final_cgpa,
        attendance_pct,
        study_hours_per_day,
        sleep_hours,
        social_hours_week,
        NTILE(10) OVER (ORDER BY final_cgpa DESC) AS decile
    FROM academic_records
)
SELECT
    CASE
        WHEN decile = 1 THEN 'Top 10% High Achievers'
        WHEN decile = 10 THEN 'Bottom 10% Cohort'
        ELSE 'Middle 80%'
    END AS student_segment,
    COUNT(*) AS count_students,
    ROUND(AVG(final_cgpa), 2) AS avg_cgpa,
    ROUND(AVG(attendance_pct), 1) AS avg_attendance,
    ROUND(AVG(study_hours_per_day), 1) AS avg_daily_study_hours,
    ROUND(AVG(sleep_hours), 1) AS avg_nightly_sleep_hours,
    ROUND(AVG(social_hours_week), 1) AS avg_weekly_social_hours
FROM ranked_students
WHERE decile IN (1, 10)
GROUP BY student_segment
ORDER BY avg_cgpa DESC;


-- ---------------------------------------------------------------------
-- QUERY 12: Prediction Audit & Risk Model Traffic (from predictions table)
-- Purpose: Monitor deployed model usage, flag rate, and mean estimates.
-- ---------------------------------------------------------------------
SELECT
    DATE(created_at) AS inference_date,
    COUNT(*) AS total_predictions,
    ROUND(AVG(predicted_cgpa), 2) AS avg_predicted_cgpa,
    ROUND(AVG(risk_probability) * 100, 1) AS avg_risk_probability_pct,
    SUM(CASE WHEN risk_label = 'at_risk' THEN 1 ELSE 0 END) AS flagged_at_risk_count,
    ROUND(SUM(CASE WHEN risk_label = 'at_risk' THEN 1.0 ELSE 0.0 END) / COUNT(*) * 100, 1) AS flagged_rate_pct
FROM predictions
GROUP BY DATE(created_at)
ORDER BY inference_date DESC;

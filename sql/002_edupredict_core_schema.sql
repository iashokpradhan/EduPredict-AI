-- =====================================================================
-- EduPredict AI — Core Relational Database Schema (Phase 2 & 4)
-- =====================================================================
-- Supports PostgreSQL 14+ and SQLite 3.35+
-- Normalized to Third Normal Form (3NF)
-- Designed for student tracking, academic risk detection, prediction auditing,
-- and high-performance Power BI analytics ingestion.
-- =====================================================================

-- 1. Students Dimension Table (Demographic and program metadata)
CREATE TABLE IF NOT EXISTS students (
    student_id VARCHAR(50) PRIMARY KEY,
    gender VARCHAR(20) NOT NULL CHECK (gender IN ('Female', 'Male', 'Other')),
    age INTEGER NOT NULL CHECK (age >= 10 AND age <= 100),
    major VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. Academic Records Fact Table (Behavioral habits, previous CGPA & target)
CREATE TABLE IF NOT EXISTS academic_records (
    record_id SERIAL PRIMARY KEY,
    student_id VARCHAR(50) NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
    attendance_pct NUMERIC(5,2) NOT NULL CHECK (attendance_pct >= 0 AND attendance_pct <= 100),
    study_hours_per_day NUMERIC(4,2) NOT NULL CHECK (study_hours_per_day >= 0 AND study_hours_per_day <= 24),
    previous_cgpa NUMERIC(4,2) NOT NULL CHECK (previous_cgpa >= 0 AND previous_cgpa <= 4),
    sleep_hours NUMERIC(4,2) NOT NULL CHECK (sleep_hours >= 0 AND sleep_hours <= 24),
    social_hours_week NUMERIC(5,2) NOT NULL CHECK (social_hours_week >= 0 AND social_hours_week <= 168),
    final_cgpa NUMERIC(4,2) CHECK (final_cgpa >= 0 AND final_cgpa <= 4),
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Performance Indexes
CREATE INDEX IF NOT EXISTS idx_records_student_id ON academic_records(student_id);
CREATE INDEX IF NOT EXISTS idx_records_final_cgpa ON academic_records(final_cgpa);
CREATE INDEX IF NOT EXISTS idx_records_prev_cgpa ON academic_records(previous_cgpa);
CREATE INDEX IF NOT EXISTS idx_records_attendance ON academic_records(attendance_pct);
CREATE INDEX IF NOT EXISTS idx_students_major ON students(major);

-- 3. Predictions Audit Table (Inference log for model tracking and monitoring)
CREATE TABLE IF NOT EXISTS predictions (
    prediction_id SERIAL PRIMARY KEY,
    student_id VARCHAR(50) REFERENCES students(student_id) ON DELETE SET NULL,
    gender VARCHAR(20),
    age NUMERIC(4,1),
    major VARCHAR(100),
    attendance_pct NUMERIC(5,2),
    study_hours_per_day NUMERIC(4,2),
    previous_cgpa NUMERIC(4,2),
    sleep_hours NUMERIC(4,2),
    social_hours_week NUMERIC(5,2),
    predicted_cgpa NUMERIC(4,2) NOT NULL,
    risk_probability NUMERIC(5,4) NOT NULL,
    risk_label VARCHAR(30) NOT NULL CHECK (risk_label IN ('at_risk', 'not_at_risk')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_predictions_created_at ON predictions(created_at);
CREATE INDEX IF NOT EXISTS idx_predictions_risk_label ON predictions(risk_label);

-- 4. Recommendations Log Table (Auditing generated guidance)
CREATE TABLE IF NOT EXISTS recommendations_log (
    id SERIAL PRIMARY KEY,
    prediction_id INTEGER REFERENCES predictions(prediction_id) ON DELETE CASCADE,
    rule_id VARCHAR(50) NOT NULL,
    title VARCHAR(150) NOT NULL,
    action TEXT NOT NULL,
    why TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_recommendations_rule_id ON recommendations_log(rule_id);

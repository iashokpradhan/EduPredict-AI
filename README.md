# EduPredict AI — IILM University Student Performance Prediction System

> **Institution:** IILM University  
> **Domain:** `@iilm.edu` — Institutional access only

[![Python 3.12 / 3.14](https://img.shields.io/badge/python-3.12%20%7C%203.14-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.143.0-009688.svg)](https://fastapi.tiangolo.com/)
[![Scikit-Learn](https://img.shields.io/badge/scikit--learn-1.9.1-orange.svg)](https://scikit-learn.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791.svg)](https://www.postgresql.org/)
[![Power BI Ready](https://img.shields.io/badge/Power%20BI-Star%20Schema-F2C811.svg)](https://powerbi.microsoft.com/)
[![Tests Passing](https://img.shields.io/badge/tests-54%20passed-brightgreen.svg)](tests/)

EduPredict AI is an end-to-end, production-grade Data Science Capstone Project built for **IILM University**. It forecasts student academic performance (Final CGPA), identifies students at risk of academic probation ($\text{Final\_CGPA} < 2.0$), provides transparent rules-based study guidance, Explainable AI waterfall attribution, faculty batch screening, 4-week academic counseling roadmaps, and delivers institutional intelligence through SQL analytics and Power BI dashboards.

**Registration and login are restricted to @iilm.edu institutional email addresses.**

---

## 🎯 Architecture & Workflow

1. **Student Data Layer:** Collects pre-examination behavioral and academic indicators (Attendance %, Daily study hours, Sleep, Social activity, Prior CGPA).
2. **Leakage-Free Preprocessing:** Standardized with Scikit-Learn `Pipeline` and `ColumnTransformer` fitted strictly on training folds within cross-validation.
3. **Machine Learning Engines:**
   - **Continuous CGPA Regression:** Gradient Boosting Regressor (Test MAE: 0.0965, RMSE: 0.1153, $R^2$: 0.9536).
   - **Academic Risk Classifier:** Class-Weighted Random Forest (Test Recall: 87.5%, ROC-AUC: 0.995).
4. **Advisory & Study Planner:** Interpretable heuristics engine generating actionable study suggestions and Pomodoro-paced weekly timetables.
5. **Relational Database (3NF):** PostgreSQL / SQLite dual-support architecture storing students, academic records, prediction audits, and recommendations.
6. **Cohort Analytics & Power BI:** Documented SQL analytics suite and Power BI Star Schema views/CSVs for academic leadership.
7. **Interactive Dashboard:** Modern HTML5/JavaScript user interface with 1-click persona presets (High Achiever, Balanced, At-Risk, Sleep Deprived).

---

## 🔐 IILM University Demo Accounts

| Role | Email | Password | Access |
|---|---|---|---|
| Student | `aarav.sharma@iilm.edu` | `student123` | Assessment, Counselor, Goals |
| Faculty Advisor | `dr.mehta@iilm.edu` | `advisor123` | All tabs + Batch Screening |

> **Note:** Registration requires a valid `@iilm.edu` email. The domain is enforced server-side.

---

## 🚀 Quick Start Guide

### 1. Environment Setup (Windows PowerShell)

```powershell
# Create and activate virtual environment
py -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### 2. Build Models & Seed Database

```powershell
# Train and serialize regression & classification pipelines
python -m src.build_models

# Initialize database schema and seed student records
python -m src.seed_db
```

### 3. Start Application Server

```powershell
python -m uvicorn src.api:app --reload
```
Open **`http://127.0.0.1:8000/`** in your browser to access the interactive web dashboard.

---

## 🧪 Comprehensive Automated Test Suite

EduPredict AI features **44 automated tests** covering unit behavior, validation rules, XSS protection, and database operations:

```powershell
# Run 30 Unit Tests
python -m unittest discover -s tests/unit -v

# Run 14 Integration Tests
python -m unittest discover -s tests/integration -v
```

---

## 📊 SQL Analytics & Power BI Dashboard

### Run Analytical SQL Queries
Explore the comprehensive query suite answering institutional research questions:
- `sql/002_edupredict_core_schema.sql`: Full DDL with 3NF relational schema.
- `sql/003_analytics_and_reporting_queries.sql`: 12+ analytical queries (GPA by major, attendance quartiles, optimal sleep curve, early warning watchlist).
- `sql/004_powerbi_views.sql`: Star Schema views tailored for Power BI Desktop.

### Power BI Ingestion in 1 Click
Export clean, pre-modeled dimension and fact CSV tables:
```powershell
python -m src.export_powerbi_data
```
Follow the step-by-step [Power BI Dashboard Blueprint Guide](docs/powerbi_dashboard_guide.md) to build interactive 4-page dashboards with copy-paste DAX measures!

---

## 🐳 Docker & Docker Compose Setup

Run the full production stack (FastAPI Backend + PostgreSQL Database) with a single command:

```powershell
docker compose up --build
```
The application will be live at `http://localhost:8000/` with healthy PostgreSQL database synchronization.

---

## 📚 Capstone Documentation & Viva Kit

Complete academic deliverables prepared for thesis submission and technical viva voce:

- 📄 **[Comprehensive Capstone Project Report](docs/capstone_project_report.md):** 14-section formal academic project report with mathematical formulations, architecture diagrams, and full evaluation results.
- 🎓 **[Viva & Technical Defense Master Guide](docs/viva_preparation_master_guide.md):** 5-minute live demonstration script, 45+ in-depth technical viva questions and answers, and trap question defense.
- 📈 **[Power BI Blueprint & DAX Guide](docs/powerbi_dashboard_guide.md):** Star schema diagram, visual layouts, and DAX measures library.
- 🔒 **[Optional Database & Telemetry Guide](docs/optional_integrations.md):** Security, least-privilege roles, and PostgreSQL configuration notes.

---

## ⚖️ Ethics, Privacy & Limitations Notice

- **Non-Diagnostic Nature:** Model predictions are statistical estimates derived from historical cohorts; they are not irrevocable academic diagnoses.
- **Provisional Threshold:** The academic risk cutoff ($\text{Final\_CGPA} < 2.0$) is a capstone project assumption, not an official university policy.
- **Human-in-the-Loop:** All automated recommendations are designed for review in consultation with academic advisers.

---

## 👥 Project Team & Authors

- **Ashok Pradhan** — Database Architecture, PostgreSQL Analytics & Power BI Dashboards
- **Rudraksh Mehra** — Machine Learning Engineering, Model Development & Predictive Analytics
- **Ayush Shukla** — Full-Stack Web Development, Explainable AI (XAI) & Cloud Deployment


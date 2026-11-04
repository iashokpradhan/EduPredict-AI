# EduPredict AI: Student Performance Prediction and Recommendation System
## Final Year Capstone Project Report

**Authors & Project Team:**  
- **Ashok Pradhan** — Database Architecture, PostgreSQL Analytics & Power BI Dashboards  
- **Rudraksh Mehra** — Machine Learning Engineering, Model Development & Predictive Analytics  
- **Ayush Shukla** — Full-Stack Web Development, Explainable AI (XAI) & Cloud Deployment  
**Degree Program:** Bachelor of Technology / Science in Computer Science & Engineering / Data Science  
**Academic Year:** 2026–2027  
**Repository:** [github.com/iashokpradhan/EduPredict-AI](https://github.com/iashokpradhan/EduPredict-AI)  
**System Architecture:** Machine Learning (scikit-learn) + Backend API (FastAPI) + Relational Database (PostgreSQL / SQLite) + Business Intelligence (Power BI) + Interactive Frontend (HTML5 / Vanilla JS)

---

## Executive Summary / Abstract

In modern higher education, timely identification of students requiring academic support is essential to preventing academic probation and attrition. **EduPredict AI** is an end-to-end, production-oriented Data Science application designed to predict student performance (Final CGPA), screen for academic risk (provisional threshold of Final CGPA < 2.0), generate transparent and actionable study-planning recommendations, and provide aggregate cohort intelligence through SQL analytics and Power BI dashboards.

To ensure scientific rigor and eliminate methodological flaws common in academic projects:
1. **Zero Data Leakage:** Features are strictly restricted to inputs available prior to semester completion. Student identifiers and target variables are excluded. Preprocessing transformations (median imputation, one-hot encoding, and standard scaling) are encapsulated inside scikit-learn `Pipeline` and `ColumnTransformer` objects, fitted solely on training splits within 5-fold cross-validation.
2. **Dual Model Paradigms:** Continuous grade estimation is formulated as a regression task (Gradient Boosting Regressor, achieving Test MAE = 0.0965, RMSE = 0.1153, $R^2$ = 0.9536), while severe underperformance is modeled as an experimental classification task (Random Forest Classifier, Recall = 87.5%, ROC-AUC = 0.995).
3. **Decoupled Heuristics:** Advice generation is decoupled from black-box ML outputs, utilizing a deterministic, transparent rules engine and a customizable Pomodoro study planner.
4. **Relational Database & Analytics:** A normalized Third Normal Form (3NF) relational schema stores student records, academic indicators, prediction audits, and recommendations. A comprehensive suite of analytical SQL queries and dedicated Power BI star-schema views deliver institutional insights.
5. **Production Readiness:** The system is served via an asynchronous FastAPI backend, verified by a 44-test automated test suite, and containerized via multi-stage Docker and Docker Compose.

---

## 1. Introduction & Problem Statement

### 1.1 Motivation
Academic institutions routinely collect behavioral and demographic data, such as lecture attendance, study habits, prior academic performance, and personal wellness indicators. However, institutions frequently suffer from the "lagging indicator dilemma": student struggles are only formally identified when end-of-semester exam grades are posted, by which point remedial intervention is too late.

### 1.2 Problem Formulation
Can pre-examination student habits and historical indicators accurately forecast academic performance and detect at-risk students early enough to enable proactive advising?

### 1.3 Project Objectives
- **Data Engineering & Preprocessing:** Clean and structure historical student data, preventing all forms of data leakage.
- **Machine Learning Modeling:** Develop, benchmark, and evaluate regression and classification pipelines against established baselines.
- **Model Explainability:** Interpret feature reliance using Permutation Importance without making false causal claims.
- **Actionable Guidance:** Implement a transparent recommendation engine and weekly study planner.
- **Database Architecture:** Engineer a PostgreSQL / SQLite database supporting transactional prediction logging and analytical queries.
- **Business Intelligence:** Design a multi-page Power BI dashboard with key performance indicators (KPIs) and departmental benchmarks.
- **API & UI Development:** Deploy a FastAPI web service and modern responsive web dashboard.

---

## 2. System Architecture

The EduPredict AI architecture follows a modular, decoupled design separating data ingestion, machine learning inference, persistence, business intelligence, and user presentation:

```mermaid
flowchart TD
    subgraph Data Layer
        CSV["Student Dataset (5,000 Records)"]
        SEED["Seed Module (seed_db.py)"]
        DB[("PostgreSQL / SQLite Database")]
    end

    subgraph Machine Learning Pipeline
        SPLIT["Train/Test Split (80/20)"]
        PIPE["Pipeline & ColumnTransformer"]
        GBR["Gradient Boosting Regressor (Final CGPA)"]
        RFC["Random Forest Classifier (Risk Screening)"]
    end

    subgraph Backend API (FastAPI)
        APP["FastAPI Gateway (api.py)"]
        EP_PRED["POST /api/v1/predict"]
        EP_RISK["POST /api/v1/risk"]
        EP_RECS["POST /api/v1/recommendations"]
        EP_PLAN["POST /api/v1/study-plan"]
        EP_COHORT["GET /api/v1/analytics/cohort"]
        EP_HIST["GET /api/v1/analytics/history"]
    end

    subgraph Presentation & Analytics
        UI["Web Dashboard (index.html)"]
        PBI["Power BI Analytics Dashboard"]
    end

    CSV --> SEED --> DB
    CSV --> SPLIT --> PIPE
    PIPE --> GBR
    PIPE --> RFC

    GBR --> APP
    RFC --> APP
    DB <--> APP

    APP <--> UI
    DB --> PBI
```

---

## 3. Dataset Understanding & Exploratory Data Analysis (EDA)

### 3.1 Data Dictionary & Schema
The dataset consists of 5,000 student records across 10 features:

| Column Name | Data Type | Domain / Range | Role in System | Leakage Consideration |
|---|---|---|---|---|
| `Student_ID` | String | Unique ID | Primary Key | **Excluded** from all models to avoid memorization |
| `Gender` | Categorical | Female, Male | Predictor | Demographic fairness audit |
| `Age` | Integer | 18 – 24 (Mean: 20.9) | Predictor | Age distribution analysis |
| `Major` | Categorical | 6 Majors | Predictor | Program-level segmentation |
| `Attendance_Pct` | Float | 26.2% – 100% (Mean: 83.8%) | Predictor & Rule Input | Available dynamically during term |
| `Study_Hours_Per_Day`| Float | 0.1 – 14.0 (Mean: 4.52 hrs) | Predictor & Rule Input | Self-reported daily study time |
| `Previous_CGPA` | Float | 1.35 – 4.00 (Mean: 3.09) | Predictor | **Must precede** current semester |
| `Sleep_Hours` | Float | 4.0 – 10.0 (Mean: 7.01 hrs) | Predictor & Rule Input | Nightly rest indicator |
| `Social_Hours_Week` | Integer | 0 – 20 (Mean: 8.01 hrs) | Predictor | Weekly social engagement |
| `Final_CGPA` | Float | 1.16 – 4.00 (Mean: 3.27) | **Target** | **Strictly excluded** from model inputs |

### 3.2 Key EDA Findings
1. **Target Distribution:** `Final_CGPA` approximates a normal distribution centered at 3.27 ($SD = 0.51$).
2. **Correlation with Target:** `Previous_CGPA` exhibits the strongest linear correlation ($r \approx 0.95$), followed by `Attendance_Pct` ($r \approx 0.28$) and `Study_Hours_Per_Day` ($r \approx 0.24$).
3. **Severe Class Imbalance in Academic Risk:** Defining at-risk students as $\text{Final\_CGPA} < 2.0$ yields exactly 42 positive cases out of 5,000 (0.84% positive class prevalence).

---

## 4. Feature Engineering & Leakage Safeguards

A core vulnerability in student modeling is **data leakage**. EduPredict AI enforces strict architectural safeguards:

1. **Target Separation:** `Final_CGPA` is isolated before training.
2. **Identifier Exclusion:** Arbitrary identifiers like `Student_ID` are dropped.
3. **Pipeline Encapsulation:**
   - Numerical pipeline: `SimpleImputer(strategy='median')` followed by `StandardScaler()`.
   - Categorical pipeline: `SimpleImputer(strategy='most_frequent')` followed by `OneHotEncoder(handle_unknown='ignore')`.
   - Unified inside `ColumnTransformer`. All scaling parameters ($\mu, \sigma$) and imputation medians are computed **strictly on training folds**. Cross-validation never fits transformations on test folds.

---

## 5. Machine Learning Models & Results

Two distinct machine learning problems were formulated and trained on an 80/20 train/test split.

### 5.1 Task A: Final CGPA Regression
Predicting continuous numerical grade point average ($y \in [0.0, 4.0]$).

#### Models Evaluated (5-Fold Training Cross-Validation):
1. **Baseline:** `DummyRegressor(strategy='mean')`
2. **Linear Models:** Ordinary Least Squares (OLS) Regression, Ridge Regression ($\alpha = 1.0$)
3. **Tree Ensembles:** Random Forest Regressor ($n=200$), Gradient Boosting Regressor ($n=100, \text{learning\_rate}=0.1$)

#### Test Set Evaluation (Held-out 1,000 rows):
| Model | Mean Absolute Error (MAE) | Root Mean Squared Error (RMSE) | $R^2$ Score |
|---|---|---|---|
| Dummy Mean Baseline | 0.4432 | 0.5198 | -0.0012 |
| Linear Regression | 0.0981 | 0.1172 | 0.9521 |
| Ridge Regression | 0.0980 | 0.1171 | 0.9522 |
| Random Forest Regressor | 0.1042 | 0.1251 | 0.9458 |
| **Gradient Boosting Regressor** | **0.0965** | **0.1153** | **0.9536** |

The Gradient Boosting Regressor reduced mean error by 78.2% relative to baseline and was serialized as `final_cgpa_regression.joblib`.

### 5.2 Task B: Academic Risk Classification (Experimental)
Binary classification where $y = 1$ if $\text{Final\_CGPA} < 2.0$ and $0$ otherwise.

Due to extreme class rarity (42 cases total; 34 in training split, 8 in held-out test split), candidate models used `class_weight='balanced'` and Stratified 5-Fold Cross Validation:

| Model | Test Recall | Test Precision | Test F1-Score | ROC-AUC |
|---|---|---|---|---|
| Dummy Majority Baseline | 0.0% | 0.0% | 0.0% | 0.500 |
| Logistic Regression (Balanced) | 87.5% | 21.2% | 34.1% | 0.988 |
| **Random Forest Classifier (Balanced)** | **87.5%** | **28.0%** | **42.4%** | **0.995** |

*Critical Academic Qualification:* The classifier detected 7 out of the 8 held-out at-risk students. However, due to the small sample size (8 cases), this model is explicitly tagged as `experimental_demo_only` in production APIs and documentation.

---

## 6. Model Explainability & Permutation Importance

Using Scikit-Learn's `permutation_importance` on held-out test data:
1. **Previous_CGPA dominates:** Permutation importance shows `Previous_CGPA` accounts for over 85% of score degradation when shuffled.
2. **Scientific Interpretation:** Prior performance is the single strongest statistical signal of future performance in this dataset. However, **correlation does not imply causation**: an adviser cannot simply "change" prior CGPA.
3. **Actionable Levers:** Routine factors (`Attendance_Pct`, `Study_Hours_Per_Day`, `Sleep_Hours`) represent the mutable behaviors where advising interventions can actually be applied.

---

## 7. Recommendation Engine & Study Planner

Rather than displaying unexplained probabilities, EduPredict AI features an interpretable, rules-based advisory system:

### 7.1 Recommendation Rules Engine (`src/recommendations.py`)
- **Rule 1 (Attendance):** Triggers if $\text{Attendance} < 80\%$. Encourages scheduled attendance recovery and advisor consultation.
- **Rule 2 (Study Time):** Triggers if $\text{Study Hours} < 2.0 \text{ hrs/day}$. Suggests breaking study into consistent daily blocks.
- **Rule 3 (Rest Routine):** Triggers if $\text{Sleep Hours} < 6.0 \text{ hrs/day}$. Alerts to sleep deprivation hazards.

### 7.2 Pomodoro Weekly Study Planner (`src/study_planner.py`)
Accepts user-reported available study minutes for each weekday (0 to 480 mins) and optional focus areas. Constructs an automated schedule dividing time into 25-minute focused study sprints followed by 5-minute restorative breaks.

---

## 8. Relational Database Architecture & SQL Analytics

### 8.1 Schema Design (Third Normal Form)
The relational schema comprises:
- `students`: Dimension table (`student_id`, `gender`, `age`, `major`, `created_at`).
- `academic_records`: Performance metrics (`attendance_pct`, `study_hours_per_day`, `previous_cgpa`, `sleep_hours`, `social_hours_week`, `final_cgpa`).
- `predictions`: Transactional inference log (`predicted_cgpa`, `risk_probability`, `risk_label`, `created_at`).
- `recommendations_log`: Guidance audit trail (`rule_id`, `title`, `action`, `why`).
- `usage_events`: System telemetry log.

### 8.2 Analytical Insights from SQL Queries
- **Performance by Major:** Psychology (Avg CGPA 3.29) and Mathematics (3.28) rank highest; Business and Engineering average 3.26. Variance across majors is modest ($<0.04$ CGPA points).
- **Attendance Tiers:** Students with $\ge 90\%$ attendance achieve an average CGPA of 3.48 with 0% risk rate. Students with $<70\%$ attendance average 2.74 with a 5.6% risk rate.
- **Sleep Window:** Maximum average CGPA (3.32) occurs in the 7–8 hour nightly sleep window; students sleeping $<5$ hours average 3.11.

---

## 9. Web Application & API Integration

- **FastAPI Backend (`src/api.py`):**
  - High performance asynchronous Python API.
  - Pydantic models validate all incoming payloads (e.g., rejecting out-of-bounds GPA $>4.0$, hours $>24$).
  - Endpoints: `/api/v1/health`, `/api/v1/predict`, `/api/v1/risk`, `/api/v1/recommendations`, `/api/v1/study-plan`, `/api/v1/analytics/cohort`, `/api/v1/analytics/history`, `/api/v1/presets`.
- **Interactive UI (`frontend/index.html`):**
  - Modern HTML5/CSS3/Vanilla JavaScript dashboard without heavy framework dependencies.
  - Features 1-click persona presets (High Achiever, Balanced Average, Academic At-Risk, Sleep Deprived).
  - Visual CGPA meter, risk severity bar, cohort benchmark comparison bars, weekly timetable planner, and live database analytics tabs.

---

## 10. Verification, Testing & Quality Assurance

The codebase includes 44 automated tests executed with Python's standard `unittest` framework:
- **30 Unit Tests (`tests/unit/`):** Test model building from synthetic fixtures, input range validation, recommendation threshold rules, planner math, frontend XSS protection (verifying `innerHTML` absence), and database operations.
- **14 Integration Tests (`tests/integration/`):** Validate dataset schema integrity, verify that model scaler weights match training split means, test API lifecycles, and confirm HTTP 422 rejections on target-leaking fields.

**All 44 tests pass with 0 errors.**

---

## 11. Ethical Considerations & Limitations

1. **Non-Diagnostic Nature:** Predictions are statistical estimates, not academic diagnoses or deterministic forecasts.
2. **Provisional Risk Threshold:** Final CGPA $< 2.0$ was established as a project benchmark, not official university policy.
3. **Data Provenance:** The 5,000-row dataset exhibits strong synthetic/regular properties. Real-world institutional deployment requires pilot studies on institution-verified cohorts.
4. **Intervention Ethics:** Predictions must never be used punitively (e.g., denying enrollment); they should exclusively trigger supportive advising.

---

## 12. Conclusion & Future Work

EduPredict AI successfully demonstrates that an end-to-end Data Science application requires more than just high machine learning scores: it demands data leakage prevention, software engineering discipline, relational database integrity, actionable advisory logic, and business intelligence reporting.

### Future Enhancements:
- Direct LMS integration (Canvas / Blackboard LTI API).
- SHAP / TreeSHAP local waterfall explainability plots in the UI.
- Secure Role-Based Access Control (RBAC) separating Student and Advisor views.

# EduPredict AI — Capstone Defense Presentation Deck

**Presentation Title:** EduPredict AI: Student Performance Prediction and Recommendation System  
**Presenter:** Ashok Pradhan  
**Degree:** Final Year B.Tech / B.S. in Computer Science / Data Science  
**Format:** 12-Slide Defense Deck with Visuals & Speaker Notes  

---

## Slide 1: Title & Executive Overview
- **Title:** EduPredict AI: Student Performance Prediction & Support System
- **Subtitle:** An End-to-End Data Science Application Combining Leakage-Aware Machine Learning, Relational Analytics, and Decision Support
- **Presenter:** Ashok Pradhan
- **Date & Academic Year:** 2026–2027
> **Speaker Notes:**  
> "Good morning, respected professors. Today I am presenting my final-year capstone project, EduPredict AI. This project addresses a fundamental challenge in higher education: identifying students who need academic support before semester finals, rather than after the grades are already posted."

---

## Slide 2: Problem Statement & Motivation
- **The Lagging Indicator Problem:** University grades arrive at the end of the term when remedial intervention is too late.
- **The Core Question:** Can pre-examination behavioral habits (attendance, study hours, sleep, prior GPA) reliably forecast academic outcomes and detect at-risk students?
- **Our Solution:** A proactive decision-support system that provides grade forecasts, risk classification, Pomodoro study planning, and institutional cohort analytics.
> **Speaker Notes:**  
> "Currently, most universities operate reactively. EduPredict AI transforms raw academic data into early warning signals, empowering academic advisers and students to take corrective action early in the semester."

---

## Slide 3: System Architecture & Workflow
- **Data Ingestion:** 5,000 student records with demographic, behavioral, and academic features.
- **Preprocessing & Modeling:** Scikit-Learn `Pipeline` & `ColumnTransformer` (zero data leakage).
- **Backend API:** Asynchronous FastAPI service handling predictions, simulations, and telemetry.
- **Database Layer:** 3NF PostgreSQL schema with SQLite local fallback.
- **Reporting & UI:** Interactive web dashboard and Power BI Star Schema reporting.
> **Speaker Notes:**  
> "Our architecture separates data ingestion, machine learning inference, transactional persistence, and business intelligence. Each layer is decoupled and production-ready."

---

## Slide 4: Data Engineering & Zero-Leakage Safeguards
- **10 Features Analyzed:** Attendance, Daily Study Hours, Prior CGPA, Sleep, Social Hours, Age, Gender, Major, Student ID, and Final CGPA.
- **Leakage Elimination:**
  - `Student_ID` excluded to avoid memorization.
  - `Final_CGPA` isolated prior to any transformations.
  - Median imputation and standard scaling fitted **strictly on training splits** within 5-fold cross-validation.
> **Speaker Notes:**  
> "A major failure mode in academic ML projects is data leakage. We ensured that no test set information, scaling parameters, or outcome variables ever leaked into the training folds."

---

## Slide 5: Machine Learning Methodology & Dual Formulation
- **Continuous Performance (Regression):**
  - Predicting continuous Final CGPA ($\in [0.0, 4.0]$).
  - Evaluated: Dummy Baseline, OLS Linear Regression, Ridge, Random Forest, and Gradient Boosting.
- **Severe Underperformance (Classification):**
  - Screening for academic probation ($\text{Final\_CGPA} < 2.0$).
  - Evaluated: Dummy Majority, Class-Weighted Logistic Regression, Class-Weighted Random Forest.
> **Speaker Notes:**  
> "We formulated two separate learning tasks: continuous CGPA prediction for general progress tracking, and class-weighted risk classification to address the rare at-risk cohort."

---

## Slide 6: Model Evaluation & Results
- **Regression Winner — Gradient Boosting Regressor:**
  - **Test MAE:** 0.0965 CGPA points (78.2% error reduction vs. 0.4432 baseline).
  - **Test RMSE:** 0.1153 | **Test $R^2$:** 0.9536.
- **Classification Winner — Class-Weighted Random Forest:**
  - **Test Recall:** 87.5% (Caught 7 of 8 held-out at-risk students).
  - **Test ROC-AUC:** 0.995 | **Test Precision:** 28.0%.
  - *Honest Disclosure:* Tagged as experimental due to small positive sample size (8 test cases).
> **Speaker Notes:**  
> "The Gradient Boosting Regressor achieved outstanding accuracy with a 0.096 MAE. On the classification side, our model caught 7 out of 8 at-risk students, delivering the high recall essential for early intervention."

---

## Slide 7: Model Explainability & Permutation Importance
- **Permutation Importance Hierarchy:**
  1. `Previous_CGPA` (86.4% relative importance — historical baseline)
  2. `Attendance_Pct` (7.8% relative importance — primary actionable lever)
  3. `Study_Hours_Per_Day` (4.1% relative importance — academic preparation lever)
  4. `Sleep_Hours` (1.2% relative importance — cognitive well-being)
  5. `Social_Hours_Week` (0.5% relative importance — balance)
- **Key Takeaway:** Prior CGPA is the strongest statistical signal, but attendance and daily study are the mutable behaviors where intervention actually works.
> **Speaker Notes:**  
> "Permutation importance shows that while prior CGPA sets the baseline, attendance and study hours are the primary levers advisers can influence to change a student's trajectory."

---

## Slide 8: Interactive "What-If" Academic Simulator
- **From Prediction to Action:** Moving beyond static numbers.
- **Real-Time Sensitivity Sliders:**
  - Attendance Boost (+5% to +30%)
  - Daily Study Boost (+0.5h to +4.0h)
- **Live Output:** Immediate re-calculation of predicted CGPA gain and risk reduction.
> **Speaker Notes:**  
> "A key innovation in EduPredict AI is the What-If Simulator. If an at-risk student increases attendance by 15% and studies 1.5 hours more per day, the simulator shows their predicted CGPA improving from 1.95 to 2.32, moving them out of academic danger."

---

## Slide 9: Recommendation Engine & Pomodoro Study Planner
- **Rule-Based Guidance:** Explicit heuristics triggered on attendance (<80%), study time (<2.0h), and sleep (<6.0h).
- **Pomodoro Study Planner:** Creates 25-minute focused study sprints with 5-minute restorative breaks.
- **Calendar Integration:** 1-click export of scheduled study blocks into `.ics` format for Google Calendar and Outlook.
> **Speaker Notes:**  
> "Rather than using an ungrounded LLM, our recommendation engine uses transparent heuristics, and our planner generates Pomodoro study blocks that students can export directly to their phone's calendar."

---

## Slide 10: Relational Database & SQL Analytics
- **Normalized Schema (3NF):** Tables for `students`, `academic_records`, `predictions`, `recommendations_log`, and `usage_events`.
- **Institutional SQL Insights:**
  - *Attendance Quartiles:* $\ge 90\%$ attendance averages 3.48 CGPA vs. $<70\%$ attendance averaging 2.74 (5.6% risk rate).
  - *Departmental Parity:* Average CGPA across all 6 majors ranges tightly between 3.25 and 3.29.
  - *Sleep Curve:* Peak average CGPA (3.32) occurs at 7–8 hours of sleep; $<5$ hours drops to 3.11.
> **Speaker Notes:**  
> "Our relational database logs every inference and powers SQL queries that reveal institutional patterns, such as the direct empirical correlation between attendance tiers and grade outcomes."

---

## Slide 11: Power BI Analytics & Star Schema
- **Dedicated Data Model:** Central `Fact_Academic_Records` connected to `Dim_Students` and `Dim_Majors_Summary`.
- **Pre-Calculated DAX Library:** Total Students, Avg CGPA, At-Risk Rate %, Honors Classifications, and Dynamic HEX Alert Colors.
- **Institutional Dashboard Pages:**
  - Page 1: Executive Academic Overview
  - Page 2: Performance Drivers & Behavioral Correlations
  - Page 3: Student Well-being & Optimal Sleep Curve
  - Page 4: Early Intervention Watchlist
> **Speaker Notes:**  
> "For university leadership, our exported Star Schema tables connect seamlessly into Power BI to provide high-level executive dashboards and early intervention watchlists."

---

## Slide 12: Conclusion & Future Scope
- **Key Achievements:**
  - End-to-end data science application: Data → ML → API → Database → Power BI → UI.
  - 46 automated tests ensuring zero regressions.
  - Production-grade Docker & Docker Compose containerization.
- **Future Enhancements:**
  - Direct Canvas / Blackboard LMS API integration.
  - Longitudinal cohort tracking across multiple university semesters.
> **Speaker Notes:**  
> "EduPredict AI proves that a successful capstone project requires machine learning rigor, software engineering discipline, and practical institutional utility. Thank you, and I look forward to your questions."

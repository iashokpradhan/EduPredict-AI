# EduPredict AI — Viva and Methodology Guide

## Abstract

EduPredict AI is a student-support prototype that uses historical academic and routine information to estimate a student's final CGPA and demonstrate a separate academic-risk classification task. The project uses leakage-aware preprocessing pipelines, compares regression and classification baselines with stronger models, and evaluates the selected experiments on held-out data. A transparent rules engine turns routine inputs into optional study suggestions, and a local API/dashboard demonstrates the workflow. The local dataset source and license have not been verified. Dataset-derived results are omitted from the code-only release and must not be treated as evidence of performance at a real institution. A low-CGPA risk label uses an explicitly provisional threshold of 2.0 on a 0-4 scale. Recommendations are rules-based, and the weekly planner is deterministic rather than generative.

## Problem statement and objectives

Students and advisers may benefit from an early, understandable summary of academic patterns. This project explores whether the provided inputs can predict `Final_CGPA`, demonstrates a separate threshold-based risk estimate, and offers transparent planning suggestions. Objectives:

1. Inspect and prepare the provided student dataset reproducibly.
2. Compare regression candidates against a simple baseline using training-only cross-validation and held-out metrics.
3. Explore a separate, clearly qualified risk-classification task.
4. Explain model evaluation and global feature reliance without implying causation.
5. Demonstrate rule-based suggestions and a local API/dashboard while keeping prediction and advice distinct.

## Scope and methodology

The expected project schema has 10 columns; the authorized source and its provenance must be verified before use. `Final_CGPA` is the regression target. `Student_ID` is excluded from predictors. The remaining eight predictors are six numeric fields (`Age`, `Attendance_Pct`, `Study_Hours_Per_Day`, `Previous_CGPA`, `Sleep_Hours`, `Social_Hours_Week`) and two categorical fields (`Gender`, `Major`).

Rows are split into training and test portions before preprocessing. Numerical values use median imputation and standardization; categorical values use most-frequent imputation and one-hot encoding. The `ColumnTransformer` is inside a scikit-learn `Pipeline`, so each cross-validation fold learns preprocessing from its own training fold only.

The regression target is continuous. Candidate models were Dummy mean, Linear Regression, Ridge, Random Forest, and Gradient Boosting. Five-fold shuffled cross-validation on the training split selects by mean MAE; the held-out test split is reserved for final evaluation.

Classification labels are `1` when `Final_CGPA < 2.0` and `0` otherwise. The cutoff is a project assumption, not a verified institutional standard. A separate stratified split preserves the rare positive class. The target and label are excluded from inputs. Candidate classifiers were a majority-class dummy, class-weighted Logistic Regression, and class-weighted Random Forest. Selection prioritizes at-risk recall, then F1 and precision. The classifier remains experimental; the number of positive examples must be checked for each authorized dataset.

## Dataset-specific results

Numeric metrics, charts, and dataset-derived findings are intentionally omitted from this code-only release because source, license, and disclosure permissions are unverified. After obtaining authorization, rerun the modelling and evaluation notebooks locally, review the results for privacy and policy implications, and only then add approved results to public documentation.

## Data dictionary

| Field | Meaning used in this project | Role |
|---|---|---|
| `Student_ID` | Record identifier | Excluded from model inputs |
| `Gender` | Categorical demographic value | Candidate input |
| `Age` | Age in years (interpreted from field name/data) | Candidate input |
| `Major` | Academic major | Candidate input |
| `Attendance_Pct` | Attendance percentage | Candidate input and rule input |
| `Study_Hours_Per_Day` | Study hours per day | Candidate input and rule input |
| `Previous_CGPA` | Prior CGPA on a 0-4 scale | Candidate input if known before prediction |
| `Sleep_Hours` | Sleep hours per day | Candidate input and rule input |
| `Social_Hours_Week` | Social hours per week | Candidate input |
| `Final_CGPA` | Final CGPA on a 0-4 scale | Regression target; source of risk label only |

Units and collection timing should be verified with the dataset owner. `Previous_CGPA` must precede the outcome period to be usable at prediction time.

## Limitations and ethical considerations

- Dataset provenance, collection process, consent, and license are unverified. Synthetic data can encode artificial relationships.
- A random split from one dataset does not establish transfer to new students, terms, or institutions.
- Strong `Previous_CGPA` dependence may dominate prediction. It is valid only if available before the forecast outcome.
- The risk threshold is not an official policy. Rare positive cases make recall, precision, and group rates unstable.
- False positives may create unnecessary concern; false negatives may delay support. Human review and context are essential.
- Recommendations use configurable heuristics and are not medical advice or guarantees. The deterministic weekly schedule is a template, not GenAI.
- The regression pipeline is saved for local demonstration; the risk pipeline is explicitly experimental. Neither is a validated decision system.

## Likely viva questions and short answers

1. **Why is this both regression and classification?** Regression predicts a numeric CGPA. Classification answers a different question: whether the target is below a chosen cutoff. The labels and evaluations are separate.
2. **Why exclude Student_ID?** It identifies a row but does not describe student performance. Including arbitrary IDs can let a model memorize accidental patterns.
3. **What is data leakage?** Leakage is when training uses information that would not be available at prediction time, or information from evaluation data. It makes results look better than a fair future test.
4. **How did you prevent preprocessing leakage?** The split occurs first. Imputers, scaling, and category encoders are inside each model pipeline, so cross-validation fits them only on each fold's training rows.
5. **Why is Previous_CGPA allowed?** It is a prior result and can be used if it is already known before the final CGPA being predicted. If recorded later, it would leak future information.
6. **What does five-fold cross-validation do?** It rotates which training fold validates a model across five runs and summarizes variation. The final test split stays separate until model selection is complete.
7. **Why compare with DummyRegressor?** It establishes a simple reference. A model should improve on a basic mean prediction, not merely report a positive R-squared.
8. **What is MAE?** Mean absolute error is the average absolute prediction error, in CGPA points. It is easy to interpret and less sensitive to large errors than RMSE.
9. **What is RMSE?** Root mean squared error squares errors before averaging, so large misses contribute more. It is also measured in CGPA points.
10. **What does R-squared mean?** It compares squared prediction error with a constant-mean baseline. One is perfect, zero is baseline-like, and a negative value is worse than that baseline.
11. **Why not use accuracy for risk classification?** When positive labels are rare, always predicting the majority class can appear accurate while missing every at-risk case. Recall, precision, F1, and confusion counts reveal that tradeoff.
12. **What is precision versus recall?** Precision is the share of flagged cases that are positive. Recall is the share of positive cases the model finds. Raising recall often increases false positives.
13. **Is 2.0 an official academic warning threshold?** No. It is a project assumption for demonstrating a separate classification task. A real application needs a verified institution-specific definition.
14. **Why is the risk model experimental?** The positive class is rare in the current local dataset. Performance estimates can change substantially when only a few positive cases differ; report the actual class counts for each authorized dataset.
15. **Does feature importance show what causes CGPA to change?** No. Permutation importance shows how much this fitted model relies on a feature in this evaluation sample. It is not causal evidence.
16. **Why is Previous_CGPA importance a concern?** It may dominate the model because it is closely associated with the outcome. That can be useful as a prior signal, but its timing must be correct and the result needs external validation.
17. **Why did you not clip predictions to 0-4?** Clipping changes predictions and can hide model behavior. The notebook reports how often outputs are outside the observed range so bounded methods can be evaluated explicitly later.
18. **Is the study planner Generative AI?** No. The current planner is a deterministic template. No LLM API, key, external call, or paid service is configured.
19. **What is the difference between model output and recommendation?** The model provides an estimate from learned patterns. The recommendation engine uses explicit rules on routine inputs. A suggestion does not explain or guarantee a predicted CGPA.
20. **What would you improve next?** Verify data provenance and policy, obtain representative cohorts, evaluate on a later-term holdout, improve rare-class evidence, assess calibration and subgroup stability, and conduct human review before real use.

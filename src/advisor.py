"""Academic Counselor & Curriculum-Tailored Recovery Planner.

Provides:
- 4-week structured academic recovery roadmaps tailored to the student's
  declared major and detected behavioral weaknesses (low attendance, study
  deficit, cognitive fatigue / sleep imbalance).
- Deterministic offline counselor (always available, zero external dependency).
- Optional LLM augmentation when an authorized API key is provided.
"""

from __future__ import annotations

import os
from typing import Any


MAJOR_CURRICULUM_ROADMAPS: dict[str, list[dict[str, Any]]] = {
    "Computer Science": [
        {
            "week": 1,
            "theme": "Core Foundations & Algorithmic Complexity",
            "milestone": "Master Big-O analysis and linear data structures (Linked Lists, Stacks, Queues).",
            "recommended_modules": ["Data Structures Review", "Algorithm Time/Space Profiling"],
            "hours_target": 12,
        },
        {
            "week": 2,
            "theme": "Non-Linear Structures & Recursion",
            "milestone": "Implement Binary Search Trees, Heaps, and graph traversal (BFS/DFS).",
            "recommended_modules": ["Tree & Graph Traversals", "Divide & Conquer Practice"],
            "hours_target": 14,
        },
        {
            "week": 3,
            "theme": "Dynamic Programming & Optimization",
            "milestone": "Solve 10 classic memoization and tabulation problems.",
            "recommended_modules": ["Dynamic Programming Paradigms", "Database Indexing & Queries"],
            "hours_target": 15,
        },
        {
            "week": 4,
            "theme": "Systems Integration & Exam Simulation",
            "milestone": "Complete 2 timed past exam papers with zero notes.",
            "recommended_modules": ["Full-Stack / Systems Synthesis", "Mock Examination Review"],
            "hours_target": 12,
        },
    ],
    "Engineering": [
        {
            "week": 1,
            "theme": "Differential Equations & Mathematical Modeling",
            "milestone": "Review 2nd-order ODEs and Laplace Transforms applied to physical systems.",
            "recommended_modules": ["Advanced Engineering Mathematics", "Calculus III Review"],
            "hours_target": 14,
        },
        {
            "week": 2,
            "theme": "Thermodynamics & Energy Balance",
            "milestone": "Complete 15 closed/open system energy conservation problems.",
            "recommended_modules": ["First & Second Law Formulation", "Phase Diagrams & Steam Tables"],
            "hours_target": 15,
        },
        {
            "week": 3,
            "theme": "Fluid Dynamics & Statics",
            "milestone": "Derive Navier-Stokes simplifications and pipe head loss calculations.",
            "recommended_modules": ["Bernoulli Energy Equation", "Stress-Strain Mechanical Analysis"],
            "hours_target": 15,
        },
        {
            "week": 4,
            "theme": "Design Verification & Practical Lab Synthesis",
            "milestone": "Synthesize design reports and practice comprehensive problem sets.",
            "recommended_modules": ["Computer-Aided Modeling", "Comprehensive Final Exam Prep"],
            "hours_target": 12,
        },
    ],
    "Business": [
        {
            "week": 1,
            "theme": "Financial Accounting & Ratio Analysis",
            "milestone": "Analyze cash flow, balance sheets, and working capital for 3 sample firms.",
            "recommended_modules": ["Financial Statement Modeling", "Working Capital Optimization"],
            "hours_target": 10,
        },
        {
            "week": 2,
            "theme": "Microeconomic Decision Models",
            "milestone": "Master cost curves, marginal revenue calculations, and pricing power.",
            "recommended_modules": ["Elasticity & Market Structures", "Pricing Strategy Frameworks"],
            "hours_target": 12,
        },
        {
            "week": 3,
            "theme": "Operations Research & Quantitative Methods",
            "milestone": "Formulate linear programming optimization models and queueing equations.",
            "recommended_modules": ["Supply Chain Optimization", "Managerial Decision Analytics"],
            "hours_target": 12,
        },
        {
            "week": 4,
            "theme": "Strategic Case Study & Executive Presentation",
            "milestone": "Draft executive brief addressing competitive advantage under uncertainty.",
            "recommended_modules": ["Capstone Case Deconstruction", "Final Synthesis Presentation"],
            "hours_target": 10,
        },
    ],
    "Psychology": [
        {
            "week": 1,
            "theme": "Research Methods & Statistical Design",
            "milestone": "Review ANOVA, regression interpretations, and effect sizes (Cohen's d).",
            "recommended_modules": ["Inferential Statistics for Behavioral Science", "Experimental Controls"],
            "hours_target": 10,
        },
        {
            "week": 2,
            "theme": "Cognitive Neuroscience & Memory Systems",
            "milestone": "Map working memory models and neural pathways of attention and executive control.",
            "recommended_modules": ["Atkinson-Shiffrin Model Review", "Neuroimaging Case Studies"],
            "hours_target": 12,
        },
        {
            "week": 3,
            "theme": "Developmental & Clinical Assessment",
            "milestone": "Examine psychometric instruments and diagnostic classification criteria.",
            "recommended_modules": ["Psychopathology Frameworks", "Behavioral Intervention Evidence"],
            "hours_target": 12,
        },
        {
            "week": 4,
            "theme": "Literature Synthesis & Empirical Defense",
            "milestone": "Synthesize 10 peer-reviewed journal articles into an integrated literature matrix.",
            "recommended_modules": ["Systematic Review Writing", "Mock Final Assessment"],
            "hours_target": 10,
        },
    ],
    "Economics": [
        {
            "week": 1,
            "theme": "Econometrics & Multiple Regression",
            "milestone": "Verify Gauss-Markov assumptions, test for heteroscedasticity and multicollinearity.",
            "recommended_modules": ["OLS Regression Diagnostics", "Stata/R Data Analysis"],
            "hours_target": 14,
        },
        {
            "week": 2,
            "theme": "Macroeconomic Equilibrium & Fiscal Policy",
            "milestone": "Solve IS-LM and AD-AS dynamic equilibrium shifts under central bank regimes.",
            "recommended_modules": ["Monetary Transmission Channels", "Open Economy Trade Balances"],
            "hours_target": 14,
        },
        {
            "week": 3,
            "theme": "Game Theory & Strategic Interaction",
            "milestone": "Compute Nash equilibria in simultaneous and sequential game matrices.",
            "recommended_modules": ["Subgame Perfect Equilibrium", "Oligopoly & Auction Theory"],
            "hours_target": 12,
        },
        {
            "week": 4,
            "theme": "Policy Paper & Final Synthesis",
            "milestone": "Conduct empirical policy evaluation using diff-in-diff methodology.",
            "recommended_modules": ["Applied Policy Evaluation", "Comprehensive Theory Review"],
            "hours_target": 12,
        },
    ],
}


def build_counselor_recovery_plan(student_features: dict[str, Any]) -> dict[str, Any]:
    """Generate a 4-week structured recovery roadmap tailored to the student."""
    major = str(student_features.get("Major", "Computer Science"))
    base_roadmap = MAJOR_CURRICULUM_ROADMAPS.get(major, MAJOR_CURRICULUM_ROADMAPS["Computer Science"])

    attendance = float(student_features.get("Attendance_Pct", 80))
    study_hrs = float(student_features.get("Study_Hours_Per_Day", 3.0))
    sleep_hrs = float(student_features.get("Sleep_Hours", 7.0))
    prev_cgpa = float(student_features.get("Previous_CGPA", 3.0))

    # Identify primary vulnerability levers
    vulnerabilities: list[str] = []
    custom_guidance: list[str] = []

    if attendance < 75.0:
        vulnerabilities.append("Critical attendance deficit (< 75% threshold)")
        custom_guidance.append(
            f"Attendance ({attendance:.1f}%) is in the danger zone. Commit to attending 100% of lectures in weeks 1-2 to regain course momentum."
        )

    if study_hrs < 2.5:
        vulnerabilities.append("Low daily study volume (< 2.5 hrs/day)")
        custom_guidance.append(
            f"Currently averaging {study_hrs:.1f}h daily study. Ramp up by +1.5h using Pomodoro blocks (25m study / 5m break)."
        )

    if sleep_hrs < 6.0:
        vulnerabilities.append("Chronic sleep deficit (< 6.0 hrs/night)")
        custom_guidance.append(
            f"Sleep ({sleep_hrs:.1f}h) impairs memory consolidation. Set a fixed 11:00 PM digital curfew to secure 7+ hours."
        )

    if prev_cgpa < 2.5:
        vulnerabilities.append("Historical GPA vulnerability (< 2.50)")
        custom_guidance.append(
            "Schedule an office-hours diagnostic with teaching assistants during Week 1 to identify foundational syllabus gaps."
        )

    if not vulnerabilities:
        vulnerabilities.append("No critical risk factors — trajectory is well balanced.")
        custom_guidance.append("Maintain existing academic routine; focus on honors-tier distinction modules.")

    # Tailor weekly action items
    enriched_schedule: list[dict[str, Any]] = []
    for item in base_roadmap:
        week_num = item["week"]
        plan_item = {
            "week": week_num,
            "theme": item["theme"],
            "primary_milestone": item["milestone"],
            "recommended_modules": item["recommended_modules"],
            "target_study_hours": item["hours_target"],
            "habits_focus": (
                "Attendance & TA Office Hours"
                if week_num == 1
                else "Pomodoro Consistency & Active Recall"
                if week_num == 2
                else "Problem Sets & Group Study Review"
                if week_num == 3
                else "Timed Mock Exams & Rest Integrity"
            ),
        }
        enriched_schedule.append(plan_item)

    return {
        "status": "ready",
        "engine": "Curriculum-Tailored Rule-Based Academic Counselor",
        "student_major": major,
        "diagnosed_vulnerabilities": vulnerabilities,
        "counselor_guidance_notes": custom_guidance,
        "four_week_curriculum_roadmap": enriched_schedule,
        "disclaimer": (
            "This counselor plan provides evidence-based study guidance aligned with typical degree milestones. "
            "It is intended to support, not replace, university academic advising."
        ),
    }

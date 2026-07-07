"""
sample_datasets.py

Sample datasets for testing chart_planner.py + report_composer.py against
the new features: explicit user_instructions, pagination for large category
sets (start_index/end_index), and unstructured/aggregate-style data without
raw ID columns.
"""

import random

random.seed(42)  # reproducible "random" data across runs

# ---------------------------------------------------------------------------
# 1. No explicit instructions, no IDs — department-wise average GPA
#    Small category count (5) — should NOT trigger pagination.
# ---------------------------------------------------------------------------
DATASET_DEPT_AVG_GPA = {
    "user_instructions": "show average gpa department wise",
    "report_type": "generic",
    "data": [
        {"department": "Computer Science", "average_gpa": 8.12, "student_count": 142},
        {"department": "Electronics", "average_gpa": 7.65, "student_count": 98},
        {"department": "Mechanical", "average_gpa": 7.30, "student_count": 76},
        {"department": "Civil", "average_gpa": 6.95, "student_count": 54},
        {"department": "Electrical", "average_gpa": 7.88, "student_count": 61},
    ],
}


# ---------------------------------------------------------------------------
# 2. EXPLICIT chart instruction — line chart, specific axes named
#    Tests RULE 0 — the LLM must use "line" with these exact axes,
#    not substitute its own judgment.
# ---------------------------------------------------------------------------
DATASET_EXPLICIT_LINE_CHART = {
    "user_instructions": "Show me a line chart with admission year on x-axis and average gpa on y-axis",
    "report_type": "generic",
    "data": [
        {"admissionYear": 2019, "avgGPA": 7.42, "totalStudents": 40},
        {"admissionYear": 2020, "avgGPA": 7.61, "totalStudents": 55},
        {"admissionYear": 2021, "avgGPA": 7.85, "totalStudents": 62},
        {"admissionYear": 2022, "avgGPA": 7.30, "totalStudents": 70},
        {"admissionYear": 2023, "avgGPA": 8.02, "totalStudents": 85},
        {"admissionYear": 2024, "avgGPA": 8.15, "totalStudents": 91},
    ],
}


# ---------------------------------------------------------------------------
# 3. EXPLICIT chart type only, axes NOT specified — LLM must infer axes
#    Tests the "chart type explicit, axes inferred" mid-ground case.
# ---------------------------------------------------------------------------
DATASET_EXPLICIT_PIE_ONLY = {
    "user_instructions": "give me a pie chart for grade distribution",
    "report_type": "generic",
    "data": [
        {"course_name": "Data Structures", "grade": "O"},
        {"course_name": "Data Structures", "grade": "A+"},
        {"course_name": "Data Structures", "grade": "A"},
        {"course_name": "Data Structures", "grade": "A"},
        {"course_name": "Data Structures", "grade": "B+"},
        {"course_name": "Data Structures", "grade": "B"},
        {"course_name": "Data Structures", "grade": "O"},
        {"course_name": "Data Structures", "grade": "C"},
        {"course_name": "Data Structures", "grade": "F"},
        {"course_name": "Data Structures", "grade": "A+"},
        {"course_name": "Data Structures", "grade": "B"},
        {"course_name": "Data Structures", "grade": "A"},
    ],
}


# ---------------------------------------------------------------------------
# 4. Explicit bar chart with named axes, aggregation implied by wording
#    Tests: does the LLM correctly set aggregation="sum" because the user
#    said "total", rather than defaulting to "none" or "count"?
# ---------------------------------------------------------------------------
DATASET_EXPLICIT_BAR_TOTAL_CREDITS = {
    "user_instructions": "give me a bar chart showing total credits per department",
    "report_type": "generic",
    "data": [
        {"department": "Computer Science", "course_name": "Data Structures", "credits": 4},
        {"department": "Computer Science", "course_name": "Operating Systems", "credits": 4},
        {"department": "Computer Science", "course_name": "Database Management", "credits": 3},
        {"department": "Electronics", "course_name": "Digital Electronics", "credits": 3},
        {"department": "Electronics", "course_name": "Signals and Systems", "credits": 4},
        {"department": "Mechanical", "course_name": "Engineering Mechanics", "credits": 3},
        {"department": "Mechanical", "course_name": "Thermodynamics", "credits": 4},
        {"department": "Civil", "course_name": "Structural Analysis", "credits": 3},
    ],
}


# ---------------------------------------------------------------------------
# 5. LARGE dataset, no explicit instructions, many categories (120)
#    This is the pagination stress test — should trigger start_index/
#    end_index chart splitting per rule 7, into 3 charts (0-50, 50-100,
#    100-120), while the table still contains all 120 rows.
# ---------------------------------------------------------------------------
_department_names = [f"Department {i:03d}" for i in range(1, 121)]
DATASET_LARGE_DEPARTMENT_HEADCOUNT = {
    "user_instructions": "show department wise student headcount",
    "report_type": "generic",
    "data": [
        {"department": name, "student_count": random.randint(3, 150)}
        for name in _department_names
    ],
}


# ---------------------------------------------------------------------------
# 6. LARGE dataset, explicit "top N" instruction — should use top_n,
#    NOT pagination, since the user explicitly wants a limited subset.
# ---------------------------------------------------------------------------
DATASET_LARGE_TOP_10_EXPLICIT = {
    "user_instructions": "show me the top 10 departments with highest average gpa",
    "report_type": "generic",
    "data": [
        {"department": f"Department {i:03d}", "average_gpa": round(random.uniform(5.5, 9.9), 2)}
        for i in range(1, 81)
    ],
}


# ---------------------------------------------------------------------------
# 7. LARGE flat student-level dataset WITHOUT ids — 200 individual
#    enrollment-style records, no explicit instructions. Tests whether
#    the planner picks sensible aggregation (e.g. count by grade, or
#    avg gpa by department) rather than trying to plot all 200 raw rows
#    directly as individual bars (which would be unreadable).
# ---------------------------------------------------------------------------
_grades = ["O", "A+", "A", "B+", "B", "C", "F"]
_departments = ["Computer Science", "Electronics", "Mechanical", "Civil", "Electrical"]
DATASET_LARGE_ENROLLMENTS_NO_ID = {
    "user_instructions": "",
    "report_type": "enrollments",
    "data": [
        {
            "student_name": f"Student {i}",
            "department": random.choice(_departments),
            "course_name": random.choice(["Data Structures", "Operating Systems", "Database Management", "Digital Electronics"]),
            "grade": random.choice(_grades),
            "semester": random.choice(["Odd", "Even"]),
        }
        for i in range(1, 201)
    ],
}


# ---------------------------------------------------------------------------
# 8. No explicit instructions, unstructured aggregate — pass percentage
#    per course. Tests rule 6's pie-chart-misuse guard (should be bar,
#    not pie, since percentages aren't parts of one whole here).
# ---------------------------------------------------------------------------
DATASET_PASS_PERCENTAGE = {
    "user_instructions": "",
    "report_type": "generic",
    "data": [
        {"course": "Data Structures", "pass_percentage": 78.5, "total_enrolled": 120},
        {"course": "Operating Systems", "pass_percentage": 82.1, "total_enrolled": 95},
        {"course": "Database Management", "pass_percentage": 91.3, "total_enrolled": 110},
        {"course": "Digital Electronics", "pass_percentage": 65.4, "total_enrolled": 88},
        {"course": "Thermodynamics", "pass_percentage": 73.9, "total_enrolled": 76},
    ],
}


# ---------------------------------------------------------------------------
# 9. Single record, no explicit instructions — should skip charts entirely
# ---------------------------------------------------------------------------
DATASET_SINGLE_RECORD = {
    "user_instructions": "",
    "report_type": "generic",
    "data": [
        {"name": "Pooja Ravichandran", "department": "Computer Science", "gpa": 9.90, "admission_year": 2019},
    ],
}


# ---------------------------------------------------------------------------
# 10. Explicit horizontal_bar with named axes on a moderately large set
#     (25 categories) — should honor the explicit chart type WITHOUT
#     triggering pagination, since 25 < 50 threshold.
# ---------------------------------------------------------------------------
DATASET_EXPLICIT_HBAR_25_COURSES = {
    "user_instructions": "plot a horizontal bar chart of course name against number of enrolled students",
    "report_type": "generic",
    "data": [
        {"course_name": f"Course {chr(65 + i)}{i:02d}", "enrolled_students": random.randint(20, 200)}
        for i in range(25)
    ],
}


ALL_DATASETS = {
    "dept_avg_gpa": DATASET_DEPT_AVG_GPA,
    "explicit_line": DATASET_EXPLICIT_LINE_CHART,
    "explicit_pie_only": DATASET_EXPLICIT_PIE_ONLY,
    "explicit_bar_total_credits": DATASET_EXPLICIT_BAR_TOTAL_CREDITS,
    "large_pagination": DATASET_LARGE_DEPARTMENT_HEADCOUNT,
    "large_explicit_top10": DATASET_LARGE_TOP_10_EXPLICIT,
    "large_enrollments_no_id": DATASET_LARGE_ENROLLMENTS_NO_ID,
    "pass_percentage": DATASET_PASS_PERCENTAGE,
    "single_record": DATASET_SINGLE_RECORD,
    "explicit_hbar_25": DATASET_EXPLICIT_HBAR_25_COURSES,
}
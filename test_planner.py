"""
test_planner.py

Standalone test script for chart_planner.py + plan_validator.py.
Run this directly to see the raw LLM plan AND the validated plan,
side by side — useful for spotting when Gemini references bad
columns or makes questionable chart choices before wiring in rendering.

Usage:
    uv run test_planner.py
"""

import json
import logging

from llm_planner.chart_planner import generate_plan
from llm_planner.plan_validator import validate_plan

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# Real payload from your earlier test — top 10 students by GPA
SAMPLE_DATA = [
    {"student_id":168,"first_name":"Pooja","last_name":"Ravichandran","email":"pooja.ravichandran@student.college.edu","date_of_birth":"2000-05-13T00:00:00","department_id":3,"admission_year":2019,"gpa":9.90},
    {"student_id":19,"first_name":"Arun","last_name":"Murthy","email":"arun.murthy@student.college.edu","date_of_birth":"2006-10-19T00:00:00","department_id":1,"admission_year":2024,"gpa":9.89},
    {"student_id":422,"first_name":"Nithya","last_name":"Chandrasekaran","email":"nithya.chandrasekaran@student.college.edu","date_of_birth":"2006-01-25T00:00:00","department_id":6,"admission_year":2023,"gpa":9.88},
    {"student_id":308,"first_name":"Uma","last_name":"Baskaran","email":"uma.baskaran@student.college.edu","date_of_birth":"2004-02-15T00:00:00","department_id":5,"admission_year":2022,"gpa":9.85},
    {"student_id":230,"first_name":"Ravi","last_name":"Narayanan","email":"ravi.narayanan@student.college.edu","date_of_birth":"2003-08-24T00:00:00","department_id":4,"admission_year":2022,"gpa":9.85},
    {"student_id":146,"first_name":"Rekha","last_name":"Iyer","email":"rekha.iyer@student.college.edu","date_of_birth":"2003-09-13T00:00:00","department_id":2,"admission_year":2021,"gpa":9.85},
    {"student_id":644,"first_name":"Kalpana","last_name":"Krishnamurthy","email":"kalpana.krishnamurthy@student.college.edu","date_of_birth":"2006-08-09T00:00:00","department_id":9,"admission_year":2023,"gpa":9.84},
    {"student_id":10,"first_name":"Girish","last_name":"Gopalan","email":"girish.gopalan@student.college.edu","date_of_birth":"2001-09-27T00:00:00","department_id":1,"admission_year":2019,"gpa":9.84},
    {"student_id":239,"first_name":"Elango","last_name":"Yogeswaran","email":"elango.yogeswaran@student.college.edu","date_of_birth":"2002-01-03T00:00:00","department_id":4,"admission_year":2019,"gpa":9.83},
    {"student_id":458,"first_name":"Rahul","last_name":"Ganapathy","email":"rahul.ganapathy@student.college.edu","date_of_birth":"2006-10-22T00:00:00","department_id":7,"admission_year":2023,"gpa":9.82},
]


def main():
    print("=" * 70)
    print("STEP 1: Calling Gemini to generate a raw ReportPlan...")
    print("=" * 70)

    raw_plan = generate_plan(
        report_type="students",
        total_records=len(SAMPLE_DATA),
        data=SAMPLE_DATA,
    )

    print("\nRAW PLAN (before validation):\n")
    print(json.dumps(raw_plan.model_dump(), indent=2))

    print("\n" + "=" * 70)
    print("STEP 2: Validating plan against actual data columns...")
    print("=" * 70)

    validated_plan = validate_plan(raw_plan, SAMPLE_DATA)

    print("\nVALIDATED PLAN (after dropping any invalid sections):\n")
    print(json.dumps(validated_plan.model_dump(), indent=2))

    dropped_count = len(raw_plan.sections) - len(validated_plan.sections)
    print("\n" + "=" * 70)
    if dropped_count > 0:
        print(f"⚠️  {dropped_count} section(s) were dropped during validation. "
              f"Check the WARNING logs above for details.")
    else:
        print("✅ All sections passed validation.")
    print("=" * 70)


if __name__ == "__main__":
    main()
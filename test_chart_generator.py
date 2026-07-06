"""
test_chart_generator.py

Force-tests all four chart types (bar, horizontal_bar, pie, line) against
manually constructed ChartSpecs — deterministic, doesn't rely on Gemini
happening to choose a particular chart type. Also includes an optional
end-to-end run using the real LLM planner.

Usage:
    uv run test_chart_generator.py
"""

import logging
from pathlib import Path

from llm_planner.plan_schema import ChartSpec
from pdf_builder.chart_generator import render_chart

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

OUTPUT_DIR = Path("temp_pdfs/chart_test_output")

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


def run_test(name: str, chart: ChartSpec, data: list[dict]):
    print(f"\n[{name}] type={chart.chart_type}, agg={chart.aggregation}, "
          f"x={chart.x_field}, y={chart.y_field}")
    try:
        buffer, aspect_ratio = render_chart(chart, data)  # <-- unpack the tuple now
    except (ValueError, NotImplementedError) as e:
        print(f"    ⚠️  Failed — {e}")
        return

    output_path = OUTPUT_DIR / f"{name}.png"
    with open(output_path, "wb") as f:
        f.write(buffer.read())
    print(f"    ✅ Saved to {output_path}")


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Vertical bar — GPA per student (no aggregation, direct values)
    run_test(
        "01_bar_gpa_per_student",
        ChartSpec(
            chart_type="bar",
            title="GPA Comparison — Top 10 Students",
            x_field="last_name",
            y_field="gpa",
            aggregation="none",
            sort_order="desc",
            top_n=None,
        ),
        SAMPLE_DATA,
    )

    # 2. Horizontal bar — count of students per department
    run_test(
        "02_horizontal_bar_dept_count",
        ChartSpec(
            chart_type="horizontal_bar",
            title="Students by Department ID",
            x_field="department_id",
            y_field=None,
            aggregation="count",
            sort_order="desc",
            top_n=None,
        ),
        SAMPLE_DATA,
    )

    # 3. Pie — share of students per admission year
    run_test(
        "03_pie_admission_year_share",
        ChartSpec(
            chart_type="pie",
            title="Share of Students by Admission Year",
            x_field="admission_year",
            y_field=None,
            aggregation="count",
            sort_order="desc",
            top_n=None,
        ),
        SAMPLE_DATA,
    )

    # 4. Pie with >6 categories — tests the "Other" slice grouping logic
    run_test(
        "04_pie_many_categories_other_slice",
        ChartSpec(
            chart_type="pie",
            title="Share of Students by Department (many categories)",
            x_field="student_id",  # 10 unique values — forces >6 slices
            y_field=None,
            aggregation="count",
            sort_order="desc",
            top_n=None,
        ),
        SAMPLE_DATA,
    )

    # 5. Line — average GPA trend across admission years
    run_test(
        "05_line_gpa_trend_by_year",
        ChartSpec(
            chart_type="line",
            title="Average GPA by Admission Year",
            x_field="admission_year",
            y_field="gpa",
            aggregation="avg",
            sort_order="none",  # ignored by line renderer intentionally
            top_n=None,
        ),
        SAMPLE_DATA,
    )

    print(f"\nDone. Open the PNGs in {OUTPUT_DIR} to inspect visually.")


if __name__ == "__main__":
    main()
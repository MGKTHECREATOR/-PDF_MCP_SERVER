"""
test_report_composer.py

End-to-end test: calls Gemini for a plan, validates it, then composes
the final PDF using report_composer.py. Also includes a manual-plan
test to specifically check chart aspect ratios (bar, horizontal_bar,
pie, line) side by side in one document.

Usage:
    uv run test_report_composer.py
"""

import logging
from pathlib import Path

from llm_planner.chart_planner import generate_plan
from llm_planner.plan_validator import validate_plan
from llm_planner.plan_schema import ReportPlan, SectionSpec, ChartSpec, TableSpec, SummarySpec
from pdf_builder.report_composer import compose_pdf

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

OUTPUT_DIR = Path("temp_pdfs")

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


def test_end_to_end_with_gemini():
    """Real pipeline: Gemini plans, we validate, then compose the PDF."""
    print("=" * 70)
    print("TEST 1: End-to-end with real Gemini plan")
    print("=" * 70)

    raw_plan = generate_plan(
        report_type="students",
        total_records=len(SAMPLE_DATA),
        data=SAMPLE_DATA,
    )
    plan = validate_plan(raw_plan, SAMPLE_DATA)

    output_path = compose_pdf(plan, SAMPLE_DATA, OUTPUT_DIR / "test_end_to_end.pdf")
    print(f"✅ Saved to {output_path}\n")


def test_all_chart_types_manual():
    """
    Manually constructed plan forcing all 4 chart types + a table +
    a summary, in one PDF. This is the important one for checking
    the pie/horizontal_bar aspect ratio distortion issue.
    """
    print("=" * 70)
    print("TEST 2: Manual plan with all chart types (check aspect ratios here)")
    print("=" * 70)

    plan = ReportPlan(
        report_title="All Chart Types — Visual QA",
        sections=[
            SectionSpec(
                section_type="summary",
                summary=SummarySpec(text="This report exists purely to visually check every chart type renders correctly and isn't distorted."),
            ),
            SectionSpec(
                section_type="chart",
                chart=ChartSpec(
                    chart_type="bar",
                    title="Bar: GPA per Student",
                    x_field="last_name", y_field="gpa",
                    aggregation="none", sort_order="desc", top_n=None,
                ),
            ),
            SectionSpec(
                section_type="chart",
                chart=ChartSpec(
                    chart_type="horizontal_bar",
                    title="Horizontal Bar: Students per Department",
                    x_field="department_id", y_field=None,
                    aggregation="count", sort_order="desc", top_n=None,
                ),
            ),
            SectionSpec(
                section_type="chart",
                chart=ChartSpec(
                    chart_type="pie",
                    title="Pie: Share by Admission Year",
                    x_field="admission_year", y_field=None,
                    aggregation="count", sort_order="desc", top_n=None,
                ),
            ),
            SectionSpec(
                section_type="chart",
                chart=ChartSpec(
                    chart_type="line",
                    title="Line: Average GPA by Admission Year",
                    x_field="admission_year", y_field="gpa",
                    aggregation="avg", sort_order="none", top_n=None,
                ),
            ),
            SectionSpec(
                section_type="table",
                table=TableSpec(
                    title="Student Records",
                    columns=["student_id", "first_name", "last_name", "gpa"],
                    sort_by="gpa", sort_order="desc", max_rows=None,
                ),
            ),
        ],
    )

    output_path = compose_pdf(plan, SAMPLE_DATA, OUTPUT_DIR / "test_all_chart_types.pdf")
    print(f"✅ Saved to {output_path}\n")


def test_empty_plan_fallback():
    """Zero sections — should trigger the raw-data fallback table."""
    print("=" * 70)
    print("TEST 3: Empty plan (fallback table)")
    print("=" * 70)

    plan = ReportPlan(report_title="Fallback Test", sections=[])
    output_path = compose_pdf(plan, SAMPLE_DATA, OUTPUT_DIR / "test_fallback.pdf")
    print(f"✅ Saved to {output_path}\n")


if __name__ == "__main__":
    test_all_chart_types_manual()
    test_empty_plan_fallback()
    test_end_to_end_with_gemini()

    print("=" * 70)
    print(f"All done. Open the PDFs in {OUTPUT_DIR} to inspect:")
    print("  - test_all_chart_types.pdf  → check pie/horizontal_bar distortion")
    print("  - test_fallback.pdf         → should show a plain raw-data table")
    print("  - test_end_to_end.pdf       → real Gemini-planned report")
    print("=" * 70)
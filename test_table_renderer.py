"""
test_table_renderer.py

Standalone test for table_renderer.py — builds a PDF containing just
the rendered table, so you can open it and check formatting/wrapping
before combining with charts in the full report.

Usage:
    uv run test_table_renderer.py
"""

from pathlib import Path
from reportlab.platypus import SimpleDocTemplate, Spacer
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch

from llm_planner.plan_schema import TableSpec
from pdf_builder.table_renderer import render_table

OUTPUT_PATH = Path("temp_pdfs/table_test_output.pdf")

SAMPLE_DATA = [
    {"student_id":168,"first_name":"Pooja","last_name":"Ravichandran","email":"pooja.ravichandran@student.college.edu","date_of_birth":"2000-05-13T00:00:00","department_id":3,"admission_year":2019,"gpa":9.90},
    {"student_id":19,"first_name":"Arun","last_name":"Murthy","email":"arun.murthy@student.college.edu","date_of_birth":"2006-10-19T00:00:00","department_id":1,"admission_year":2024,"gpa":9.89},
    {"student_id":422,"first_name":"Nithya","last_name":"Chandrasekaran","email":"nithya.chandrasekaran@student.college.edu","date_of_birth":"2006-01-25T00:00:00","department_id":6,"admission_year":2023,"gpa":9.88},
    {"student_id":308,"first_name":"Uma","last_name":"Baskaran","email":"uma.baskaran@student.college.edu","date_of_birth":"2004-02-15T00:00:00","department_id":5,"admission_year":2022,"gpa":9.85},
    {"student_id":230,"first_name":"Ravi","last_name":"Narayanan","email":"ravi.narayanan@student.college.edu","date_of_birth":"2003-08-24T00:00:00","department_id":4,"admission_year":2022,"gpa":9.85},
    {"student_id":146,"first_name":"Rekha","last_name":"Iyer","email":"rekha.iyer@student.college.edu","date_of_birth":"2003-09-13T00:00:00","department_id":2,"admission_year":2021,"gpa":None},  # tests None handling
]


def main():
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    table_spec = TableSpec(
        title="Student Records",
        columns=["student_id", "first_name", "last_name", "email", "date_of_birth", "gpa"],
        sort_by="gpa",
        sort_order="desc",
        max_rows=None,
    )

    table = render_table(table_spec, SAMPLE_DATA)

    doc = SimpleDocTemplate(str(OUTPUT_PATH), pagesize=letter)
    doc.build([Spacer(1, 0.3 * inch), table])

    print(f"✅ Saved to {OUTPUT_PATH} — open it to inspect.")


if __name__ == "__main__":
    main()
"""
test_report_composer_v2.py

Full end-to-end test: for each dataset in sample_datasets.py, calls
Gemini for a plan (with user_instructions), validates it, and composes
a real PDF. Produces one PDF per dataset so you can open and inspect
each scenario individually.

Usage:
    uv run test_report_composer_v2.py                  # run all datasets
    uv run test_report_composer_v2.py large_pagination  # run just one
"""

import sys
from pathlib import Path
import time

from llm_planner.chart_planner import generate_plan
from llm_planner.plan_validator import validate_plan
from pdf_builder.report_composer import compose_pdf
from sample_datasets import ALL_DATASETS

OUTPUT_DIR = Path("temp_pdfs/v2_scenarios")


def run_one(key: str, dataset: dict):
    print(f"\n[{key}] generating plan...")
    raw_plan = generate_plan(
        report_type=dataset["report_type"],
        total_records=len(dataset["data"]),
        data=dataset["data"],
        user_instructions=dataset["user_instructions"],
    )
    plan = validate_plan(raw_plan, dataset["data"])

    chart_count = sum(1 for s in plan.sections if s.section_type == "chart")
    table_count = sum(1 for s in plan.sections if s.section_type == "table")
    print(f"    plan: {chart_count} chart section(s), {table_count} table section(s)")

    output_path = compose_pdf(plan, dataset["data"], OUTPUT_DIR / f"{key}.pdf")
    print(f"    ✅ Saved to {output_path}")


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if len(sys.argv) > 1:
        key = sys.argv[1]
        if key not in ALL_DATASETS:
            print(f"Unknown dataset '{key}'. Available: {list(ALL_DATASETS.keys())}")
            return
        run_one(key, ALL_DATASETS[key])
    else:
        for i, (key, dataset) in enumerate(ALL_DATASETS.items()):
            if i > 0:
                print("\n(waiting 13s to respect free-tier rate limit...)")
                time.sleep(13)  # 5 req/min = ~1 every 12s; 13s gives a small buffer
            run_one(key, dataset)


if __name__ == "__main__":
    main()
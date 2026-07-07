"""
test_planner_v2.py

Runs chart_planner.py + plan_validator.py against every dataset in
sample_datasets.py, printing the resulting plan for each. Fast/cheap —
run this before test_report_composer_v2.py to sanity-check LLM behavior
across all scenarios (explicit instructions, pagination, no-id data).

Usage:
    uv run test_planner_v2.py                  # run all datasets
    uv run test_planner_v2.py large_pagination  # run just one, by key
"""

import json
import sys
import time

from llm_planner.chart_planner import generate_plan
from llm_planner.plan_validator import validate_plan
from sample_datasets import ALL_DATASETS


def run_one(key: str, dataset: dict):
    print("\n" + "=" * 80)
    print(f"DATASET: {key}")
    print(f"user_instructions: {dataset['user_instructions'] or '(none)'}")
    print(f"report_type: {dataset['report_type']}  |  total_records: {len(dataset['data'])}")
    print("=" * 80)

    raw_plan = generate_plan(
        report_type=dataset["report_type"],
        total_records=len(dataset["data"]),
        data=dataset["data"],
        user_instructions=dataset["user_instructions"],
    )
    validated_plan = validate_plan(raw_plan, dataset["data"])

    print(json.dumps(validated_plan.model_dump(), indent=2))

    dropped = len(raw_plan.sections) - len(validated_plan.sections)
    if dropped > 0:
        print(f"\n⚠️  {dropped} section(s) dropped during validation.")

    # Quick summary of chart types chosen — useful for a fast eyeball check
    chart_types = [
        s.chart.chart_type for s in validated_plan.sections if s.section_type == "chart"
    ]
    print(f"\nChart types chosen: {chart_types or '(none — table/summary only)'}")


def main():
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
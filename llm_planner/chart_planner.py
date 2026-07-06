"""
llm_planner/chart_planner.py

Calls Gemini once per report to produce a complete ReportPlan.
Sends only a schema + sample rows + basic stats (NOT the full dataset)
to keep token cost down — the LLM decides WHAT to chart, the actual
aggregation over the full dataset happens later in pdf_builder/.
"""

import json
import logging
from typing import Any

from google import genai
from google.genai import types
from pydantic import ValidationError

from llm_planner.plan_schema import ReportPlan
from llm_planner.prompt_templates import SYSTEM_PROMPT
from llm_planner import GEMINI_API_KEY

logger = logging.getLogger("chart_planner")

client = genai.Client(api_key=GEMINI_API_KEY)
MODEL_NAME = "gemini-2.5-flash"  # good default: fast + cheap + strong at structured JSON

MAX_SAMPLE_ROWS = 8
MAX_RETRIES = 1  # one retry with error feedback, then fall back


def _infer_column_types(data: list[dict[str, Any]]) -> dict[str, str]:
    """Best-effort dtype guess per column, used to help the LLM
    avoid requesting numeric aggregation on text fields."""
    types_map: dict[str, str] = {}
    for row in data:
        for key, value in row.items():
            if key in types_map:
                continue
            if isinstance(value, bool):
                types_map[key] = "boolean"
            elif isinstance(value, (int, float)):
                types_map[key] = "numeric"
            elif value is None:
                continue  # wait for a non-null sample
            else:
                types_map[key] = "text"
    return types_map


def _compute_numeric_stats(data: list[dict[str, Any]], columns: dict[str, str]) -> dict[str, dict]:
    """min/max/avg for numeric columns only — gives the LLM enough
    context to make sensible chart decisions without seeing every row."""
    stats: dict[str, dict] = {}
    for col, dtype in columns.items():
        if dtype != "numeric":
            continue
        values = [row[col] for row in data if isinstance(row.get(col), (int, float))]
        if values:
            stats[col] = {
                "min": min(values),
                "max": max(values),
                "avg": round(sum(values) / len(values), 2),
            }
    return stats


def _build_user_message(
    report_type: str,
    total_records: int,
    data: list[dict[str, Any]],
    previous_error: str | None = None,
) -> str:
    columns = _infer_column_types(data)
    stats = _compute_numeric_stats(data, columns)
    sample = data[:MAX_SAMPLE_ROWS]

    payload = {
        "report_type": report_type,
        "total_records": total_records,
        "columns": columns,
        "numeric_stats": stats,
        "sample_rows": sample,
    }

    message = (
        "Here is the data context for this report:\n\n"
        f"{json.dumps(payload, indent=2, default=str)}\n\n"
        "Produce a ReportPlan JSON as instructed."
    )

    if previous_error:
        message += (
            "\n\nYOUR PREVIOUS ATTEMPT WAS INVALID:\n"
            f"{previous_error}\n"
            "Fix this and return a corrected ReportPlan JSON."
        )

    return message


def generate_plan(
    report_type: str,
    total_records: int,
    data: list[dict[str, Any]],
) -> ReportPlan:
    """
    Calls Gemini once (with up to one retry) to produce a ReportPlan.
    Raises ValueError if Gemini fails to produce a valid plan after retries —
    caller (report_composer.py) should catch this and fall back to a raw table.
    """
    previous_error: str | None = None

    for attempt in range(MAX_RETRIES + 1):
        user_message = _build_user_message(report_type, total_records, data, previous_error)

        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=user_message,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                response_mime_type="application/json",  # forces valid JSON output, no markdown fences
                max_output_tokens=2000,
            ),
        )

        raw_text = response.text

        try:
            parsed = json.loads(raw_text)
            plan = ReportPlan.model_validate(parsed)
            return plan

        except (json.JSONDecodeError, ValidationError) as e:
            previous_error = str(e)
            logger.warning(f"Plan generation attempt {attempt + 1} failed: {previous_error}")
            continue

    raise ValueError(
        f"Gemini failed to produce a valid ReportPlan after {MAX_RETRIES + 1} attempts. "
        f"Last error: {previous_error}"
    )
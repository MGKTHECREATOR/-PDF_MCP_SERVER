"""
llm_planner/chart_planner.py

Calls Gemini once per report to produce a complete ReportPlan.
Now accepts optional user_instructions — the original natural language
request — so the LLM can honor EXPLICIT chart/axis requests instead of
always using its own judgment.
"""

import json
import logging
import os
from typing import Any, Optional

from google import genai
from google.genai import types
from pydantic import ValidationError

from llm_planner.plan_schema import ReportPlan
from llm_planner.prompt_templates import SYSTEM_PROMPT

import time
from google.genai.errors import ClientError

RATE_LIMIT_RETRY_DELAY = 25  # seconds — slightly above the "retry in Xs" Gemini reports
MAX_RATE_LIMIT_RETRIES = 2

logger = logging.getLogger("chart_planner")

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
MODEL_NAME = "gemini-2.5-flash"

MAX_SAMPLE_ROWS = 8
MAX_RETRIES = 1


def _infer_column_types(data: list[dict[str, Any]]) -> dict[str, str]:
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
                continue
            else:
                types_map[key] = "text"
    return types_map


def _compute_numeric_stats(data: list[dict[str, Any]], columns: dict[str, str]) -> dict[str, dict]:
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
    user_instructions: Optional[str] = None,
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
    )

    if user_instructions and user_instructions.strip():
        message += (
            "ORIGINAL USER REQUEST (verbatim):\n"
            f'"{user_instructions.strip()}"\n\n'
            "Check this request for EXPLICIT chart/visualization instructions "
            "(chart type, specific fields for x-axis/y-axis, etc.) before "
            "deciding the plan. If explicit instructions are present, follow "
            "them exactly as described in your system instructions. If the "
            "request does not specify visualization details, use your own "
            "judgment as normal.\n\n"
        )
    else:
        message += "No specific user instructions were provided beyond the data request — use your own judgment for chart selection.\n\n"

    message += "Produce a ReportPlan JSON as instructed."

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
    user_instructions: Optional[str] = None,
) -> ReportPlan:
    previous_error: str | None = None

    for attempt in range(MAX_RETRIES + 1):
        user_message = _build_user_message(
            report_type, total_records, data, user_instructions, previous_error
        )

        for rate_limit_attempt in range(MAX_RATE_LIMIT_RETRIES + 1):
            try:
                response = client.models.generate_content(
                    model=MODEL_NAME,
                    contents=user_message,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        response_mime_type="application/json",
                        max_output_tokens=2000,
                    ),
                )
                break  # success — exit the rate-limit retry loop
            except ClientError as e:
                if e.code == 429 and rate_limit_attempt < MAX_RATE_LIMIT_RETRIES:
                    logger.warning(
                        f"Rate limited by Gemini — waiting {RATE_LIMIT_RETRY_DELAY}s "
                        f"before retry ({rate_limit_attempt + 1}/{MAX_RATE_LIMIT_RETRIES})"
                    )
                    time.sleep(RATE_LIMIT_RETRY_DELAY)
                    continue
                raise  # not a 429, or out of rate-limit retries — bubble up

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

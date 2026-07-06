"""
llm_planner/plan_validator.py

Validates an LLM-generated ReportPlan against the actual data.
Invalid sections (referencing non-existent columns, bad aggregations,
etc.) are dropped rather than failing the whole plan — prioritizing
"always produce a usable PDF" over strict guarantees.
"""

import logging
from typing import Any

from llm_planner.plan_schema import ReportPlan, SectionSpec, ChartSpec, TableSpec

logger = logging.getLogger("plan_validator")


def _get_available_columns(data: list[dict[str, Any]]) -> set[str]:
    """Collect the union of keys across records, in case some rows
    have slightly different shapes (e.g. optional/nullable fields)."""
    columns: set[str] = set()
    for record in data:
        columns.update(record.keys())
    return columns


def _is_numeric_column(data: list[dict[str, Any]], field: str) -> bool:
    """Checks whether a column's non-null values are numeric,
    used to sanity-check aggregations like avg/sum/max/min."""
    values = [row.get(field) for row in data if row.get(field) is not None]
    if not values:
        return False
    return all(isinstance(v, (int, float)) for v in values)


def _validate_chart(chart: ChartSpec, columns: set[str], data: list[dict[str, Any]]) -> str | None:
    """Returns an error string if invalid, else None."""
    if chart.x_field not in columns:
        return f"chart x_field '{chart.x_field}' not found in data columns {columns}"

    if chart.y_field is not None and chart.y_field not in columns:
        return f"chart y_field '{chart.y_field}' not found in data columns {columns}"

    if chart.aggregation in ("avg", "sum", "max", "min"):
        target_field = chart.y_field or chart.x_field
        if not _is_numeric_column(data, target_field):
            return (
                f"aggregation '{chart.aggregation}' requested on non-numeric "
                f"field '{target_field}'"
            )

    if chart.top_n is not None and chart.top_n <= 0:
        return f"top_n must be a positive integer, got {chart.top_n}"

    return None


def _validate_table(table: TableSpec, columns: set[str]) -> str | None:
    """Returns an error string if invalid, else None."""
    missing = [c for c in table.columns if c not in columns]
    if missing:
        return f"table columns {missing} not found in data columns {columns}"

    if table.sort_by is not None and table.sort_by not in columns:
        return f"table sort_by '{table.sort_by}' not found in data columns {columns}"

    if table.max_rows is not None and table.max_rows <= 0:
        return f"max_rows must be a positive integer, got {table.max_rows}"

    return None


def validate_plan(plan: ReportPlan, data: list[dict[str, Any]]) -> ReportPlan:
    """
    Validates every section in the plan against the actual data shape.
    Invalid sections are dropped and logged. Returns a new ReportPlan
    containing only valid sections.

    If ALL sections end up invalid, the returned plan will have an
    empty sections list — report_composer.py should handle that case
    by falling back to a plain table of the raw data.
    """
    if not data:
        logger.warning("validate_plan called with empty data — dropping all sections")
        return ReportPlan(report_title=plan.report_title, sections=[])

    columns = _get_available_columns(data)
    valid_sections: list[SectionSpec] = []

    for i, section in enumerate(plan.sections):
        error = None

        if section.section_type == "chart":
            if section.chart is None:
                error = "section_type is 'chart' but chart field is missing"
            else:
                error = _validate_chart(section.chart, columns, data)

        elif section.section_type == "table":
            if section.table is None:
                error = "section_type is 'table' but table field is missing"
            else:
                error = _validate_table(section.table, columns)

        elif section.section_type == "summary":
            if section.summary is None or not section.summary.text.strip():
                error = "section_type is 'summary' but summary text is missing/empty"

        else:
            error = f"unknown section_type '{section.section_type}'"

        if error:
            logger.warning(f"Dropping section {i} ({section.section_type}): {error}")
            continue

        valid_sections.append(section)

    if not valid_sections:
        logger.warning(
            "All sections were invalid — returning empty plan. "
            "report_composer.py should fall back to a raw data table."
        )

    return ReportPlan(report_title=plan.report_title, sections=valid_sections)
"""
pdf_builder/table_renderer.py

Renders a single TableSpec into a reportlab Table flowable, ready to
add to a PDF document alongside chart images.
"""

import logging
from datetime import date, datetime
from typing import Any

from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet

from llm_planner.plan_schema import TableSpec

logger = logging.getLogger("table_renderer")

styles = getSampleStyleSheet()

# Keep colors consistent with chart_generator.py's palette
HEADER_BG = colors.HexColor("#3B6E9E")
HEADER_TEXT = colors.white
ROW_ALT_BG = colors.HexColor("#F2F6FA")
GRID_COLOR = colors.HexColor("#CCCCCC")

MAX_COLUMN_WIDTH = 1.6 * inch
MIN_COLUMN_WIDTH = 0.7 * inch


def _format_cell(value: Any) -> str:
    """
    Converts a raw JSON value into a display-friendly string.
    Handles the common types coming out of Postgres-via-JSON:
    None, floats, ISO datetime strings, plain strings/ints.
    """
    if value is None:
        return "-"

    if isinstance(value, float):
        return f"{value:.2f}"

    if isinstance(value, (date, datetime)):
        return value.strftime("%Y-%m-%d")

    if isinstance(value, str):
        # Postgres/JSON often serializes dates as ISO strings —
        # trim the time component if present for readability.
        if "T" in value and len(value) >= 19 and value[:4].isdigit():
            try:
                parsed = datetime.fromisoformat(value)
                return parsed.strftime("%Y-%m-%d")
            except ValueError:
                pass
        return value

    return str(value)


def _prepare_rows(table_spec: TableSpec, data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Applies sort_by, sort_order, and max_rows from the table spec."""
    rows = list(data)

    if table_spec.sort_by:
        sort_field = table_spec.sort_by

        # Split into rows with a real value vs rows where it's None —
        # None should ALWAYS sort last, regardless of asc/desc.
        with_value = [r for r in rows if r.get(sort_field) is not None]
        without_value = [r for r in rows if r.get(sort_field) is None]

        with_value.sort(
            key=lambda r: r[sort_field],
            reverse=(table_spec.sort_order == "desc"),
        )

        rows = with_value + without_value

    if table_spec.max_rows is not None:
        rows = rows[: table_spec.max_rows]

    return rows


def render_table(table_spec: TableSpec, data: list[dict[str, Any]]) -> Table:
    """
    Renders a TableSpec + raw data into a styled reportlab Table flowable.
    Raises ValueError if there's no data to render.
    """
    if not data:
        raise ValueError(f"No data to render for table '{table_spec.title}'")

    rows = _prepare_rows(table_spec, data)
    columns = table_spec.columns

    # Header row — wrap column names in Paragraph for consistent styling
    header_style = styles["Normal"].clone("header")
    header_style.textColor = HEADER_TEXT
    header_style.fontName = "Helvetica-Bold"
    header_style.fontSize = 9

    body_style = styles["Normal"].clone("body")
    body_style.fontSize = 8
    body_style.leading = 10

    table_data = [
        [Paragraph(col.replace("_", " ").title(), header_style) for col in columns]
    ]

    for row in rows:
        table_data.append([
            Paragraph(_format_cell(row.get(col)), body_style) for col in columns
        ])

    # Distribute column widths evenly within available page width,
    # clamped between min/max so no single column gets absurdly wide/narrow
    available_width = 6.5 * inch  # standard usable width on a letter page with margins
    col_width = available_width / len(columns)
    col_width = max(MIN_COLUMN_WIDTH, min(MAX_COLUMN_WIDTH, col_width))
    col_widths = [col_width] * len(columns)

    table = Table(table_data, colWidths=col_widths, repeatRows=1)  # repeat header on page breaks

    style_commands = [
        ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
        ("TEXTCOLOR", (0, 0), (-1, 0), HEADER_TEXT),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, GRID_COLOR),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]

    # Zebra striping for readability on longer tables
    for i in range(1, len(table_data)):
        if i % 2 == 0:
            style_commands.append(("BACKGROUND", (0, i), (-1, i), ROW_ALT_BG))

    table.setStyle(TableStyle(style_commands))

    return table
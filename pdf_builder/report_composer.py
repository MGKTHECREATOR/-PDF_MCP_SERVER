# report_composer.py
"""
pdf_builder/report_composer.py

Takes a validated ReportPlan + the raw data, and produces a complete
PDF file on disk. Walks plan.sections in order and renders each one
using chart_generator.py or table_renderer.py — no per-reportType
branching, this is fully generic and driven entirely by the plan.
"""

import logging
from pathlib import Path
from typing import Any

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Image,
    PageBreak,
)

from llm_planner.plan_schema import ReportPlan
from pdf_builder.chart_generator import render_chart
from pdf_builder.table_renderer import render_table

logger = logging.getLogger("report_composer")

styles = getSampleStyleSheet()

TITLE_STYLE = ParagraphStyle(
    "ReportTitle", parent=styles["Title"],
    fontSize=22, textColor=colors.HexColor("#1F3864"),
    spaceAfter=14, alignment=1,  # centered
)

SECTION_TITLE_STYLE = ParagraphStyle(
    "SectionTitle", parent=styles["Heading2"],
    fontSize=14, textColor=colors.HexColor("#1F3864"),
    spaceBefore=18, spaceAfter=10,
    borderPadding=0,
)

SUMMARY_STYLE = ParagraphStyle(
    "SummaryText",
    parent=styles["Normal"],
    fontSize=10,
    leading=14,
    textColor=colors.HexColor("#333333"),
    spaceAfter=10,
)

CHART_IMAGE_WIDTH = 6.5 * inch  # matches usable page width used in table_renderer.py
MAX_CHART_HEIGHT = 7.5 * inch   # avoid a single tall chart overflowing the page


def _render_summary_section(points: list[str]) -> list:
    flowables = [Paragraph("Executive Summary", SECTION_TITLE_STYLE)]
    for point in points:
        flowables.append(Paragraph(f"•&nbsp;&nbsp;{point}", BULLET_STYLE))
    flowables.append(Spacer(1, 0.15 * inch))
    return flowables


def _render_chart_section(chart_spec, data: list[dict[str, Any]]) -> list:
    """
    Returns flowables for a chart section: title + image.
    Sizes the image using the chart's REAL aspect ratio (returned by
    chart_generator.py) so pie charts stay circular and horizontal
    bars aren't squashed — rather than forcing a fixed box.
    Returns an empty list (skips silently) if rendering fails —
    one bad chart should not break the whole report.
    """
    try:
        png_buffer, aspect_ratio = render_chart(chart_spec, data)
    except (ValueError, NotImplementedError) as e:
        logger.warning(f"Skipping chart '{chart_spec.title}': {e}")
        return []

    width = CHART_IMAGE_WIDTH
    height = width / aspect_ratio

    if height > MAX_CHART_HEIGHT:
        height = MAX_CHART_HEIGHT
        width = height * aspect_ratio

    img = Image(png_buffer, width=width, height=height)

    return [
        Paragraph(chart_spec.title, SECTION_TITLE_STYLE),
        img,
        Spacer(1, 0.15 * inch),
    ]


def _render_table_section(table_spec, data: list[dict[str, Any]]) -> list:
    """
    Returns flowables for a table section: title + table.
    Returns an empty list (skips silently) if rendering fails.
    """
    try:
        table = render_table(table_spec, data)
    except ValueError as e:
        logger.warning(f"Skipping table '{table_spec.title}': {e}")
        return []

    return [
        Paragraph(table_spec.title, SECTION_TITLE_STYLE),
        table,
        Spacer(1, 0.15 * inch),
    ]


def _render_fallback_table(data: list[dict[str, Any]]) -> list:
    """
    Used when the plan has zero valid sections (e.g. LLM planning failed
    entirely, or every section got dropped in validation). Renders a
    plain table of ALL fields present in the data so the PDF is still
    useful rather than empty.
    """
    from llm_planner.plan_schema import TableSpec

    if not data:
        return [Paragraph("No records found.", SUMMARY_STYLE)]

    all_columns = list(data[0].keys())
    fallback_spec = TableSpec(
        title="Raw Data",
        columns=all_columns,
        sort_by=None,
        sort_order="asc",
        max_rows=None,
    )

    logger.warning("Rendering fallback raw-data table — plan had zero valid sections")
    return _render_table_section(fallback_spec, data)


def compose_pdf(
    plan: ReportPlan,
    data: list[dict[str, Any]],
    output_path: str | Path,
) -> Path:
    """
    Builds the complete PDF from a validated ReportPlan and the raw data.
    Writes the file to output_path and returns the Path.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        topMargin=0.7 * inch,
        bottomMargin=0.7 * inch,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
    )

    flowables = []

    # Report header
    flowables.append(Paragraph(plan.report_title, TITLE_STYLE))
    flowables.append(Spacer(1, 0.1 * inch))

    if not plan.sections:
        flowables.extend(_render_fallback_table(data))
    else:
        for section in plan.sections:
            if section.section_type == "summary" and section.summary:
                flowables.extend(_render_summary_section(section.summary.points))

            elif section.section_type == "chart" and section.chart:
                flowables.extend(_render_chart_section(section.chart, data))

            elif section.section_type == "table" and section.table:
                flowables.extend(_render_table_section(section.table, data))
            
            elif section.section_type == "insights" and section.insights:
                flowables.extend(_render_insights_section(section.insights.points))

            elif section.section_type == "recommendations" and section.recommendations:
                flowables.extend(_render_recommendations_section(section.recommendations.points))

            else:
                logger.warning(f"Skipping malformed section: {section}")

    doc.build(flowables)
    logger.info(f"PDF written to {output_path}")

    return output_path


BULLET_STYLE = ParagraphStyle(
    "BulletText",
    parent=styles["Normal"],
    fontSize=10,
    leading=15,
    leftIndent=14,
    bulletIndent=0,
    spaceAfter=6,
    textColor=colors.HexColor("#333333"),
)

def _render_insights_section(points: list[str]) -> list:
    flowables = [Paragraph("Key Insights", SECTION_TITLE_STYLE)]
    for point in points:
        flowables.append(Paragraph(f"•&nbsp;&nbsp;{point}", BULLET_STYLE))
    flowables.append(Spacer(1, 0.15 * inch))
    return flowables

def _render_recommendations_section(points: list[str]) -> list:
    flowables = [Paragraph("Recommendations", SECTION_TITLE_STYLE)]
    for point in points:
        flowables.append(Paragraph(f"•&nbsp;&nbsp;{point}", BULLET_STYLE))
    flowables.append(Spacer(1, 0.15 * inch))
    return flowables
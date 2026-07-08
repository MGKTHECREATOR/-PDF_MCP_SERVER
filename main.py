#!/usr/bin/env python3
"""
main.py
MCP server entrypoint for the PDF report generator.
Uses FastMCP with SSE transport for Igentic Studio compatibility.

generate_pdf_report is the real tool: takes JSON data from
Data_Fetcher_Agent, plans visualizations via Gemini, renders a PDF,
and returns a reference to the generated file.

NOTE: Azure Blob upload is not wired in yet — PDFs are currently saved
to temp_pdfs/ and a local path is returned. Swap in blob_uploader.py
once the Azure Storage account is ready; the tool's external interface
(what it returns) will change from a local path to a blob URL, but the
rest of the pipeline stays identical.
"""

from dotenv import load_dotenv
load_dotenv()

import os
import uuid
import logging
from pathlib import Path
from typing import Any, Optional

from fastmcp import FastMCP

from llm_planner.chart_planner import generate_plan
from llm_planner.plan_validator import validate_plan
from pdf_builder.report_composer import compose_pdf

logging.basicConfig(
    level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO')),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

mcp = FastMCP(os.getenv('MCP_SERVER_NAME', 'PDF Report MCP Server'))

TEMP_PDF_DIR = Path("temp_pdfs")


@mcp.tool(
    name="ping",
    description="Simple connectivity check. Call this to confirm the server is running and reachable."
)
def ping_tool() -> str:
    return "pong"


@mcp.tool(
    name="health_check",
    description="Returns basic server status info."
)
def health_check_tool() -> dict:
    return {
        "status": "ok",
        "server": "pdf-report-server",
        "stage": "connectivity-check"
    }


@mcp.tool(
    name="generate_pdf_report",
    description=(
        "Generates a PDF report with tables and data visualizations (bar, "
        "horizontal bar, pie, and line charts) from structured JSON data. "
        "The chart selection is decided by an LLM planner based on the data "
        "shape and any explicit visualization instructions in the original "
        "user request. Returns a reference to the generated PDF file."
    )
)
def generate_pdf_report_tool(
    report_type: str,
    data: list[dict[str, Any]],
    user_instructions: Optional[str] = None,
) -> dict:
    """
    Args:
        report_type: The category of data (e.g. "students", "faculty",
            "courses", "enrollments", "departments", "generic") — used as
            context for the LLM planner, not for template selection.
        data: The raw records to report on, as a list of JSON objects.
        user_instructions: The original natural language request from the
            end user, if available. Used to detect and honor EXPLICIT
            chart type / axis / aggregation requests (e.g. "show this as
            a line chart with X on the x-axis"). If omitted or empty, the
            LLM uses its own judgment for chart selection.

    Returns:
        dict with keys:
            status: "success" or "error"
            pdf_path: local filesystem path to the generated PDF (temporary —
                will become a blob URL once storage is wired in)
            filename: the generated PDF's filename
            error: present only if status is "error"
    """
    total_records = len(data)
    logger.info(
        f"generate_pdf_report called — report_type={report_type}, "
        f"total_records={total_records}, "
        f"user_instructions={'(none)' if not user_instructions else user_instructions!r}"
    )

    if total_records == 0:
        logger.warning("generate_pdf_report called with empty data")
        return {
            "status": "error",
            "error": "No records provided — cannot generate a report from empty data.",
        }

    try:
        raw_plan = generate_plan(
            report_type=report_type,
            total_records=total_records,
            data=data,
            user_instructions=user_instructions,
        )
        plan = validate_plan(raw_plan, data)

    except Exception as e:
        logger.exception("Plan generation failed")
        return {
            "status": "error",
            "error": f"Failed to generate report plan: {e}",
        }

    filename = f"report_{uuid.uuid4().hex[:10]}.pdf"
    output_path = TEMP_PDF_DIR / filename

    try:
        compose_pdf(plan, data, output_path)
    except Exception as e:
        logger.exception("PDF composition failed")
        return {
            "status": "error",
            "error": f"Failed to compose PDF: {e}",
        }

    logger.info(f"PDF successfully generated at {output_path}")

    return {
        "status": "success",
        "pdf_path": str(output_path.resolve()),
        "filename": filename,
        "note": "This is a LOCAL file path — Azure Blob upload not yet wired in.",
    }


if __name__ == "__main__":
    TEMP_PDF_DIR.mkdir(parents=True, exist_ok=True)

    logger.info("Starting PDF Report MCP Server (SSE transport)...")
    print(f"Starting {os.getenv('MCP_SERVER_NAME', 'PDF Report MCP Server')}")

    port = int(os.getenv('PORT', 8000))
    host = os.getenv('HOST', '0.0.0.0')

    mcp.run(transport="sse", host=host, port=port)
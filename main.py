#!/usr/bin/env python3
"""
main.py
MCP server entrypoint for the PDF report generator.
Uses FastMCP with HTTP/ASGI transport (Streamable HTTP) for
Azure App Service / Igentic Studio compatibility.

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
import io
import pandas as pd 
from pathlib import Path
from typing import Any, Optional

from fastmcp import FastMCP

from llm_planner.chart_planner import generate_plan
from llm_planner.plan_validator import validate_plan
from pdf_builder.report_composer import compose_pdf
from blob_uploader import upload_pdf_bytes_to_blob

logging.basicConfig(
    level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO')),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

mcp = FastMCP(os.getenv('MCP_SERVER_NAME', 'PDF Report MCP Server'))



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
    name="generate_report",
    description=(
        "Generates a PDF report with tables and data visualizations (bar, "
        "horizontal bar, pie, and line charts) from structured JSON data. "
        "The chart selection is decided by an LLM planner based on the data "
        "shape and any explicit visualization instructions in the original "
        "user request. Returns a reference to the generated PDF file."
    )
)
def generate_pdf_report_tool(
    report_title: str,
    dataset: str,
    dashboard_items: list[str],
    generate_pdf: bool = True,
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

    df = pd.read_csv(io.StringIO(dataset))
    data = df.fillna("").to_dict(orient="records")
    report_type = report_title
    user_instructions = "; ".join(item for item in dashboard_items if item.strip()) or None
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
    pdf_buffer = io.BytesIO()

    try:
        compose_pdf(plan, data, pdf_buffer)
    except Exception as e:
        logger.exception("PDF composition failed")
        return {
            "status": "error",
            "error": f"Failed to compose PDF: {e}",
        }

    pdf_buffer.seek(0)
    logger.info("PDF generated in memory, uploading to blob storage")

    try:
        pdf_url = upload_pdf_bytes_to_blob(pdf_buffer.read(), filename)
    except Exception as e:
        logger.exception("Blob upload failed")
        return {
            "status": "error",
            "error": f"PDF generated but failed to upload to storage: {e}",
        }

    return {
        "status": "success",
        "pdf_path": pdf_url,
        "filename": filename,
    }


# --------------------------------------------------
# Expose ASGI app for Azure / gunicorn
# --------------------------------------------------

AZURE_HOST = "intellireport-mcp-f5bjhefshwe3bacq.centralindia-01.azurewebsites.net"

app = mcp.http_app(
    path="/mcp",
    stateless_http=True,
    host_origin_protection=True,
    allowed_hosts=[
        AZURE_HOST,
    ],
    allowed_origins=[
        f"https://{AZURE_HOST}",
    ],
)

if __name__ == "__main__":
    import uvicorn

    logger.info("Starting PDF Report MCP Server (HTTP/ASGI transport)...")
    print(
        f"Starting {os.getenv('MCP_SERVER_NAME', 'PDF Report MCP Server')}"
    )

    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port
    )

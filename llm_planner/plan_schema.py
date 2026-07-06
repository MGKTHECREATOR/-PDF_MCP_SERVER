"""
llm_planner/plan_schema.py

Defines the structured "report plan" the LLM must produce.
This is the contract between the LLM's decision-making and the
deterministic rendering code in pdf_builder/.
"""

from typing import Literal, Optional
from pydantic import BaseModel, Field


class ChartSpec(BaseModel):
    """A single chart the LLM has decided to include."""
    chart_type: Literal["bar", "horizontal_bar", "pie", "line"]
    title: str
    x_field: str
    y_field: Optional[str] = None
    aggregation: Literal["none", "count", "avg", "sum", "max", "min"] = "none"
    sort_order: Literal["asc", "desc", "none"] = "none"
    top_n: Optional[int] = Field(
        default=None,
        description="If set, only chart the top N categories/values."
    )


class TableSpec(BaseModel):
    """A data table the LLM has decided to include."""
    title: str
    columns: list[str]
    sort_by: Optional[str] = None
    sort_order: Literal["asc", "desc"] = "asc"
    max_rows: Optional[int] = None


class SummarySpec(BaseModel):
    """A short narrative text block the LLM has written."""
    text: str


class SectionSpec(BaseModel):
    """
    One section of the report, in the order it should appear.
    Exactly one of chart/table/summary should be populated,
    matching section_type.
    """
    section_type: Literal["chart", "table", "summary"]
    chart: Optional[ChartSpec] = None
    table: Optional[TableSpec] = None
    summary: Optional[SummarySpec] = None


class ReportPlan(BaseModel):
    """
    The complete rendering plan for one report.
    This is the ONLY thing the LLM returns — report_composer.py
    executes this deterministically against the real data.
    """
    report_title: str
    sections: list[SectionSpec]
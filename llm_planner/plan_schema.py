"""
llm_planner/plan_schema.py
"""

from typing import Literal, Optional
from pydantic import BaseModel, Field


class ChartSpec(BaseModel):
    chart_type: Literal["bar", "horizontal_bar", "pie", "line", "scatter"]
    title: str
    x_field: str
    y_field: Optional[str] = None
    aggregation: Literal["none", "count", "avg", "sum", "max", "min"] = "none"
    sort_order: Literal["asc", "desc", "none"] = "none"
    top_n: Optional[int] = None
    start_index: Optional[int] = None
    end_index: Optional[int] = None


class TableSpec(BaseModel):
    title: str
    columns: list[str]
    sort_by: Optional[str] = None
    sort_order: Literal["asc", "desc"] = "asc"
    max_rows: Optional[int] = None


class SummarySpec(BaseModel):
    """Executive summary — now a set of 4-5 bullet points, not one paragraph."""
    points: list[str]


class InsightSpec(BaseModel):
    """Key insights — factual observations grounded in the data."""
    points: list[str]


class RecommendationSpec(BaseModel):
    """Actionable recommendations following from the insights."""
    points: list[str]


class SectionSpec(BaseModel):
    section_type: Literal["chart", "table", "summary", "insights", "recommendations"]
    chart: Optional[ChartSpec] = None
    table: Optional[TableSpec] = None
    summary: Optional[SummarySpec] = None
    insights: Optional[InsightSpec] = None
    recommendations: Optional[RecommendationSpec] = None


class ReportPlan(BaseModel):
    report_title: str
    sections: list[SectionSpec]
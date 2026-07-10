# chart_generator.py

"""
pdf_builder/chart_generator.py

Renders a single ChartSpec into a matplotlib chart, saved as a PNG
buffer ready to embed in a reportlab PDF.

Implemented chart types: bar, horizontal_bar, pie, line

Each render function returns (buffer, aspect_ratio) so report_composer.py
can size the embedded image correctly instead of guessing a fixed ratio —
this prevents pie charts from being squashed into ovals, etc.
"""

import io
import logging
from collections import Counter, defaultdict
from typing import Any

import matplotlib
matplotlib.use("Agg")  # non-interactive backend — required for server-side rendering
import matplotlib.pyplot as plt

from llm_planner.plan_schema import ChartSpec

logger = logging.getLogger("chart_generator")

# Keep visuals consistent across all charts in a report
plt.rcParams["font.size"] = 10
plt.rcParams["axes.edgecolor"] = "#444444"
plt.rcParams["axes.labelcolor"] = "#222222"

# Shared color palette — used for pie slices and general consistency
PALETTE = [
    "#3B6E9E", "#5B9BD5", "#8FBCE6", "#2E5C8A", "#A9CCE3",
    "#1F4E79", "#6FA8DC", "#4A86C5", "#7CA9D4", "#9FC5E8",
]


# ---------------------------------------------------------------------------
# Shared aggregation / sorting logic — used by all chart types
# ---------------------------------------------------------------------------

def _aggregate(data: list[dict[str, Any]], chart: ChartSpec) -> tuple[list, list]:
    """
    Groups/aggregates the raw data according to chart.x_field, chart.y_field,
    and chart.aggregation. Returns (labels, values) ready to plot.
    """
    if chart.aggregation == "none":
        labels = [str(row.get(chart.x_field, "")) for row in data]
        values = [row.get(chart.y_field) for row in data]

    elif chart.aggregation == "count":
        counts = Counter(str(row.get(chart.x_field, "Unknown")) for row in data)
        labels = list(counts.keys())
        values = list(counts.values())

    else:
        # avg / sum / max / min grouped by x_field
        groups: dict[str, list[float]] = defaultdict(list)
        target_field = chart.y_field or chart.x_field
        for row in data:
            key = str(row.get(chart.x_field, "Unknown"))
            val = row.get(target_field)
            if isinstance(val, (int, float)):
                groups[key].append(val)

        labels = list(groups.keys())
        if chart.aggregation == "avg":
            values = [sum(v) / len(v) for v in groups.values()]
        elif chart.aggregation == "sum":
            values = [sum(v) for v in groups.values()]
        elif chart.aggregation == "max":
            values = [max(v) for v in groups.values()]
        elif chart.aggregation == "min":
            values = [min(v) for v in groups.values()]
        else:
            values = [0 for _ in groups]

    return labels, values


def _apply_sort_and_limit(labels: list, values: list, chart: ChartSpec) -> tuple[list, list]:
    """Applies sort_order, then top_n OR start_index/end_index from the chart spec."""
    if chart.sort_order in ("asc", "desc"):
        paired = sorted(
            zip(labels, values),
            key=lambda p: p[1],
            reverse=(chart.sort_order == "desc"),
        )
        labels, values = zip(*paired) if paired else ([], [])
        labels, values = list(labels), list(values)

    if chart.start_index is not None and chart.end_index is not None:
        labels = labels[chart.start_index:chart.end_index]
        values = values[chart.start_index:chart.end_index]
    elif chart.top_n is not None:
        labels = labels[: chart.top_n]
        values = values[: chart.top_n]

    return labels, values


def _prepare_data(chart: ChartSpec, data: list[dict[str, Any]]) -> tuple[list, list]:
    """Shared prep step: aggregate, sort, limit. Raises ValueError if empty."""
    labels, values = _aggregate(data, chart)
    labels, values = _apply_sort_and_limit(labels, values, chart)

    if not labels:
        logger.warning(f"Chart '{chart.title}' has no data to plot")
        raise ValueError(f"No plottable data for chart '{chart.title}'")

    return labels, values


def _fig_to_buffer(fig) -> tuple[io.BytesIO, float]:
    """
    Common save/cleanup step for every chart renderer.
    Returns (buffer, aspect_ratio) where aspect_ratio = width / height,
    read directly from the actual figure size — so report_composer.py
    can size the embedded image correctly instead of guessing.
    """
    width_in, height_in = fig.get_size_inches()
    aspect_ratio = width_in / height_in

    buffer = io.BytesIO()
    fig.savefig(buffer, format="png")
    plt.close(fig)  # critical — prevents memory leak across multiple chart renders
    buffer.seek(0)

    return buffer, aspect_ratio


# ---------------------------------------------------------------------------
# Chart type: bar (vertical)
# ---------------------------------------------------------------------------

def render_bar_chart(chart: ChartSpec, data: list[dict[str, Any]]) -> tuple[io.BytesIO, float]:
    """Vertical bar chart — best for comparing values across few-to-moderate categories."""
    labels, values = _prepare_data(chart, data)

    fig, ax = plt.subplots(figsize=(7, 4), dpi=150)
    bars = ax.bar(labels, values, color="#3B6E9E", edgecolor="none")

    ax.set_title(chart.title, fontsize=12, fontweight="bold", pad=12)
    ax.set_ylabel(chart.y_field or "count")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    if len(labels) > 6 or max(len(str(l)) for l in labels) > 8:
        plt.xticks(rotation=45, ha="right")

    for bar, val in zip(bars, values):
        ax.annotate(
            f"{val:.2f}" if isinstance(val, float) else str(val),
            xy=(bar.get_x() + bar.get_width() / 2, bar.get_height()),
            xytext=(0, 3),
            textcoords="offset points",
            ha="center",
            fontsize=8,
        )

    fig.tight_layout()
    return _fig_to_buffer(fig)


# ---------------------------------------------------------------------------
# Chart type: horizontal_bar
# ---------------------------------------------------------------------------

def render_horizontal_bar_chart(chart: ChartSpec, data: list[dict[str, Any]]) -> tuple[io.BytesIO, float]:
    """Horizontal bar chart — best for long category labels or many categories."""
    labels, values = _prepare_data(chart, data)

    # Reverse so the top-ranked item (after desc sort) appears at the TOP —
    # matplotlib's barh plots bottom-to-top by default.
    labels = list(reversed(labels))
    values = list(reversed(values))

    fig, ax = plt.subplots(figsize=(7, max(4, len(labels) * 0.4)), dpi=150)
    bars = ax.barh(labels, values, color="#3B6E9E", edgecolor="none")

    ax.set_title(chart.title, fontsize=12, fontweight="bold", pad=12)
    ax.set_xlabel(chart.y_field or "count")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    for bar, val in zip(bars, values):
        ax.annotate(
            f"{val:.2f}" if isinstance(val, float) else str(val),
            xy=(bar.get_width(), bar.get_y() + bar.get_height() / 2),
            xytext=(4, 0),
            textcoords="offset points",
            ha="left",
            va="center",
            fontsize=8,
        )

    fig.tight_layout()
    return _fig_to_buffer(fig)


# ---------------------------------------------------------------------------
# Chart type: pie
# ---------------------------------------------------------------------------

def render_pie_chart(chart: ChartSpec, data: list[dict[str, Any]]) -> tuple[io.BytesIO, float]:
    """
    Pie chart — best for showing proportion/share across a SMALL number of
    categories (prompt guidance caps this at ~6). If more slip through,
    they're grouped into an 'Other' slice to keep the chart readable.
    """
    labels, values = _prepare_data(chart, data)

    MAX_SLICES = 6
    if len(labels) > MAX_SLICES:
        top_labels = labels[: MAX_SLICES - 1]
        top_values = values[: MAX_SLICES - 1]
        other_total = sum(values[MAX_SLICES - 1:])
        labels = top_labels + ["Other"]
        values = top_values + [other_total]

    # Filter out non-positive values — pie slices can't be zero/negative
    filtered = [(l, v) for l, v in zip(labels, values) if v and v > 0]
    if not filtered:
        raise ValueError(f"No positive values to plot for pie chart '{chart.title}'")
    labels, values = zip(*filtered)

    fig, ax = plt.subplots(figsize=(6, 6), dpi=150)
    colors = [PALETTE[i % len(PALETTE)] for i in range(len(labels))]

    wedges, _, autotexts = ax.pie(
        values,
        labels=labels,
        autopct="%1.1f%%",
        startangle=90,
        colors=colors,
        wedgeprops={"edgecolor": "white", "linewidth": 1.5},
        textprops={"fontsize": 9},
    )
    for autotext in autotexts:
        autotext.set_color("white")
        autotext.set_fontweight("bold")

    ax.set_title(chart.title, fontsize=12, fontweight="bold", pad=12)
    ax.axis("equal")  # keeps the pie circular, not elliptical

    fig.tight_layout()
    return _fig_to_buffer(fig)


# ---------------------------------------------------------------------------
# Chart type: line
# ---------------------------------------------------------------------------

def render_line_chart(chart: ChartSpec, data: list[dict[str, Any]]) -> tuple[io.BytesIO, float]:
    """
    Line chart — best for trends across an ordered/sequential field
    (e.g. admission_year, academic_year). Unlike bar/pie, line charts
    should NOT be sorted by value — they need to preserve the natural
    order of the x_field (chronological, typically), so sort_order from
    the chart spec is intentionally ignored here.
    """
    labels, values = _aggregate(data, chart)

    if not labels:
        logger.warning(f"Chart '{chart.title}' has no data to plot")
        raise ValueError(f"No plottable data for chart '{chart.title}'")

    # Line charts plot in x-axis order, not value order — sort by label instead
    try:
        paired = sorted(zip(labels, values), key=lambda p: float(p[0]))
    except (ValueError, TypeError):
        # x_field isn't numeric/sortable as a number — fall back to string sort
        paired = sorted(zip(labels, values), key=lambda p: str(p[0]))

    if chart.top_n is not None:
        paired = paired[: chart.top_n]

    labels, values = zip(*paired)

    fig, ax = plt.subplots(figsize=(7, 4), dpi=150)
    ax.plot(labels, values, marker="o", color="#3B6E9E", linewidth=2, markersize=5)
    ax.fill_between(range(len(labels)), values, alpha=0.08, color="#3B6E9E")

    ax.set_title(chart.title, fontsize=12, fontweight="bold", pad=12)
    ax.set_ylabel(chart.y_field or "count")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(True, axis="y", linestyle="--", alpha=0.3)

    if len(labels) > 6:
        plt.xticks(rotation=45, ha="right")

    for x, val in zip(labels, values):
        ax.annotate(
            f"{val:.2f}" if isinstance(val, float) else str(val),
            xy=(x, val),
            xytext=(0, 8),
            textcoords="offset points",
            ha="center",
            fontsize=8,
        )

    fig.tight_layout()
    return _fig_to_buffer(fig)


def render_scatter_chart(chart: ChartSpec, data: list[dict[str, Any]]) -> tuple[io.BytesIO, float]:
    """Scatter plot — best for showing relationship/correlation between two numeric fields."""
    x_values = [row.get(chart.x_field) for row in data if isinstance(row.get(chart.x_field), (int, float))]
    y_values = [row.get(chart.y_field) for row in data if isinstance(row.get(chart.y_field), (int, float))]

    if not x_values or not y_values or len(x_values) != len(y_values):
        raise ValueError(f"No valid numeric pairs to plot for scatter chart '{chart.title}'")

    fig, ax = plt.subplots(figsize=(7, 4.5), dpi=150)
    ax.scatter(x_values, y_values, color="#3B6E9E", s=60, edgecolor="white", linewidth=0.8)

    ax.set_title(chart.title, fontsize=12, fontweight="bold", pad=12)
    ax.set_xlabel(chart.x_field.replace("_", " ").title())
    ax.set_ylabel((chart.y_field or "").replace("_", " ").title())
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(True, linestyle="--", alpha=0.3)

    fig.tight_layout()
    return _fig_to_buffer(fig)


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

_RENDERERS = {
    "bar": render_bar_chart,
    "horizontal_bar": render_horizontal_bar_chart,
    "pie": render_pie_chart,
    "line": render_line_chart,
    "scatter": render_scatter_chart,
}


def render_chart(chart: ChartSpec, data: list[dict[str, Any]]) -> tuple[io.BytesIO, float]:
    """
    Dispatch function — routes to the correct renderer based on chart_type.
    Returns (png_buffer, aspect_ratio). Raises NotImplementedError for
    unknown types so report_composer.py can catch and skip gracefully.
    """
    renderer = _RENDERERS.get(chart.chart_type)
    if renderer is None:
        raise NotImplementedError(f"Chart type '{chart.chart_type}' is not implemented")
    return renderer(chart, data)
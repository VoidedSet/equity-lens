"""
Chart Engine — Professional Financial Visualizations
=====================================================
Matplotlib-based chart generation with a premium dark theme,
consistent color palette (one per company), and auto-save.
"""

import os
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import pandas as pd

# ─── Configuration ───────────────────────────────────────────────────────────

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Premium color palette — one per company
COMPANY_COLORS = {
    "Chalet_Hotels": "#FF6B6B",      # Coral Red
    "EIH_Limited": "#4ECDC4",        # Teal
    "Indian_Hotels": "#45B7D1",      # Sky Blue
    "Juniper_Hotels": "#96CEB4",     # Sage Green
    "Lemon_Tree_Hotels": "#FFEAA7",  # Lemon Yellow
}

# Generic palette for non-company charts
ACCENT_COLORS = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7",
                  "#DDA0DD", "#F0A500", "#6C5CE7", "#A8E6CF", "#FF8A5C"]

# Dark theme setup
DARK_BG = "#1a1a2e"
DARK_SURFACE = "#16213e"
DARK_TEXT = "#e8e8e8"
DARK_GRID = "#2a2a4a"
DARK_ACCENT = "#0f3460"


def setup_dark_theme():
    """Apply the premium dark theme globally."""
    plt.rcParams.update({
        "figure.facecolor": DARK_BG,
        "axes.facecolor": DARK_SURFACE,
        "axes.edgecolor": DARK_GRID,
        "axes.labelcolor": DARK_TEXT,
        "text.color": DARK_TEXT,
        "xtick.color": DARK_TEXT,
        "ytick.color": DARK_TEXT,
        "grid.color": DARK_GRID,
        "grid.alpha": 0.3,
        "font.family": "sans-serif",
        "font.size": 11,
        "axes.titlesize": 14,
        "axes.titleweight": "bold",
        "figure.titlesize": 16,
        "figure.titleweight": "bold",
        "legend.facecolor": DARK_SURFACE,
        "legend.edgecolor": DARK_GRID,
        "legend.fontsize": 9,
    })


setup_dark_theme()


def _save_chart(fig, name: str) -> str:
    """Save chart to output directory and return path."""
    filepath = os.path.join(OUTPUT_DIR, f"{name}.png")
    fig.savefig(filepath, dpi=150, bbox_inches="tight",
                facecolor=DARK_BG, edgecolor="none", pad_inches=0.3)
    plt.close(fig)
    return filepath


def _format_number(val):
    """Smart number formatting for chart labels."""
    if pd.isna(val):
        return "N/A"
    if abs(val) >= 1000:
        return f"₹{val:,.0f}"
    if abs(val) < 1:
        return f"{val:.2f}"
    return f"{val:.1f}"


# ─── Chart Types ─────────────────────────────────────────────────────────────

def grouped_bar_chart(
    data: pd.DataFrame,
    title: str,
    ylabel: str = "Value",
    chart_name: str = "grouped_bar",
    show_values: bool = True,
    is_percentage: bool = False,
) -> str:
    """
    Grouped bar chart — companies as groups, periods as bars (or vice versa).

    data: DataFrame with companies as index, periods as columns.
    """
    n_companies = len(data.index)
    n_periods = len(data.columns)

    fig, ax = plt.subplots(figsize=(max(12, n_periods * 1.5), 7))

    x = np.arange(n_periods)
    width = 0.8 / n_companies

    for i, company in enumerate(data.index):
        color = COMPANY_COLORS.get(company, ACCENT_COLORS[i % len(ACCENT_COLORS)])
        bars = ax.bar(x + i * width - (n_companies - 1) * width / 2,
                      data.loc[company].values.astype(float),
                      width, label=company.replace("_", " "),
                      color=color, alpha=0.85, edgecolor="white", linewidth=0.3)

        if show_values and n_periods <= 6:
            for bar in bars:
                height = bar.get_height()
                if not np.isnan(height):
                    label = f"{height:.1f}%" if is_percentage else _format_number(height)
                    ax.annotate(label,
                                xy=(bar.get_x() + bar.get_width() / 2, height),
                                xytext=(0, 4), textcoords="offset points",
                                ha="center", va="bottom", fontsize=7, color=DARK_TEXT)

    ax.set_xlabel("Period", fontsize=12)
    ax.set_ylabel(ylabel, fontsize=12)
    ax.set_title(title, fontsize=15, pad=15)
    ax.set_xticks(x)
    ax.set_xticklabels(data.columns, rotation=45, ha="right", fontsize=9)
    ax.legend(loc="upper left", framealpha=0.9)
    ax.grid(axis="y", alpha=0.2)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    fig.tight_layout()
    return _save_chart(fig, chart_name)


def line_chart(
    data: pd.DataFrame,
    title: str,
    ylabel: str = "Value",
    chart_name: str = "line_chart",
    is_percentage: bool = False,
    show_markers: bool = True,
) -> str:
    """
    Line chart — each row is a series (company or metric).

    data: DataFrame with series as index, periods as columns.
    """
    fig, ax = plt.subplots(figsize=(max(12, len(data.columns) * 0.8), 7))

    for i, series_name in enumerate(data.index):
        color = COMPANY_COLORS.get(series_name, ACCENT_COLORS[i % len(ACCENT_COLORS)])
        values = data.loc[series_name].values.astype(float)
        ax.plot(data.columns, values,
                color=color, linewidth=2.5, marker="o" if show_markers else None,
                markersize=5, label=series_name.replace("_", " "),
                alpha=0.9)

        # Annotate last point
        last_val = values[-1] if not np.isnan(values[-1]) else None
        if last_val is not None:
            label = f"{last_val:.1f}%" if is_percentage else _format_number(last_val)
            ax.annotate(label, xy=(data.columns[-1], last_val),
                        xytext=(10, 0), textcoords="offset points",
                        fontsize=9, color=color, fontweight="bold")

    ax.set_xlabel("Period", fontsize=12)
    ax.set_ylabel(ylabel, fontsize=12)
    ax.set_title(title, fontsize=15, pad=15)
    ax.legend(loc="best", framealpha=0.9)
    ax.grid(axis="both", alpha=0.2)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    plt.xticks(rotation=45, ha="right", fontsize=9)
    fig.tight_layout()
    return _save_chart(fig, chart_name)


def radar_chart(
    values: dict,
    title: str,
    chart_name: str = "radar_chart",
) -> str:
    """
    Radar/spider chart for scorecard visualization.

    values: dict of {axis_label: score (0-100)}
    """
    categories = list(values.keys())
    scores = list(values.values())
    n = len(categories)

    angles = [x / float(n) * 2 * np.pi for x in range(n)]
    angles += angles[:1]
    scores += scores[:1]

    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))
    ax.set_facecolor(DARK_SURFACE)

    ax.fill(angles, scores, color="#4ECDC4", alpha=0.25)
    ax.plot(angles, scores, color="#4ECDC4", linewidth=2.5)

    # Add score labels
    for angle, score, cat in zip(angles[:-1], scores[:-1], categories):
        ax.text(angle, score + 5, f"{score:.0f}", ha="center", va="center",
                fontsize=10, fontweight="bold", color="#4ECDC4")

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories, fontsize=10, color=DARK_TEXT)
    ax.set_ylim(0, 100)
    ax.set_yticks([20, 40, 60, 80, 100])
    ax.set_yticklabels(["20", "40", "60", "80", "100"], fontsize=8, color=DARK_TEXT)
    ax.spines["polar"].set_color(DARK_GRID)
    ax.grid(color=DARK_GRID, alpha=0.3)
    ax.set_title(title, fontsize=15, pad=20, color=DARK_TEXT)

    fig.patch.set_facecolor(DARK_BG)
    fig.tight_layout()
    return _save_chart(fig, chart_name)


def heatmap_chart(
    data: pd.DataFrame,
    title: str,
    chart_name: str = "heatmap",
    fmt: str = ".1f",
) -> str:
    """
    Heatmap for ranking/comparison matrices.

    data: DataFrame with companies as rows, metrics as columns.
    """
    fig, ax = plt.subplots(figsize=(max(10, len(data.columns) * 1.5), max(5, len(data.index) * 0.8)))

    # Normalize for color mapping
    norm_data = data.apply(lambda x: (x - x.min()) / (x.max() - x.min() + 1e-10), axis=0)

    im = ax.imshow(norm_data.values.astype(float), cmap="RdYlGn", aspect="auto", alpha=0.85)

    ax.set_xticks(np.arange(len(data.columns)))
    ax.set_yticks(np.arange(len(data.index)))
    ax.set_xticklabels([c.replace("_", " ") for c in data.columns], rotation=45, ha="right", fontsize=10)
    ax.set_yticklabels([c.replace("_", " ") for c in data.index], fontsize=10)

    # Annotate cells
    for i in range(len(data.index)):
        for j in range(len(data.columns)):
            val = data.iloc[i, j]
            if not np.isnan(val):
                text_color = "black" if norm_data.iloc[i, j] > 0.5 else "white"
                ax.text(j, i, f"{val:{fmt}}", ha="center", va="center",
                        fontsize=9, color=text_color, fontweight="bold")

    ax.set_title(title, fontsize=15, pad=15)
    fig.tight_layout()
    return _save_chart(fig, chart_name)


def single_bar_chart(
    data: dict,
    title: str,
    ylabel: str = "Value",
    chart_name: str = "single_bar",
    is_percentage: bool = False,
    horizontal: bool = False,
) -> str:
    """
    Simple bar chart — dict of {label: value}.
    """
    fig, ax = plt.subplots(figsize=(10, 6))

    labels = [k.replace("_", " ") for k in data.keys()]
    values = list(data.values())
    colors = [COMPANY_COLORS.get(k, ACCENT_COLORS[i % len(ACCENT_COLORS)])
              for i, k in enumerate(data.keys())]

    if horizontal:
        bars = ax.barh(labels, values, color=colors, alpha=0.85, edgecolor="white", linewidth=0.3)
        ax.set_xlabel(ylabel, fontsize=12)
        for bar, val in zip(bars, values):
            if not np.isnan(val):
                label = f"{val:.1f}%" if is_percentage else _format_number(val)
                ax.text(val + (max(values) * 0.02), bar.get_y() + bar.get_height() / 2,
                        label, va="center", fontsize=10, color=DARK_TEXT)
    else:
        bars = ax.bar(labels, values, color=colors, alpha=0.85, edgecolor="white", linewidth=0.3)
        ax.set_ylabel(ylabel, fontsize=12)
        for bar, val in zip(bars, values):
            if not np.isnan(val):
                label = f"{val:.1f}%" if is_percentage else _format_number(val)
                ax.text(bar.get_x() + bar.get_width() / 2, val + (max(values) * 0.02),
                        label, ha="center", fontsize=10, color=DARK_TEXT)

    ax.set_title(title, fontsize=15, pad=15)
    ax.grid(axis="y" if not horizontal else "x", alpha=0.2)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    plt.xticks(rotation=30, ha="right") if not horizontal else None
    fig.tight_layout()
    return _save_chart(fig, chart_name)


def multi_line_chart(
    series_dict: dict,
    x_labels: list,
    title: str,
    ylabel: str = "Value",
    chart_name: str = "multi_line",
) -> str:
    """
    Multiple line series on one chart.

    series_dict: {series_name: list_of_values}
    x_labels: shared x-axis labels
    """
    fig, ax = plt.subplots(figsize=(max(12, len(x_labels) * 0.8), 7))

    for i, (name, vals) in enumerate(series_dict.items()):
        color = COMPANY_COLORS.get(name, ACCENT_COLORS[i % len(ACCENT_COLORS)])
        ax.plot(x_labels, vals, color=color, linewidth=2.5, marker="o",
                markersize=5, label=name.replace("_", " "), alpha=0.9)

    ax.set_xlabel("Period", fontsize=12)
    ax.set_ylabel(ylabel, fontsize=12)
    ax.set_title(title, fontsize=15, pad=15)
    ax.legend(loc="best", framealpha=0.9)
    ax.grid(axis="both", alpha=0.2)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.xticks(rotation=45, ha="right", fontsize=9)
    fig.tight_layout()
    return _save_chart(fig, chart_name)

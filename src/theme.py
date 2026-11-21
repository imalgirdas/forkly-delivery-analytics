"""
Script:   theme.py
Purpose:  Shared chart style for all notebooks and the dashboard
          (navy, white and green). Import with:
              import sys; sys.path.append(str(BASE / "src"))
              from theme import *
              apply_theme()
"""
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
from matplotlib import font_manager
from matplotlib.colors import LinearSegmentedColormap

# Colours ----
NAVY = "#0B2545"        # main brand colour, primary series
NAVY_2 = "#1D3E6E"
STEEL = "#5B7BA6"       # secondary blue
NAVY_LIGHT = "#B4C4DA"  # comparison / previous period
GREEN = "#1FA67A"       # accent, highlights, "good"
GREEN_DARK = "#12765A"
MINT = "#A3DCC6"
GREY = "#8A94A6"        # neutral / "other"
GREY_LIGHT = "#D7DCE3"
ALERT = "#C8553D"       # only for negative values and problem periods

TEXT = "#16202E"
TEXT_MUTED = "#5F6B7A"
GRID = "#E6EAF0"
BG = "#FFFFFF"

CATEGORICAL = [NAVY, GREEN, STEEL, MINT, GREY, NAVY_LIGHT, GREEN_DARK, GREY_LIGHT]
YEAR_COLORS = {2021: "#C6D3E5", 2022: "#93AACB", 2023: "#5B7BA6", 2024: "#2C4F80", 2025: NAVY}
RATING_COLORS = [ALERT, "#E3A08F", GREY_LIGHT, MINT, GREEN]  # 1 to 5 stars

CMAP_NAVY = LinearSegmentedColormap.from_list("forkly_navy", ["#F4F7FB", "#B4C4DA", "#3F6496", NAVY])
CMAP_GREEN = LinearSegmentedColormap.from_list("forkly_green", ["#F2FAF6", MINT, GREEN, "#0D5E46"])
CMAP_DIVERGING = LinearSegmentedColormap.from_list("forkly_div", [GREEN, "#F5F7FA", NAVY])

SOURCE = "Source: Forkly (simulated data), 2021-2025"


def _pick_font():
    """Use the first nice font that is installed (Segoe UI on Windows)."""
    installed = set(font_manager.get_font_names())
    for name in ["Segoe UI", "Inter", "Helvetica Neue", "Arial", "DejaVu Sans"]:
        if name in installed:
            return name
    return "DejaVu Sans"


def apply_theme():
    """Set matplotlib defaults for every chart in the project."""
    mpl.rcParams.update({
        "font.family": _pick_font(),
        "font.size": 10,
        "figure.facecolor": BG,
        "figure.dpi": 110,
        "savefig.facecolor": BG,
        "savefig.dpi": 200,
        "savefig.bbox": "tight",
        "axes.facecolor": BG,
        "axes.edgecolor": GRID,
        "axes.linewidth": 1.0,
        "axes.labelcolor": TEXT_MUTED,
        "axes.labelsize": 9.5,
        "axes.titlesize": 13,
        "axes.titleweight": "bold",
        "axes.titlecolor": TEXT,
        "axes.titlelocation": "left",
        "axes.titlepad": 12,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.spines.left": False,
        "axes.grid": True,
        "axes.grid.axis": "y",
        "axes.axisbelow": True,
        "axes.prop_cycle": mpl.cycler(color=CATEGORICAL),
        "grid.color": GRID,
        "grid.linewidth": 0.8,
        "xtick.color": TEXT_MUTED,
        "ytick.color": TEXT_MUTED,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "xtick.major.size": 0,
        "ytick.major.size": 0,
        "xtick.major.pad": 6,
        "ytick.major.pad": 6,
        "legend.frameon": False,
        "legend.fontsize": 9,
        "legend.title_fontsize": 9,
        "lines.linewidth": 2.2,
        "lines.solid_capstyle": "round",
        "patch.linewidth": 0,
        "text.color": TEXT,
    })


# Titles and notes ----
def title(ax, text, subtitle=None, subtitle_color=TEXT_MUTED, subtitle_weight="normal"):
    """Bold title with an optional subtitle underneath (top left of the chart)."""
    ax.set_title(text, pad=28 if subtitle else 12)
    if subtitle:
        ax.annotate(subtitle, xy=(0, 1), xycoords="axes fraction", xytext=(0, 9), textcoords="offset points",
                    fontsize=9.5, color=subtitle_color, weight=subtitle_weight, va="bottom", ha="left")


def fig_header(fig, text, subtitle=None, y=1.02):
    """Title for a whole figure (dashboard pages, multi-chart figures)."""
    fig.text(0.01, y, text, fontsize=17, weight="bold", color=NAVY, ha="left", va="bottom")
    if subtitle:
        fig.text(0.01, y - 0.005, subtitle, fontsize=10.5, color=TEXT_MUTED, ha="left", va="top")


def source_note(fig, text=SOURCE):
    fig.text(0.01, -0.02, text, fontsize=8, color=GREY, ha="left", va="top")


def legend_top(ax, ncol=4, loc="upper right", **kwargs):
    """Compact one-row legend inside the top of the plot area."""
    return ax.legend(loc=loc, ncol=ncol, handlelength=1.2, columnspacing=1.2, **kwargs)


def hbar_style(ax):
    """Horizontal bar charts: vertical grid only."""
    ax.grid(axis="x", visible=True)
    ax.grid(axis="y", visible=False)
    return ax


def clean_heatmap(ax):
    ax.grid(False)
    ax.tick_params(length=0)
    return ax


def label_bars(ax, bars, fmt="{:,.0f}", color=TEXT, inside=False, fontsize=8.5, padding=3):
    """Value labels on bars. fmt is a format string or a function."""
    f = fmt if callable(fmt) else fmt.format
    ax.bar_label(bars, labels=[f(b.get_height()) for b in bars], padding=padding, fontsize=fontsize,
                 color=color, label_type="center" if inside else "edge")


def label_hbars(ax, bars, fmt="{:,.0f}", color=TEXT, fontsize=8.5, padding=3):
    f = fmt if callable(fmt) else fmt.format
    ax.bar_label(bars, labels=[f(b.get_width()) for b in bars], padding=padding, fontsize=fontsize, color=color)


def zero_line(ax, axis="y"):
    (ax.axhline if axis == "y" else ax.axvline)(0, color=TEXT_MUTED, lw=0.9, zorder=1)


# Number formats ----
def _sign(v):
    return "-" if v < 0 else ""

# axis tick formats (":g" drops trailing zeros, so 1.25 stays 1.25 and 2.0 becomes 2)
eur_m = mtick.FuncFormatter(lambda v, p=None: f"{_sign(v)}€{round(abs(v) / 1e6, 3):g}M")
eur_k = mtick.FuncFormatter(lambda v, p=None: f"{_sign(v)}€{round(abs(v) / 1e3, 1):,g}k")
eur = mtick.FuncFormatter(lambda v, p=None: f"{_sign(v)}€{round(abs(v), 2):,g}")
thousands = mtick.FuncFormatter(lambda v, p=None: f"{round(v / 1e3, 1):,g}k" if abs(v) >= 1000 else f"{v:,.0f}")
pct = mtick.FuncFormatter(lambda v, p=None: f"{round(v, 1):g}%")


def fmt_eur(v, decimals=2):
    return f"{_sign(v)}€{abs(v):,.{decimals}f}"


# Saving ----
def save_fig(fig, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path)


# Plotly (Dash dashboard) ----
# same colours for the interactive version in dashboard_dash.py.
# plotly is only imported inside plotly_theme(), so the notebooks still run without it
FONT_STACK = '"Segoe UI", Inter, "Helvetica Neue", Arial, sans-serif'
SCALE_NAVY = [[0, "#F4F7FB"], [0.33, "#B4C4DA"], [0.66, "#3F6496"], [1, NAVY]]
SCALE_GREEN = [[0, "#F2FAF6"], [0.33, MINT], [0.66, GREEN], [1, "#0D5E46"]]


def plotly_theme():
    """Register the "forkly" Plotly template and make it the default."""
    import plotly.graph_objects as go
    import plotly.io as pio

    axis = dict(showline=False, zeroline=False, ticks="", gridcolor=GRID, linecolor=GRID, automargin=True,
                tickfont=dict(size=11, color=TEXT_MUTED), title=dict(font=dict(size=11, color=TEXT_MUTED)))
    pio.templates["forkly"] = go.layout.Template(layout=dict(
        font=dict(family=FONT_STACK, size=12, color=TEXT),
        colorway=CATEGORICAL,
        paper_bgcolor=BG,
        plot_bgcolor=BG,
        margin=dict(l=50, r=16, t=36, b=36),
        xaxis={**axis, "showgrid": False},
        yaxis={**axis, "showgrid": True},
        legend=dict(orientation="h", x=0, y=1.02, xanchor="left", yanchor="bottom", bgcolor="rgba(0,0,0,0)",
                    font=dict(size=11, color=TEXT_MUTED), title=dict(text="")),
        hoverlabel=dict(bgcolor=NAVY, bordercolor=NAVY, font=dict(family=FONT_STACK, color=BG, size=12)),
        bargap=0.3,
        colorscale=dict(sequential=SCALE_NAVY),
    ))
    pio.templates.default = "forkly"

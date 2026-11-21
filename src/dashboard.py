"""
Script:   dashboard.py
Purpose:  Build the 5-page static dashboard with matplotlib + seaborn
            1 Executive overview        2 Customers & retention
            3 Restaurants & cities      4 Delivery operations
            5 Marketing & unit economics
Input:    Forkly/Data_clean/*.csv (through analysis.py), theme.py
Output:   Forkly/output/dashboard/page_1_*.png ... page_5_*.png
          Forkly/output/dashboard/Forkly_dashboard.pdf
          Forkly/output/dashboard/Forkly_dashboard.html (one file, tabs across the 5 pages)
"""
import base64
import html

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import FancyBboxPatch, Rectangle

from analysis import YEARS, build_all
from load import DASH_DIR
from theme import *

PAGE_SIZE = (16, 9)
N_PAGES = 5
NAV_LABELS = ["Overview", "Customers", "Restaurants", "Operations", "Marketing"]


# Page layout ----
def new_page(page_no, page_title, subtitle):
    """Blank page with a navy header band, page number and footer."""
    fig = plt.figure(figsize=PAGE_SIZE)
    fig.patches.append(Rectangle((0, 0.925), 1, 0.075, transform=fig.transFigure, color=NAVY, zorder=0))
    fig.text(0.02, 0.962, "forkly", fontsize=18, weight="bold", color=GREEN, va="center")
    fig.text(0.085, 0.962, page_title, fontsize=17, weight="bold", color=BG, va="center")
    # page tabs (current page in green), same order as the HTML navigation
    renderer = fig.canvas.get_renderer()
    x = 0.98
    for i, label in reversed(list(enumerate(NAV_LABELS, start=1))):
        current = i == page_no
        txt = fig.text(x, 0.962, label, fontsize=10.5, va="center", ha="right",
                       color=GREEN if current else NAVY_LIGHT, weight="bold" if current else "normal")
        width = txt.get_window_extent(renderer).width / fig.bbox.width
        if current:
            fig.patches.append(Rectangle((x - width, 0.926), width, 0.006, transform=fig.transFigure,
                                         color=GREEN, zorder=1))
        x -= width + 0.02
    fig.text(0.02, 0.905, subtitle, fontsize=10.5, color=TEXT_MUTED, va="center")
    fig.text(0.02, 0.018, "Source: Forkly (simulated data, fictional company), 2021-2025. GMV = value of items sold "
             "on non-cancelled orders.", fontsize=7.5, color=GREY)
    fig.text(0.98, 0.018, "Food & grocery delivery analytics", fontsize=7.5, color=GREY, ha="right")
    return fig


def kpi_cards(fig, cards, y=0.765, h=0.115, x0=0.02, x1=0.98, gap=0.012):
    """Row of KPI cards: (label, value, change text, good?) tuples."""
    w = (x1 - x0 - gap * (len(cards) - 1)) / len(cards)
    for i, (label, value, change, good) in enumerate(cards):
        x = x0 + i * (w + gap)
        fig.patches.append(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.008",
                                          transform=fig.transFigure, fc="#F4F7FB", ec="none", zorder=0))
        fig.patches.append(Rectangle((x, y), 0.004, h, transform=fig.transFigure, color=GREEN if good is not False else ALERT))
        fig.text(x + 0.012, y + h - 0.02, label.upper(), fontsize=8, color=TEXT_MUTED, weight="bold", va="top")
        fig.text(x + 0.012, y + h * 0.52, value, fontsize=19, color=NAVY, weight="bold", va="center")
        if change:
            color = GREY if good is None else (GREEN_DARK if good else ALERT)
            fig.text(x + 0.012, y + 0.012, change, fontsize=8.5, color=color, weight="bold", va="bottom")


def chart_grid(fig, rows=2, cols=3, top=0.67, bottom=0.075, left=0.045, **kw):
    return fig.add_gridspec(rows, cols, left=left, right=0.975, top=top, bottom=bottom,
                            hspace=kw.pop("hspace", 0.55), wspace=kw.pop("wspace", 0.28), **kw)


def change(cur, prev, kind="pct", higher_is_better=True):
    """Text and colour flag for a 2025 vs 2024 change."""
    diff = cur - prev
    arrow = "▲" if diff > 0 else "▼"
    good = (diff > 0) == higher_is_better
    if kind == "pct":
        txt = f"{arrow} {diff / prev:+.1%} vs 2024"
    elif kind == "pp":
        txt = f"{arrow} {diff:+.1f} pp vs 2024"
    else:
        txt = f"{arrow} {diff:+.2f} vs 2024"
    return txt, good


def small_title(ax, text, subtitle=None):
    ax.set_title(text, fontsize=11.5, pad=22 if subtitle else 8)
    if subtitle:
        ax.annotate(subtitle, xy=(0, 1), xycoords="axes fraction", xytext=(0, 6), textcoords="offset points",
                    fontsize=8.5, color=TEXT_MUTED, va="bottom")


def year_bars(ax, series, fmt, highlight=2025, colors=None, ylim=None):
    colors = colors or [NAVY if y == highlight else NAVY_LIGHT for y in series.index]
    bars = ax.bar(series.index, series.values, color=colors, width=0.62)
    label_bars(ax, bars, fmt, fontsize=8)
    ax.set_xticks(series.index)
    if ylim:
        ax.set_ylim(*ylim)
    return bars


# Page 1 ----
def page_executive(t):
    k = t["kpi_by_year"]
    c, p = k.loc[2025], k.loc[2024]
    fig = new_page(1, "Executive overview", "Five years of Forkly: from a loss-making launch to a profitable, "
                                             "12-city delivery platform")
    kpi_cards(fig, [
        ("GMV 2025", f"€{c.gmv / 1e6:.2f}M", *change(c.gmv, p.gmv)),
        ("Orders", f"{c.orders / 1e3:.1f}k", *change(c.orders, p.orders)),
        ("Average basket", fmt_eur(c.aov), *change(c.aov, p.aov)),
        ("Active customers", f"{c.active_customers / 1e3:.1f}k", *change(c.active_customers, p.active_customers)),
        ("Contribution margin", f"{c['contribution_margin_%']:.1f}%",
         *change(c["contribution_margin_%"], p["contribution_margin_%"], "pp")),
        ("Delivery rating", f"{c.delivery_rating:.2f}", *change(c.delivery_rating, p.delivery_rating, "abs")),
    ])
    gs = chart_grid(fig)

    ax = fig.add_subplot(gs[0, :2])
    m = t["monthly"]
    ax.plot(m.index, m["gmv"], color=NAVY)
    ax.fill_between(m.index, m["gmv"], color=NAVY, alpha=0.06)
    peak = m["gmv"].idxmax()
    ax.scatter([peak], [m.loc[peak, "gmv"]], color=GREEN, s=40, zorder=3)
    ax.annotate(f"Peak {peak:%b %Y}: €{m.loc[peak, 'gmv'] / 1e3:.0f}k", (peak, m.loc[peak, "gmv"]),
                xytext=(-10, 4), textcoords="offset points", ha="right", fontsize=8.5, color=GREEN_DARK, weight="bold")
    ax.yaxis.set_major_formatter(eur_k); ax.set_ylim(0, m["gmv"].max() * 1.15)
    small_title(ax, "Monthly GMV", "Strong December peaks; growth every year")

    ax = fig.add_subplot(gs[0, 2])
    g = t["gmv_by_city_group"]
    ax.bar(g.index, g["Launch cities"], color=NAVY, width=0.62, label="Launch cities")
    ax.bar(g.index, g["Expansion cities"], bottom=g["Launch cities"], color=GREEN, width=0.62,
           label="Expansion cities", edgecolor=BG, linewidth=1)
    for x in g.index:
        ax.text(x, g.loc[x].sum() * 1.02, f"€{g.loc[x].sum() / 1e6:.1f}M", ha="center", fontsize=8, weight="bold")
    ax.yaxis.set_major_formatter(eur_m); ax.set_xticks(g.index); ax.set_ylim(0, g.sum(axis=1).max() * 1.18)
    legend_top(ax, ncol=1, loc="upper left", fontsize=8)
    small_title(ax, "GMV by market", "Growth comes from cities added since 2022")

    ax = fig.add_subplot(gs[1, 0])
    ue = t["unit_economics"]["contribution"]
    year_bars(ax, ue, lambda v: fmt_eur(v), colors=[ALERT if v < 0 else (NAVY if y == 2025 else NAVY_LIGHT)
                                                    for y, v in ue.items()])
    zero_line(ax); ax.yaxis.set_major_formatter(eur)
    small_title(ax, "Contribution per order", "Profitable per order since 2023")

    ax = fig.add_subplot(gs[1, 1])
    year_bars(ax, k["late_rate_%"], "{:.1f}%", colors=[ALERT if y == 2022 else (NAVY if y == 2025 else NAVY_LIGHT)
                                                       for y in k.index])
    ax.yaxis.set_major_formatter(pct); ax.set_ylim(0, k["late_rate_%"].max() * 1.2)
    small_title(ax, "Late deliveries", "2022 operations crunch, then steady recovery")

    ax = fig.add_subplot(gs[1, 2])
    for col, color, name in [("promo_order_%", NAVY, "Promo"), ("plus_order_%", GREEN, "Plus"),
                             ("grocery_order_%", STEEL, "Grocery")]:
        ax.plot(k.index, k[col], marker="o", ms=5, color=color)
        ax.annotate(f"{name} {k[col].iloc[-1]:.0f}%", (2025, k[col].iloc[-1]), xytext=(7, 0), textcoords="offset points",
                    va="center", fontsize=8.5, color=color, weight="bold")
    ax.set_xticks(k.index); ax.set_xlim(2020.7, 2026.4); ax.yaxis.set_major_formatter(pct)
    small_title(ax, "Business mix", "% of orders")
    return fig


# Page 2 ----
def page_customers(t):
    k = t["kpi_by_year"]
    c, p = k.loc[2025], k.loc[2024]
    yoy, nr, seg = t["yoy_retention"], t["new_vs_returning"], t["rfm_segments"]
    plus = t["plus_vs_non_member"]
    fig = new_page(2, "Customers & retention", "Who orders, how often they come back and which customers carry "
                                                "the revenue")
    kpi_cards(fig, [
        ("New customers 2025", f"{c.new_customers / 1e3:.1f}k", *change(c.new_customers, p.new_customers)),
        ("Retained 2024 → 2025", f"{yoy[2024]:.0f}%", *change(yoy[2024], yoy[2023], "pp")),
        ("Orders from returning", f"{nr.loc[2025, 'Returning customer']:.0f}%",
         *change(nr.loc[2025, "Returning customer"], nr.loc[2024, "Returning customer"], "pp")),
        ("Orders per customer", f"{c.orders_per_customer:.2f}", *change(c.orders_per_customer, p.orders_per_customer, "abs")),
        ("Champions share of GMV", f"{seg.loc['Champions', 'gmv_%']:.0f}%",
         f"{seg.loc['Champions', 'customers_%']:.0f}% of customers", None),
    ])
    gs = chart_grid(fig, width_ratios=[1.45, 1, 1])

    ax = fig.add_subplot(gs[:, 0])
    coh = t["cohort_retention"]
    sns.heatmap(coh, cmap=CMAP_NAVY, annot=True, fmt=".0f", cbar=False, linewidths=1, linecolor=BG,
                annot_kws={"fontsize": 7}, ax=ax)
    clean_heatmap(ax)
    ax.set_xlabel(""); ax.set_ylabel("")
    ax.tick_params(axis="both", labelsize=7.5); ax.tick_params(axis="y", rotation=0)
    small_title(ax, "Cohort retention (%)", "Share of each signup quarter ordering again N quarters later (columns)")

    ax = fig.add_subplot(gs[0, 1])
    ax.bar(nr.index, nr["Returning customer"], color=NAVY, width=0.62, label="Returning")
    ax.bar(nr.index, nr["New customer"], bottom=nr["Returning customer"], color=GREEN, width=0.62, label="New",
           edgecolor=BG, linewidth=1)
    for x, v in nr["Returning customer"].items():
        if v > 8:
            ax.text(x, v / 2, f"{v:.0f}%", ha="center", va="center", color=BG, fontsize=8, weight="bold")
    ax.set_xticks(nr.index); ax.yaxis.set_major_formatter(pct)
    legend_top(ax, ncol=2, loc="lower left", bbox_to_anchor=(0, 1.0), fontsize=8)
    small_title(ax, "Orders: returning vs new", " ")

    ax = fig.add_subplot(gs[0, 2])
    bars = ax.bar(["Non-member", "Plus member"], plus.loc[["Non-member", "Plus member"], "orders_per_customer"],
                  color=[GREY_LIGHT, GREEN], width=0.55)
    label_bars(ax, bars, "{:.1f}", fontsize=9)
    small_title(ax, "Forkly Plus: orders per customer", "2025, members vs non-members")

    ax = fig.add_subplot(gs[1, 1])
    y = np.arange(len(seg))
    ax.barh(y - 0.19, seg["customers_%"], height=0.38, color=NAVY_LIGHT, label="Customers")
    bars = ax.barh(y + 0.19, seg["gmv_%"], height=0.38, color=NAVY, label="GMV")
    label_hbars(ax, bars, "{:.0f}%", fontsize=7.5)
    ax.set_yticks(y, seg.index, fontsize=8); ax.invert_yaxis(); hbar_style(ax); ax.xaxis.set_major_formatter(pct)
    legend_top(ax, ncol=2, loc="lower right", fontsize=8)
    small_title(ax, "RFM segments", "% of customers vs % of last-12-month GMV")

    ax = fig.add_subplot(gs[1, 2])
    mix = t["channel_mix"].loc[[2022, 2025]].T.sort_values(2025)
    y = np.arange(len(mix))
    ax.barh(y - 0.19, mix[2022], height=0.38, color=NAVY_LIGHT, label="2022")
    bars = ax.barh(y + 0.19, mix[2025], height=0.38, color=[GREEN if i == "Referral" else NAVY for i in mix.index], label="2025")
    label_hbars(ax, bars, "{:.0f}%", fontsize=7.5)
    ax.set_yticks(y, mix.index, fontsize=8); hbar_style(ax); ax.xaxis.set_major_formatter(pct)
    legend_top(ax, ncol=2, loc="lower right", fontsize=8)
    small_title(ax, "Signups by channel", "Share of new customers, 2022 vs 2025")
    return fig


# Page 3 ----
def page_restaurants(t):
    cz, cy, par = t["cuisine_performance"], t["gmv_by_city_year"], t["restaurant_pareto"]
    k = t["kpi_by_year"]
    top20 = par.loc[(par["restaurants_%"] - 20).abs().idxmin(), "cum_gmv_%"]
    grocery = cz.loc["Grocery", "share_2025_%"]
    fig = new_page(3, "Restaurants & cities", "Where GMV is made: markets, cuisines and partner concentration")
    city25 = cy[2025].sort_values(ascending=False)
    kpi_cards(fig, [
        ("Live cities", f"{(cy[2025] > 0).sum()}", f"{(cy[2024] > 0).sum()} in 2024", None),
        ("Largest market", city25.index[0], f"{city25.iloc[0] / city25.sum():.0%} of 2025 GMV", None),
        ("Grocery share of GMV", f"{grocery:.0f}%", "launched Feb 2024", True),
        ("Top 20% of partners", f"{top20:.0f}%", "share of 2025 GMV", None),
        ("Food rating", f"{k.loc[2025, 'food_rating']:.2f}",
         *change(k.loc[2025, "food_rating"], k.loc[2024, "food_rating"], "abs")),
    ])
    gs = chart_grid(fig, width_ratios=[1, 1.25, 1], left=0.075, wspace=0.45)

    ax = fig.add_subplot(gs[0, 0])
    s = city25.sort_values()
    bars = ax.barh(s.index, s.values, color=[GREEN if v == s.max() else NAVY for v in s.values], height=0.65)
    label_hbars(ax, bars, lambda v: f"€{v / 1e3:.0f}k", fontsize=7.5)
    ax.tick_params(axis="y", labelsize=8); hbar_style(ax); ax.xaxis.set_major_formatter(eur_k)
    small_title(ax, "GMV by city, 2025")

    ax = fig.add_subplot(gs[0, 1])
    cyo = cy.loc[cy.sum(axis=1).sort_values(ascending=False).index]
    sns.heatmap(cyo / 1e3, cmap=CMAP_NAVY, annot=True, fmt=",.0f", cbar=False, linewidths=1.2, linecolor=BG,
                mask=cyo == 0, annot_kws={"fontsize": 7}, ax=ax)
    clean_heatmap(ax); ax.set_xlabel(""); ax.set_ylabel(""); ax.tick_params(labelsize=7.5)
    small_title(ax, "GMV by city and year (€k)", "Blank = not launched yet")

    ax = fig.add_subplot(gs[0, 2])
    ax.plot(par["restaurants_%"], par["cum_gmv_%"], color=NAVY)
    ax.fill_between(par["restaurants_%"], par["cum_gmv_%"], color=NAVY, alpha=0.06)
    ax.plot([0, 100], [0, 100], color=GREY_LIGHT, lw=1, ls="--")
    ax.scatter([20], [top20], color=GREEN, s=35, zorder=3)
    ax.annotate(f"Top 20% = {top20:.0f}% of GMV", (20, top20), xytext=(26, top20 - 14), fontsize=8.5,
                color=GREEN_DARK, weight="bold")
    ax.set_xlim(0, 100); ax.set_ylim(0, 102); ax.xaxis.set_major_formatter(pct); ax.yaxis.set_major_formatter(pct)
    ax.set_xlabel("Restaurants ranked by GMV", fontsize=8)
    small_title(ax, "GMV concentration, 2025")

    ax = fig.add_subplot(gs[1, 0])
    s = cz[2025].sort_values().tail(10)
    bars = ax.barh(s.index, s.values, color=[GREEN if i == "Grocery" else NAVY for i in s.index], height=0.65)
    label_hbars(ax, bars, lambda v: f"€{v / 1e3:.0f}k", fontsize=7.5)
    ax.tick_params(axis="y", labelsize=8); hbar_style(ax); ax.xaxis.set_major_formatter(eur_k)
    small_title(ax, "Top 10 categories by GMV, 2025")

    ax = fig.add_subplot(gs[1, 1])
    g = cz["growth_2023_2025_%"].dropna().sort_values()
    bars = ax.barh(g.index, g.values, color=[GREEN if v >= 25 else NAVY for v in g.values], height=0.65)
    label_hbars(ax, bars, "{:+.0f}%", fontsize=7)
    ax.tick_params(axis="y", labelsize=7.5); hbar_style(ax); ax.xaxis.set_major_formatter(pct)
    small_title(ax, "GMV growth by cuisine, 2023 → 2025", "Green = 25% or more")

    ax = fig.add_subplot(gs[1, 2])
    a = cz["aov"].sort_values().tail(8)
    bars = ax.barh(a.index, a.values, color=[GREEN if i == "Grocery" else STEEL for i in a.index], height=0.65)
    label_hbars(ax, bars, lambda v: fmt_eur(v), fontsize=7.5)
    ax.tick_params(axis="y", labelsize=8); hbar_style(ax); ax.xaxis.set_major_formatter(eur)
    small_title(ax, "Highest average baskets", "All years")
    return fig


# Page 4 ----
def page_operations(t):
    k, sup, m = t["kpi_by_year"], t["support"], t["monthly"]
    c, p = k.loc[2025], k.loc[2024]
    fig = new_page(4, "Delivery operations", "Speed, punctuality, cancellations and customer support")
    kpi_cards(fig, [
        ("Avg delivery time", f"{c.avg_delivery_min:.1f} min",
         *change(c.avg_delivery_min, p.avg_delivery_min, "abs", higher_is_better=False)),
        ("Late deliveries", f"{c['late_rate_%']:.1f}%", *change(c["late_rate_%"], p["late_rate_%"], "pp", False)),
        ("Cancellation rate", f"{c['cancel_rate_%']:.1f}%", *change(c["cancel_rate_%"], p["cancel_rate_%"], "pp", False)),
        ("Tickets per 100 orders", f"{sup.loc[2025, 'tickets_per_100_orders']:.1f}",
         *change(sup.loc[2025, "tickets_per_100_orders"], sup.loc[2024, "tickets_per_100_orders"], "abs", False)),
        ("Median ticket resolution", f"{sup.loc[2025, 'median_resolution_h']:.1f} h",
         *change(sup.loc[2025, "median_resolution_h"], sup.loc[2024, "median_resolution_h"], "abs", False)),
    ])
    gs = chart_grid(fig)

    ax = fig.add_subplot(gs[0, :2])
    ax.plot(m.index, m["late_rate"], color=NAVY, label="Late deliveries (%)")
    ax.fill_between(m.index, m["late_rate"], color=NAVY, alpha=0.06)
    crunch = m.loc["2022", "late_rate"]
    ax.axvspan(pd.Timestamp("2022-01-01"), pd.Timestamp("2022-12-31"), color=ALERT, alpha=0.06, lw=0)
    ax.text(pd.Timestamp("2022-07-01"), m["late_rate"].max() * 1.02, "2022 operations crunch", ha="center",
            fontsize=8.5, color=ALERT, weight="bold")
    ax.yaxis.set_major_formatter(pct); ax.set_ylim(0, m["late_rate"].max() * 1.12)
    small_title(ax, "Late delivery rate by month", "More than 5 minutes after the promised time")

    ax = fig.add_subplot(gs[0, 2])
    r = t["rating_by_delay"]["delivery_rating"]
    colors = [GREEN, GREEN, NAVY_LIGHT, STEEL, NAVY_2, NAVY, ALERT]
    bars = ax.bar(range(len(r)), r.values, color=colors, width=0.65)
    label_bars(ax, bars, "{:.1f}", fontsize=7.5)
    ax.set_xticks(range(len(r)), [s.replace(" min", "") for s in r.index.astype(str)], rotation=35, ha="right", fontsize=7.5)
    ax.set_ylim(1, 5)
    small_title(ax, "Delivery rating vs promised time", "Average stars")

    ax = fig.add_subplot(gs[1, 0])
    w = t["late_by_weather"]
    bars = ax.bar(w.index, w.values, color=[NAVY_LIGHT, STEEL, NAVY, NAVY_2], width=0.6)
    label_bars(ax, bars, "{:.1f}%", fontsize=8)
    ax.yaxis.set_major_formatter(pct)
    small_title(ax, "Late rate by weather", "All years")

    ax = fig.add_subplot(gs[1, 1])
    v = t["vehicle_mix"][["E-bike", "Bicycle", "Scooter", "Car"]]
    bottom = np.zeros(len(v))
    for col, color in zip(v.columns, [GREEN, NAVY, STEEL, GREY_LIGHT]):
        ax.bar(v.index, v[col], bottom=bottom, color=color, width=0.62, label=col, edgecolor=BG, linewidth=1)
        bottom += v[col].values
    ax.set_xticks(v.index); ax.yaxis.set_major_formatter(pct)
    ax.set_ylim(0, 118); ax.set_yticks([0, 25, 50, 75, 100])
    legend_top(ax, ncol=4, loc="upper center", fontsize=7.5)
    small_title(ax, "Deliveries by vehicle", "E-bikes replaced bicycles")

    ax = fig.add_subplot(gs[1, 2])
    cr = t["cancel_reasons"].loc[[2022, 2025]].T
    cr = cr.div(cr.sum()) * 100
    cr = cr.sort_values(2022).tail(6)
    y = np.arange(len(cr))
    ax.barh(y - 0.19, cr[2022], height=0.38, color=NAVY_LIGHT, label="2022")
    ax.barh(y + 0.19, cr[2025], height=0.38, color=NAVY, label="2025")
    ax.set_yticks(y, cr.index, fontsize=7.5); hbar_style(ax); ax.xaxis.set_major_formatter(pct)
    legend_top(ax, ncol=2, loc="lower right", fontsize=8)
    small_title(ax, "Top cancellation reasons", "% of cancellations")
    return fig


# Page 5 ----
def page_marketing(t):
    k, ue, pr = t["kpi_by_year"], t["unit_economics"], t["promo_effect"]
    c, p = k.loc[2025], k.loc[2024]
    fig = new_page(5, "Marketing & unit economics", "What each order earns and what it costs to win a customer")
    kpi_cards(fig, [
        ("Net revenue 2025", f"€{c.net_revenue / 1e3:.0f}k", *change(c.net_revenue, p.net_revenue)),
        ("Take rate", f"{c['take_rate_%']:.1f}%", *change(c["take_rate_%"], p["take_rate_%"], "pp")),
        ("Contribution / order", fmt_eur(ue.loc[2025, "contribution"]),
         *change(ue.loc[2025, "contribution"], ue.loc[2024, "contribution"], "abs")),
        ("Marketing spend", f"€{c.marketing_spend / 1e3:.0f}k", *change(c.marketing_spend, p.marketing_spend, "pct", False)),
        ("Cost per new customer", fmt_eur(c.cac), *change(c.cac, p.cac, "pct", False)),
    ])
    gs = chart_grid(fig, width_ratios=[1.35, 1, 1], left=0.085, wspace=0.3)

    ax = fig.add_subplot(gs[0, 0])
    parts = ue.copy()
    for col in ["platform_discount", "courier_pay", "refund_amount"]:
        parts[col] = -parts[col]
    x = np.arange(len(parts))
    for cols in ([("commission", NAVY, "Commission"), ("delivery_fee", STEEL, "Delivery fee"),
                  ("service_fee", NAVY_LIGHT, "Service fee")],
                 [("courier_pay", GREY, "Courier pay"), ("platform_discount", GREY_LIGHT, "Discounts"),
                  ("refund_amount", "#E3A08F", "Refunds")]):
        b = np.zeros(len(parts))
        for col, color, name in cols:
            ax.bar(x, parts[col], bottom=b, color=color, width=0.55, label=name, edgecolor=BG, linewidth=0.8)
            b += parts[col].values
    ax.plot(x, parts["contribution"], color=GREEN, marker="o", ms=7, lw=2.4, label="Contribution",
            markeredgecolor=BG, markeredgewidth=1.5, zorder=5)
    for xi, v in zip(x, parts["contribution"]):
        ax.annotate(fmt_eur(v), (xi, v), xytext=(0, 9 if v >= 0 else -14), textcoords="offset points", ha="center",
                    fontsize=8, weight="bold", color=GREEN_DARK if v >= 0 else ALERT,
                    bbox=dict(boxstyle="round,pad=0.2", fc=BG, ec="none"))
    zero_line(ax); ax.set_xticks(x, parts.index); ax.yaxis.set_major_formatter(eur)
    ax.set_ylim(-11, 15.5)
    legend_top(ax, ncol=4, loc="upper left", fontsize=7.5)
    small_title(ax, "Revenue and cost per order (€)", "Revenue above zero, costs below")

    ax = fig.add_subplot(gs[0, 1])
    sp = t["marketing_by_channel_year"]["spend"].unstack("channel")
    sp = sp[sp.sum().sort_values(ascending=False).index]
    bottom = np.zeros(len(sp))
    for col, color in zip(sp.columns, [NAVY, STEEL, GREEN, NAVY_LIGHT, MINT, GREY_LIGHT]):
        ax.bar(sp.index, sp[col], bottom=bottom, color=color, width=0.62, label=col, edgecolor=BG, linewidth=0.8)
        bottom += sp[col].values
    ax.set_xticks(sp.index); ax.yaxis.set_major_formatter(eur_k)
    ax.set_ylim(0, sp.sum(axis=1).max() * 1.45)
    ax.legend(fontsize=7, loc="upper right", ncol=2)
    small_title(ax, "Marketing spend by channel", "Cut by 70% in 2023")

    ax = fig.add_subplot(gs[0, 2])
    year_bars(ax, k["cac"], lambda v: fmt_eur(v, 0))
    ax.yaxis.set_major_formatter(eur)
    small_title(ax, "Cost per new customer (CAC)", "Total spend / new customers")

    ax = fig.add_subplot(gs[1, 0])
    cps = t["marketing_by_channel_year"]["cost_per_signup"].unstack("year").drop(index="TV & Outdoor", errors="ignore")
    c2 = cps[[2022, 2025]].sort_values(2025, ascending=False)
    y = np.arange(len(c2))
    ax.barh(y - 0.19, c2[2022], height=0.38, color=NAVY_LIGHT, label="2022")
    bars = ax.barh(y + 0.19, c2[2025], height=0.38, color=[GREEN if i == "Referral Rewards" else NAVY for i in c2.index],
                   label="2025")
    label_hbars(ax, bars, lambda v: fmt_eur(v, 0), fontsize=7.5)
    ax.set_yticks(y, c2.index, fontsize=8); ax.invert_yaxis(); hbar_style(ax); ax.xaxis.set_major_formatter(eur)
    legend_top(ax, ncol=2, loc="lower right", fontsize=8)
    small_title(ax, "Cost per attributed signup", "Referral is the cheapest channel")

    ax = fig.add_subplot(gs[1, 1])
    bars = ax.bar(pr.index, pr["paid_by_forkly_%_gmv"], color=[NAVY if y <= 2022 else NAVY_LIGHT for y in pr.index], width=0.62)
    label_bars(ax, bars, "{:.1f}%", fontsize=8)
    ax.set_xticks(pr.index); ax.yaxis.set_major_formatter(pct)
    small_title(ax, "Discounts paid by Forkly", "% of GMV")

    ax = fig.add_subplot(gs[1, 2])
    x = np.arange(len(pr))
    ax.bar(x - 0.19, pr["repeat_no_promo_%"], width=0.38, color=GREY_LIGHT, label="No promo")
    bars = ax.bar(x + 0.19, pr["repeat_promo_%"], width=0.38, color=GREEN, label="With promo")
    label_bars(ax, bars, "{:.0f}%", fontsize=7.5)
    ax.set_xticks(x, pr.index); ax.yaxis.set_major_formatter(pct); ax.set_ylim(0, 100)
    legend_top(ax, ncol=2, fontsize=8)
    small_title(ax, "90-day repeat after first order", "First order with vs without promo")
    return fig


PAGES = [("executive_overview", page_executive), ("customers_retention", page_customers),
         ("restaurants_cities", page_restaurants), ("delivery_operations", page_operations),
         ("marketing_unit_economics", page_marketing)]


# HTML dashboard ----
# One self-contained file: a navigation bar switches between the 5 pages,
# each page is the PNG (embedded as base64) plus 3-4 written takeaways.
def takeaways(t):
    """Short findings under each page, computed from the same tables as the charts."""
    k = t["kpi_by_year"]
    c, p = k.loc[2025], k.loc[2024]
    ue, promo, rfm = t["unit_economics"], t["promo_effect"], t["rfm_segments"]
    plus, ret, nvr = t["plus_vs_non_member"], t["yoy_retention"], t["new_vs_returning"]
    city = t["gmv_by_city_year"][2025].sort_values(ascending=False)
    cuis = t["cuisine_performance"]
    par = t["restaurant_pareto"]
    top20 = np.interp(20, par["restaurants_%"], par["cum_gmv_%"])
    delay, weather, sup = t["rating_by_delay"]["delivery_rating"], t["late_by_weather"], t["support"]
    mkt = t["marketing_by_channel_year"].xs(2025, level="year")["cost_per_signup"].dropna().sort_values()
    worst = k["late_rate_%"].idxmax()
    lift = (promo["repeat_promo_%"] - promo["repeat_no_promo_%"]).loc[2022:]
    return {
        1: [f"GMV grew from <b>€{k.gmv.iloc[0] / 1e6:.2f}M in 2021 to €{c.gmv / 1e6:.2f}M in 2025</b>, "
            f"and orders from {k.orders.iloc[0] / 1e3:.0f}k to {c.orders / 1e3:.0f}k.",
            f"Each order lost <b>€{-ue.contribution.iloc[0]:.2f}</b> in 2021. In 2025 it made "
            f"<b>€{ue.contribution.loc[2025]:.2f}</b>, mainly because Forkly-funded discounts fell from "
            f"{promo['paid_by_forkly_%_gmv'].iloc[0]:.1f}% to {promo['paid_by_forkly_%_gmv'].loc[2025]:.1f}% of GMV.",
            f"Contribution margin is <b>{c['contribution_margin_%']:.1f}%</b>, down "
            f"{p['contribution_margin_%'] - c['contribution_margin_%']:.1f} pp on 2024, as Plus members "
            f"({c['plus_order_%']:.0f}% of orders) pay almost no delivery fee.",
            f"The delivery rating recovered from {k.delivery_rating.min():.2f} in {k.delivery_rating.idxmin()} "
            f"to <b>{c.delivery_rating:.2f}</b>."],
        2: [f"Year-over-year retention fell from {ret.iloc[0]:.0f}% to {ret.loc[2022]:.0f}% after the 2022 "
            f"service problems and has stayed near <b>{ret.iloc[-1]:.0f}%</b> since.",
            f"Returning customers placed <b>{nvr.loc[2025, 'Returning customer']:.0f}%</b> of 2025 orders.",
            f"Champions are {rfm.loc['Champions', 'customers_%']:.0f}% of customers but bring in "
            f"<b>{rfm.loc['Champions', 'gmv_%']:.0f}% of GMV</b> over the last 12 months.",
            f"Plus members order <b>{plus.loc['Plus member', 'orders_per_customer']:.1f} times a year</b>, "
            f"against {plus.loc['Non-member', 'orders_per_customer']:.1f} for non-members, with about the same basket."],
        3: [f"{city.index[0]} is the largest city with <b>{city.iloc[0] / city.sum() * 100:.0f}% of 2025 GMV</b>, "
            f"followed by {city.index[1]} and {city.index[2]}.",
            f"Grocery, launched in 2024, is already the largest category at "
            f"<b>{cuis.loc['Grocery', 'share_2025_%']:.0f}% of GMV</b>.",
            f"The top 20% of partners make <b>{top20:.0f}% of GMV</b>, so restaurant revenue is far less "
            f"concentrated than customer revenue."],
        4: [f"The late rate peaked at <b>{k.loc[worst, 'late_rate_%']:.0f}% in {worst}</b> and was "
            f"{c['late_rate_%']:.1f}% in 2025. Average delivery time is {c.avg_delivery_min:.1f} minutes.",
            f"Ratings stay at 4.3 or higher until an order is 5 minutes late, then fall to "
            f"<b>{delay.loc['5-10 late']:.1f}</b> at 5-10 minutes and <b>{delay.iloc[-1]:.1f}</b> at 20+ minutes.",
            f"Heavy rain raises the late rate from {weather.loc['Dry']:.1f}% to <b>{weather.loc['Heavy rain']:.1f}%</b>.",
            f"Support tickets are down to <b>{sup.loc[2025, 'tickets_per_100_orders']:.1f} per 100 orders</b>, "
            f"with a median resolution time of {sup.loc[2025, 'median_resolution_h']:.1f} h."],
        5: [f"Take rate is <b>{c['take_rate_%']:.1f}%</b> and net revenue €{c.net_revenue / 1e3:.0f}k in 2025.",
            f"Marketing spend fell from €{k.marketing_spend.loc[2022] / 1e3:.0f}k in 2022 to "
            f"€{c.marketing_spend / 1e3:.0f}k, and CAC from €{k.cac.loc[2022]:.2f} to <b>€{c.cac:.2f}</b>.",
            f"{mkt.index[0]} is the cheapest channel at <b>€{mkt.iloc[0]:.0f} per signup</b>; "
            f"{mkt.index[-1]} costs €{mkt.iloc[-1]:.0f}.",
            f"Since 2022, customers whose first order used a promo are <b>{lift.min():.0f}-{lift.max():.0f} pp</b> "
            f"more likely to order again within 90 days."],
    }


HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Forkly Dashboard</title>
<style>
  :root {{ --navy: {navy}; --navy2: {navy2}; --green: {green}; --light: {light}; --text: {text};
           --muted: {muted}; --grid: {grid}; }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; background: #F4F6F9; color: var(--text);
          font-family: "Segoe UI", Inter, "Helvetica Neue", Arial, sans-serif; }}
  nav {{ position: sticky; top: 0; z-index: 10; background: var(--navy); display: flex; align-items: center;
         gap: 8px; padding: 0 24px; height: 58px; box-shadow: 0 2px 8px rgba(11,37,69,.25); }}
  .brand {{ color: var(--green); font-weight: 700; font-size: 22px; margin-right: 24px; letter-spacing: -.3px; }}
  .tabs {{ display: flex; gap: 4px; flex: 1; overflow-x: auto; }}
  .tabs a {{ color: var(--light); text-decoration: none; font-size: 15px; padding: 18px 14px 15px;
             border-bottom: 3px solid transparent; white-space: nowrap; }}
  .tabs a:hover {{ color: #fff; }}
  .tabs a.active {{ color: #fff; font-weight: 600; border-bottom-color: var(--green); }}
  .pdf {{ color: var(--navy); background: var(--green); padding: 7px 14px; border-radius: 6px;
          text-decoration: none; font-size: 14px; font-weight: 600; white-space: nowrap; }}
  main {{ max-width: 1440px; margin: 0 auto; padding: 24px; }}
  section {{ display: none; }}
  section.active {{ display: block; }}
  .page {{ width: 100%; height: auto; display: block; border-radius: 8px; background: #fff;
           box-shadow: 0 1px 4px rgba(11,37,69,.12); }}
  .notes {{ background: #fff; border-left: 4px solid var(--green); border-radius: 8px; margin-top: 18px;
            padding: 16px 24px; box-shadow: 0 1px 4px rgba(11,37,69,.08); }}
  .notes h2 {{ margin: 0 0 8px; font-size: 16px; color: var(--navy); }}
  .notes ul {{ margin: 0; padding-left: 20px; line-height: 1.6; }}
  .notes b {{ color: var(--navy); }}
  .pager {{ display: flex; justify-content: space-between; margin-top: 16px; font-size: 14px; }}
  .pager a {{ color: var(--navy2); text-decoration: none; }}
  footer {{ text-align: center; color: var(--muted); font-size: 12px; padding: 8px 24px 28px; }}
  @media (max-width: 700px) {{ nav {{ padding: 0 12px; }} .pdf {{ display: none; }} main {{ padding: 12px; }} }}
</style>
</head>
<body>
<nav>
  <span class="brand">forkly</span>
  <div class="tabs">{tabs}</div>
  <a class="pdf" href="Forkly_dashboard.pdf">PDF</a>
</nav>
<main>
{sections}
</main>
<footer>Forkly is a fictional company and all data is simulated (2021-2025). Use the tabs or the left/right arrow keys to switch pages.</footer>
<script>
  const ids = {ids};
  function show(id) {{
    if (!ids.includes(id)) id = ids[0];
    document.querySelectorAll("section").forEach(s => s.classList.toggle("active", s.id === id));
    document.querySelectorAll(".tabs a").forEach(a => a.classList.toggle("active", a.hash === "#" + id));
    window.scrollTo(0, 0);
  }}
  window.addEventListener("hashchange", () => show(location.hash.slice(1)));
  document.addEventListener("keydown", e => {{
    const i = ids.indexOf(location.hash.slice(1) || ids[0]);
    if (e.key === "ArrowRight" && i < ids.length - 1) location.hash = ids[i + 1];
    if (e.key === "ArrowLeft" && i > 0) location.hash = ids[i - 1];
  }});
  show(location.hash.slice(1));
</script>
</body>
</html>
"""


def build_html(tables, png_paths, path):
    """Write one self-contained HTML file with tab navigation across the dashboard pages."""
    ids = [name for name, _ in PAGES]
    notes = takeaways(tables)
    tabs, sections = [], []
    for i, (name, label, png) in enumerate(zip(ids, NAV_LABELS, png_paths), start=1):
        tabs.append(f'<a href="#{name}">{label}</a>')
        img = base64.b64encode(png.read_bytes()).decode("ascii")
        bullets = "".join(f"<li>{b}</li>" for b in notes[i])
        prev_link = f'<a href="#{ids[i - 2]}">&larr; {NAV_LABELS[i - 2]}</a>' if i > 1 else "<span></span>"
        next_link = f'<a href="#{ids[i]}">{NAV_LABELS[i]} &rarr;</a>' if i < len(ids) else "<span></span>"
        sections.append(
            f'<section id="{name}">\n'
            f'  <img class="page" alt="{html.escape(label)} dashboard page" src="data:image/png;base64,{img}">\n'
            f'  <div class="notes"><h2>Key takeaways</h2><ul>{bullets}</ul></div>\n'
            f'  <div class="pager">{prev_link}{next_link}</div>\n'
            f'</section>')
    page = HTML_TEMPLATE.format(navy=NAVY, navy2=NAVY_2, green=GREEN, light=NAVY_LIGHT, text=TEXT,
                                muted=TEXT_MUTED, grid=GRID, tabs="".join(tabs),
                                sections="\n".join(sections), ids=str(ids).replace("'", '"'))
    path.write_text(page, encoding="utf-8")


def run(tables=None):
    apply_theme()
    plt.rcParams.update({"axes.titlepad": 8, "xtick.labelsize": 8, "ytick.labelsize": 8, "savefig.bbox": None})
    tables = tables or build_all(save=False)
    DASH_DIR.mkdir(parents=True, exist_ok=True)
    pdf_path = DASH_DIR / "Forkly_dashboard.pdf"
    png_paths = []
    with PdfPages(pdf_path) as pdf:
        for i, (name, builder) in enumerate(PAGES, start=1):
            fig = builder(tables)
            png_paths.append(DASH_DIR / f"page_{i}_{name}.png")
            fig.savefig(png_paths[-1], dpi=150, bbox_inches=None)
            pdf.savefig(fig, bbox_inches=None)
            plt.close(fig)
            print(f"  page {i}: {name}")
    build_html(tables, png_paths, DASH_DIR / "Forkly_dashboard.html")
    print(f"  saved 5 PNG pages, {pdf_path.name} and Forkly_dashboard.html to {DASH_DIR}")


if __name__ == "__main__":
    run()

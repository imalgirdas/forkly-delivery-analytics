"""
Script:   dashboard_dash.py
Purpose:  Interactive 4-page Forkly dashboard in Dash + Plotly
            1 Overview                     2 Customers
            3 Restaurants & operations     4 Marketing & unit economics
          Year filter in the header (KPI cards compare with the year before),
          city filter on page 3, metric switch on page 4.
          The static matplotlib version is still in dashboard.py.
Input:    Forkly/Data_clean/*.csv (through analysis.py), theme.py
Output:   local web app, run with  python src/dashboard_dash.py  and open http://127.0.0.1:8050
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from dash import Dash, Input, Output, dcc, html

from analysis import YEARS, build_all
from theme import *

plotly_theme()
T = build_all(save=False)   # all tables are small, so build them once at start-up

PAGES = [("/", "Overview"), ("/customers", "Customers"), ("/restaurants", "Restaurants & operations"),
         ("/marketing", "Marketing & unit economics")]
GRAPH_CONFIG = {"displayModeBar": False}


# Small helpers ----
def change(cur, prev, year, kind="pct", higher_is_better=True):
    """Text and good/bad flag for the selected year vs the year before."""
    if prev is None or pd.isna(prev) or pd.isna(cur):
        return "no earlier year", None
    diff = cur - prev
    arrow = "▲" if diff > 0 else "▼"
    good = (diff > 0) == higher_is_better
    if kind == "pct":
        txt = f"{arrow} {diff / prev:+.1%}"
    elif kind == "pp":
        txt = f"{arrow} {diff:+.1f} pp"
    else:
        txt = f"{arrow} {diff:+.2f}"
    return f"{txt} vs {year - 1}", good


def prev_val(s, year):
    return s.get(year - 1) if hasattr(s, "get") else None


def kpi(label, value, delta=("", None)):
    text, good = delta
    flag = "neutral" if good is None else ("good" if good else "bad")
    return html.Div([html.Div(label, className="kpi-label"),
                     html.Div(value, className="kpi-value"),
                     html.Div(text, className=f"kpi-delta {flag}")], className=f"kpi {flag}")


def card(title, subtitle, fig=None, graph_id=None, wide=False, tall=False, controls=None):
    """White chart card. Pass a figure, or a graph_id that a callback fills."""
    graph = dcc.Graph(id=graph_id, config=GRAPH_CONFIG) if graph_id else dcc.Graph(figure=fig, config=GRAPH_CONFIG)
    head = [html.H3(title), html.P(subtitle or " ", className="sub")]
    if controls is not None:
        head.append(controls)
    cls = "card" + (" wide" if wide else "") + (" tall" if tall else "")
    return html.Div(head + [graph], className=cls)


def notes(items, label="Key takeaways (2025)"):
    return html.Div([html.H3(label), html.Ul([html.Li(dcc.Markdown(i)) for i in items])], className="notes")


def layout(fig, h=300, **kw):
    fig.update_layout(height=h, **kw)
    return fig


def year_colors(index, year, special=None):
    """Selected year in navy, the rest light; special maps a year to its own colour."""
    special = special or {}
    return [special.get(y, NAVY if y == year else NAVY_LIGHT) for y in index]


def year_bars(series, year, texttemplate, hover, colors=None, h=300):
    fig = go.Figure(go.Bar(x=series.index, y=series.values, marker_color=colors or year_colors(series.index, year),
                           texttemplate=texttemplate, textposition="outside", cliponaxis=False,
                           hovertemplate=hover + "<extra></extra>"))
    fig.update_xaxes(type="category")
    return layout(fig, h)


def compare_hbars(df, a, b, fmt, hover, highlight=None, h=300):
    """Grouped horizontal bars, column a (light) vs column b (navy or green)."""
    fig = go.Figure()
    if a is not None:
        fig.add_bar(y=df.index, x=df[a], orientation="h", name=str(a), marker_color=NAVY_LIGHT,
                    hovertemplate=f"%{{y}}<br>{a}: {hover}<extra></extra>")
    colors = [GREEN if i == highlight else NAVY for i in df.index]
    fig.add_bar(y=df.index, x=df[b], orientation="h", name=str(b), marker_color=colors, texttemplate=fmt,
                textposition="outside", cliponaxis=False, hovertemplate=f"%{{y}}<br>{b}: {hover}<extra></extra>")
    fig.update_layout(barmode="group", bargap=0.25)
    fig.update_xaxes(showgrid=True, range=[0, np.nanmax(df.values) * 1.18])   # room for the value labels
    fig.update_yaxes(showgrid=False, autorange="reversed")
    return layout(fig, h)


def shade_year(fig, year):
    fig.add_vrect(x0=pd.Timestamp(f"{year}-01-01"), x1=pd.Timestamp(f"{year}-12-31"), fillcolor=GREEN,
                  opacity=0.07, line_width=0, layer="below")


# Page 1: Overview ----
def page_overview(t, y):
    k = t["kpi_by_year"]
    c = k.loc[y]
    pv = lambda col: prev_val(k[col], y)
    cards = [
        kpi(f"GMV {y}", f"€{c.gmv / 1e6:.2f}M", change(c.gmv, pv("gmv"), y)),
        kpi("Orders", f"{c.orders / 1e3:.1f}k", change(c.orders, pv("orders"), y)),
        kpi("Average basket", fmt_eur(c.aov), change(c.aov, pv("aov"), y)),
        kpi("Active customers", f"{c.active_customers / 1e3:.1f}k", change(c.active_customers, pv("active_customers"), y)),
        kpi("Contribution margin", f"{c['contribution_margin_%']:.1f}%",
            change(c["contribution_margin_%"], pv("contribution_margin_%"), y, "pp")),
        kpi("Delivery rating", f"{c.delivery_rating:.2f}", change(c.delivery_rating, pv("delivery_rating"), y, "abs")),
    ]

    # monthly GMV, selected year shaded
    m = t["monthly"]
    peak = m["gmv"].idxmax()
    f1 = go.Figure(go.Scatter(x=m.index, y=m["gmv"], mode="lines", line=dict(color=NAVY, width=2.4), fill="tozeroy",
                              fillcolor="rgba(11,37,69,0.06)", hovertemplate="%{x|%b %Y}<br>€%{y:,.0f}<extra></extra>"))
    f1.add_scatter(x=[peak], y=[m.loc[peak, "gmv"]], mode="markers+text", marker=dict(color=GREEN, size=9),
                   text=[f"Peak {peak:%b %Y}: €{m.loc[peak, 'gmv'] / 1e3:.0f}k"], textposition="middle left",
                   textfont=dict(color=GREEN_DARK, size=11), hoverinfo="skip", showlegend=False)
    shade_year(f1, y)
    f1.update_yaxes(tickprefix="€", tickformat="~s", rangemode="tozero")
    layout(f1, showlegend=False)

    # launch vs expansion cities
    g = t["gmv_by_city_group"]
    f2 = go.Figure()
    for col, color in [("Launch cities", NAVY), ("Expansion cities", GREEN)]:
        f2.add_bar(x=g.index, y=g[col], name=col, marker_color=color,
                   hovertemplate=f"%{{x}} {col}<br>€%{{y:,.0f}}<extra></extra>")
    f2.add_scatter(x=g.index, y=g.sum(axis=1), mode="text", text=[f"€{v / 1e6:.1f}M" for v in g.sum(axis=1)],
                   textposition="top center", showlegend=False, hoverinfo="skip")
    f2.update_layout(barmode="stack")
    f2.update_xaxes(type="category")
    f2.update_yaxes(tickprefix="€", tickformat="~s")
    layout(f2)

    ue = t["unit_economics"]["contribution"]
    f3 = year_bars(ue, y, "%{text}", "%{x}: %{text} per order",
                   colors=[ALERT if v < 0 else (NAVY if yr == y else NAVY_LIGHT) for yr, v in ue.items()])
    f3.update_traces(text=[fmt_eur(v) for v in ue])
    f3.update_yaxes(tickprefix="€", zeroline=True, zerolinecolor=TEXT_MUTED)

    f4 = year_bars(k["late_rate_%"], y, "%{y:.1f}%", "%{x}: %{y:.1f}% late",
                   colors=year_colors(k.index, y, {2022: ALERT} if y != 2022 else None))
    f4.update_yaxes(ticksuffix="%")

    f5 = go.Figure()
    for col, color, name in [("promo_order_%", NAVY, "Promo"), ("plus_order_%", GREEN, "Plus"),
                             ("grocery_order_%", STEEL, "Grocery")]:
        f5.add_scatter(x=k.index, y=k[col], name=name, mode="lines+markers", line=dict(color=color, width=2.4),
                       marker=dict(size=7), hovertemplate=f"%{{x}} {name}: %{{y:.1f}}%<extra></extra>")
    f5.update_xaxes(type="category")
    f5.update_yaxes(ticksuffix="%")
    layout(f5)

    charts = [
        card("Monthly GMV", f"Strong December peaks; {y} shaded", f1, wide=True),
        card("GMV by market", "Growth comes from cities added since 2022", f2),
        card("Contribution per order", "Revenue minus courier pay, discounts and refunds", f3),
        card("Late deliveries", "% of orders more than 5 min after the promised time", f4),
        card("Business mix", "% of orders", f5),
    ]
    return cards, charts, TAKEAWAYS[1]


# Page 2: Customers ----
def page_customers(t, y):
    k = t["kpi_by_year"]
    c = k.loc[y]
    yoy, nr, seg, plus = t["yoy_retention"], t["new_vs_returning"], t["rfm_segments"], t["plus_vs_non_member"]
    ret = yoy.get(y - 1)    # yoy is indexed by the starting year, so 2024 = retained 2024 -> 2025
    ret_prev = yoy.get(y - 2)
    returning = nr.loc[y, "Returning customer"]
    cards = [
        kpi(f"New customers {y}", f"{c.new_customers / 1e3:.1f}k", change(c.new_customers, prev_val(k["new_customers"], y), y)),
        kpi(f"Retained {y - 1} → {y}", "–" if ret is None else f"{ret:.0f}%",
            change(ret, ret_prev, y, "pp") if ret is not None else ("first year", None)),
        kpi("Orders from returning", f"{returning:.0f}%",
            change(returning, nr["Returning customer"].get(y - 1), y, "pp")),
        kpi("Orders per customer", f"{c.orders_per_customer:.2f}",
            change(c.orders_per_customer, prev_val(k["orders_per_customer"], y), y, "abs")),
        kpi("Champions share of GMV", f"{seg.loc['Champions', 'gmv_%']:.0f}%",
            (f"{seg.loc['Champions', 'customers_%']:.0f}% of customers, last 12 months", None)),
    ]

    coh = t["cohort_retention"]
    f1 = go.Figure(go.Heatmap(z=coh.values, x=[str(c) for c in coh.columns], y=coh.index, colorscale=SCALE_NAVY,
                              showscale=False, xgap=2, ygap=2, texttemplate="%{z:.0f}", textfont=dict(size=10),
                              hovertemplate="Cohort %{y}, quarter +%{x}<br>%{z:.1f}% ordered<extra></extra>"))
    f1.update_yaxes(autorange="reversed", showgrid=False)
    f1.update_xaxes(title_text="Quarters since signup", side="top")
    layout(f1, 640)

    f2 = go.Figure()
    for col, color, name in [("Returning customer", NAVY, "Returning"), ("New customer", GREEN, "New")]:
        f2.add_bar(x=nr.index, y=nr[col], name=name, marker_color=color, texttemplate="%{y:.0f}%",
                   textposition="inside", insidetextanchor="middle",
                   hovertemplate=f"%{{x}} {name}: %{{y:.1f}}%<extra></extra>")
    f2.update_layout(barmode="stack")
    f2.update_xaxes(type="category")
    f2.update_yaxes(ticksuffix="%", range=[0, 100])
    layout(f2)

    p = plus.reindex(["Non-member", "Plus member"])
    f3 = go.Figure(go.Bar(x=p.index, y=p["orders_per_customer"], marker_color=[GREY_LIGHT, GREEN],
                          texttemplate="%{y:.1f}", textposition="outside", cliponaxis=False,
                          customdata=np.stack([p["customers"], p["aov"]], axis=1),
                          hovertemplate="%{x}<br>%{y:.1f} orders per customer<br>%{customdata[0]:,.0f} customers"
                                        "<br>basket €%{customdata[1]:.2f}<extra></extra>"))
    layout(f3)

    f4 = go.Figure()
    f4.add_bar(y=seg.index, x=seg["customers_%"], orientation="h", name="Customers", marker_color=NAVY_LIGHT,
               hovertemplate="%{y}: %{x:.1f}% of customers<extra></extra>")
    f4.add_bar(y=seg.index, x=seg["gmv_%"], orientation="h", name="GMV", marker_color=NAVY, texttemplate="%{x:.0f}%",
               textposition="outside", cliponaxis=False, hovertemplate="%{y}: %{x:.1f}% of GMV<extra></extra>")
    f4.update_layout(barmode="group", bargap=0.25)
    f4.update_xaxes(ticksuffix="%", showgrid=True, range=[0, seg[["customers_%", "gmv_%"]].max().max() * 1.15])
    f4.update_yaxes(autorange="reversed", showgrid=False)
    layout(f4)

    mix = t["channel_mix"]
    base = y - 1 if y - 1 in mix.index else None
    m = mix.loc[[yr for yr in (base, y) if yr is not None]].T.sort_values(y, ascending=False)
    f5 = compare_hbars(m, base, y, "%{x:.0f}%", "%{x:.1f}%", highlight="Referral")
    f5.update_xaxes(ticksuffix="%")

    charts = [
        card("Cohort retention (%)", "Share of each signup quarter ordering again N quarters later", f1, tall=True),
        card("Orders: returning vs new", "% of orders each year", f2),
        card("Forkly Plus: orders per customer", "2025, members vs non-members", f3),
        card("RFM segments", "% of customers vs % of last-12-month GMV", f4),
        card("Signups by channel", f"Share of new customers, {base} vs {y}" if base else f"Share of new customers, {y}", f5),
    ]
    return cards, charts, TAKEAWAYS[2]


# Page 3: Restaurants & operations ----
def page_restaurants(t, y):
    k, cy, cz = t["kpi_by_year"], t["gmv_by_city_year"], t["cuisine_performance"]
    c = k.loc[y]
    pv = lambda col: prev_val(k[col], y)
    city_y = cy[y].sort_values(ascending=False)
    live, live_prev = (cy[y] > 0).sum(), ((cy[y - 1] > 0).sum() if y - 1 in cy.columns else None)
    grocery = cz.loc["Grocery", y] / cz[y].sum() * 100 if "Grocery" in cz.index else np.nan
    cards = [
        kpi("Live cities", f"{live}", (f"{live_prev} in {y - 1}", None) if live_prev is not None else ("", None)),
        kpi("Largest market", city_y.index[0], (f"{city_y.iloc[0] / city_y.sum():.0%} of {y} GMV", None)),
        kpi("Grocery share of GMV", f"{grocery:.0f}%", ("launched Feb 2024", None)),
        kpi("Avg delivery time", f"{c.avg_delivery_min:.1f} min",
            change(c.avg_delivery_min, pv("avg_delivery_min"), y, "abs", higher_is_better=False)),
        kpi("Late deliveries", f"{c['late_rate_%']:.1f}%", change(c["late_rate_%"], pv("late_rate_%"), y, "pp", False)),
        kpi("Cancellation rate", f"{c['cancel_rate_%']:.1f}%",
            change(c["cancel_rate_%"], pv("cancel_rate_%"), y, "pp", False)),
    ]

    # cuisines and partners
    top = cz[y].sort_values(ascending=False).head(10)
    f3 = go.Figure(go.Bar(y=top.index, x=top.values, orientation="h",
                          marker_color=[GREEN if i == "Grocery" else NAVY for i in top.index],
                          texttemplate="€%{x:.3s}", textposition="outside", cliponaxis=False,
                          hovertemplate="%{y}: €%{x:,.0f}<extra></extra>"))
    f3.update_xaxes(tickprefix="€", tickformat="~s", showgrid=True, range=[0, top.max() * 1.2])
    f3.update_yaxes(autorange="reversed", showgrid=False)
    layout(f3, 340)

    par = t["restaurant_pareto"]
    top20 = np.interp(20, par["restaurants_%"], par["cum_gmv_%"])
    f4 = go.Figure(go.Scatter(x=par["restaurants_%"], y=par["cum_gmv_%"], mode="lines", line=dict(color=NAVY, width=2.4),
                              fill="tozeroy", fillcolor="rgba(11,37,69,0.06)",
                              hovertemplate="Top %{x:.0f}% of partners<br>%{y:.0f}% of GMV<extra></extra>"))
    f4.add_scatter(x=[0, 100], y=[0, 100], mode="lines", line=dict(color=GREY_LIGHT, dash="dash", width=1), hoverinfo="skip")
    f4.add_scatter(x=[20], y=[top20], mode="markers+text", marker=dict(color=GREEN, size=9),
                   text=[f"Top 20% = {top20:.0f}% of GMV"], textposition="bottom right",
                   textfont=dict(color=GREEN_DARK, size=11), hoverinfo="skip")
    f4.update_xaxes(ticksuffix="%", range=[0, 100], title_text="Restaurants ranked by GMV")
    f4.update_yaxes(ticksuffix="%", range=[0, 102])
    layout(f4, 340, showlegend=False)

    # operations
    m = t["monthly"]
    f5 = go.Figure(go.Scatter(x=m.index, y=m["late_rate"], mode="lines", line=dict(color=NAVY, width=2.4), fill="tozeroy",
                              fillcolor="rgba(11,37,69,0.06)", hovertemplate="%{x|%b %Y}<br>%{y:.1f}% late<extra></extra>"))
    f5.add_vrect(x0=pd.Timestamp("2022-01-01"), x1=pd.Timestamp("2022-12-31"), fillcolor=ALERT, opacity=0.06,
                 line_width=0, layer="below", annotation_text="2022 operations crunch", annotation_position="top",
                 annotation_font=dict(color=ALERT, size=11))
    if y != 2022:
        shade_year(f5, y)
    f5.update_yaxes(ticksuffix="%", rangemode="tozero")
    layout(f5, showlegend=False)

    r = t["rating_by_delay"]
    f6 = go.Figure(go.Bar(x=r.index.astype(str), y=r["delivery_rating"],
                          marker_color=[GREEN, GREEN, NAVY_LIGHT, STEEL, NAVY_2, NAVY, ALERT][:len(r)],
                          texttemplate="%{y:.1f}", textposition="outside", cliponaxis=False, customdata=r["reviews"],
                          hovertemplate="%{x}<br>%{y:.2f} stars<br>%{customdata:,} reviews<extra></extra>"))
    f6.update_yaxes(range=[1, 5])
    layout(f6)

    w = t["late_by_weather"].dropna()
    f7 = go.Figure(go.Bar(x=w.index, y=w.values, marker_color=[NAVY_LIGHT, STEEL, NAVY, NAVY_2][:len(w)],
                          texttemplate="%{y:.1f}%", textposition="outside", cliponaxis=False,
                          hovertemplate="%{x}: %{y:.1f}% late<extra></extra>"))
    f7.update_yaxes(ticksuffix="%")
    layout(f7)

    v = t["vehicle_mix"]
    v = v[[col for col in ["E-bike", "Bicycle", "Scooter", "Car"] if col in v.columns]]
    f8 = go.Figure()
    for col, color in zip(v.columns, [GREEN, NAVY, STEEL, GREY_LIGHT]):
        f8.add_bar(x=v.index, y=v[col], name=col, marker_color=color,
                   hovertemplate=f"%{{x}} {col}: %{{y:.1f}}%<extra></extra>")
    f8.update_layout(barmode="stack")
    f8.update_xaxes(type="category")
    f8.update_yaxes(ticksuffix="%", range=[0, 100])
    layout(f8)

    cr = t["cancel_reasons"]
    base = y - 1 if y - 1 in cr.index else None
    cr = cr.loc[[yr for yr in (base, y) if yr is not None]].T
    cr = (cr.div(cr.sum()) * 100).sort_values(y, ascending=False).head(6)
    f9 = compare_hbars(cr, base, y, "%{x:.0f}%", "%{x:.1f}%")
    f9.update_xaxes(ticksuffix="%")

    city_filter = dcc.Dropdown(id="city-filter", options=sorted(cy.index), multi=True, placeholder="All cities",
                               className="city-filter")
    charts = [
        card(f"GMV by city, {y}", "Pick cities to compare (empty = all)", graph_id="city-bars", controls=city_filter),
        card("GMV by city and year (€k)", "Blank = not launched yet", graph_id="city-heatmap", wide=True),
        card(f"Top 10 categories by GMV, {y}", "Grocery in green", f3),
        card("GMV concentration, 2025", "Cumulative share of GMV by partner", f4),
        card("Delivery rating vs promised time", "Average stars by minutes early / late", f6),
        card("Late delivery rate by month", "More than 5 minutes after the promised time", f5, wide=True),
        card("Late rate by weather", "All years", f7),
        card("Deliveries by vehicle", "% of deliveries; e-bikes replaced bicycles", f8),
        card("Top cancellation reasons", "% of cancellations", f9, wide=True),
    ]
    return cards, charts, TAKEAWAYS[3] + TAKEAWAYS[4]


def city_figures(t, y, cities):
    cy = t["gmv_by_city_year"]
    if cities:
        cy = cy.loc[[c for c in cities if c in cy.index]]
    s = cy[y].sort_values(ascending=False)
    f1 = go.Figure(go.Bar(y=s.index, x=s.values, orientation="h",
                          marker_color=[GREEN if v == s.max() else NAVY for v in s.values],
                          texttemplate="€%{x:.3s}", textposition="outside", cliponaxis=False,
                          hovertemplate="%{y}: €%{x:,.0f}<extra></extra>"))
    f1.update_xaxes(tickprefix="€", tickformat="~s", showgrid=True, range=[0, s.max() * 1.2])
    f1.update_yaxes(autorange="reversed", showgrid=False)
    layout(f1, max(260, 28 * len(s) + 60))

    cyo = cy.loc[cy.sum(axis=1).sort_values(ascending=False).index]
    z = (cyo / 1e3).where(cyo > 0)
    f2 = go.Figure(go.Heatmap(z=z.values, x=[str(c) for c in z.columns], y=z.index, colorscale=SCALE_NAVY,
                              showscale=False, xgap=2, ygap=2, texttemplate="%{z:,.0f}", textfont=dict(size=11),
                              hovertemplate="%{y}, %{x}<br>€%{z:,.1f}k<extra></extra>"))
    f2.update_yaxes(autorange="reversed", showgrid=False)
    layout(f2, max(260, 28 * len(z) + 60))
    return f1, f2


# Page 4: Marketing & unit economics ----
def page_marketing(t, y):
    k, ue, pr = t["kpi_by_year"], t["unit_economics"], t["promo_effect"]
    c = k.loc[y]
    pv = lambda col: prev_val(k[col], y)
    cards = [
        kpi(f"Net revenue {y}", f"€{c.net_revenue / 1e3:.0f}k", change(c.net_revenue, pv("net_revenue"), y)),
        kpi("Take rate", f"{c['take_rate_%']:.1f}%", change(c["take_rate_%"], pv("take_rate_%"), y, "pp")),
        kpi("Contribution / order", fmt_eur(ue.loc[y, "contribution"]),
            change(ue.loc[y, "contribution"], prev_val(ue["contribution"], y), y, "abs")),
        kpi("Marketing spend", f"€{c.marketing_spend / 1e3:.0f}k",
            change(c.marketing_spend, pv("marketing_spend"), y, "pct", False)),
        kpi("Cost per new customer", fmt_eur(c.cac), change(c.cac, pv("cac"), y, "pct", False)),
    ]

    # revenue above zero, costs below, contribution as a line
    f1 = go.Figure()
    for col, color, name, sign in [("commission", NAVY, "Commission", 1), ("delivery_fee", STEEL, "Delivery fee", 1),
                                   ("service_fee", NAVY_LIGHT, "Service fee", 1), ("courier_pay", GREY, "Courier pay", -1),
                                   ("platform_discount", GREY_LIGHT, "Discounts", -1),
                                   ("refund_amount", "#E3A08F", "Refunds", -1)]:
        f1.add_bar(x=ue.index, y=sign * ue[col], name=name, marker_color=color,
                   hovertemplate=f"%{{x}} {name}: €%{{y:.2f}}<extra></extra>")
    f1.add_scatter(x=ue.index, y=ue["contribution"], name="Contribution", mode="lines+markers",
                   line=dict(color=GREEN, width=2.6), marker=dict(size=9, line=dict(color=BG, width=1.5)),
                   hovertemplate="%{x} contribution: €%{y:.2f}<extra></extra>")
    # labels on a white box, otherwise they disappear on the navy bars
    # (x is the position on the category axis, not the year itself)
    for i, v in enumerate(ue["contribution"]):
        f1.add_annotation(x=i, y=v, text=f"<b>{fmt_eur(v)}</b>", yshift=16, showarrow=False, bgcolor=BG,
                          font=dict(color=GREEN_DARK if v >= 0 else ALERT, size=11))
    f1.update_layout(barmode="relative")
    f1.update_xaxes(type="category")
    f1.update_yaxes(tickprefix="€", zeroline=True, zerolinecolor=TEXT_MUTED)
    layout(f1, 340)

    f3 = year_bars(k["cac"], y, "€%{y:.0f}", "%{x}: €%{y:.2f} per new customer")
    f3.update_yaxes(tickprefix="€")

    cps = t["marketing_by_channel_year"]["cost_per_signup"].unstack("year").drop(index="TV & Outdoor", errors="ignore")
    base = y - 1 if y - 1 in cps.columns else None
    c2 = cps[[yr for yr in (base, y) if yr is not None]].sort_values(y, ascending=False)
    f4 = compare_hbars(c2, base, y, "€%{x:.0f}", "€%{x:.2f} per signup", highlight="Referral Rewards")
    f4.update_xaxes(tickprefix="€")

    f5 = year_bars(pr["paid_by_forkly_%_gmv"], y, "%{y:.1f}%", "%{x}: %{y:.2f}% of GMV")
    f5.update_yaxes(ticksuffix="%")

    f6 = go.Figure()
    f6.add_bar(x=pr.index, y=pr["repeat_no_promo_%"], name="No promo", marker_color=GREY_LIGHT,
               hovertemplate="%{x} no promo: %{y:.1f}%<extra></extra>")
    f6.add_bar(x=pr.index, y=pr["repeat_promo_%"], name="With promo", marker_color=GREEN, texttemplate="%{y:.0f}%",
               textposition="outside", cliponaxis=False, hovertemplate="%{x} with promo: %{y:.1f}%<extra></extra>")
    f6.update_layout(barmode="group")
    f6.update_xaxes(type="category")
    f6.update_yaxes(ticksuffix="%", range=[0, 100])
    layout(f6)

    metric = dcc.RadioItems(id="mkt-metric", options=[{"label": "Spend", "value": "spend"},
                                                      {"label": "Signups", "value": "signups"}],
                            value="spend", inline=True, className="pills small")
    charts = [
        card("Revenue and cost per order (€)", "Revenue above zero, costs below; contribution in green", f1, wide=True),
        card("Marketing by channel", f"Stacked by channel, {y} highlighted", graph_id="mkt-channel", controls=metric),
        card("Cost per new customer (CAC)", "Total spend / new customers", f3),
        card("Cost per attributed signup", "Referral is the cheapest channel", f4, wide=True),
        card("Discounts paid by Forkly", "% of GMV", f5),
        card("90-day repeat after first order", "First order with vs without promo", f6, wide=True),
    ]
    return cards, charts, TAKEAWAYS[5]


def channel_figure(t, y, metric):
    sp = t["marketing_by_channel_year"][metric].unstack("channel")
    sp = sp[sp.sum().sort_values(ascending=False).index]
    prefix = "€" if metric == "spend" else ""
    f = go.Figure()
    for col, color in zip(sp.columns, [NAVY, STEEL, GREEN, NAVY_LIGHT, MINT, GREY_LIGHT, GREY, GREEN_DARK]):
        f.add_bar(x=sp.index, y=sp[col], name=col, marker_color=color,
                  hovertemplate=f"%{{x}} {col}: {prefix}%{{y:,.0f}}<extra></extra>")
    # light band behind the selected year
    i = list(sp.index).index(y)
    f.add_shape(type="rect", xref="x", yref="paper", x0=i - 0.45, x1=i + 0.45, y0=0, y1=1, fillcolor=GREEN,
                opacity=0.1, line_width=0, layer="below")
    f.update_layout(barmode="stack", legend=dict(y=-0.12, yanchor="top"))
    f.update_xaxes(type="category")
    f.update_yaxes(tickprefix=prefix, tickformat="~s")
    return layout(f, 380, margin=dict(t=10))


# Takeaways ----
# same text as the static dashboard (always about 2025), bold in Markdown instead of <b>
def takeaways(t):
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
        1: [f"GMV grew from **€{k.gmv.iloc[0] / 1e6:.2f}M in 2021 to €{c.gmv / 1e6:.2f}M in 2025**, "
            f"and orders from {k.orders.iloc[0] / 1e3:.0f}k to {c.orders / 1e3:.0f}k.",
            f"Each order lost **€{-ue.contribution.iloc[0]:.2f}** in 2021. In 2025 it made "
            f"**€{ue.contribution.loc[2025]:.2f}**, mainly because Forkly-funded discounts fell from "
            f"{promo['paid_by_forkly_%_gmv'].iloc[0]:.1f}% to {promo['paid_by_forkly_%_gmv'].loc[2025]:.1f}% of GMV.",
            f"Contribution margin is **{c['contribution_margin_%']:.1f}%**, down "
            f"{p['contribution_margin_%'] - c['contribution_margin_%']:.1f} pp on 2024, as Plus members "
            f"({c['plus_order_%']:.0f}% of orders) pay almost no delivery fee.",
            f"The delivery rating recovered from {k.delivery_rating.min():.2f} in {k.delivery_rating.idxmin()} "
            f"to **{c.delivery_rating:.2f}**."],
        2: [f"Year-over-year retention fell from {ret.iloc[0]:.0f}% to {ret.loc[2022]:.0f}% after the 2022 "
            f"service problems and has stayed near **{ret.iloc[-1]:.0f}%** since.",
            f"Returning customers placed **{nvr.loc[2025, 'Returning customer']:.0f}%** of 2025 orders.",
            f"Champions are {rfm.loc['Champions', 'customers_%']:.0f}% of customers but bring in "
            f"**{rfm.loc['Champions', 'gmv_%']:.0f}% of GMV** over the last 12 months.",
            f"Plus members order **{plus.loc['Plus member', 'orders_per_customer']:.1f} times a year**, "
            f"against {plus.loc['Non-member', 'orders_per_customer']:.1f} for non-members, with about the same basket."],
        3: [f"{city.index[0]} is the largest city with **{city.iloc[0] / city.sum() * 100:.0f}% of 2025 GMV**, "
            f"followed by {city.index[1]} and {city.index[2]}.",
            f"Grocery, launched in 2024, is already the largest category at "
            f"**{cuis.loc['Grocery', 'share_2025_%']:.0f}% of GMV**.",
            f"The top 20% of partners make **{top20:.0f}% of GMV**, so restaurant revenue is far less "
            f"concentrated than customer revenue."],
        4: [f"The late rate peaked at **{k.loc[worst, 'late_rate_%']:.0f}% in {worst}** and was "
            f"{c['late_rate_%']:.1f}% in 2025. Average delivery time is {c.avg_delivery_min:.1f} minutes.",
            f"Ratings stay at 4.3 or higher until an order is 5 minutes late, then fall to "
            f"**{delay.loc['5-10 late']:.1f}** at 5-10 minutes and **{delay.iloc[-1]:.1f}** at 20+ minutes.",
            f"Heavy rain raises the late rate from {weather.loc['Dry']:.1f}% to **{weather.loc['Heavy rain']:.1f}%**.",
            f"Support tickets are down to **{sup.loc[2025, 'tickets_per_100_orders']:.1f} per 100 orders**, "
            f"with a median resolution time of {sup.loc[2025, 'median_resolution_h']:.1f} h."],
        5: [f"Take rate is **{c['take_rate_%']:.1f}%** and net revenue €{c.net_revenue / 1e3:.0f}k in 2025.",
            f"Marketing spend fell from €{k.marketing_spend.loc[2022] / 1e3:.0f}k in 2022 to "
            f"€{c.marketing_spend / 1e3:.0f}k, and CAC from €{k.cac.loc[2022]:.2f} to **€{c.cac:.2f}**.",
            f"{mkt.index[0]} is the cheapest channel at **€{mkt.iloc[0]:.0f} per signup**; "
            f"{mkt.index[-1]} costs €{mkt.iloc[-1]:.0f}.",
            f"Since 2022, customers whose first order used a promo are **{lift.min():.0f}-{lift.max():.0f} pp** "
            f"more likely to order again within 90 days."],
    }


TAKEAWAYS = takeaways(T)
BUILDERS = {"/": page_overview, "/customers": page_customers, "/restaurants": page_restaurants,
            "/marketing": page_marketing}
SUBTITLES = {
    "/": "Five years of Forkly: from a loss-making launch to a profitable, 12-city delivery platform",
    "/customers": "Who orders, how often they come back and which customers carry the revenue",
    "/restaurants": "Where GMV is made, and how fast and reliably it gets delivered",
    "/marketing": "What each order earns and what it costs to win a customer",
}


# App ----
CSS = f"""
* {{ box-sizing: border-box; }}
body {{ margin: 0; background: #F4F6F9; color: {TEXT}; font-family: {FONT_STACK}; }}
nav {{ position: sticky; top: 0; z-index: 10; background: {NAVY}; display: flex; align-items: center; gap: 8px;
       padding: 0 24px; min-height: 58px; box-shadow: 0 2px 8px rgba(11,37,69,.25); flex-wrap: wrap; }}
.brand {{ color: {GREEN}; font-weight: 700; font-size: 22px; margin-right: 24px; letter-spacing: -.3px; }}
.tabs {{ display: flex; gap: 4px; flex: 1; overflow-x: auto; }}
.tabs a {{ color: {NAVY_LIGHT}; text-decoration: none; font-size: 15px; padding: 18px 14px 15px;
           border-bottom: 3px solid transparent; white-space: nowrap; }}
.tabs a:hover {{ color: #fff; }}
.tabs a.active {{ color: #fff; font-weight: 600; border-bottom-color: {GREEN}; }}
.pills {{ display: flex; gap: 4px; }}
.pills label {{ color: {NAVY_LIGHT}; padding: 5px 11px; border-radius: 6px; cursor: pointer; font-size: 14px; }}
.pills input {{ display: none; }}
.pills label:has(input:checked) {{ background: {GREEN}; color: {NAVY}; font-weight: 600; }}
.pills.small label {{ color: {TEXT_MUTED}; font-size: 12px; padding: 3px 9px; border: 1px solid {GRID}; }}
.pills.small label:has(input:checked) {{ color: #fff; background: {NAVY}; border-color: {NAVY}; }}
.year-label {{ color: {NAVY_LIGHT}; font-size: 13px; margin-right: 4px; }}
main {{ max-width: 1440px; margin: 0 auto; padding: 20px 24px; }}
.page-sub {{ color: {TEXT_MUTED}; margin: 0 0 16px; font-size: 15px; }}
.kpis {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 12px; margin-bottom: 16px; }}
.kpi {{ background: #fff; border-radius: 8px; padding: 12px 14px; border-left: 4px solid {GREEN};
        box-shadow: 0 1px 4px rgba(11,37,69,.08); }}
.kpi.bad {{ border-left-color: {ALERT}; }}
.kpi-label {{ font-size: 11px; font-weight: 700; color: {TEXT_MUTED}; text-transform: uppercase; letter-spacing: .3px; }}
.kpi-value {{ font-size: 26px; font-weight: 700; color: {NAVY}; margin: 4px 0; white-space: nowrap;
              overflow: hidden; text-overflow: ellipsis; }}
.kpi-delta {{ font-size: 12.5px; font-weight: 600; color: {GREY}; }}
.kpi-delta.good {{ color: {GREEN_DARK}; }}
.kpi-delta.bad {{ color: {ALERT}; }}
.grid {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; }}
.card {{ background: #fff; border-radius: 8px; padding: 14px 16px 6px; box-shadow: 0 1px 4px rgba(11,37,69,.08);
         min-width: 0; }}
.card.wide {{ grid-column: span 2; }}
.card.tall {{ grid-row: span 2; }}
.card h3 {{ margin: 0; font-size: 15px; color: {TEXT}; }}
.card .sub {{ margin: 2px 0 6px; font-size: 12.5px; color: {TEXT_MUTED}; }}
.city-filter {{ margin-bottom: 6px; font-size: 13px; }}
.notes {{ background: #fff; border-left: 4px solid {GREEN}; border-radius: 8px; margin-top: 16px; padding: 14px 24px;
          box-shadow: 0 1px 4px rgba(11,37,69,.08); }}
.notes h3 {{ margin: 0 0 6px; font-size: 16px; color: {NAVY}; }}
.notes ul {{ margin: 0; padding-left: 20px; line-height: 1.55; }}
.notes p {{ margin: 0; }}
.notes strong {{ color: {NAVY}; }}
footer {{ text-align: center; color: {TEXT_MUTED}; font-size: 12px; padding: 8px 24px 28px; }}
@media (max-width: 1000px) {{ .grid {{ grid-template-columns: minmax(0, 1fr); }}
                              .card.wide, .card.tall {{ grid-column: auto; grid-row: auto; }} }}
@media (max-width: 700px) {{ nav {{ padding: 0 12px; }} main {{ padding: 12px 16px; }} }}
"""

app = Dash(__name__, title="Forkly Dashboard", suppress_callback_exceptions=True)
app.index_string = app.index_string.replace("{%css%}", "{%css%}<style>" + CSS + "</style>")

app.layout = html.Div([
    dcc.Location(id="url"),
    html.Nav([
        html.Span("forkly", className="brand"),
        html.Div([dcc.Link(label, href=path, id=f"tab-{i}") for i, (path, label) in enumerate(PAGES)], className="tabs"),
        html.Span("Year", className="year-label"),
        dcc.RadioItems(id="year", options=[{"label": str(y), "value": y} for y in YEARS], value=YEARS[-1],
                       inline=True, className="pills"),
    ]),
    html.Main(id="page"),
    html.Footer("Forkly is a fictional company and all data is simulated (2021-2025). "
                "GMV = value of items sold on non-cancelled orders."),
])


@app.callback(Output("page", "children"), *[Output(f"tab-{i}", "className") for i in range(len(PAGES))],
              Input("url", "pathname"), Input("year", "value"))
def render(path, year):
    path = path if path in BUILDERS else "/"
    cards, charts, bullets = BUILDERS[path](T, year)
    page = [html.P(SUBTITLES[path], className="page-sub"),
            html.Div(cards, className="kpis"),
            html.Div(charts, className="grid"),
            notes(bullets)]
    return page, *["active" if p == path else "" for p, _ in PAGES]


@app.callback(Output("city-bars", "figure"), Output("city-heatmap", "figure"),
              Input("city-filter", "value"), Input("year", "value"))
def update_cities(cities, year):
    return city_figures(T, year, cities)


@app.callback(Output("mkt-channel", "figure"), Input("mkt-metric", "value"), Input("year", "value"))
def update_channels(metric, year):
    return channel_figure(T, year, metric or "spend")


if __name__ == "__main__":
    app.run(debug=False)

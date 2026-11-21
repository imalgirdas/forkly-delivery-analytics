"""
Script:   analysis.py
Purpose:  Build the KPI and summary tables used by the dashboard
          (same logic as notebooks/03_analysis.ipynb)
Input:    Forkly/Data_clean/*.csv
Output:   Forkly/output/tables/*.csv, dict of DataFrames for dashboard.py
"""
import numpy as np
import pandas as pd

from load import TAB_DIR, load_clean

YEARS = [2021, 2022, 2023, 2024, 2025]


def order_table(df):
    """One row per order with revenue, cost and delivery columns joined in."""
    od = (df["orders"]
          .merge(df["cities"][["city_id", "city", "launch_date"]], on="city_id", how="left")
          .merge(df["restaurants"][["restaurant_id", "cuisine", "commission_rate"]], on="restaurant_id", how="left")
          .merge(df["promotions"][["promo_id", "funded_by"]], on="promo_id", how="left")
          .merge(df["deliveries"][["order_id", "courier_id", "courier_pay", "delivery_minutes", "minutes_vs_promise",
                                   "is_late", "weather_condition"]], on="order_id", how="left")
          .merge(df["reviews"][["order_id", "food_rating", "delivery_rating"]], on="order_id", how="left"))

    refunds = df["support_tickets"].groupby("order_id")["refund_amount"].sum()
    od["refund_amount"] = od["order_id"].map(refunds).fillna(0)

    share = od["funded_by"].map({"Platform": 1.0, "Shared": 0.5, "Restaurant": 0.0}).fillna(0)
    od["commission"] = od["items_subtotal"] * od["commission_rate"]
    od["platform_discount"] = od["discount_amount"] * share
    od["net_revenue"] = od["commission"] + od["delivery_fee"] + od["service_fee"] - od["platform_discount"]
    od["contribution"] = od["net_revenue"] - od["courier_pay"].fillna(0) - od["refund_amount"]
    return od


def kpi_by_year(od, done, df):
    g = done.groupby("year")
    customers, mkt = df["customers"], df["marketing_spend"]
    kpi = pd.DataFrame({
        "orders": od.groupby("year").size(),
        "gmv": g["items_subtotal"].sum(),
        "aov": g["items_subtotal"].mean(),
        "active_customers": od.groupby("year")["customer_id"].nunique(),
        "new_customers": customers.groupby("signup_year").size(),
        "net_revenue": g["net_revenue"].sum(),
        "contribution": g["contribution"].sum(),
        "cancel_rate_%": od.groupby("year")["is_cancelled"].mean() * 100,
        "late_rate_%": g["is_late"].mean() * 100,
        "avg_delivery_min": g["delivery_minutes"].mean(),
        "delivery_rating": g["delivery_rating"].mean(),
        "food_rating": g["food_rating"].mean(),
        "promo_order_%": od.groupby("year")["has_promo"].mean() * 100,
        "plus_order_%": od.groupby("year")["is_plus_order"].mean() * 100,
        "grocery_order_%": od.groupby("year")["vertical"].apply(lambda s: (s == "Grocery").mean() * 100),
        "marketing_spend": mkt.groupby(mkt["date"].dt.year)["spend_eur"].sum(),
    })
    kpi["take_rate_%"] = kpi["net_revenue"] / kpi["gmv"] * 100
    kpi["contribution_margin_%"] = kpi["contribution"] / kpi["gmv"] * 100
    kpi["orders_per_customer"] = kpi["orders"] / kpi["active_customers"]
    kpi["cac"] = kpi["marketing_spend"] / kpi["new_customers"]
    kpi["gmv_growth_%"] = kpi["gmv"].pct_change() * 100
    kpi.index.name = "year"
    return kpi.astype(float)


def retention_tables(df):
    orders, customers = df["orders"], df["customers"]
    q = orders[["customer_id", "order_datetime"]].merge(customers[["customer_id", "signup_date"]], on="customer_id")
    q["cohort"] = q["signup_date"].dt.to_period("Q")
    q["q_since"] = (q["order_datetime"].dt.to_period("Q") - q["cohort"]).apply(lambda d: d.n)
    size = customers.groupby(customers["signup_date"].dt.to_period("Q")).size()
    cohort = (q.groupby(["cohort", "q_since"])["customer_id"].nunique().unstack().div(size, axis=0) * 100).loc[:, 0:8]
    cohort.index = cohort.index.astype(str)

    buyers = orders.groupby("year")["customer_id"].apply(set)
    yoy = pd.Series({y: len(buyers[y] & buyers[y + 1]) / len(buyers[y]) * 100 for y in YEARS[:-1]},
                    name="retained_next_year_%")

    first_year = orders.groupby("customer_id")["year"].min().rename("first_year")
    nr = orders.join(first_year, on="customer_id")
    nr["type"] = np.where(nr["year"] == nr["first_year"], "New customer", "Returning customer")
    new_ret = pd.crosstab(nr["year"], nr["type"], normalize="index") * 100
    return cohort, yoy, new_ret


def first_order_repeat(orders, done):
    """First order per customer, its promo/late flags and whether a 2nd order came within 90 days."""
    ranked = orders.sort_values("order_datetime").assign(n=lambda d: d.groupby("customer_id").cumcount() + 1)
    second = ranked[ranked["n"] == 2].set_index("customer_id")["order_datetime"].rename("second_order")
    first = ranked[ranked["n"] == 1][["customer_id", "order_id", "order_datetime", "has_promo", "year"]]
    first = first.join(second, on="customer_id")
    first = first.merge(done[["order_id", "is_late"]], on="order_id", how="left")
    first["repeat_90d"] = (first["second_order"] - first["order_datetime"]).dt.days <= 90
    return first[first["order_datetime"] < "2025-10-01"]   # needs 90 days of follow-up


def rfm_segments(done):
    snapshot = pd.Timestamp("2026-01-01")
    last12 = done[done["order_datetime"] >= snapshot - pd.DateOffset(months=12)]
    rfm = pd.DataFrame({
        "recency_days": (snapshot - done.groupby("customer_id")["order_datetime"].max()).dt.days,
        "frequency": last12.groupby("customer_id").size(),
        "monetary": last12.groupby("customer_id")["items_subtotal"].sum(),
    }).fillna({"frequency": 0, "monetary": 0})
    rfm["R"] = pd.qcut(rfm["recency_days"].rank(method="first"), 5, labels=[5, 4, 3, 2, 1]).astype(int)
    rfm["F"] = pd.qcut(rfm["frequency"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)

    conditions = [(rfm.R >= 4) & (rfm.F >= 4), (rfm.R >= 3) & (rfm.F >= 3), (rfm.R >= 4) & (rfm.F <= 2),
                  rfm.R == 3, (rfm.R <= 2) & (rfm.F >= 3)]
    names = ["Champions", "Loyal", "New / promising", "Needs attention", "At risk"]
    rfm["segment"] = np.select(conditions, names, default="Lost / inactive")

    seg = rfm.groupby("segment").agg(customers=("R", "size"), avg_recency_days=("recency_days", "mean"),
                                     avg_orders_12m=("frequency", "mean"), gmv_12m=("monetary", "sum"))
    seg["customers_%"] = seg["customers"] / seg["customers"].sum() * 100
    seg["gmv_%"] = seg["gmv_12m"] / seg["gmv_12m"].sum() * 100
    return seg.reindex(names + ["Lost / inactive"])


def build_all(df=None, save=True):
    df = df or load_clean()
    od = order_table(df)
    done = od[~od["is_cancelled"]].copy()
    t = {}

    t["kpi_by_year"] = kpi_by_year(od, done, df)
    t["monthly"] = done.groupby("month").agg(orders=("order_id", "size"), gmv=("items_subtotal", "sum"),
                                             late_rate=("is_late", "mean"), delivery_min=("delivery_minutes", "mean"),
                                             delivery_rating=("delivery_rating", "mean"))
    t["monthly"] = t["monthly"].astype(float)
    t["monthly"]["late_rate"] *= 100

    # growth by city
    cy = done.groupby(["year", "city", "launch_date"])["items_subtotal"].sum().reset_index()
    cy["group"] = np.where(cy["launch_date"].dt.year == 2021, "Launch cities", "Expansion cities")
    t["gmv_by_city_group"] = cy.pivot_table(index="year", columns="group", values="items_subtotal",
                                            aggfunc="sum", fill_value=0)[["Launch cities", "Expansion cities"]]
    t["gmv_by_city_year"] = done.pivot_table(index="city", columns="year", values="items_subtotal",
                                             aggfunc="sum", fill_value=0)

    # unit economics
    t["unit_economics"] = done.groupby("year")[["commission", "delivery_fee", "service_fee", "platform_discount",
                                                "courier_pay", "refund_amount", "contribution"]].mean()

    # customers
    t["cohort_retention"], t["yoy_retention"], t["new_vs_returning"] = retention_tables(df)
    ch = df["customers"].groupby(["signup_year", "acquisition_channel"]).size().unstack()
    t["channel_mix"] = ch.div(ch.sum(axis=1), axis=0) * 100
    t["rfm_segments"] = rfm_segments(done)

    # Plus
    o25 = done[done["year"] == 2025]
    c25 = o25.groupby("customer_id").agg(orders=("order_id", "size"), aov=("items_subtotal", "mean"),
                                         delivery_fee=("delivery_fee", "mean"), plus=("is_plus_order", "max"))
    c25["group"] = np.where(c25["plus"], "Plus member", "Non-member")
    t["plus_vs_non_member"] = c25.groupby("group").agg(customers=("orders", "size"), orders_per_customer=("orders", "mean"),
                                                       aov=("aov", "mean"), avg_delivery_fee=("delivery_fee", "mean"))

    # promotions and first orders
    first = first_order_repeat(df["orders"], done)
    pr = first.pivot_table(index="year", columns="has_promo", values="repeat_90d", aggfunc="mean") * 100
    pr.columns = ["repeat_no_promo_%", "repeat_promo_%"]
    promo = done.groupby("year").agg(discount_total=("discount_amount", "sum"), paid_by_forkly=("platform_discount", "sum"))
    promo["paid_by_forkly_%_gmv"] = promo["paid_by_forkly"] / t["kpi_by_year"]["gmv"] * 100
    t["promo_effect"] = promo.join(pr)
    lr = first.dropna(subset=["is_late"]).assign(is_late=lambda d: d["is_late"].astype(bool)).groupby("is_late")["repeat_90d"].mean() * 100
    t["late_first_order_repeat"] = lr.rename(index={False: "On time", True: "Late"}).to_frame("repeat_90d_%")

    # delivery experience
    rated = done.dropna(subset=["delivery_rating", "minutes_vs_promise"]).copy()
    labels = ["5+ min early", "0-5 early", "0-5 late", "5-10 late", "10-15 late", "15-20 late", "20+ late"]
    rated["bucket"] = pd.cut(rated["minutes_vs_promise"], [-np.inf, -5, 0, 5, 10, 15, 20, np.inf], labels=labels)
    t["rating_by_delay"] = rated.groupby("bucket", observed=True).agg(reviews=("order_id", "size"),
                                                                     delivery_rating=("delivery_rating", "mean"))
    t["late_by_weather"] = (done.groupby("weather_condition")["is_late"].mean().astype(float) * 100).reindex(["Dry", "Rain", "Heavy rain", "Snow"])
    veh = done.merge(df["couriers"][["courier_id", "vehicle_type"]], on="courier_id", how="left")
    vy = veh.pivot_table(index="year", columns="vehicle_type", values="order_id", aggfunc="size")
    t["vehicle_mix"] = vy.div(vy.sum(axis=1), axis=0) * 100
    t["cancel_reasons"] = df["orders"].groupby(["year", "cancellation_reason"]).size().unstack(fill_value=0)

    tk = df["support_tickets"].merge(df["orders"][["order_id", "year"]], on="order_id")
    sup = tk.groupby("year").agg(tickets=("ticket_id", "size"), median_resolution_h=("resolution_hours", "median"),
                                 csat=("csat_score", "mean"), refunds=("refund_amount", "sum"))
    sup["tickets_per_100_orders"] = sup["tickets"] / t["kpi_by_year"]["orders"] * 100
    t["support"] = sup

    # weather demand: orders vs a normal day for that city and month
    cd = (df["orders"].groupby(["order_date", "city_id"]).size().rename("orders").reset_index()
          .merge(df["weather_daily"], left_on=["order_date", "city_id"], right_on=["date", "city_id"], how="left"))
    cd["idx"] = cd["orders"] / cd.groupby(["city_id", cd["order_date"].dt.to_period("M")])["orders"].transform("mean")
    cd["rain"] = pd.cut(cd["precip_mm"], [-0.1, 0, 2, 5, 10, 100], labels=["Dry", "0-2 mm", "2-5 mm", "5-10 mm", "10+ mm"])
    t["rain_demand"] = (cd.groupby("rain", observed=True)["idx"].mean() - 1) * 100

    # marketing
    mk = df["marketing_spend"].assign(year=df["marketing_spend"]["date"].dt.year)
    cyr = mk.groupby(["year", "channel"]).agg(spend=("spend_eur", "sum"), signups=("attributed_signups", "sum"))
    cyr["cost_per_signup"] = cyr["spend"] / cyr["signups"].replace(0, np.nan)
    t["marketing_by_channel_year"] = cyr

    # cuisines and restaurants
    cz = done.pivot_table(index="cuisine", columns="year", values="items_subtotal", aggfunc="sum", fill_value=0)
    cz["growth_2023_2025_%"] = (cz[2025] / cz[2023].replace(0, np.nan) - 1) * 100
    cz["share_2025_%"] = cz[2025] / cz[2025].sum() * 100
    cz["aov"] = done.groupby("cuisine")["items_subtotal"].mean()
    t["cuisine_performance"] = cz.sort_values(2025, ascending=False)
    rg = done[done["year"] == 2025].groupby("restaurant_id")["items_subtotal"].sum().sort_values(ascending=False)
    t["restaurant_pareto"] = (rg.cumsum() / rg.sum() * 100).reset_index(drop=True).to_frame("cum_gmv_%")
    t["restaurant_pareto"]["restaurants_%"] = (np.arange(1, len(rg) + 1) / len(rg)) * 100
    t["seasonality"] = (lambda s: s.div(s.mean(axis=1), axis=0))(
        done.groupby(["year", done["order_datetime"].dt.month])["order_id"].size().unstack())
    t["weekday_hour"] = (done.assign(wd=done["order_datetime"].dt.dayofweek)
                         .pivot_table(index="wd", columns="hour", values="order_id", aggfunc="size"))

    if save:
        TAB_DIR.mkdir(parents=True, exist_ok=True)
        for name, table in t.items():
            table.to_csv(TAB_DIR / f"{name}.csv")
        print(f"  saved {len(t)} summary tables to {TAB_DIR}")
    return t


if __name__ == "__main__":
    tables = build_all()
    print(tables["kpi_by_year"].T.round(2))

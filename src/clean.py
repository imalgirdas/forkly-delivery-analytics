"""
Script:   clean.py
Purpose:  Fix the data-quality problems in the raw files and save clean copies
          (same steps as notebooks/01_cleaning.ipynb, as a script for run_all.py)
Input:    Forkly/Data/*.csv
Output:   Forkly/Data_clean/*.csv, Forkly/Data_clean/cleaning_log.csv
"""
import numpy as np
import pandas as pd

from load import CLEAN_DIR, load_raw

log = []


def log_fix(table, issue, rows, action):
    log.append({"table": table, "issue": issue, "rows_affected": int(rows), "action": action})
    print(f"  [{table}] {issue}: {int(rows):,} rows -> {action}")


# Orders ----
def clean_orders(orders):
    platform_map = {"ios": "iOS", "android": "Android", "web": "Web"}
    payment_map = {"card": "Card", "apple pay": "Apple Pay", "google pay": "Google Pay",
                   "cash": "Cash", "forkly wallet": "Forkly Wallet"}

    before = orders["platform"].copy()
    orders["platform"] = orders["platform"].str.strip().str.lower().map(platform_map)
    log_fix("orders", "platform in wrong case", (before != orders["platform"]).sum(), "mapped to iOS / Android / Web")

    before = orders["payment_method"].copy()
    orders["payment_method"] = orders["payment_method"].str.strip().str.lower().map(payment_map)
    log_fix("orders", "payment_method uppercase / trailing space", (before != orders["payment_method"]).sum(),
            "trimmed and mapped to standard names")

    # text first: some duplicates only differ by casing
    n_dup = orders.duplicated().sum()
    orders = orders.drop_duplicates().reset_index(drop=True)
    log_fix("orders", "duplicated rows", n_dup, "dropped")
    assert orders["order_id"].is_unique

    calc_total = (orders["items_subtotal"] + orders["delivery_fee"] + orders["service_fee"]
                  - orders["discount_amount"] + orders["tip_amount"]).round(2)
    wrong = (calc_total - orders["total_amount"]).abs() > 0.02
    orders.loc[wrong, "total_amount"] = calc_total[wrong]
    log_fix("orders", "total_amount still includes tip on cancelled orders", wrong.sum(), "recalculated")

    orders["promo_id"] = orders["promo_id"].astype("Int64")
    orders["has_promo"] = orders["promo_id"].notna()
    orders["is_cancelled"] = orders["order_status"].eq("Cancelled")
    orders["order_date"] = orders["order_datetime"].dt.normalize()
    orders["year"] = orders["order_datetime"].dt.year
    orders["month"] = orders["order_datetime"].dt.to_period("M").dt.to_timestamp()
    orders["hour"] = orders["order_datetime"].dt.hour
    return orders


# Customers ----
def clean_customers(customers, orders):
    iso = pd.to_datetime(customers["signup_date"], format="%Y-%m-%d", errors="coerce")
    dmy = pd.to_datetime(customers["signup_date"], format="%d/%m/%Y", errors="coerce")
    log_fix("customers", "signup_date in DD/MM/YYYY format", (iso.isna() & dmy.notna()).sum(), "parsed separately")
    customers["signup_date"] = iso.fillna(dmy)

    bad_age = customers["age"].notna() & ~customers["age"].between(16, 100)
    log_fix("customers", "age outside 16-100", bad_age.sum(), "set to missing")
    customers.loc[bad_age, "age"] = np.nan
    customers["age"] = customers["age"].astype("Int64")
    customers["age_group"] = pd.cut(customers["age"].astype("float"), bins=[15, 24, 34, 44, 54, 64, 100],
                                    labels=["16-24", "25-34", "35-44", "45-54", "55-64", "65+"])
    customers["age_group"] = customers["age_group"].cat.add_categories("Unknown").fillna("Unknown")

    gender_map = {"female": "Female", "f": "Female", "male": "Male", "m": "Male", "other": "Other", "o": "Other"}
    before = customers["gender"].copy()
    customers["gender"] = customers["gender"].str.strip().str.lower().map(gender_map).fillna("Unknown")
    log_fix("customers", "gender spelled F / female / blank", (before != customers["gender"]).sum(), "standardised")

    first_order = customers["customer_id"].map(orders.groupby("customer_id")["order_date"].min())
    early = first_order.notna() & (first_order < customers["signup_date"])
    customers.loc[early, "signup_date"] = first_order[early]
    log_fix("customers", "first order before signup_date", early.sum(), "signup_date moved to first order date")

    customers["signup_year"] = customers["signup_date"].dt.year
    customers["signup_month"] = customers["signup_date"].dt.to_period("M").dt.to_timestamp()
    return customers


# Restaurants ----
def clean_restaurants(restaurants):
    key = restaurants["cuisine"].str.strip().str.lower()
    standard = (restaurants.assign(key=key).groupby("key")["cuisine"]
                .agg(lambda s: s.str.strip().value_counts().idxmax()))
    before = restaurants["cuisine"].copy()
    restaurants["cuisine"] = key.map(standard)
    log_fix("restaurants", "cuisine casing / trailing spaces", (before != restaurants["cuisine"]).sum(), "standardised")
    return restaurants


# Order items ----
def clean_order_items(order_items, orders, menu_items):
    items = order_items.merge(orders[["order_id", "year"]], on="order_id", how="left")
    missing = items["unit_price"].isna()
    items["unit_price"] = items["unit_price"].fillna(items.groupby(["item_id", "year"])["unit_price"].transform("median"))

    if items["unit_price"].isna().any():
        base = menu_items.set_index("item_id")["base_price_2021"]
        infl = (items.dropna(subset=["unit_price"]).assign(r=lambda d: d["unit_price"] / d["item_id"].map(base))
                .groupby("year")["r"].median())
        gap = items["unit_price"].isna()
        items.loc[gap, "unit_price"] = (items.loc[gap, "item_id"].map(base) * items.loc[gap, "year"].map(infl)).round(2)

    items["line_total"] = (items["quantity"] * items["unit_price"]).round(2)
    log_fix("order_items", "missing unit_price / line_total", missing.sum(), "filled with same item's price that year")
    return items.drop(columns="year")


# Deliveries ----
def clean_deliveries(deliveries, orders):
    d = deliveries.merge(orders[["order_id", "order_datetime"]], on="order_id", how="left")
    from_ts = ((d["dropoff_datetime"] - d["order_datetime"]).dt.total_seconds() / 60).round(1)
    bad = (d["delivery_minutes"] <= 0) | (d["delivery_minutes"] > 180)
    d.loc[bad, "delivery_minutes"] = from_ts[bad]
    log_fix("deliveries", "delivery_minutes <= 0 or > 180", bad.sum(), "recalculated from timestamps")

    failed = d["delivery_status"].eq("Failed")
    d["is_late"] = d["is_late"].astype("boolean")
    d.loc[failed, "delivery_minutes"] = np.nan
    d.loc[failed, "is_late"] = pd.NA

    missing = d["courier_id"].isna()
    log_fix("deliveries", "missing courier_id", missing.sum(), "kept, flagged with courier_known = False")
    d["courier_id"] = d["courier_id"].astype("Int64")
    d["courier_known"] = ~missing
    d["minutes_vs_promise"] = (d["delivery_minutes"] - d["promised_minutes"]).round(1)
    return d.drop(columns="order_datetime")


# Reviews, tickets, marketing ----
def clean_reviews(reviews):
    for col in ["food_rating", "delivery_rating"]:
        bad = ~reviews[col].between(1, 5)
        log_fix("reviews", f"{col} outside 1-5", bad.sum(), "set to missing")
        reviews.loc[bad, col] = np.nan
        reviews[col] = reviews[col].astype("Int64")
    return reviews


def clean_tickets(tickets):
    wrong = tickets["resolved_datetime"] < tickets["created_datetime"]
    tickets.loc[wrong, "resolved_datetime"] = (tickets.loc[wrong, "created_datetime"]
                                               + pd.to_timedelta(tickets.loc[wrong, "resolution_hours"], unit="h")).dt.floor("s")
    log_fix("support_tickets", "resolved before created", wrong.sum(), "recalculated as created + resolution_hours")
    return tickets


def clean_marketing(mkt):
    mkt = mkt.sort_values(["channel", "date"]).reset_index(drop=True)
    missing = mkt["spend_eur"].isna()
    mkt["spend_eur"] = mkt.groupby("channel")["spend_eur"].transform(lambda s: s.interpolate(limit_direction="both")).round(2)
    log_fix("marketing_spend", "missing spend_eur", missing.sum(), "interpolated within channel")
    return mkt


# Checks ----
FOREIGN_KEYS = [
    ("orders", "customer_id", "customers", "customer_id"),
    ("orders", "restaurant_id", "restaurants", "restaurant_id"),
    ("orders", "city_id", "cities", "city_id"),
    ("orders", "promo_id", "promotions", "promo_id"),
    ("order_items", "order_id", "orders", "order_id"),
    ("order_items", "item_id", "menu_items", "item_id"),
    ("deliveries", "order_id", "orders", "order_id"),
    ("deliveries", "courier_id", "couriers", "courier_id"),
    ("reviews", "order_id", "orders", "order_id"),
    ("support_tickets", "order_id", "orders", "order_id"),
    ("subscriptions", "customer_id", "customers", "customer_id"),
    ("restaurants", "city_id", "cities", "city_id"),
    ("menu_items", "restaurant_id", "restaurants", "restaurant_id"),
]


def check_keys(df):
    for child, ccol, parent, pcol in FOREIGN_KEYS:
        orphans = (~df[child][ccol].dropna().isin(df[parent][pcol])).sum()
        assert orphans == 0, f"{child}.{ccol}: {orphans} rows point to missing {parent}"
    print(f"  all {len(FOREIGN_KEYS)} foreign keys match")


def run():
    log.clear()
    print("Cleaning raw data...")
    raw = load_raw()
    df = {k: v.copy() for k, v in raw.items()}

    df["orders"] = clean_orders(df["orders"])
    df["customers"] = clean_customers(df["customers"], df["orders"])
    df["restaurants"] = clean_restaurants(df["restaurants"])
    df["order_items"] = clean_order_items(df["order_items"], df["orders"], df["menu_items"])
    df["deliveries"] = clean_deliveries(df["deliveries"], df["orders"])
    df["reviews"] = clean_reviews(df["reviews"])
    df["support_tickets"] = clean_tickets(df["support_tickets"])
    df["marketing_spend"] = clean_marketing(df["marketing_spend"])
    check_keys(df)

    CLEAN_DIR.mkdir(exist_ok=True)
    for name, table in df.items():
        table.to_csv(CLEAN_DIR / f"{name}.csv", index=False)
    pd.DataFrame(log).to_csv(CLEAN_DIR / "cleaning_log.csv", index=False)
    print(f"  saved {len(df)} clean tables to {CLEAN_DIR}")
    return df


if __name__ == "__main__":
    run()

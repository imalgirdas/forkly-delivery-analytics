"""
Script:   load.py
Purpose:  Project paths and functions to read the raw and cleaned CSV files
Input:    Forkly/Data/*.csv, Forkly/Data_clean/*.csv
Output:   dict of pandas DataFrames
"""
from pathlib import Path

import pandas as pd

# Paths ----
# src/ sits one level below the project folder
BASE = Path(__file__).resolve().parents[1]
RAW_DIR = BASE / "Data"
CLEAN_DIR = BASE / "Data_clean"
OUTPUT_DIR = BASE / "output"
FIG_DIR = OUTPUT_DIR / "figures"
TAB_DIR = OUTPUT_DIR / "tables"
DASH_DIR = OUTPUT_DIR / "dashboard"

TABLES = ["calendar", "cities", "weather_daily", "customers", "restaurants", "menu_items", "couriers",
          "promotions", "subscriptions", "orders", "order_items", "deliveries", "reviews",
          "support_tickets", "marketing_spend"]

# date columns per table (customers.signup_date is only parsed for clean data,
# the raw file has two formats)
RAW_DATES = {
    "calendar": ["date"],
    "cities": ["launch_date"],
    "weather_daily": ["date"],
    "restaurants": ["onboarded_date", "offboarded_date"],
    "couriers": ["join_date"],
    "promotions": ["start_date", "end_date"],
    "subscriptions": ["start_date", "end_date"],
    "orders": ["order_datetime"],
    "deliveries": ["pickup_datetime", "dropoff_datetime"],
    "reviews": ["review_datetime"],
    "support_tickets": ["created_datetime", "resolved_datetime"],
    "marketing_spend": ["date"],
}
CLEAN_DATES = {**RAW_DATES,
               "customers": ["signup_date", "signup_month"],
               "orders": ["order_datetime", "order_date", "month"]}


def _read_folder(folder, date_cols):
    folder = Path(folder)
    missing = [t for t in TABLES if not (folder / f"{t}.csv").exists()]
    if missing:
        raise FileNotFoundError(f"Missing files in {folder}: {', '.join(missing)}")
    return {t: pd.read_csv(folder / f"{t}.csv", parse_dates=date_cols.get(t, [])) for t in TABLES}


def load_raw(folder=RAW_DIR):
    """The 15 raw tables, as delivered."""
    return _read_folder(folder, RAW_DATES)


def load_clean(folder=CLEAN_DIR):
    """The 15 cleaned tables written by clean.py (or 01_cleaning.ipynb)."""
    return _read_folder(folder, CLEAN_DATES)


if __name__ == "__main__":
    for name, table in load_raw().items():
        print(f"{name:18s} {len(table):>9,} rows x {table.shape[1]:>2} cols")

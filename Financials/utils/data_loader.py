import os
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

NA_MARKERS = {
    "NOT_AVAILABLE_PUBLICLY", "NOT_AVAILABLE", "SUBSCRIPTION_REQUIRED",
    "LP_REPORTED_ONLY", "MANAGER_REPORTED_ONLY", "TOO_YOUNG_TO_EVALUATE",
    "NEEDS_MANUAL_REVIEW", "STALE", "NOT_MEANINGFUL_YET"
}


def _load(filename: str) -> pd.DataFrame:
    path = os.path.join(DATA_DIR, filename)
    if os.path.exists(path):
        try:
            df = pd.read_csv(path, dtype=str)
            df = df.dropna(how="all")
            return df
        except Exception as e:
            return pd.DataFrame()
    return pd.DataFrame()


def load_funds() -> pd.DataFrame:
    df = _load("funds.csv")
    if df.empty:
        return df
    numeric_cols = ["fund_size_usd_bn", "vintage_year"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def load_performance() -> pd.DataFrame:
    df = _load("performance.csv")
    if df.empty:
        return df
    numeric_cols = [
        "committed_usd_m", "contributed_usd_m", "distributed_usd_m",
        "market_value_usd_m", "net_irr_pct", "dpi", "rvpi", "tvpi", "data_age_months"
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def load_manager_profiles() -> pd.DataFrame:
    return _load("manager_profiles.csv")


def load_market_segments() -> pd.DataFrame:
    return _load("market_segments.csv")


def load_sources() -> pd.DataFrame:
    return _load("sources.csv")


def load_deals() -> pd.DataFrame:
    return _load("deals.csv")


def load_lp_commitments() -> pd.DataFrame:
    return _load("lp_commitments.csv")


def save_csv(df: pd.DataFrame, filename: str):
    path = os.path.join(DATA_DIR, filename)
    os.makedirs(DATA_DIR, exist_ok=True)
    df.to_csv(path, index=False)


def funds_with_performance(funds_df, perf_df) -> set:
    if perf_df.empty or funds_df.empty:
        return set()
    direct = perf_df[perf_df.get("is_predecessor_benchmark", pd.Series(["No"] * len(perf_df))) != "Yes"]
    return set(direct["fund_id"].unique())


def funds_needing_review(funds_df) -> pd.DataFrame:
    if funds_df.empty:
        return funds_df
    mask = (
        funds_df["fund_size_usd_bn"].isna() |
        funds_df["target_size_usd_bn"].isin(NA_MARKERS) |
        (funds_df["source_confidence"] == "Low") |
        funds_df["final_close_date"].isin(NA_MARKERS)
    )
    return funds_df[mask]

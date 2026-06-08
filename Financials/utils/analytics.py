from datetime import datetime

NA_MARKERS = {
    "NOT_AVAILABLE_PUBLICLY", "NOT_AVAILABLE", "SUBSCRIPTION_REQUIRED",
    "LP_REPORTED_ONLY", "MANAGER_REPORTED_ONLY", "TOO_YOUNG_TO_EVALUATE",
    "NEEDS_MANUAL_REVIEW", "STALE", "NOT_MEANINGFUL_YET", "nan", "", "None"
}


def is_na(v) -> bool:
    return str(v).strip() in NA_MARKERS


def to_num(v):
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


def calculate_performance_flags(row) -> str:
    flags = []

    vintage = to_num(row.get("vintage_year"))
    current_year = datetime.now().year
    fund_age = (current_year - int(vintage)) if vintage else None

    net_irr = to_num(row.get("net_irr_pct"))
    dpi = to_num(row.get("dpi"))
    tvpi = to_num(row.get("tvpi"))
    rvpi = to_num(row.get("rvpi"))

    source_type = str(row.get("source_type", "")).upper()
    as_of = str(row.get("as_of_date", ""))
    is_pred = str(row.get("is_predecessor_benchmark", "")).lower() in ("true", "yes", "1")

    # Age / staleness (skip for predecessor benchmarks — they have their own vintage)
    if fund_age is not None and fund_age <= 3 and not is_pred:
        flags.append("Too young to evaluate — IRR not meaningful")

    # Stale data check
    if as_of and as_of not in NA_MARKERS:
        try:
            as_of_dt = datetime.strptime(as_of[:10], "%Y-%m-%d")
            months_old = (datetime.now() - as_of_dt).days / 30
            if months_old > 18:
                flags.append("Stale data — as-of date exceeds 18 months")
        except ValueError:
            pass

    # IRR / DPI flags
    if net_irr is not None and dpi is not None:
        if net_irr > 20 and dpi < 0.25:
            flags.append("High interim return; limited cash realization")
        elif net_irr > 15 and dpi < 0.4:
            flags.append("Moderate IRR; DPI below 0.4x — mostly unrealized")

    # NAV-heavy TVPI
    if tvpi is not None and dpi is not None:
        if tvpi > 1.3 and dpi < 0.5:
            flags.append("NAV-heavy return; realization risk remains")

    # Capital returned
    if dpi is not None and dpi >= 1.0:
        flags.append("Capital substantially returned (DPI >= 1.0x)")

    # Source type warning
    if "LP_REPORTED" in source_type:
        flags.append("LP-level capital account — not official full-fund return")

    # No data
    if net_irr is None and dpi is None and tvpi is None:
        flags.append("Performance unavailable publicly")

    # Predecessor
    if is_pred:
        flags.append("Predecessor benchmark — not the tracked fund")

    return " | ".join(flags) if flags else "No flags"


def compute_metrics(row):
    contributed = to_num(row.get("contributed_usd_m"))
    distributed = to_num(row.get("distributed_usd_m"))
    market_value = to_num(row.get("market_value_usd_m"))

    result = {}
    if contributed and contributed > 0:
        if distributed is not None:
            result["dpi_calc"] = round(distributed / contributed, 4)
        if market_value is not None:
            result["rvpi_calc"] = round(market_value / contributed, 4)
        if distributed is not None and market_value is not None:
            result["tvpi_calc"] = round((distributed + market_value) / contributed, 4)
    return result


def apply_flags_to_df(perf_df, funds_df=None):
    import pandas as pd

    if funds_df is not None and len(funds_df):
        vintage_map = funds_df.set_index("fund_id")["vintage_year"].to_dict()
        perf_df = perf_df.copy()
        if "vintage_year" not in perf_df.columns:
            perf_df["vintage_year"] = perf_df["fund_id"].map(vintage_map)

    perf_df["quality_flag"] = perf_df.apply(calculate_performance_flags, axis=1)
    return perf_df

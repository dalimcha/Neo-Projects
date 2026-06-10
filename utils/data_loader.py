"""
data_loader.py
──────────────
Central data I/O layer.  All pages import from here.
Reads CSV files from /data, merges them, and returns clean DataFrames.
Falls back gracefully when files are missing or partially populated.
"""

from __future__ import annotations
import os
import pandas as pd
import numpy as np
import streamlit as st
from datetime import datetime, date
from pathlib import Path
from typing import Optional

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT  = Path(__file__).parent.parent
DATA  = ROOT / "data"

UNIVERSE_CSV      = DATA / "universe.csv"
PRICES_CSV        = DATA / "prices.csv"
RETURNS_SNAPSHOT_CSV = DATA / "returns_snapshot.csv"
SECTOR_PERFORMANCE_CSV = DATA / "sector_performance.csv"
VOLUME_SHOCKS_CSV = DATA / "volume_shocks.csv"
FUNDAMENTALS_CSV  = DATA / "fundamentals.csv"
ORDER_BOOK_CSV    = DATA / "order_book.csv"
FILINGS_CSV       = DATA / "filings.csv"
NEWS_CSV          = DATA / "news.csv"
SECTORS_CSV       = DATA / "sectors.csv"
NOTES_CSV         = DATA / "notes.csv"
AI_SUMMARIES_CSV  = DATA / "ai_summaries.csv"
QUARTERLY_CSV     = DATA / "quarterly_financials.csv"
CORPORATE_ACTIONS_CSV = DATA / "corporate_actions.csv"
DATA_QUALITY_LOG_CSV = DATA / "data_quality_log.csv"
FAILED_TICKERS_CSV = DATA / "failed_tickers.csv"


# ── Generic helpers ───────────────────────────────────────────────────────────

def _safe_read(path: Path, **kwargs) -> pd.DataFrame:
    """Read CSV, return empty DataFrame on any error."""
    try:
        if path.exists():
            return pd.read_csv(path, **kwargs)
    except Exception:
        pass
    return pd.DataFrame()


def _to_float(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


# ── Universe ──────────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600)
def load_universe() -> pd.DataFrame:
    """
    Master list of companies.
    Columns: ticker, company_name, sector, industry,
             index_membership, isin, bse_code, nse_code
    """
    df = _safe_read(UNIVERSE_CSV)
    if df.empty:
        return _empty_universe()
    df["ticker"] = df["ticker"].astype(str).str.strip().str.upper()
    return df


def _empty_universe() -> pd.DataFrame:
    cols = ["ticker","company_name","sector","industry",
            "index_membership","isin","bse_code","nse_code"]
    return pd.DataFrame(columns=cols)


# ── Prices ────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def load_prices() -> pd.DataFrame:
    """
    Daily price + return data.
    Columns: ticker, date, close, high, low, open, volume,
             return_1d, return_1w, return_1m, return_3m, return_6m, return_1y,
             high_52w, low_52w, dist_52w_high_pct, dist_52w_low_pct,
             deliverable_qty, deliverable_pct
    """
    df = _safe_read(PRICES_CSV)
    if df.empty:
        return pd.DataFrame()
    df["ticker"] = df["ticker"].astype(str).str.strip().str.upper()
    num_cols = ["close","high","low","open","volume","return_1d","return_1w",
                "return_1m","return_3m","return_6m","return_1y",
                "high_52w","low_52w","dist_52w_high_pct","dist_52w_low_pct",
                "deliverable_qty","deliverable_pct"]
    for c in num_cols:
        if c in df.columns:
            df[c] = _to_float(df[c])
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df


@st.cache_data(ttl=300)
def load_returns_snapshot() -> pd.DataFrame:
    df = _safe_read(RETURNS_SNAPSHOT_CSV)
    if df.empty:
        return pd.DataFrame()
    if "ticker" in df.columns:
        df["ticker"] = df["ticker"].astype(str).str.strip().str.upper()
    num_cols = [
        "price","prev_close","volume","avg_volume_30d","volume_ratio_30d",
        "return_1d","return_1w","return_1m","return_3m","return_6m","return_1y",
        "high_52w","low_52w","dist_52w_high_pct","dist_52w_low_pct","market_cap_cr",
    ]
    for c in num_cols:
        if c in df.columns:
            df[c] = _to_float(df[c])
    for c in ["date", "price_timestamp", "fundamentals_as_of", "updated_at"]:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce")
    return df


@st.cache_data(ttl=300)
def load_sector_performance() -> pd.DataFrame:
    df = _safe_read(SECTOR_PERFORMANCE_CSV)
    if df.empty:
        return pd.DataFrame()
    num_cols = [
        "stock_count","valid_return_count","advancers","decliners","unchanged",
        "positive_pct","negative_pct","avg_return_1d","median_return_1d",
        "avg_return_1w","avg_return_1m","market_cap_sum_cr",
    ]
    for c in num_cols:
        if c in df.columns:
            df[c] = _to_float(df[c])
    for c in ["price_timestamp", "updated_at"]:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce")
    return df


@st.cache_data(ttl=300)
def load_volume_shocks() -> pd.DataFrame:
    df = _safe_read(VOLUME_SHOCKS_CSV)
    if df.empty:
        return pd.DataFrame()
    if "ticker" in df.columns:
        df["ticker"] = df["ticker"].astype(str).str.strip().str.upper()
    num_cols = [
        "price","volume","avg_volume_30d","volume_ratio_30d","return_1d","return_1w","return_1m",
    ]
    for c in num_cols:
        if c in df.columns:
            df[c] = _to_float(df[c])
    for c in ["date", "price_timestamp", "updated_at"]:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce")
    return df


# ── Fundamentals ──────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600)
def load_fundamentals() -> pd.DataFrame:
    """
    Fundamental / valuation data (from Screener export).
    Columns: ticker, as_of_date, market_cap_cr, enterprise_value_cr,
             pe, ev_ebitda, pb, ps, roe, roce, roa,
             debt_equity, current_ratio, interest_coverage,
             revenue_ttm, ebitda_ttm, pat_ttm,
             revenue_growth_1y, revenue_growth_3y,
             ebitda_margin, pat_margin, ebitda_growth_1y, pat_growth_1y,
             promoter_holding, fii_holding, dii_holding, public_holding,
             latest_result_date, result_quarter,
             cash, total_debt, working_capital_days, cfo_ttm
    """
    df = _safe_read(FUNDAMENTALS_CSV)
    if df.empty:
        return pd.DataFrame()
    df["ticker"] = df["ticker"].astype(str).str.strip().str.upper()
    num_cols = [
        "market_cap_cr","enterprise_value_cr","pe","ev_ebitda","pb","ps",
        "roe","roce","roa","debt_equity","current_ratio","interest_coverage",
        "revenue_ttm","ebitda_ttm","pat_ttm","revenue_growth_1y","revenue_growth_3y",
        "ebitda_margin","pat_margin","ebitda_growth_1y","pat_growth_1y",
        "promoter_holding","fii_holding","dii_holding","public_holding",
        "cash","total_debt","working_capital_days","cfo_ttm",
    ]
    for c in num_cols:
        if c in df.columns:
            df[c] = _to_float(df[c])
    return df


# ── Order Book ────────────────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def load_order_book() -> pd.DataFrame:
    """
    Order book intelligence database.
    Each row = one company's order-book data point.
    Source traceability fields are mandatory.
    """
    df = _safe_read(ORDER_BOOK_CSV)
    if df.empty:
        return pd.DataFrame()
    df["ticker"] = df["ticker"].astype(str).str.strip().str.upper()
    num_cols = [
        "market_cap_cr","ev_cr","ttm_revenue_cr","annual_revenue_cr",
        "order_book_cr","order_inflow_cr","order_inflow_growth_pct",
        "ob_revenue_ratio","ob_marketcap_ratio","ob_ev_ratio","btb_ratio",
        "revenue_growth_pct","ebitda_margin_pct","pat_growth_pct",
        "debt_equity","working_capital_days","receivables_growth_pct",
        "execution_cycle_months","confidence_score","ob_score",
        "peer_ev_ebitda","sector_ev_ebitda","cfo_conversion",
    ]
    for c in num_cols:
        if c in df.columns:
            df[c] = _to_float(df[c])
    if "source_date" in df.columns:
        df["source_date"] = pd.to_datetime(df["source_date"], format="mixed", errors="coerce")
    return df


def save_order_book(df: pd.DataFrame) -> None:
    df.to_csv(ORDER_BOOK_CSV, index=False)
    st.cache_data.clear()


# ── Filings ───────────────────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def load_filings() -> pd.DataFrame:
    df = _safe_read(FILINGS_CSV)
    if df.empty:
        return pd.DataFrame()
    df["ticker"] = df["ticker"].astype(str).str.strip().str.upper()
    for c in ["date", "ingested_at"]:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce")
    if "is_material" in df.columns:
        df["is_material"] = df["is_material"].fillna(False).astype(bool)
    for c in ["company_name", "type", "subject", "exchange", "source", "source_url", "ai_summary", "sentiment", "affected_metrics"]:
        if c in df.columns:
            df[c] = df[c].fillna("").astype(str).str.strip()
    return df.sort_values("date", ascending=False) if "date" in df.columns else df


# ── News ──────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def load_news() -> pd.DataFrame:
    df = _safe_read(NEWS_CSV)
    if df.empty:
        return pd.DataFrame()
    for c in ["date", "ingested_at"]:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce")
    if "tickers_mentioned" in df.columns:
        df["tickers_mentioned"] = (
            df["tickers_mentioned"]
            .fillna("")
            .astype(str)
            .str.upper()
            .str.strip()
        )
    if "is_material" in df.columns:
        df["is_material"] = df["is_material"].fillna(False).astype(bool)
    for c in ["headline", "source", "url", "sector", "sentiment", "ai_summary", "categories", "source_type"]:
        if c in df.columns:
            df[c] = df[c].fillna("").astype(str).str.strip()
    return df.sort_values("date", ascending=False) if "date" in df.columns else df


@st.cache_data(ttl=300)
def load_corporate_actions() -> pd.DataFrame:
    df = _safe_read(CORPORATE_ACTIONS_CSV)
    if df.empty:
        return pd.DataFrame()
    if "ticker" in df.columns:
        df["ticker"] = df["ticker"].astype(str).str.strip().str.upper()
    for c in ["announcement_date", "effective_date", "ingested_at"]:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce")
    return df.sort_values("announcement_date", ascending=False) if "announcement_date" in df.columns else df


@st.cache_data(ttl=300)
def load_data_quality_log() -> pd.DataFrame:
    df = _safe_read(DATA_QUALITY_LOG_CSV)
    if df.empty:
        return pd.DataFrame()
    for c in ["last_refresh_at", "logged_at"]:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce")
    return df.sort_values("logged_at", ascending=False) if "logged_at" in df.columns else df


@st.cache_data(ttl=300)
def load_failed_tickers() -> pd.DataFrame:
    df = _safe_read(FAILED_TICKERS_CSV)
    if df.empty:
        return pd.DataFrame()
    if "ticker" in df.columns:
        df["ticker"] = df["ticker"].astype(str).str.strip().str.upper()
    if "failed_at" in df.columns:
        df["failed_at"] = pd.to_datetime(df["failed_at"], errors="coerce")
    return df.sort_values("failed_at", ascending=False) if "failed_at" in df.columns else df


# ── Sectors ───────────────────────────────────────────────────────────────────

@st.cache_data(ttl=86400)
def load_sectors() -> pd.DataFrame:
    df = _safe_read(SECTORS_CSV)
    return df if not df.empty else pd.DataFrame()


# ── Notes ─────────────────────────────────────────────────────────────────────

def load_notes(ticker: Optional[str] = None) -> pd.DataFrame:
    """Load user research notes. Not cached so edits are always fresh."""
    df = _safe_read(NOTES_CSV)
    if df.empty:
        return pd.DataFrame(columns=["ticker","date","content","tags"])
    df["ticker"] = df["ticker"].astype(str).str.strip().str.upper()
    if ticker:
        df = df[df["ticker"] == ticker.upper()]
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df.sort_values("date", ascending=False) if "date" in df.columns else df


def save_note(ticker: str, content: str, tags: str = "") -> None:
    """Append a new note. Creates notes.csv if it doesn't exist."""
    df = _safe_read(NOTES_CSV)
    new_row = pd.DataFrame([{
        "ticker": ticker.upper(),
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "content": content,
        "tags": tags,
    }])
    df = pd.concat([df, new_row], ignore_index=True)
    df.to_csv(NOTES_CSV, index=False)


# ── AI Summaries ──────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600)
def load_ai_summaries() -> dict:
    """Return dict keyed by ticker/key → summary text"""
    df = _safe_read(AI_SUMMARIES_CSV)
    if df.empty or "key" not in df.columns:
        return {}
    return dict(zip(df["key"].astype(str), df.get("summary", pd.Series(dtype=str))))


# ── Merged dataset ────────────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def load_full_universe() -> pd.DataFrame:
    """
    Merge universe + prices + fundamentals into a single wide DataFrame.
    This is the main data source for All Companies and screeners.
    """
    snapshot = load_returns_snapshot()
    uni   = load_universe()
    price = load_prices()
    fund  = load_fundamentals()
    filings = load_filings()

    if not snapshot.empty:
        df = snapshot.copy()
        if not fund.empty:
            fund_latest = fund.sort_values("as_of_date") if "as_of_date" in fund.columns else fund
            if "as_of_date" in fund.columns:
                fund_latest = fund_latest.groupby("ticker", as_index=False).last()
            df = df.merge(fund_latest, on="ticker", how="left", suffixes=("", "_fund"))
            for col in ["company_name", "sector", "industry", "index_membership"]:
                fund_col = f"{col}_fund"
                if fund_col in df.columns:
                    df[col] = df[col].fillna(df[fund_col])
                    df = df.drop(columns=[fund_col])
        if not filings.empty and "ticker" in filings.columns:
            fil = filings.copy()
            if "date" in fil.columns:
                fil["date"] = pd.to_datetime(fil["date"], errors="coerce")
                latest_filing = (
                    fil.sort_values("date")
                    .groupby("ticker", as_index=False)
                    .last()[["ticker", "date", "type", "subject"]]
                    .rename(columns={
                        "date": "latest_filing_date",
                        "type": "latest_filing_type",
                        "subject": "latest_filing_subject",
                    })
                )
                df = df.merge(latest_filing, on="ticker", how="left")
        return df

    if uni.empty:
        return pd.DataFrame()

    df = uni.copy()

    # Merge latest price row per ticker
    if not price.empty:
        if "date" in price.columns:
            latest_price = (
                price.sort_values("date")
                     .groupby("ticker", as_index=False)
                     .last()
            )
        else:
            latest_price = price
        df = df.merge(latest_price, on="ticker", how="left")

    # Merge fundamentals
    if not fund.empty:
        fund_latest = (
            fund.sort_values("as_of_date") if "as_of_date" in fund.columns
            else fund
        )
        if "as_of_date" in fund.columns:
            fund_latest = fund_latest.groupby("ticker", as_index=False).last()
        df = df.merge(fund_latest, on="ticker", how="left")

    return df


# ── Derived views ─────────────────────────────────────────────────────────────

def get_top_movers(n: int = 10, direction: str = "gainers") -> pd.DataFrame:
    """Top N gainers or losers by 1D return."""
    df = load_full_universe()
    if df.empty or "return_1d" not in df.columns:
        return pd.DataFrame()
    df = df.dropna(subset=["return_1d"])
    if direction == "gainers":
        return df.nlargest(n, "return_1d")
    return df.nsmallest(n, "return_1d")


def get_volume_shocks(n: int = 10) -> pd.DataFrame:
    """Top N volume shocks (volume vs 20D avg)."""
    df = load_full_universe()
    if df.empty or "volume" not in df.columns:
        return pd.DataFrame()
    # If we have volume_ratio_20d column, use it; else sort by raw volume
    sort_col = "volume_ratio_20d" if "volume_ratio_20d" in df.columns else "volume"
    return df.dropna(subset=[sort_col]).nlargest(n, sort_col)


def get_52w_extremes() -> dict[str, pd.DataFrame]:
    """Return dicts of stocks near 52W high and 52W low."""
    df = load_full_universe()
    if df.empty:
        return {"near_high": pd.DataFrame(), "near_low": pd.DataFrame()}
    near_high = pd.DataFrame()
    near_low  = pd.DataFrame()
    if "dist_52w_high_pct" in df.columns:
        near_high = df[df["dist_52w_high_pct"].abs() < 5].nsmallest(20, "dist_52w_high_pct")
    if "dist_52w_low_pct" in df.columns:
        near_low = df[df["dist_52w_low_pct"].abs() < 5].nsmallest(20, "dist_52w_low_pct")
    return {"near_high": near_high, "near_low": near_low}


def get_sector_summary() -> pd.DataFrame:
    """Aggregate sector-level performance metrics."""
    df = load_full_universe()
    if df.empty or "sector" not in df.columns:
        return pd.DataFrame()
    agg = {}
    ret_cols = [c for c in ["return_1d","return_1w","return_1m","return_3m","return_6m","return_1y"]
                if c in df.columns]
    for col in ret_cols:
        agg[col] = "mean"
    if "market_cap_cr" in df.columns:
        agg["market_cap_cr"] = "sum"
    agg["ticker"] = "count"
    result = df.groupby("sector").agg(agg).reset_index()
    result.rename(columns={"ticker": "num_stocks"}, inplace=True)
    return result


def get_company_detail(ticker: str) -> dict:
    """Return all available data for a single company as a dict of DataFrames/scalars."""
    ticker = ticker.upper()
    uni   = load_universe()
    price = load_prices()
    fund  = load_fundamentals()
    ob    = load_order_book()
    fil   = load_filings()
    news  = load_news()
    notes = load_notes(ticker)

    company_row = uni[uni["ticker"] == ticker].iloc[0].to_dict() if not uni.empty and len(uni[uni["ticker"] == ticker]) else {}
    price_row   = price[price["ticker"] == ticker].sort_values("date").iloc[-1].to_dict() if not price.empty and "date" in price.columns and len(price[price["ticker"] == ticker]) else {}
    fund_row    = fund[fund["ticker"] == ticker].iloc[-1].to_dict() if not fund.empty and len(fund[fund["ticker"] == ticker]) else {}
    ob_rows     = ob[ob["ticker"] == ticker] if not ob.empty else pd.DataFrame()
    fil_rows    = fil[fil["ticker"] == ticker] if not fil.empty else pd.DataFrame()
    news_rows   = _filter_news_by_ticker(news, ticker)

    return {
        "meta":     company_row,
        "price":    price_row,
        "fund":     fund_row,
        "ob":       ob_rows,
        "filings":  fil_rows,
        "news":     news_rows,
        "notes":    notes,
    }


def _filter_news_by_ticker(news: pd.DataFrame, ticker: str) -> pd.DataFrame:
    if news.empty:
        return pd.DataFrame()
    if "tickers_mentioned" in news.columns:
        return news[news["tickers_mentioned"].astype(str).str.contains(ticker, na=False)]
    return pd.DataFrame()


# ── Screener / order-book flags for New Ideas page ───────────────────────────

def flag_ob_mispricing() -> pd.DataFrame:
    """Return order book companies matching mispricing criteria."""
    ob = load_order_book()
    if ob.empty:
        return pd.DataFrame()
    flags = []

    if "ob_revenue_ratio" in ob.columns:
        f1 = ob[ob["ob_revenue_ratio"] >= 2].copy()
        f1["flag"] = "Order Book > 2x TTM Revenue"
        flags.append(f1)

        f2 = ob[(ob["ob_revenue_ratio"] > 0) &
                (ob.get("ob_marketcap_ratio", pd.Series(dtype=float)) >= 1)].copy() if "ob_marketcap_ratio" in ob.columns else pd.DataFrame()
        if not f2.empty:
            f2["flag"] = "Order Book > Market Cap"
            flags.append(f2)

    if "order_inflow_growth_pct" in ob.columns and "return_1y" in ob.columns:
        f3 = ob[(ob["order_inflow_growth_pct"] >= 20) & (ob["return_1y"] < -0.10)].copy()
        if not f3.empty:
            f3["flag"] = "Strong Order Inflow but Weak Price"
            flags.append(f3)

    if not flags:
        return pd.DataFrame()

    result = pd.concat(flags, ignore_index=True).drop_duplicates(subset=["ticker"])
    return result


# ── Settings helpers ──────────────────────────────────────────────────────────

SETTINGS_FILE = ROOT / ".env"

def load_settings() -> dict:
    """Load settings from .env file"""
    settings = {
        "ANTHROPIC_API_KEY": os.environ.get("ANTHROPIC_API_KEY", ""),
        "EMAIL_FROM": os.environ.get("EMAIL_FROM", ""),
        "EMAIL_TO": os.environ.get("EMAIL_TO", ""),
        "EMAIL_PASSWORD": os.environ.get("EMAIL_PASSWORD", ""),
        "SMTP_HOST": os.environ.get("SMTP_HOST", "smtp.gmail.com"),
        "SMTP_PORT": os.environ.get("SMTP_PORT", "587"),
    }
    # Also read from .env file if exists
    if SETTINGS_FILE.exists():
        with open(SETTINGS_FILE) as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    key, _, val = line.partition("=")
                    settings[key.strip()] = val.strip()
    return settings


def save_settings(settings: dict) -> None:
    lines = [f"{k}={v}" for k, v in settings.items()]
    with open(SETTINGS_FILE, "w") as f:
        f.write("\n".join(lines) + "\n")
    # Also set as env vars
    for k, v in settings.items():
        os.environ[k] = v


# ── Quarterly Financials ──────────────────────────────────────────────────────

QUARTER_ORDER = ["Q1", "Q2", "Q3", "Q4"]


@st.cache_data(ttl=3600)
def load_quarterly() -> pd.DataFrame:
    """
    Quarterly financial data for analysis across multiple fiscal years.

    Columns:
        ticker, fiscal_year, quarter, period_end,
        revenue_cr, ebitda_cr, ebitda_margin_pct,
        pat_cr, pat_margin_pct,
        order_inflow_cr, order_book_cr,
        ebitda_yoy_pct, revenue_yoy_pct, pat_yoy_pct,
        is_reported
    """
    df = _safe_read(QUARTERLY_CSV)
    if df.empty:
        return df

    num_cols = [
        "revenue_cr", "ebitda_cr", "ebitda_margin_pct",
        "pat_cr", "pat_margin_pct",
        "order_inflow_cr", "order_book_cr",
        "ebitda_yoy_pct", "revenue_yoy_pct", "pat_yoy_pct",
    ]
    for c in num_cols:
        if c in df.columns:
            df[c] = _to_float(df[c])

    if "period_end" in df.columns:
        df["period_end"] = pd.to_datetime(df["period_end"], errors="coerce")

    # Standardise FY labels (FY23, FY24, etc.) and quarter codes
    if "fiscal_year" in df.columns:
        df["fiscal_year"] = df["fiscal_year"].astype(str).str.upper().str.strip()
    if "quarter" in df.columns:
        df["quarter"] = df["quarter"].astype(str).str.upper().str.strip()

    # Sort chronologically
    if "period_end" in df.columns:
        df = df.sort_values("period_end")

    return df.reset_index(drop=True)


def get_company_quarterly(ticker: str) -> pd.DataFrame:
    """Return quarterly history for a single ticker, sorted chronologically."""
    q = load_quarterly()
    if q.empty or "ticker" not in q.columns:
        return pd.DataFrame()
    return q[q["ticker"].astype(str).str.upper() == ticker.upper()].reset_index(drop=True)


def pivot_quarterly_metric(qdf: pd.DataFrame, metric: str) -> pd.DataFrame:
    """
    Pivot a quarterly DataFrame so rows = quarters (Q1..Q4),
    columns = fiscal years, values = metric.

    Useful for Q1 FY23 vs Q1 FY24 vs Q1 FY25 side-by-side comparison.
    """
    if qdf.empty or metric not in qdf.columns:
        return pd.DataFrame()

    pv = (
        qdf.pivot_table(
            index="quarter", columns="fiscal_year",
            values=metric, aggfunc="first",
        )
        .reindex(QUARTER_ORDER)
    )
    # Sort columns chronologically
    cols = sorted(pv.columns, key=lambda x: str(x))
    return pv[cols]


def compute_quarterly_yoy(qdf: pd.DataFrame, metric: str) -> pd.DataFrame:
    """
    Add a YoY %% growth column to a pivoted quarterly DataFrame.

    Returns the same DataFrame plus columns named '{prevFY}→{nextFY} %'
    showing each year-over-year change for the same quarter.
    """
    pv = pivot_quarterly_metric(qdf, metric)
    if pv.empty or pv.shape[1] < 2:
        return pv

    out = pv.copy()
    cols = list(pv.columns)
    for prev, nxt in zip(cols[:-1], cols[1:]):
        out[f"{prev}→{nxt} %"] = (pv[nxt] / pv[prev] - 1) * 100
    return out


def quarterly_summary_stats(qdf: pd.DataFrame, metric: str) -> dict:
    """
    Per-quarter summary statistics across the available fiscal years.

    Returns a dict like:
        {"Q1": {"latest": ..., "yoy_pct": ..., "3y_cagr_pct": ..., "trend": "up|flat|down"},
         "Q2": {...}, ...}
    """
    pv = pivot_quarterly_metric(qdf, metric)
    if pv.empty:
        return {}

    result: dict = {}
    cols = list(pv.columns)
    for q in QUARTER_ORDER:
        if q not in pv.index:
            continue
        row = pv.loc[q].dropna()
        if row.empty:
            continue
        latest_fy = row.index[-1]
        latest    = float(row.iloc[-1])
        prev      = float(row.iloc[-2]) if len(row) >= 2 else None
        first     = float(row.iloc[0])
        n_years   = max(1, len(row) - 1)

        yoy = ((latest / prev) - 1) * 100 if prev and prev != 0 else None
        try:
            cagr = ((latest / first) ** (1 / n_years) - 1) * 100 if first else None
        except (ValueError, ZeroDivisionError):
            cagr = None

        # Trend: simple slope sign across all years
        try:
            slope = (row.iloc[-1] - row.iloc[0]) / max(1, len(row) - 1)
            if slope > 0.02 * abs(row.iloc[0]):
                trend = "up"
            elif slope < -0.02 * abs(row.iloc[0]):
                trend = "down"
            else:
                trend = "flat"
        except Exception:
            trend = "flat"

        result[q] = {
            "latest_fy":  latest_fy,
            "latest":     latest,
            "prev":       prev,
            "first":      first,
            "n_years":    n_years,
            "yoy_pct":    yoy,
            "cagr_pct":   cagr,
            "trend":      trend,
            "all_years":  dict(row),
        }
    return result

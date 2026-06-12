"""
validation.py
─────────────
Universe completeness and data quality gates.

EVERY analytic in the app must check `passes()` before computing.
If validation fails, show the warning panel and refuse to display
fake numbers.

The thresholds are deliberately strict: an institutional terminal
that shows partial data is worse than one that admits it has no data.
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from html import escape
from typing import Optional
from pathlib import Path
from zoneinfo import ZoneInfo
import pandas as pd
import streamlit as st


# ── Universe definitions ──────────────────────────────────────────────────────

UNIVERSE_SPECS = {
    "Nifty 50":      {"expected": 50,   "min_valid": 45},
    "Nifty 100":     {"expected": 100,  "min_valid": 90},
    "Nifty 500":     {"expected": 500,  "min_valid": 475},
    "Top 1000":      {"expected": 1000, "min_valid": 950},
}

# Per-analytic minimum thresholds (% of selected universe)
ANALYTIC_GATES = {
    "breadth":          0.90,   # 90% need valid 1D return
    "top_movers":       0.90,
    "volume_shocks":    0.80,
    "52w_extremes":     0.80,
    "sector_heatmap":   0.80,   # 80% need sector + valid return
    "ai_summary":       0.90,
}

# Freshness windows (in hours, for trading-day data)
FRESHNESS = {
    "fresh":   24,
    "delayed": 48,
    "stale":   168,
}


@dataclass
class UniverseReport:
    """Snapshot of the selected universe's data quality."""
    universe:                 str            = "—"
    expected_count:           int            = 0
    min_valid_required:       int            = 0

    actual_loaded:            int            = 0
    valid_price_rows:         int            = 0
    missing_price_rows:       int            = 0
    valid_1d_return_rows:     int            = 0
    valid_volume_rows:        int            = 0
    valid_market_cap_rows:    int            = 0
    valid_sector_rows:        int            = 0

    data_source_prices:       str            = "—"
    data_source_fundamentals: str            = "—"
    data_source_news:         str            = "—"

    last_price_fetch:         Optional[datetime] = None
    last_fundamentals_fetch:  Optional[datetime] = None
    last_news_fetch:          Optional[datetime] = None

    failed_tickers:           list[str]      = field(default_factory=list)

    # Computed during finalisation
    passes:                   bool           = False
    completeness_pct:         float          = 0.0
    fetch_status:             str            = "Failed"   # Fresh | Delayed | Stale | Failed
    failure_reasons:          list[str]      = field(default_factory=list)

    # Per-analytic gates (filled by validate_analytic)
    analytic_status:          dict           = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = asdict(self)
        for k in ("last_price_fetch", "last_fundamentals_fetch", "last_news_fetch"):
            v = d.get(k)
            d[k] = v.isoformat() if isinstance(v, datetime) else None
        return d


# ── Builders ──────────────────────────────────────────────────────────────────

def _classify_freshness(ts: Optional[datetime]) -> str:
    """Map a timestamp to Fresh/Delayed/Stale/Failed."""
    if ts is None:
        return "Failed"
    now = datetime.now(tz=IST)
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=IST)
    else:
        ts = ts.astimezone(IST)
    age = now - ts
    if age <= timedelta(hours=FRESHNESS["fresh"]):
        return "Fresh"
    if age <= timedelta(hours=FRESHNESS["delayed"]):
        return "Delayed"
    if age <= timedelta(hours=FRESHNESS["stale"]):
        return "Stale"
    return "Stale"


def _safe_count_valid(s: pd.Series) -> int:
    if s is None or len(s) == 0:
        return 0
    return int(s.notna().sum())


def build_universe_report(
    universe_label: str,
    universe_df: pd.DataFrame,
    prices_df: Optional[pd.DataFrame] = None,
    fundamentals_df: Optional[pd.DataFrame] = None,
    news_df: Optional[pd.DataFrame] = None,
    failed_tickers: Optional[list[str]] = None,
    source_prices: str = "—",
    source_fundamentals: str = "—",
    source_news: str = "—",
) -> UniverseReport:
    """
    Compute a UniverseReport from the currently-loaded data.

    The caller passes whatever DataFrames it has. Anything missing
    is treated as zero — we never inflate completeness.
    """
    spec = UNIVERSE_SPECS.get(universe_label, {"expected": 0, "min_valid": 0})
    rep = UniverseReport(
        universe=universe_label,
        expected_count=spec["expected"],
        min_valid_required=spec["min_valid"],
    )

    # Universe count
    if universe_df is not None and not universe_df.empty:
        rep.actual_loaded = len(universe_df)
        if "sector" in universe_df.columns:
            rep.valid_sector_rows = _safe_count_valid(universe_df["sector"])

    # Price-derived counts (one row per ticker = latest)
    if prices_df is not None and not prices_df.empty:
        latest = (
            prices_df.sort_values("date").groupby("ticker").tail(1)
            if "date" in prices_df.columns else prices_df
        )
        rep.valid_price_rows      = _safe_count_valid(latest.get("close", pd.Series()))
        rep.missing_price_rows    = max(0, rep.actual_loaded - rep.valid_price_rows)
        rep.valid_1d_return_rows  = _safe_count_valid(latest.get("return_1d", pd.Series()))
        rep.valid_volume_rows     = _safe_count_valid(latest.get("volume", pd.Series()))
        if "date" in prices_df.columns:
            ts = pd.to_datetime(prices_df["date"], errors="coerce").max()
            rep.last_price_fetch  = ts.to_pydatetime() if pd.notna(ts) else None

    if fundamentals_df is not None and not fundamentals_df.empty:
        rep.valid_market_cap_rows = _safe_count_valid(fundamentals_df.get("market_cap_cr", pd.Series()))
        if "as_of_date" in fundamentals_df.columns:
            ts = pd.to_datetime(fundamentals_df["as_of_date"], errors="coerce").max()
            rep.last_fundamentals_fetch = ts.to_pydatetime() if pd.notna(ts) else None

    if news_df is not None and not news_df.empty and "date" in news_df.columns:
        ts = pd.to_datetime(news_df["date"], errors="coerce").max()
        rep.last_news_fetch = ts.to_pydatetime() if pd.notna(ts) else None

    rep.data_source_prices       = source_prices
    rep.data_source_fundamentals = source_fundamentals
    rep.data_source_news         = source_news
    rep.failed_tickers           = list(failed_tickers or [])

    # ── Pass / fail logic ────────────────────────────────────────────────
    reasons: list[str] = []

    if rep.actual_loaded < rep.min_valid_required:
        reasons.append(
            f"Universe size {rep.actual_loaded} below required "
            f"{rep.min_valid_required} for {universe_label}."
        )
    if rep.valid_price_rows < rep.min_valid_required:
        reasons.append(
            f"Only {rep.valid_price_rows} valid latest price rows; "
            f"need at least {rep.min_valid_required}."
        )
    if rep.valid_1d_return_rows < rep.min_valid_required:
        reasons.append(
            f"Only {rep.valid_1d_return_rows} valid 1D return rows; "
            f"need at least {rep.min_valid_required}."
        )
    if rep.valid_sector_rows < rep.min_valid_required:
        reasons.append(
            f"Only {rep.valid_sector_rows} valid sector labels; "
            f"need at least {rep.min_valid_required}."
        )
    if rep.last_price_fetch is None:
        reasons.append("No price-fetch timestamp on record.")

    rep.completeness_pct = (
        100.0 * rep.valid_price_rows / rep.expected_count
        if rep.expected_count > 0 else 0.0
    )
    rep.fetch_status   = _classify_freshness(rep.last_price_fetch)
    rep.failure_reasons = reasons
    rep.passes         = (len(reasons) == 0)

    # Per-analytic gates
    base = max(rep.actual_loaded, 1)
    rep.analytic_status = {
        "breadth":        rep.valid_1d_return_rows / base >= ANALYTIC_GATES["breadth"]
                          and rep.passes,
        "top_movers":     rep.valid_1d_return_rows / base >= ANALYTIC_GATES["top_movers"]
                          and rep.passes,
        "volume_shocks":  rep.valid_volume_rows    / base >= ANALYTIC_GATES["volume_shocks"]
                          and rep.passes,
        "52w_extremes":   rep.valid_price_rows     / base >= ANALYTIC_GATES["52w_extremes"]
                          and rep.passes,
        "sector_heatmap": (rep.valid_sector_rows   / base >= ANALYTIC_GATES["sector_heatmap"]
                          and rep.valid_1d_return_rows / base >= ANALYTIC_GATES["sector_heatmap"]
                          and rep.passes),
        "ai_summary":     rep.valid_1d_return_rows / base >= ANALYTIC_GATES["ai_summary"]
                          and rep.passes,
    }

    return rep


# ── Convenience gates for callers ─────────────────────────────────────────────

def gate(rep: UniverseReport, analytic: str) -> bool:
    """Single source of truth — should this analytic render?"""
    return bool(rep.analytic_status.get(analytic, False))


# ── Display helpers ───────────────────────────────────────────────────────────

_STATUS_COLOR = {
    "Fresh":   ("#16a34a", "#052e16"),
    "Delayed": ("#d97706", "#1c1100"),
    "Stale":   ("#dc2626", "#450a0a"),
    "Failed":  ("#dc2626", "#450a0a"),
}


def render_data_quality_panel(rep: UniverseReport, compact: bool = False) -> None:
    """
    Legacy helper kept only for hidden diagnostics.
    The product surface should expose a single discreet timestamp plus a one-line
    paused banner when the universe is incomplete.
    """
    def _fmt_ts(ts: Optional[datetime], fmt: str) -> str:
        if ts is None:
            return "—"
        return escape(ts.strftime(fmt))

    stamp = (
        f"{rep.universe} · {rep.valid_price_rows}/{rep.expected_count} · "
        f"Updated {_fmt_ts(rep.last_price_fetch, '%d %b %H:%M')} IST"
    )
    fg, _ = _STATUS_COLOR.get(rep.fetch_status, ("#dc2626", "#450a0a"))
    st.caption(stamp)
    if not rep.passes:
        st.warning(
            f"Universe incomplete ({rep.valid_price_rows}/{rep.expected_count}) — analytics paused",
            icon="",
        )


# ── Logging ──────────────────────────────────────────────────────────────────

def append_quality_log(rep: UniverseReport, log_path: Path) -> None:
    """Append a snapshot of the report to data/data_quality_log.csv."""
    row = {
        "ts":                     datetime.now().isoformat(timespec="seconds"),
        "universe":               rep.universe,
        "expected":               rep.expected_count,
        "loaded":                 rep.actual_loaded,
        "valid_prices":           rep.valid_price_rows,
        "valid_returns":          rep.valid_1d_return_rows,
        "valid_volume":           rep.valid_volume_rows,
        "valid_mcap":             rep.valid_market_cap_rows,
        "valid_sectors":          rep.valid_sector_rows,
        "completeness_pct":       round(rep.completeness_pct, 2),
        "fetch_status":           rep.fetch_status,
        "source_prices":          rep.data_source_prices,
        "source_fundamentals":    rep.data_source_fundamentals,
        "source_news":            rep.data_source_news,
        "last_price_fetch":       rep.last_price_fetch.isoformat() if rep.last_price_fetch else "",
        "passes":                 rep.passes,
        "failure_reasons":        " | ".join(rep.failure_reasons),
        "failed_tickers":         ",".join(rep.failed_tickers[:50]),  # cap to avoid bloat
    }
    df = pd.DataFrame([row])
    try:
        if log_path.exists():
            df.to_csv(log_path, mode="a", header=False, index=False)
        else:
            df.to_csv(log_path, index=False)
    except Exception:
        pass  # logging failures must never crash the app
IST = ZoneInfo("Asia/Kolkata")

"""
update_filings.py

Canonical NSE filings refresh for the India Markets Terminal.

Writes a normalized `data/filings.csv` and logs refresh status. If live fetch
fails, the existing file is kept in place and the failure is logged instead of
silently wiping the dataset.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.nse_fetcher import fetch_corporate_announcements
from utils.pipeline import (
    FILINGS_CSV,
    append_failed_tickers,
    atomic_write_csv,
    ensure_data_files,
    log_quality,
    make_run_id,
    now_ist_iso,
    read_csv_safe,
)
from utils.data_loader import load_universe


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


FILINGS_COLUMNS = [
    "ticker",
    "company_name",
    "date",
    "time",
    "type",
    "subject",
    "exchange",
    "source",
    "source_url",
    "ai_summary",
    "sentiment",
    "is_material",
    "materiality_score",
    "affected_metrics",
    "ingested_at",
]

MATERIALITY_BY_TYPE = {
    "Results": 90,
    "Order Win": 80,
    "Credit Rating": 70,
    "Investor Presentation": 65,
    "Annual Report": 60,
    "Fundraise": 60,
    "Management Change": 55,
    "Board Meeting": 40,
    "General": 25,
}


def _materiality_score(event_type: str, sentiment: str) -> int:
    score = MATERIALITY_BY_TYPE.get(str(event_type or "").strip(), 35)
    sentiment = str(sentiment or "").strip().lower()
    if sentiment == "positive":
        score += 5
    elif sentiment == "negative":
        score += 8
    return max(0, min(100, score))


def _normalize_filings(df: pd.DataFrame, universe: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=FILINGS_COLUMNS)

    out = df.copy()
    out["ticker"] = out["ticker"].astype(str).str.strip().str.upper()
    if "company" in out.columns and "company_name" not in out.columns:
        out = out.rename(columns={"company": "company_name"})
    out["company_name"] = out.get("company_name", pd.Series(dtype=str)).astype(str).str.strip()
    if not universe.empty and "ticker" in universe.columns:
        names = universe[["ticker", "company_name"]].drop_duplicates("ticker")
        out = out.drop(columns=["company_name"], errors="ignore").merge(names, on="ticker", how="left")
    out["date"] = pd.to_datetime(out.get("date"), errors="coerce")
    out["time"] = out.get("time", pd.Series(dtype=str)).astype(str).str.strip()
    out["type"] = out.get("type", pd.Series(dtype=str)).astype(str).str.strip()
    out["subject"] = out.get("subject", pd.Series(dtype=str)).astype(str).str.strip()
    out["exchange"] = out.get("exchange", "NSE")
    out["source"] = "NSE Corporate Announcements"
    if "url" in out.columns and "source_url" not in out.columns:
        out = out.rename(columns={"url": "source_url"})
    out["source_url"] = out.get("source_url", pd.Series(dtype=str)).astype(str).str.strip()
    out["ai_summary"] = out.get("ai_summary", "")
    out["sentiment"] = out.get("sentiment", "")
    out["is_material"] = out.get("is_material", False)
    out["materiality_score"] = [
        _materiality_score(t, s) for t, s in zip(out["type"], out["sentiment"])
    ]
    out["affected_metrics"] = out.get("affected_metrics", "")
    out["ingested_at"] = now_ist_iso()
    for col in FILINGS_COLUMNS:
        if col not in out.columns:
            out[col] = pd.NA
    out = out[FILINGS_COLUMNS]
    out = out.dropna(subset=["ticker", "date", "subject"])
    out = out.drop_duplicates(subset=["ticker", "date", "subject"], keep="first")
    return out.sort_values(["date", "time"], ascending=False).reset_index(drop=True)


def run(days: int = 3, category: str = "equities") -> int:
    ensure_data_files()
    run_id = make_run_id("filings")

    logger.info("Fetching NSE corporate announcements (days=%d, category=%s)", days, category)
    live = fetch_corporate_announcements(category=category, n_days=days)
    existing = read_csv_safe(FILINGS_CSV)
    universe = load_universe()

    if live.empty:
        append_failed_tickers([{
            "run_id": run_id,
            "dataset": "filings",
            "ticker": category,
            "stage": "nse_fetch",
            "source": "NSE Corporate Announcements",
            "error_message": "No filings returned from fetch_corporate_announcements",
            "failed_at": now_ist_iso(),
        }])
        log_quality(
            run_id=run_id,
            dataset="filings",
            universe="Nifty500",
            expected_rows=0,
            loaded_rows=len(existing),
            source="NSE Corporate Announcements",
            last_refresh_at=now_ist_iso() if not existing.empty else None,
            details="No live filings fetched; retained existing file.",
            status_override="cached" if not existing.empty else "failed",
        )
        logger.warning("No live filings fetched. Existing file retained.")
        return 0

    norm_live = _normalize_filings(live, universe)
    norm_existing = _normalize_filings(existing, universe) if not existing.empty else pd.DataFrame(columns=FILINGS_COLUMNS)
    combined = pd.concat([norm_live, norm_existing], ignore_index=True)
    combined = combined.drop_duplicates(subset=["ticker", "date", "subject"], keep="first")
    combined = combined.sort_values(["date", "time"], ascending=False).reset_index(drop=True)

    atomic_write_csv(combined, FILINGS_CSV, FILINGS_COLUMNS)
    log_quality(
        run_id=run_id,
        dataset="filings",
        universe="Nifty500",
        expected_rows=0,
        loaded_rows=len(combined),
        source="NSE Corporate Announcements",
        last_refresh_at=now_ist_iso(),
        details=f"Stored filings rows: {len(combined)}",
        status_override="fresh",
    )
    logger.info("Filings update complete: %d rows written to %s", len(combined), FILINGS_CSV)
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Update NSE filings")
    parser.add_argument("--days", type=int, default=3, help="Days back to fetch")
    parser.add_argument("--category", default="equities", help="NSE category filter")
    args = parser.parse_args()
    raise SystemExit(run(days=args.days, category=args.category))

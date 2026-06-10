"""
Build the canonical NIFTY universe file from official NSE constituent lists.

Priority:
1. Official NSE index constituent CSVs
2. Manual CSV import when NSE is blocked

This script writes `data/universe.csv` with source and timestamp metadata.
It does not invent sectors; sectors are derived deterministically from the
industry string when NSE does not provide a direct sector field.
"""

from __future__ import annotations

import argparse
import io
import logging
import sys
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.pipeline import (
    UNIVERSE_CSV,
    UNIVERSE_COLUMNS,
    append_failed_tickers,
    atomic_write_csv,
    classify_sector,
    ensure_data_files,
    log_quality,
    make_run_id,
    now_ist_iso,
    parse_manual_universe_import,
)


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

NSE_URLS = {
    "Nifty50": "https://nsearchives.nseindia.com/content/indices/ind_nifty50list.csv",
    "Nifty100": "https://nsearchives.nseindia.com/content/indices/ind_nifty100list.csv",
    "Nifty500": "https://nsearchives.nseindia.com/content/indices/ind_nifty500list.csv",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
    ),
    "Accept": "text/csv,application/json,*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/",
}

EXPECTED = {
    "Nifty50": 50,
    "Nifty100": 100,
    "Nifty500": 500,
}


def fetch_index_csv(index_name: str, run_id: str) -> pd.DataFrame:
    sess = requests.Session()
    sess.headers.update(HEADERS)
    try:
        sess.get("https://www.nseindia.com", timeout=10)
    except Exception:
        pass

    url = NSE_URLS[index_name]
    try:
        resp = sess.get(url, timeout=25)
        resp.raise_for_status()
        raw = pd.read_csv(io.StringIO(resp.text))
    except Exception as exc:
        append_failed_tickers([{
            "run_id": run_id,
            "dataset": "universe",
            "ticker": index_name,
            "stage": "fetch_index_csv",
            "source": url,
            "error_message": str(exc),
            "failed_at": now_ist_iso(),
        }])
        logger.error("Failed to fetch %s: %s", index_name, exc)
        return pd.DataFrame()

    rename = {
        "Company Name": "company_name",
        "Industry": "industry",
        "Symbol": "ticker",
        "ISIN Code": "isin",
    }
    raw = raw.rename(columns={k: v for k, v in rename.items() if k in raw.columns})
    if "ticker" not in raw.columns:
        raise ValueError(f"{index_name} CSV missing Symbol column")

    out = raw.copy()
    out["ticker"] = out["ticker"].astype(str).str.strip().str.upper()
    out["company_name"] = out.get("company_name", pd.Series(dtype=str)).astype(str).str.strip()
    out["industry"] = out.get("industry", pd.Series(dtype=str)).astype(str).str.strip()
    out["sector"] = out["industry"].map(classify_sector)
    out["index_membership"] = index_name
    out["isin"] = out.get("isin", pd.Series(dtype=str))
    out["bse_code"] = out.get("bse_code", "")
    out["nse_code"] = out.get("nse_code", out["ticker"])
    out["source"] = f"NSE Constituents:{index_name}"
    out["fetched_at"] = now_ist_iso()
    out = out[~out["ticker"].astype(str).str.contains("DUMMY", case=False, na=False)].copy()
    out = out[~out["company_name"].astype(str).str.contains("DUMMY", case=False, na=False)].copy()
    return out[UNIVERSE_COLUMNS].drop_duplicates(subset=["ticker"]).reset_index(drop=True)


def merge_indices(frames: list[pd.DataFrame]) -> pd.DataFrame:
    combined = pd.concat(frames, ignore_index=True)
    combined = combined[~combined["ticker"].astype(str).str.contains("DUMMY", case=False, na=False)].copy()
    merged = (
        combined.groupby("ticker", as_index=False)
        .agg({
            "company_name": "first",
            "sector": "first",
            "industry": "first",
            "index_membership": lambda s: "|".join(sorted(set(s))),
            "isin": "first",
            "bse_code": "first",
            "nse_code": "first",
            "source": lambda s: "|".join(sorted(set(s))),
            "fetched_at": "max",
        })
    )
    return merged[UNIVERSE_COLUMNS].sort_values("ticker").reset_index(drop=True)


def run(indices: list[str], import_csv: str | None = None, import_label: str = "Nifty500") -> None:
    ensure_data_files()
    run_id = make_run_id("universe")

    if import_csv:
        df = parse_manual_universe_import(Path(import_csv), import_label)
        atomic_write_csv(df, UNIVERSE_CSV, UNIVERSE_COLUMNS)
        log_quality(
            run_id=run_id,
            dataset="universe",
            universe=import_label,
            expected_rows=EXPECTED.get(import_label, len(df)),
            loaded_rows=len(df),
            valid_sector_rows=int(df["sector"].astype(str).replace("", pd.NA).notna().sum()),
            source=f"Manual Import:{Path(import_csv).name}",
            last_refresh_at=now_ist_iso(),
            details=f"Manual universe import from {import_csv}",
        )
        logger.info("Universe written from manual import: %s (%d rows)", UNIVERSE_CSV, len(df))
        return

    frames: list[pd.DataFrame] = []
    for index_name in indices:
        if index_name not in NSE_URLS:
            logger.warning("Skipping unsupported index: %s", index_name)
            continue
        df = fetch_index_csv(index_name, run_id)
        if not df.empty:
            logger.info("%s rows fetched for %s", len(df), index_name)
            frames.append(df)

    if not frames:
        logger.error("No universe data fetched. Existing universe retained.")
        log_quality(
            run_id=run_id,
            dataset="universe",
            universe="|".join(indices),
            expected_rows=max(EXPECTED.get(i, 0) for i in indices) if indices else 0,
            loaded_rows=0,
            source="NSE Constituents",
            last_refresh_at=None,
            details="Universe fetch failed for all requested indices. Existing file retained.",
        )
        return

    merged = merge_indices(frames)
    atomic_write_csv(merged, UNIVERSE_CSV, UNIVERSE_COLUMNS)

    expected_rows = max(EXPECTED.get(i, 0) for i in indices) if indices else len(merged)
    valid_sector_rows = int(merged["sector"].astype(str).replace("", pd.NA).notna().sum())
    log_quality(
        run_id=run_id,
        dataset="universe",
        universe="|".join(indices),
        expected_rows=expected_rows,
        loaded_rows=len(merged),
        valid_sector_rows=valid_sector_rows,
        source="NSE Constituents",
        last_refresh_at=now_ist_iso(),
        details=f"Fetched indices: {','.join(indices)}",
    )
    logger.info("Universe written to %s (%d rows)", UNIVERSE_CSV, len(merged))


def parse_indices(value: str) -> list[str]:
    mapping = {
        "50": "Nifty50",
        "100": "Nifty100",
        "500": "Nifty500",
        "nifty50": "Nifty50",
        "nifty100": "Nifty100",
        "nifty500": "Nifty500",
    }
    out: list[str] = []
    for token in value.split(","):
        key = token.strip().lower()
        if not key:
            continue
        mapped = mapping.get(key, token.strip())
        if mapped not in out:
            out.append(mapped)
    return out or ["Nifty500"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Update the equity universe from NSE constituent files.")
    parser.add_argument("--index", default="500", help="Comma-separated set: 50,100,500")
    parser.add_argument("--import-csv", help="Manual import path for universe CSV")
    parser.add_argument("--label", default="Nifty500", help="Label used with --import-csv")
    args = parser.parse_args()

    run(parse_indices(args.index), import_csv=args.import_csv, import_label=args.label)

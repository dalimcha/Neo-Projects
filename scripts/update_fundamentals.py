"""
update_fundamentals.py

Manual fundamentals ingestion for the India Markets Terminal.

Supported sources:
- Screener exports
- Trendlyne exports
- Bloomberg Excel/CSV snapshots

This script normalizes uploaded data into `data/fundamentals.csv`.
It never fabricates missing values.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.pipeline import (
    FUNDAMENTALS_CSV,
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


FUNDAMENTALS_COLUMNS = [
    "ticker", "as_of_date", "market_cap_cr", "enterprise_value_cr",
    "pe", "ev_ebitda", "pb", "ps", "roe", "roce", "roa",
    "industry_pe", "historical_pe_3y", "historical_pe_5y", "historical_pe_10y",
    "avg_roe_3y", "avg_roe_5y",
    "debt_equity", "current_ratio", "interest_coverage",
    "revenue_ttm", "ebitda_ttm", "pat_ttm",
    "revenue_growth_1y", "revenue_growth_3y", "revenue_growth_5y",
    "ebitda_margin", "pat_margin", "ebitda_growth_1y", "pat_growth_1y", "pat_growth_3y", "pat_growth_5y",
    "promoter_holding", "fii_holding", "dii_holding", "public_holding",
    "latest_result_date", "result_quarter",
    "cash", "total_debt", "working_capital_days", "cfo_ttm",
    "source", "ingested_at",
]


SOURCE_COLUMN_MAPS = {
    "screener": {
        "Ticker": "ticker",
        "Symbol": "ticker",
        "NSE Code": "ticker",
        "BSE Code": "bse_code",
        "Name": "company_name",
        "Market Capitalization": "market_cap_cr",
        "Market Cap": "market_cap_cr",
        "Enterprise Value": "enterprise_value_cr",
        "Enterprise Value (Cr)": "enterprise_value_cr",
        "P/E": "pe",
        "PE": "pe",
        "Price to Earning": "pe",
        "Industry PE": "industry_pe",
        "EV/EBITDA": "ev_ebitda",
        "EVEBITDA": "ev_ebitda",
        "P/B": "pb",
        "PB": "pb",
        "Price to book value": "pb",
        "P/S": "ps",
        "PS": "ps",
        "Price to Sales": "ps",
        "Historical PE 3Years": "historical_pe_3y",
        "Historical PE 5Years": "historical_pe_5y",
        "Historical PE 10Years": "historical_pe_10y",
        "ROE %": "roe",
        "ROE": "roe",
        "Return on equity": "roe",
        "Average return on equity 3Years": "avg_roe_3y",
        "Average return on equity 5Years": "avg_roe_5y",
        "ROCE %": "roce",
        "ROCE": "roce",
        "Return on capital employed": "roce",
        "ROA %": "roa",
        "Return on assets": "roa",
        "D/E": "debt_equity",
        "Debt to equity": "debt_equity",
        "Current ratio": "current_ratio",
        "Interest Coverage Ratio": "interest_coverage",
        "Sales": "revenue_ttm",
        "Revenue": "revenue_ttm",
        "EBITDA": "ebitda_ttm",
        "Net Profit": "pat_ttm",
        "Revenue growth": "revenue_growth_1y",
        "Sales growth": "revenue_growth_1y",
        "3Years Sales Growth": "revenue_growth_3y",
        "Sales growth 3Years": "revenue_growth_3y",
        "Sales growth 5Years": "revenue_growth_5y",
        "Operating Profit Margin": "ebitda_margin",
        "EBITDA Margin %": "ebitda_margin",
        "OPM": "ebitda_margin",
        "Profit after tax margin": "pat_margin",
        "PAT Margin %": "pat_margin",
        "EBITDA growth": "ebitda_growth_1y",
        "Profit growth": "pat_growth_1y",
        "PAT Gr %": "pat_growth_1y",
        "Profit growth 3Years": "pat_growth_3y",
        "Profit growth 5Years": "pat_growth_5y",
        "Promoter holding": "promoter_holding",
        "Promoter Holding %": "promoter_holding",
        "FII holding": "fii_holding",
        "FII Holding %": "fii_holding",
        "DII holding": "dii_holding",
        "DII Holding %": "dii_holding",
        "Public holding": "public_holding",
        "Debt": "total_debt",
        "Cash Equivalents": "cash",
        "Borrowings": "total_debt",
        "Working Capital Days": "working_capital_days",
        "Cash from Operations last year": "cfo_ttm",
        "Latest Results": "latest_result_date",
        "Result Quarter": "result_quarter",
    },
    "trendlyne": {
        "NSE Symbol": "ticker",
        "Ticker": "ticker",
        "Mcap": "market_cap_cr",
        "EV": "enterprise_value_cr",
        "PE TTM": "pe",
        "EV/EBITDA TTM": "ev_ebitda",
        "Price to Book Value": "pb",
        "Price to Sales": "ps",
        "ROE TTM": "roe",
        "ROCE TTM": "roce",
        "Debt/Equity": "debt_equity",
        "Sales TTM": "revenue_ttm",
        "EBITDA TTM": "ebitda_ttm",
        "PAT TTM": "pat_ttm",
        "Sales Growth": "revenue_growth_1y",
        "EBITDA Margin": "ebitda_margin",
        "PAT Margin": "pat_margin",
        "Promoter Holding": "promoter_holding",
        "FII Holding": "fii_holding",
        "DII Holding": "dii_holding",
    },
    "bloomberg": {
        "Ticker": "ticker",
        "EQY_FUND_TICKER": "ticker",
        "CUR_MKT_CAP": "market_cap_cr",
        "ENTERPRISE_VALUE": "enterprise_value_cr",
        "PE_RATIO": "pe",
        "EV_TO_EBITDA": "ev_ebitda",
        "PX_TO_BOOK_RATIO": "pb",
        "PX_TO_SALES_RATIO": "ps",
        "RETURN_COM_EQY": "roe",
        "RETURN_ON_INV_CAPITAL": "roce",
        "BS_TOT_ASSET_RETURN": "roa",
        "TOT_DEBT_TO_TOT_EQY": "debt_equity",
        "SALES_REV_TURN": "revenue_ttm",
        "EBITDA": "ebitda_ttm",
        "NET_INCOME": "pat_ttm",
        "SALES_GROWTH": "revenue_growth_1y",
        "EBITDA_MARGIN": "ebitda_margin",
        "NET_MARGIN": "pat_margin",
        "HOLDER_PCT": "promoter_holding",
    },
}


NUMERIC_COLUMNS = [c for c in FUNDAMENTALS_COLUMNS if c not in {
    "ticker", "as_of_date", "latest_result_date", "result_quarter", "source", "ingested_at"
}]


def _read_input(path: Path) -> pd.DataFrame:
    if path.suffix.lower() in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    return pd.read_csv(path)


def _normalize(df: pd.DataFrame, source: str, universe: pd.DataFrame) -> pd.DataFrame:
    col_map = SOURCE_COLUMN_MAPS[source]
    out = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns}).copy()

    if "ticker" not in out.columns:
        raise ValueError("No ticker column found after source-specific column mapping.")

    out["ticker"] = out["ticker"].astype(str).str.strip().str.upper()
    out = out[out["ticker"].isin(set(universe["ticker"].astype(str).str.upper()))].copy()

    if "as_of_date" not in out.columns:
        out["as_of_date"] = str(pd.Timestamp.today().date())
    if "source" not in out.columns:
        out["source"] = source
    out["ingested_at"] = now_ist_iso()

    for col in FUNDAMENTALS_COLUMNS:
        if col not in out.columns:
            out[col] = pd.NA

    for col in NUMERIC_COLUMNS:
        out[col] = pd.to_numeric(out[col], errors="coerce")

    out["latest_result_date"] = pd.to_datetime(out["latest_result_date"], errors="coerce")
    out["as_of_date"] = pd.to_datetime(out["as_of_date"], errors="coerce")

    out = out[FUNDAMENTALS_COLUMNS].copy()
    out = out.dropna(subset=["ticker"])
    out = out.drop_duplicates(subset=["ticker"], keep="last")
    return out.sort_values("ticker").reset_index(drop=True)


def run(import_csv_path: str, source: str, merge: bool = False) -> int:
    ensure_data_files()
    run_id = make_run_id("fundamentals")
    universe = load_universe()

    if universe.empty:
        raise ValueError("Universe is empty. Run update_universe.py before importing fundamentals.")

    path = Path(import_csv_path)
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")

    raw = _read_input(path)
    norm = _normalize(raw, source=source, universe=universe)

    if merge and FUNDAMENTALS_CSV.exists():
        existing = read_csv_safe(FUNDAMENTALS_CSV)
        combined = pd.concat([existing, norm], ignore_index=True)
        combined["as_of_date"] = pd.to_datetime(combined["as_of_date"], errors="coerce")
        combined = combined.sort_values("as_of_date").groupby("ticker", as_index=False).last()
        out = combined[FUNDAMENTALS_COLUMNS]
    else:
        out = norm

    atomic_write_csv(out, FUNDAMENTALS_CSV, FUNDAMENTALS_COLUMNS)
    log_quality(
        run_id=run_id,
        dataset="fundamentals",
        universe="Nifty500",
        expected_rows=len(universe),
        loaded_rows=len(out),
        valid_market_cap_rows=int(out["market_cap_cr"].notna().sum()),
        source=source,
        last_refresh_at=now_ist_iso(),
        details=f"Imported from {path.name}; merge={merge}",
    )
    logger.info("Fundamentals update complete: %d rows written", len(out))
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import manual fundamentals data")
    parser.add_argument("--import-csv", required=True, help="Path to CSV/XLSX export")
    parser.add_argument("--source", required=True, choices=["screener", "trendlyne", "bloomberg"])
    parser.add_argument("--merge", action="store_true", help="Merge with existing fundamentals instead of replacing")
    args = parser.parse_args()
    try:
        raise SystemExit(run(import_csv_path=args.import_csv, source=args.source, merge=args.merge))
    except Exception as exc:
        append_failed_tickers([{
            "run_id": make_run_id("fundamentals"),
            "dataset": "fundamentals",
            "ticker": args.source,
            "stage": "import",
            "source": args.import_csv,
            "error_message": str(exc),
            "failed_at": now_ist_iso(),
        }])
        logger.exception("Fundamentals import failed")
        raise

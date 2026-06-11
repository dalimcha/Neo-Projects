"""
update_quarterly.py

Import quarterly Screener-style exports into data/quarterly_financials.csv.

Expected source shape:
- one row per company
- latest quarter columns
- preceding quarter / preceding year quarter columns
- optional 2 quarters back / 3 quarters back columns

This script does not guess the latest quarter label. Pass it explicitly.
"""

from __future__ import annotations

import argparse
import logging
import sys
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.data_loader import load_universe
from utils.pipeline import (
    append_failed_tickers,
    atomic_write_csv,
    ensure_data_files,
    make_run_id,
    now_ist_iso,
    read_csv_safe,
)


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


ROOT = Path(__file__).parent.parent
QUARTERLY_CSV = ROOT / "data" / "quarterly_financials.csv"

QUARTERLY_COLUMNS = [
    "ticker",
    "fiscal_year",
    "quarter",
    "period_end",
    "revenue_cr",
    "ebitda_cr",
    "ebitda_margin_pct",
    "pat_cr",
    "pat_margin_pct",
    "order_inflow_cr",
    "order_book_cr",
    "ebitda_yoy_pct",
    "revenue_yoy_pct",
    "pat_yoy_pct",
    "is_reported",
]

QUARTER_END = {
    "Q1": "-06-30",
    "Q2": "-09-30",
    "Q3": "-12-31",
    "Q4": "-03-31",
}


@dataclass(frozen=True)
class QuarterRef:
    fiscal_year: str
    quarter: str


def _read_input(path: Path) -> pd.DataFrame:
    if path.suffix.lower() in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    return pd.read_csv(path)


def _clean_ticker(series: pd.Series) -> pd.Series:
    return series.astype(str).str.strip().str.upper()


def _fy_num(fy: str) -> int:
    digits = "".join(ch for ch in str(fy).upper() if ch.isdigit())
    if len(digits) >= 2:
        return int(digits[-2:])
    raise ValueError(f"Could not parse fiscal year: {fy}")


def _fy_label(num: int) -> str:
    return f"FY{num:02d}"


def _previous_quarter(ref: QuarterRef, steps: int = 1) -> QuarterRef:
    order = ["Q1", "Q2", "Q3", "Q4"]
    idx = order.index(ref.quarter)
    fy = _fy_num(ref.fiscal_year)
    for _ in range(steps):
        idx -= 1
        if idx < 0:
            idx = 3
            fy -= 1
    return QuarterRef(_fy_label(fy), order[idx])


def _same_quarter_previous_year(ref: QuarterRef) -> QuarterRef:
    return QuarterRef(_fy_label(_fy_num(ref.fiscal_year) - 1), ref.quarter)


def _period_end(ref: QuarterRef) -> str:
    fy = _fy_num(ref.fiscal_year)
    if ref.quarter == "Q4":
        year = 2000 + fy
    else:
        year = 2000 + fy - 1
    return f"{year}{QUARTER_END[ref.quarter]}"


def _num(row: pd.Series, col: str):
    if col not in row.index:
        return pd.NA
    return pd.to_numeric(pd.Series([row.get(col)]), errors="coerce").iloc[0]


def _margin(num, den):
    if pd.isna(num) or pd.isna(den) or den in (0, 0.0):
        return pd.NA
    return (float(num) / float(den)) * 100.0


def _build_rows(source: pd.DataFrame, latest_quarter: str, latest_fiscal_year: str, valid_tickers: set[str]) -> pd.DataFrame:
    latest_ref = QuarterRef(latest_fiscal_year.upper(), latest_quarter.upper())
    prev_ref = _previous_quarter(latest_ref, 1)
    prev2_ref = _previous_quarter(latest_ref, 2)
    prev3_ref = _previous_quarter(latest_ref, 3)
    yoy_ref = _same_quarter_previous_year(latest_ref)

    out_rows = []

    for _, row in source.iterrows():
        ticker = str(row.get("NSE Code", row.get("Ticker", ""))).strip().upper()
        if not ticker or ticker not in valid_tickers:
            continue

        latest_sales = _num(row, "Sales latest quarter")
        latest_ebitda = _num(row, "EBIDT latest quarter")
        latest_pat = _num(row, "Net Profit latest quarter")

        templates = [
            (
                latest_ref,
                latest_sales,
                latest_ebitda,
                latest_pat,
                _num(row, "YOY Quarterly sales growth"),
                _num(row, "Operating profit growth"),
                _num(row, "YOY Quarterly profit growth"),
            ),
            (
                prev_ref,
                _num(row, "Sales preceding quarter"),
                _num(row, "EBIDT preceding quarter"),
                _num(row, "Net Profit preceding quarter"),
                pd.NA,
                pd.NA,
                pd.NA,
            ),
            (
                prev2_ref,
                _num(row, "Sales 2quarters back"),
                _num(row, "Operating profit 2quarters back"),
                _num(row, "Net profit 2quarters back"),
                pd.NA,
                pd.NA,
                pd.NA,
            ),
            (
                prev3_ref,
                _num(row, "Sales 3quarters back"),
                _num(row, "Operating profit 3quarters back"),
                _num(row, "Net profit 3quarters back"),
                pd.NA,
                pd.NA,
                pd.NA,
            ),
            (
                yoy_ref,
                _num(row, "Sales preceding year quarter"),
                _num(row, "Operating profit preceding year quarter"),
                _num(row, "Profit after tax preceding year quarter"),
                pd.NA,
                pd.NA,
                pd.NA,
            ),
        ]

        for ref, revenue, ebitda, pat, rev_yoy, ebitda_yoy, pat_yoy in templates:
            if pd.isna(revenue) and pd.isna(ebitda) and pd.isna(pat):
                continue
            out_rows.append(
                {
                    "ticker": ticker,
                    "fiscal_year": ref.fiscal_year,
                    "quarter": ref.quarter,
                    "period_end": _period_end(ref),
                    "revenue_cr": revenue,
                    "ebitda_cr": ebitda,
                    "ebitda_margin_pct": _margin(ebitda, revenue),
                    "pat_cr": pat,
                    "pat_margin_pct": _margin(pat, revenue),
                    "order_inflow_cr": pd.NA,
                    "order_book_cr": pd.NA,
                    "ebitda_yoy_pct": ebitda_yoy,
                    "revenue_yoy_pct": rev_yoy,
                    "pat_yoy_pct": pat_yoy,
                    "is_reported": True,
                }
            )

    out = pd.DataFrame(out_rows)
    if out.empty:
        return pd.DataFrame(columns=QUARTERLY_COLUMNS)

    out["period_end"] = pd.to_datetime(out["period_end"], errors="coerce")
    out = out.drop_duplicates(subset=["ticker", "fiscal_year", "quarter"], keep="first")
    out = out.sort_values(["ticker", "period_end"]).reset_index(drop=True)
    for col in QUARTERLY_COLUMNS:
        if col not in out.columns:
            out[col] = pd.NA
    return out[QUARTERLY_COLUMNS]


def run(import_csv_path: str, latest_quarter: str, latest_fiscal_year: str, merge: bool = True) -> int:
    ensure_data_files()
    path = Path(import_csv_path)
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")

    universe = load_universe()
    if universe.empty:
        raise ValueError("Universe is empty. Run update_universe.py before importing quarterly data.")

    raw = _read_input(path)
    valid_tickers = set(_clean_ticker(universe["ticker"]))
    norm = _build_rows(raw, latest_quarter=latest_quarter, latest_fiscal_year=latest_fiscal_year, valid_tickers=valid_tickers)

    if merge and QUARTERLY_CSV.exists():
        existing = read_csv_safe(QUARTERLY_CSV)
        out = pd.concat([existing, norm], ignore_index=True)
        out["period_end"] = pd.to_datetime(out["period_end"], errors="coerce")
        out = out.sort_values("period_end").drop_duplicates(subset=["ticker", "fiscal_year", "quarter"], keep="last")
    else:
        out = norm

    atomic_write_csv(out, QUARTERLY_CSV, QUARTERLY_COLUMNS)
    logger.info("Quarterly update complete: %d rows written", len(out))
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import quarterly Screener export")
    parser.add_argument("--import-csv", required=True, help="Path to quarterly CSV/XLSX export")
    parser.add_argument("--latest-quarter", required=True, choices=["Q1", "Q2", "Q3", "Q4"])
    parser.add_argument("--latest-fiscal-year", required=True, help="e.g. FY26")
    parser.add_argument("--no-merge", action="store_true", help="Replace instead of merge")
    args = parser.parse_args()
    try:
        raise SystemExit(
            run(
                import_csv_path=args.import_csv,
                latest_quarter=args.latest_quarter,
                latest_fiscal_year=args.latest_fiscal_year,
                merge=not args.no_merge,
            )
        )
    except Exception as exc:
        append_failed_tickers(
            [
                {
                    "run_id": make_run_id("quarterly"),
                    "dataset": "quarterly",
                    "ticker": "BULK_IMPORT",
                    "stage": "import",
                    "source": args.import_csv,
                    "error_message": str(exc),
                    "failed_at": now_ist_iso(),
                }
            ]
        )
        logger.exception("Quarterly import failed")
        raise

"""
update_universe.py
──────────────────
Fetch official NSE index constituent CSVs and write them to data/universe.csv.

NSE publishes the official index files at:
    https://nsearchives.nseindia.com/content/indices/ind_nifty50list.csv
    https://nsearchives.nseindia.com/content/indices/ind_nifty100list.csv
    https://nsearchives.nseindia.com/content/indices/ind_nifty500list.csv

These are the canonical lists used by the validation layer.

Run:
    python scripts/update_universe.py                 # default: Nifty 500
    python scripts/update_universe.py --index 100
    python scripts/update_universe.py --index 50,100,500

The script merges all requested indices into one universe.csv with an
`index_membership` column like "Nifty50|Nifty100|Nifty500".
"""

from __future__ import annotations
import sys, argparse, logging, io
from pathlib import Path

import requests
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"
UNIVERSE_CSV = DATA / "universe.csv"

NSE_URLS = {
    "Nifty50":     "https://nsearchives.nseindia.com/content/indices/ind_nifty50list.csv",
    "NiftyNext50": "https://nsearchives.nseindia.com/content/indices/ind_niftynext50list.csv",
    "Nifty100":    "https://nsearchives.nseindia.com/content/indices/ind_nifty100list.csv",
    "Nifty500":    "https://nsearchives.nseindia.com/content/indices/ind_nifty500list.csv",
}

HEADERS = {
    "User-Agent":
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/121.0 Safari/537.36",
    "Accept": "text/csv,application/json,*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/",
}


def _fetch_index(index_name: str) -> pd.DataFrame:
    url = NSE_URLS[index_name]
    logger.info("Fetching %s from %s", index_name, url)

    # NSE blocks bare requests; establish session via homepage first
    sess = requests.Session()
    sess.headers.update(HEADERS)
    try:
        sess.get("https://www.nseindia.com/", timeout=10)
    except Exception:
        pass

    try:
        r = sess.get(url, timeout=20)
        r.raise_for_status()
    except Exception as e:
        logger.error("Fetch failed for %s: %s", index_name, e)
        return pd.DataFrame()

    try:
        df = pd.read_csv(io.StringIO(r.text))
    except Exception as e:
        logger.error("CSV parse failed for %s: %s", index_name, e)
        return pd.DataFrame()

    # Standardise column names — NSE CSVs use varying header capitalisation
    rename = {
        "Company Name": "company_name",
        "Industry":     "industry",
        "Symbol":       "ticker",
        "Series":       "series",
        "ISIN Code":    "isin",
    }
    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})

    if "ticker" not in df.columns:
        logger.error("%s CSV is missing Symbol column", index_name)
        return pd.DataFrame()

    df["ticker"] = df["ticker"].astype(str).str.strip().str.upper()
    df["index_membership"] = index_name
    return df[["ticker", "company_name", "industry", "isin", "index_membership"]]


def run(indices: list[str]) -> None:
    logger.info("=== Universe Update Started ===")
    DATA.mkdir(exist_ok=True)

    frames = []
    for idx in indices:
        if idx not in NSE_URLS:
            logger.warning("Unknown index %s — skipping", idx)
            continue
        f = _fetch_index(idx)
        if not f.empty:
            frames.append(f)

    if not frames:
        logger.error("No constituents fetched. Universe NOT updated.")
        logger.error("If you are on a network that blocks NSE, "
                     "download the CSV manually from "
                     "https://www.nseindia.com/products-services/indices-nifty500-index "
                     "and run --import-csv path/to/file.csv")
        return

    combined = pd.concat(frames, ignore_index=True)

    # Merge index_membership for stocks in multiple indices (Nifty 50 ⊂ 100 ⊂ 500)
    merged = (
        combined
        .groupby(["ticker"], as_index=False)
        .agg({
            "company_name": "first",
            "industry":     "first",
            "isin":         "first",
            "index_membership": lambda s: "|".join(sorted(set(s))),
        })
    )

    # Add empty sector column if not present — sectors live in sectors.csv
    if "sector" not in merged.columns:
        merged["sector"] = ""
    if "bse_code" not in merged.columns:
        merged["bse_code"] = ""
    if "nse_code" not in merged.columns:
        merged["nse_code"] = merged["ticker"]

    # Order columns
    cols = ["ticker", "company_name", "sector", "industry",
            "index_membership", "isin", "bse_code", "nse_code"]
    merged = merged[[c for c in cols if c in merged.columns]]

    # Backup existing universe before overwriting
    if UNIVERSE_CSV.exists():
        backup = UNIVERSE_CSV.with_suffix(".csv.bak")
        UNIVERSE_CSV.replace(backup)
        logger.info("Backed up existing universe to %s", backup)

    merged.to_csv(UNIVERSE_CSV, index=False)
    logger.info("Wrote %d unique tickers across %d indices to %s",
                len(merged), len(indices), UNIVERSE_CSV)

    # Quick health check
    for idx in indices:
        n = merged["index_membership"].str.contains(idx, na=False).sum()
        logger.info("  %s: %d tickers", idx, n)


def import_csv(path: str, index_label: str) -> None:
    """Load a manually downloaded NSE CSV (when network blocks NSE)."""
    logger.info("Importing %s as %s", path, index_label)
    df = pd.read_csv(path)
    rename = {
        "Company Name": "company_name", "Industry": "industry",
        "Symbol": "ticker", "ISIN Code": "isin",
    }
    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})
    df["ticker"] = df["ticker"].astype(str).str.strip().str.upper()
    df["index_membership"] = index_label
    df["sector"] = df.get("sector", "")
    df["bse_code"] = df.get("bse_code", "")
    df["nse_code"] = df["ticker"]
    out_cols = ["ticker","company_name","sector","industry",
                "index_membership","isin","bse_code","nse_code"]
    df = df[[c for c in out_cols if c in df.columns]]
    df.to_csv(UNIVERSE_CSV, index=False)
    logger.info("Wrote %d tickers to %s", len(df), UNIVERSE_CSV)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Update universe from NSE")
    parser.add_argument(
        "--index", default="500",
        help="Comma-separated subset of 50/100/Next50/500 (default: 500)",
    )
    parser.add_argument(
        "--import-csv",
        help="Bypass network — import a manually downloaded NSE CSV",
    )
    parser.add_argument(
        "--label", default="Nifty500",
        help="When using --import-csv, the index label to record",
    )
    args = parser.parse_args()

    if args.import_csv:
        import_csv(args.import_csv, args.label)
    else:
        wanted = []
        for token in args.index.split(","):
            t = token.strip()
            if t == "50":   wanted.append("Nifty50")
            elif t == "100": wanted.append("Nifty100")
            elif t.lower() == "next50": wanted.append("NiftyNext50")
            elif t == "500": wanted.append("Nifty500")
            elif t in NSE_URLS: wanted.append(t)
        if not wanted:
            wanted = ["Nifty500"]
        run(wanted)

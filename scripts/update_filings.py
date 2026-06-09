"""
update_filings.py
─────────────────
Fetches NSE corporate announcements for the last N days,
classifies them, and appends new rows to data/filings.csv.

Run daily (or multiple times per day):
    python scripts/update_filings.py

Options:
    --days N        How many days back to fetch (default: 3)
    --category CAT  NSE category filter (default: all)
"""

import sys, argparse, logging
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.nse_fetcher import fetch_corporate_announcements
from utils.data_loader import load_filings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR  = Path(__file__).parent.parent / "data"
FILINGS_CSV = DATA_DIR / "filings.csv"


def run(days=3, category=""):
    logger.info("=== Filings Update Started (days=%d) ===", days)

    logger.info("Fetching NSE corporate announcements…")
    new_df = fetch_corporate_announcements(category=category, n_days=days)

    if new_df.empty:
        logger.warning("No announcements fetched. NSE session may have expired.")
        return

    logger.info("Fetched %d announcements", len(new_df))

    # Load existing
    existing = load_filings()
    if existing.empty:
        combined = new_df
    else:
        # Deduplicate on ticker + date + subject
        dedup_cols = [c for c in ["ticker", "date", "subject"] if c in new_df.columns and c in existing.columns]
        combined = pd.concat([new_df, existing], ignore_index=True)
        if dedup_cols:
            combined = combined.drop_duplicates(subset=dedup_cols, keep="first")

    combined = combined.sort_values("date", ascending=False) if "date" in combined.columns else combined

    combined.to_csv(FILINGS_CSV, index=False)
    new_count = len(combined) - (len(existing) if not existing.empty else 0)
    logger.info("Saved %d total rows (%d new) to %s", len(combined), max(new_count, 0), FILINGS_CSV)
    logger.info("=== Filings Update Complete ===")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Update NSE filings")
    parser.add_argument("--days", type=int, default=3, help="Days back to fetch")
    parser.add_argument("--category", default="", help="NSE category filter")
    args = parser.parse_args()
    run(days=args.days, category=args.category)

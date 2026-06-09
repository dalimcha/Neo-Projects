"""
update_prices.py
────────────────
Fetches NSE bhavcopy for the latest trading day, computes
multi-period returns, and writes to data/prices.csv.

Run daily after market close (or schedule via cron):
    python scripts/update_prices.py

Options:
    --date YYYY-MM-DD   Fetch specific date (default: today)
    --yf                Use yfinance instead of bhavcopy (slower, more history)
"""

import sys, os, argparse, logging
from pathlib import Path
from datetime import date, datetime, timedelta

import pandas as pd

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.nse_fetcher import fetch_bhavcopy, fetch_bulk_prices, calculate_returns_from_bhavcopy
from utils.data_loader import load_universe

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"
PRICES_CSV = DATA_DIR / "prices.csv"


def run(target_date=None, use_yf=False):
    logger.info("=== Price Update Started ===")

    # Load universe
    uni = load_universe()
    if uni.empty:
        logger.error("Universe is empty — add companies to data/universe.csv")
        return

    tickers = uni["ticker"].tolist()
    logger.info("Universe: %d tickers", len(tickers))

    if use_yf:
        logger.info("Fetching prices via yfinance (this may take a few minutes)…")
        _update_via_yfinance(tickers)
    else:
        logger.info("Fetching NSE bhavcopy…")
        _update_via_bhavcopy(target_date, tickers)

    logger.info("=== Price Update Complete ===")


def _update_via_bhavcopy(target_date, tickers):
    bhav = fetch_bhavcopy(target_date)
    if bhav.empty:
        logger.warning("Bhavcopy fetch failed — trying yfinance fallback")
        _update_via_yfinance(tickers)
        return

    # Map bhavcopy to our schema
    bhav = bhav.rename(columns={
        "SYMBOL": "ticker", "CLOSE": "close", "OPEN": "open",
        "HIGH": "high", "LOW": "low", "PREVCLOSE": "prev_close",
        "TOTTRDQTY": "volume", "TIMESTAMP": "date",
        "_bhavcopy_date": "date",
    })

    if "_bhavcopy_date" in bhav.columns:
        bhav["date"] = pd.to_datetime(bhav["_bhavcopy_date"])

    bhav["ticker"] = bhav["ticker"].astype(str).str.strip().str.upper()
    bhav["return_1d"] = (bhav["close"] - bhav["prev_close"]) / bhav["prev_close"]

    # Filter to our universe
    bhav = bhav[bhav["ticker"].isin(tickers)]
    logger.info("Matched %d tickers from bhavcopy", len(bhav))

    # Load existing prices for multi-period return calculation
    existing = pd.read_csv(PRICES_CSV) if PRICES_CSV.exists() else pd.DataFrame()
    if not existing.empty:
        existing["date"] = pd.to_datetime(existing["date"], errors="coerce")

    # Calculate multi-period returns
    if not existing.empty and "date" in existing.columns:
        today = bhav["date"].max() if "date" in bhav.columns else pd.Timestamp.today()
        for period_days, col_name in [
            (7, "return_1w"), (30, "return_1m"), (90, "return_3m"),
            (180, "return_6m"), (365, "return_1y"),
        ]:
            cutoff = today - pd.Timedelta(days=period_days)
            hist = existing[existing["date"] >= cutoff]
            if hist.empty:
                continue
            oldest_close = (
                hist.sort_values("date")
                    .groupby("ticker")["close"]
                    .first()
                    .reset_index()
                    .rename(columns={"close": f"close_{period_days}d"})
            )
            bhav = bhav.merge(oldest_close, on="ticker", how="left")
            if f"close_{period_days}d" in bhav.columns:
                bhav[col_name] = (bhav["close"] - bhav[f"close_{period_days}d"]) / bhav[f"close_{period_days}d"]
                bhav.drop(columns=[f"close_{period_days}d"], inplace=True)

        # 52W high/low
        cutoff_1y = today - pd.Timedelta(days=365)
        hist_1y = existing[existing["date"] >= cutoff_1y]
        if not hist_1y.empty:
            hi_lo = hist_1y.groupby("ticker")["close"].agg(
                high_52w="max", low_52w="min"
            ).reset_index()
            bhav = bhav.merge(hi_lo, on="ticker", how="left")
            bhav["high_52w"] = bhav[["high_52w","close"]].max(axis=1)
            bhav["low_52w"]  = bhav[["low_52w","close"]].min(axis=1)
            bhav["dist_52w_high_pct"] = (bhav["close"] / bhav["high_52w"] - 1) * 100
            bhav["dist_52w_low_pct"]  = (bhav["close"] / bhav["low_52w"]  - 1) * 100
    else:
        bhav["high_52w"]          = bhav["high"]
        bhav["low_52w"]           = bhav["low"]
        bhav["dist_52w_high_pct"] = 0
        bhav["dist_52w_low_pct"]  = 0

    # Append to history
    if not existing.empty:
        # Remove same-date rows to avoid duplicates
        if "date" in existing.columns:
            today_str = bhav["date"].max().strftime("%Y-%m-%d") if "date" in bhav.columns else ""
            existing = existing[existing["date"].astype(str).str[:10] != today_str]
        combined = pd.concat([existing, bhav], ignore_index=True)
    else:
        combined = bhav

    combined.to_csv(PRICES_CSV, index=False)
    logger.info("Prices written to %s (%d rows total)", PRICES_CSV, len(combined))


def _update_via_yfinance(tickers, period="1y"):
    """Fetch full history via yfinance and compute all returns."""
    from utils.nse_fetcher import fetch_bulk_prices
    logger.info("Fetching %d tickers via yfinance (period=%s)…", len(tickers), period)

    # Process in batches of 50
    batch_size = 50
    all_dfs = []
    for i in range(0, len(tickers), batch_size):
        batch = tickers[i:i+batch_size]
        logger.info("Batch %d/%d", i//batch_size + 1, (len(tickers)-1)//batch_size + 1)
        df = fetch_bulk_prices(batch, period=period)
        if not df.empty:
            all_dfs.append(df)

    if not all_dfs:
        logger.error("No price data retrieved via yfinance")
        return

    history = pd.concat(all_dfs, ignore_index=True)
    history["date"] = pd.to_datetime(history["date"])
    history = history.sort_values(["ticker", "date"])

    # Compute returns from history
    today = history["date"].max()
    latest = history.groupby("ticker").last().reset_index()

    for period_days, col_name in [
        (1, "return_1d"), (7, "return_1w"), (30, "return_1m"),
        (90, "return_3m"), (180, "return_6m"), (365, "return_1y"),
    ]:
        cutoff = today - pd.Timedelta(days=period_days)
        old = (
            history[history["date"] <= cutoff]
            .sort_values("date")
            .groupby("ticker")["close"]
            .last()
            .reset_index()
            .rename(columns={"close": f"close_old"})
        )
        if not old.empty:
            latest = latest.merge(old, on="ticker", how="left")
            latest[col_name] = (latest["close"] - latest["close_old"]) / latest["close_old"]
            latest.drop(columns=["close_old"], inplace=True)

    # 52W H/L
    hist_1y = history[history["date"] >= today - pd.Timedelta(days=365)]
    if not hist_1y.empty:
        hi_lo = hist_1y.groupby("ticker")["close"].agg(high_52w="max", low_52w="min").reset_index()
        latest = latest.merge(hi_lo, on="ticker", how="left")
        latest["dist_52w_high_pct"] = (latest["close"] / latest["high_52w"] - 1) * 100
        latest["dist_52w_low_pct"]  = (latest["close"] / latest["low_52w"]  - 1) * 100

    latest.to_csv(PRICES_CSV, index=False)
    logger.info("yfinance prices written to %s (%d rows)", PRICES_CSV, len(latest))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Update price data")
    parser.add_argument("--date", help="Target date YYYY-MM-DD")
    parser.add_argument("--yf", action="store_true", help="Use yfinance (full history)")
    args = parser.parse_args()

    target = None
    if args.date:
        target = datetime.strptime(args.date, "%Y-%m-%d").date()

    run(target_date=target, use_yf=args.yf)

"""
Phase 1 market data engine.

Outputs:
- data/prices.csv
- data/returns_snapshot.csv
- data/sector_performance.csv
- data/volume_shocks.csv
- data/data_quality_log.csv
- data/failed_tickers.csv
- data/corporate_actions.csv (schema only if missing)

Design rules:
- Prefer NSE bhavcopy for latest daily fields where available.
- Use yfinance as fallback and for longer-period return history.
- Never overwrite a healthy prior dataset with an incomplete failed refresh.
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.nse_fetcher import fetch_bhavcopy
from utils.pipeline import (
    FUNDAMENTALS_CSV,
    PRICES_CSV,
    RETURNS_SNAPSHOT_CSV,
    SECTOR_PERFORMANCE_CSV,
    VOLUME_SHOCKS_CSV,
    UNIVERSE_CSV,
    PRICES_COLUMNS,
    RETURNS_SNAPSHOT_COLUMNS,
    SECTOR_PERFORMANCE_COLUMNS,
    VOLUME_SHOCKS_COLUMNS,
    append_failed_tickers,
    atomic_write_csv,
    coerce_numeric,
    ensure_data_files,
    latest_trading_date_from_prices,
    log_quality,
    make_run_id,
    now_ist_iso,
    read_csv_safe,
    safe_pct_change,
    safe_ratio,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

MIN_VALID_ROWS = 475
BATCH_SIZE = 80


def load_universe() -> pd.DataFrame:
    df = read_csv_safe(UNIVERSE_CSV)
    if df.empty:
        raise RuntimeError("Universe is empty. Run scripts/update_universe.py first.")
    df["ticker"] = df["ticker"].astype(str).str.strip().str.upper()
    return df.drop_duplicates(subset=["ticker"]).reset_index(drop=True)


def load_fundamentals() -> pd.DataFrame:
    df = read_csv_safe(FUNDAMENTALS_CSV)
    if df.empty:
        return df
    df["ticker"] = df["ticker"].astype(str).str.strip().str.upper()
    num_cols = ["market_cap_cr"]
    return coerce_numeric(df, num_cols)


def fetch_yfinance_history(tickers: list[str], run_id: str, period: str = "10y") -> tuple[pd.DataFrame, list[dict]]:
    try:
        import yfinance as yf
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Missing dependency: yfinance. Install project dependencies first with "
            "`python3 -m pip install -r requirements.txt` from the india_terminal folder."
        ) from exc

    failures: list[dict] = []
    frames: list[pd.DataFrame] = []

    for start in range(0, len(tickers), BATCH_SIZE):
        batch = tickers[start:start + BATCH_SIZE]
        yf_tickers = [f"{t}.NS" for t in batch]
        logger.info("Fetching yfinance batch %d-%d of %d", start + 1, min(start + BATCH_SIZE, len(tickers)), len(tickers))
        try:
            raw = yf.download(
                yf_tickers,
                period=period,
                interval="1d",
                progress=False,
                auto_adjust=False,
                group_by="ticker",
                threads=True,
            )
        except Exception as exc:
            for ticker in batch:
                failures.append({
                    "run_id": run_id,
                    "dataset": "prices",
                    "ticker": ticker,
                    "stage": "yfinance_download_batch",
                    "source": "yfinance",
                    "error_message": str(exc),
                    "failed_at": now_ist_iso(),
                })
            continue

        for ticker in batch:
            sym = f"{ticker}.NS"
            try:
                if len(batch) == 1 and ("Close" in raw.columns or "Adj Close" in raw.columns):
                    item = raw.copy()
                else:
                    if sym not in raw.columns.get_level_values(0):
                        raise KeyError(f"No data for {ticker}")
                    item = raw[sym].copy()
                item = item.reset_index()
                item.columns = [str(c).lower().replace(" ", "_") for c in item.columns]
                item["ticker"] = ticker
                item = item.rename(columns={"adj_close": "adj_close"})
                frames.append(item)
            except Exception as exc:
                failures.append({
                    "run_id": run_id,
                    "dataset": "prices",
                    "ticker": ticker,
                    "stage": "yfinance_symbol_parse",
                    "source": "yfinance",
                    "error_message": str(exc),
                    "failed_at": now_ist_iso(),
                })

    if not frames:
        return pd.DataFrame(), failures

    hist = pd.concat(frames, ignore_index=True)
    hist["date"] = pd.to_datetime(hist["date"], errors="coerce")
    hist = hist.dropna(subset=["date"]).sort_values(["ticker", "date"]).reset_index(drop=True)
    for col in ["open", "high", "low", "close", "adj_close", "volume"]:
        if col in hist.columns:
            hist[col] = pd.to_numeric(hist[col], errors="coerce")
    return hist, failures


def build_snapshot_from_history(history: pd.DataFrame) -> pd.DataFrame:
    if history.empty:
        return pd.DataFrame(columns=PRICES_COLUMNS)

    latest_rows = []
    for ticker, g in history.groupby("ticker"):
        g = g.sort_values("date").reset_index(drop=True)
        last = g.iloc[-1]
        close_series = g["close"]
        volume_series = g["volume"] if "volume" in g.columns else pd.Series(dtype=float)

        def past_close(days: int):
            cutoff = g["date"].max() - pd.Timedelta(days=days)
            prior = g[g["date"] <= cutoff]
            return prior.iloc[-1]["close"] if not prior.empty else pd.NA

        prev_close = g.iloc[-2]["close"] if len(g) >= 2 else pd.NA
        row = {
            "ticker": ticker,
            "date": last["date"],
            "open": last.get("open", pd.NA),
            "high": last.get("high", pd.NA),
            "low": last.get("low", pd.NA),
            "close": last.get("close", pd.NA),
            "adj_close": last.get("adj_close", last.get("close", pd.NA)),
            "prev_close": prev_close,
            "volume": last.get("volume", pd.NA),
            "avg_volume_30d": volume_series.tail(30).mean() if not volume_series.empty else pd.NA,
            "return_1d": safe_pct_change(last.get("close", pd.NA), prev_close),
            "return_1w": safe_pct_change(last.get("close", pd.NA), past_close(7)),
            "return_1m": safe_pct_change(last.get("close", pd.NA), past_close(30)),
            "return_3m": safe_pct_change(last.get("close", pd.NA), past_close(90)),
            "return_6m": safe_pct_change(last.get("close", pd.NA), past_close(180)),
            "return_1y": safe_pct_change(last.get("close", pd.NA), past_close(365)),
            "return_3y": safe_pct_change(last.get("close", pd.NA), past_close(365 * 3)),
            "return_5y": safe_pct_change(last.get("close", pd.NA), past_close(365 * 5)),
            "return_10y": safe_pct_change(last.get("close", pd.NA), past_close(365 * 10)),
            "high_52w": close_series.tail(252).max(),
            "low_52w": close_series.tail(252).min(),
            "source": "yfinance",
            "price_timestamp": now_ist_iso(),
            "updated_at": now_ist_iso(),
        }
        row["volume_ratio_30d"] = safe_ratio(row["volume"], row["avg_volume_30d"])
        row["dist_52w_high_pct"] = safe_pct_change(row["close"], row["high_52w"])
        row["dist_52w_low_pct"] = safe_pct_change(row["close"], row["low_52w"])
        if pd.notna(row["dist_52w_high_pct"]):
            row["dist_52w_high_pct"] = float(row["dist_52w_high_pct"]) * 100
        if pd.notna(row["dist_52w_low_pct"]):
            row["dist_52w_low_pct"] = float(row["dist_52w_low_pct"]) * 100
        latest_rows.append(row)

    snapshot = pd.DataFrame(latest_rows)
    return snapshot


def overlay_bhavcopy(snapshot: pd.DataFrame, target_date: date | None) -> pd.DataFrame:
    if snapshot.empty:
        return snapshot

    bhav = fetch_bhavcopy(target_date)
    if bhav.empty:
        logger.warning("NSE bhavcopy unavailable. Keeping yfinance-derived latest fields.")
        return snapshot

    bhav = bhav.rename(columns={
        "SYMBOL": "ticker",
        "OPEN": "open",
        "HIGH": "high",
        "LOW": "low",
        "CLOSE": "close",
        "PREVCLOSE": "prev_close",
        "TOTTRDQTY": "volume",
    })
    bhav["ticker"] = bhav["ticker"].astype(str).str.strip().str.upper()
    if "_bhavcopy_date" in bhav.columns:
        bhav["date"] = pd.to_datetime(bhav["_bhavcopy_date"], errors="coerce")

    fields = ["date", "open", "high", "low", "close", "prev_close", "volume"]
    overlay = bhav[["ticker"] + [f for f in fields if f in bhav.columns]].copy()

    out = snapshot.set_index("ticker")
    ov = overlay.set_index("ticker")
    matched = out.index.intersection(ov.index)
    for field in fields:
        if field in ov.columns and field in out.columns:
            out.loc[matched, field] = ov.loc[matched, field]

    out.loc[matched, "return_1d"] = (pd.to_numeric(out.loc[matched, "close"], errors="coerce") /
                                     pd.to_numeric(out.loc[matched, "prev_close"], errors="coerce")) - 1
    out.loc[matched, "source"] = "NSE Bhavcopy"
    out.loc[matched, "price_timestamp"] = now_ist_iso()
    return out.reset_index()


def build_returns_snapshot(universe: pd.DataFrame, prices: pd.DataFrame, fundamentals: pd.DataFrame) -> pd.DataFrame:
    merged = universe.merge(prices, on="ticker", how="left")
    if not fundamentals.empty:
        if "as_of_date" in fundamentals.columns:
            fundamentals["as_of_date"] = pd.to_datetime(fundamentals["as_of_date"], errors="coerce")
            fundamentals_latest = fundamentals.sort_values("as_of_date").groupby("ticker", as_index=False).last()
        else:
            fundamentals_latest = fundamentals.copy()
        keep = [c for c in ["ticker", "market_cap_cr", "as_of_date", "source"] if c in fundamentals_latest.columns]
        fundamentals_latest = fundamentals_latest[keep].rename(columns={
            "source": "fundamentals_source",
            "as_of_date": "fundamentals_as_of",
        })
        merged = merged.merge(fundamentals_latest, on="ticker", how="left")

    merged["price"] = merged.get("close")
    if "source_y" in merged.columns:
        merged["price_source"] = merged["source_y"]
    elif "source" in merged.columns:
        merged["price_source"] = merged["source"]
    else:
        merged["price_source"] = pd.NA
    merged["updated_at"] = now_ist_iso()

    for col in RETURNS_SNAPSHOT_COLUMNS:
        if col not in merged.columns:
            merged[col] = pd.NA
    return merged[RETURNS_SNAPSHOT_COLUMNS].sort_values(["sector", "ticker"]).reset_index(drop=True)


def build_sector_performance(snapshot: pd.DataFrame) -> pd.DataFrame:
    if snapshot.empty:
        return pd.DataFrame(columns=SECTOR_PERFORMANCE_COLUMNS)

    df = snapshot.copy()
    df["sector"] = df["sector"].fillna("").astype(str).str.strip()
    df = coerce_numeric(df, ["return_1d", "return_1w", "return_1m", "market_cap_cr"])
    rows = []
    for sector, g in df[df["sector"] != ""].groupby("sector"):
        ret = g["return_1d"]
        valid = ret.dropna()
        adv = int((valid > 0).sum())
        dec = int((valid < 0).sum())
        unc = int((valid == 0).sum())
        base = len(valid)
        rows.append({
            "sector": sector,
            "stock_count": int(len(g)),
            "valid_return_count": base,
            "advancers": adv,
            "decliners": dec,
            "unchanged": unc,
            "positive_pct": round((adv / base) * 100, 2) if base else pd.NA,
            "negative_pct": round((dec / base) * 100, 2) if base else pd.NA,
            "avg_return_1d": valid.mean() if base else pd.NA,
            "median_return_1d": valid.median() if base else pd.NA,
            "avg_return_1w": pd.to_numeric(g["return_1w"], errors="coerce").mean() if "return_1w" in g.columns else pd.NA,
            "avg_return_1m": pd.to_numeric(g["return_1m"], errors="coerce").mean() if "return_1m" in g.columns else pd.NA,
            "market_cap_sum_cr": pd.to_numeric(g["market_cap_cr"], errors="coerce").sum(min_count=1),
            "price_source": ",".join(sorted(set(g["price_source"].dropna().astype(str))))[:200],
            "price_timestamp": g["price_timestamp"].dropna().astype(str).max() if "price_timestamp" in g.columns else pd.NA,
            "updated_at": now_ist_iso(),
        })
    out = pd.DataFrame(rows)
    if out.empty:
        return pd.DataFrame(columns=SECTOR_PERFORMANCE_COLUMNS)
    for col in SECTOR_PERFORMANCE_COLUMNS:
        if col not in out.columns:
            out[col] = pd.NA
    return out[SECTOR_PERFORMANCE_COLUMNS].sort_values("avg_return_1d", ascending=False, na_position="last")


def build_volume_shocks(snapshot: pd.DataFrame, threshold: float = 2.0) -> pd.DataFrame:
    if snapshot.empty:
        return pd.DataFrame(columns=VOLUME_SHOCKS_COLUMNS)
    df = snapshot.copy()
    df = coerce_numeric(df, ["volume_ratio_30d"])
    df = df[df["volume_ratio_30d"] >= threshold].copy()
    if df.empty:
        return pd.DataFrame(columns=VOLUME_SHOCKS_COLUMNS)
    for col in VOLUME_SHOCKS_COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA
    return df[VOLUME_SHOCKS_COLUMNS].sort_values("volume_ratio_30d", ascending=False, na_position="last")


def validate_snapshot(universe: pd.DataFrame, prices: pd.DataFrame, snapshot: pd.DataFrame) -> tuple[bool, dict]:
    loaded_rows = len(universe)
    valid_price_rows = int(snapshot["price"].notna().sum()) if "price" in snapshot.columns else 0
    valid_1d_rows = int(snapshot["return_1d"].notna().sum()) if "return_1d" in snapshot.columns else 0
    valid_sector_rows = int(universe["sector"].astype(str).replace("", pd.NA).notna().sum()) if "sector" in universe.columns else 0
    details = {
        "loaded_rows": loaded_rows,
        "valid_price_rows": valid_price_rows,
        "valid_1d_rows": valid_1d_rows,
        "valid_sector_rows": valid_sector_rows,
        "latest_price_date": latest_trading_date_from_prices(prices),
    }
    passed = (
        loaded_rows >= MIN_VALID_ROWS and
        valid_price_rows >= MIN_VALID_ROWS and
        valid_1d_rows >= MIN_VALID_ROWS and
        valid_sector_rows >= MIN_VALID_ROWS
    )
    return passed, details


def run(target_date: date | None = None) -> int:
    ensure_data_files()
    run_id = make_run_id("prices")
    universe = load_universe()
    fundamentals = load_fundamentals()

    try:
        history, failures = fetch_yfinance_history(universe["ticker"].tolist(), run_id)
    except RuntimeError as exc:
        logger.error(str(exc))
        log_quality(
            run_id=run_id,
            dataset="prices",
            universe="Nifty500",
            expected_rows=500,
            loaded_rows=0,
            source="yfinance/NSE Bhavcopy",
            last_refresh_at=None,
            details=str(exc),
        )
        return 1
    if failures:
        append_failed_tickers(failures)
    if history.empty:
        logger.error("Price history fetch failed for all tickers. Existing data retained.")
        log_quality(
            run_id=run_id,
            dataset="prices",
            universe="Nifty500",
            expected_rows=500,
            loaded_rows=0,
            source="yfinance/NSE Bhavcopy",
            last_refresh_at=None,
            details="No price history returned.",
        )
        return 1

    prices = build_snapshot_from_history(history)
    prices = overlay_bhavcopy(prices, target_date)
    snapshot = build_returns_snapshot(universe, prices, fundamentals)
    sector_perf = build_sector_performance(snapshot)
    volume_shocks = build_volume_shocks(snapshot)

    passed, details = validate_snapshot(universe, prices, snapshot)
    valid_market_cap_rows = int(snapshot["market_cap_cr"].notna().sum()) if "market_cap_cr" in snapshot.columns else 0

    log_quality(
        run_id=run_id,
        dataset="prices",
        universe="Nifty500",
        expected_rows=500,
        loaded_rows=details["loaded_rows"],
        valid_price_rows=details["valid_price_rows"],
        valid_1d_rows=details["valid_1d_rows"],
        valid_sector_rows=details["valid_sector_rows"],
        valid_market_cap_rows=valid_market_cap_rows,
        source="NSE Bhavcopy + yfinance fallback",
        last_refresh_at=now_ist_iso(),
        details=str(details),
    )

    if not passed:
        logger.error("Validation failed. Existing price outputs retained. Details: %s", details)
        return 2

    atomic_write_csv(prices, PRICES_CSV, PRICES_COLUMNS)
    atomic_write_csv(snapshot, RETURNS_SNAPSHOT_CSV, RETURNS_SNAPSHOT_COLUMNS)
    atomic_write_csv(sector_perf, SECTOR_PERFORMANCE_CSV, SECTOR_PERFORMANCE_COLUMNS)
    atomic_write_csv(volume_shocks, VOLUME_SHOCKS_CSV, VOLUME_SHOCKS_COLUMNS)
    logger.info(
        "Wrote prices=%d snapshot=%d sectors=%d volume_shocks=%d",
        len(prices), len(snapshot), len(sector_perf), len(volume_shocks)
    )
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Update market prices and derived Phase 1 datasets.")
    parser.add_argument("--date", help="Optional target date in YYYY-MM-DD")
    args = parser.parse_args()

    target = None
    if args.date:
        target = datetime.strptime(args.date, "%Y-%m-%d").date()

    raise SystemExit(run(target_date=target))

"""
nse_fetcher.py
──────────────
Fetch live market data from NSE.
Primary:  NSE bhavcopy CSV (free, no auth)
Fallback: yfinance (.NS tickers)

Usage:
    from utils.nse_fetcher import fetch_bhavcopy, fetch_index_snapshot
"""

from __future__ import annotations
import io, zipfile, time, logging
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd
import requests

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"

# ── NSE request headers ───────────────────────────────────────────────────────
_NSE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/",
    "Origin":  "https://www.nseindia.com",
}

_SESSION: Optional[requests.Session] = None


def _get_session() -> requests.Session:
    """Build a requests Session with NSE cookies."""
    global _SESSION
    if _SESSION is None:
        _SESSION = requests.Session()
        _SESSION.headers.update(_NSE_HEADERS)
        try:
            _SESSION.get("https://www.nseindia.com", timeout=10)
            time.sleep(0.5)
        except Exception:
            pass
    return _SESSION


# ── Bhavcopy ──────────────────────────────────────────────────────────────────

def fetch_bhavcopy(for_date: Optional[date] = None) -> pd.DataFrame:
    """
    Download and parse the NSE CM bhavcopy for the given date.
    Returns DataFrame with columns:
        SYMBOL, SERIES, OPEN, HIGH, LOW, CLOSE, PREVCLOSE,
        TOTTRDQTY (volume), TOTTRDVAL, TIMESTAMP
    Falls back to D-1 if today's file isn't yet published.
    """
    if for_date is None:
        for_date = date.today()

    # Try up to 3 past trading days
    for delta in range(5):
        d = for_date - timedelta(days=delta)
        if d.weekday() >= 5:   # skip weekends
            continue
        df = _try_bhavcopy(d)
        if df is not None:
            df["_bhavcopy_date"] = d
            logger.info("Bhavcopy loaded for %s (%d rows)", d, len(df))
            return df

    logger.warning("Could not fetch bhavcopy; returning empty DataFrame")
    return pd.DataFrame()


def _try_bhavcopy(d: date) -> Optional[pd.DataFrame]:
    month_abbr = d.strftime("%b").upper()
    fname = f"cm{d.strftime('%d')}{month_abbr}{d.strftime('%Y')}bhav.csv.zip"
    url = (
        f"https://nsearchives.nseindia.com/content/historical/EQUITIES/"
        f"{d.strftime('%Y')}/{month_abbr}/{fname}"
    )
    try:
        sess = _get_session()
        resp = sess.get(url, timeout=20, stream=True)
        if resp.status_code != 200:
            return None
        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
            csv_name = zf.namelist()[0]
            with zf.open(csv_name) as f:
                df = pd.read_csv(f)
        df.columns = df.columns.str.strip()
        # Keep equity series only
        if "SERIES" in df.columns:
            df = df[df["SERIES"] == "EQ"]
        num_cols = ["OPEN","HIGH","LOW","CLOSE","PREVCLOSE","TOTTRDQTY","TOTTRDVAL"]
        for c in num_cols:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce")
        return df
    except Exception as e:
        logger.debug("Bhavcopy fetch failed for %s: %s", d, e)
        return None


# ── Index snapshot ────────────────────────────────────────────────────────────

def fetch_index_snapshot() -> dict:
    """
    Try to fetch live index data from NSE API.
    Falls back to yfinance on failure.
    Returns dict with keys: nifty50, niftyNext50, nifty500, sensex, bankNifty, vix
    Each value: {name, value, change, change_pct}
    """
    snapshot = _try_nse_indices()
    if snapshot:
        return snapshot
    return _yf_index_fallback()


def _try_nse_indices() -> dict:
    url = "https://www.nseindia.com/api/allIndices"
    try:
        sess = _get_session()
        resp = sess.get(url, timeout=10)
        if resp.status_code != 200:
            return {}
        data = resp.json()
        indices = {item["indexSymbol"]: item for item in data.get("data", [])}
        out = {}
        mapping = {
            "nifty50":    "NIFTY 50",
            "niftyNext50":"NIFTY NEXT 50",
            "nifty500":   "NIFTY 500",
            "bankNifty":  "NIFTY BANK",
            "vix":        "INDIA VIX",
        }
        for key, sym in mapping.items():
            if sym in indices:
                item = indices[sym]
                out[key] = {
                    "name":       sym,
                    "value":      float(item.get("last", 0)),
                    "change":     float(item.get("change", 0)),
                    "change_pct": float(item.get("percentChange", 0)),
                }
        return out
    except Exception:
        return {}


def _yf_index_fallback() -> dict:
    try:
        import yfinance as yf
        tickers = {
            "nifty50":     "^NSEI",
            "niftyNext50": "^NIFTYNXT50",
            "nifty500":    "^CRSLDX",
            "bankNifty":   "^NSEBANK",
            "sensex":      "^BSESN",
            "vix":         "^INDIAVIX",
        }
        out = {}
        data = yf.download(
            list(tickers.values()), period="2d", interval="1d",
            progress=False, group_by="ticker"
        )
        for key, sym in tickers.items():
            try:
                closes = data[sym]["Close"].dropna() if sym in data else pd.Series()
                if len(closes) >= 2:
                    prev, last = closes.iloc[-2], closes.iloc[-1]
                    chg = last - prev
                    pct = (chg / prev) * 100
                elif len(closes) == 1:
                    last, chg, pct = closes.iloc[-1], 0, 0
                else:
                    continue
                out[key] = {
                    "name": sym, "value": round(float(last), 2),
                    "change": round(float(chg), 2), "change_pct": round(float(pct), 2)
                }
            except Exception:
                continue
        return out
    except ImportError:
        return {}


# ── Corporate announcements ───────────────────────────────────────────────────

def fetch_corporate_announcements(
    category: str = "equities", n_days: int = 3
) -> pd.DataFrame:
    """
    Fetch NSE corporate announcements for last n_days.
    Returns DataFrame with: symbol, company, date, subject, desc, type, url
    """
    url = "https://www.nseindia.com/api/corporate-announcements"
    params = {"index": category}
    try:
        sess = _get_session()
        resp = sess.get(url, params=params, timeout=15)
        if resp.status_code != 200:
            return pd.DataFrame()
        data = resp.json()
        rows = []
        cutoff = datetime.now() - timedelta(days=n_days)
        for item in data:
            try:
                dt = pd.to_datetime(item.get("exchdisstime",""), errors="coerce")
                if pd.isnull(dt) or dt < cutoff:
                    continue
                rows.append({
                    "ticker":  item.get("symbol","").strip().upper(),
                    "company": item.get("sm_name",""),
                    "date":    dt.date(),
                    "time":    dt.strftime("%H:%M"),
                    "subject": item.get("subject",""),
                    "type":    _classify_announcement(item.get("subject","")),
                    "url":     f"https://nsearchives.nseindia.com/{item.get('attachmentName','')}",
                })
            except Exception:
                continue
        if not rows:
            return pd.DataFrame()
        return pd.DataFrame(rows).sort_values("date", ascending=False)
    except Exception as e:
        logger.debug("Corporate announcements fetch failed: %s", e)
        return pd.DataFrame()


def _classify_announcement(subject: str) -> str:
    s = subject.lower()
    if any(x in s for x in ["order", "contract", "bagged", "secured", "award"]):
        return "Order Win"
    if any(x in s for x in ["result", "financial", "quarter", "q1","q2","q3","q4"]):
        return "Results"
    if any(x in s for x in ["dividend", "dividend"]):
        return "Dividend"
    if any(x in s for x in ["board meeting", "board meet"]):
        return "Board Meeting"
    if any(x in s for x in ["agm", "annual general"]):
        return "AGM"
    if any(x in s for x in ["credit rating", "rating"]):
        return "Credit Rating"
    if any(x in s for x in ["investor presentation", "concall", "conf call"]):
        return "Investor Presentation"
    if any(x in s for x in ["pledge", "encumber"]):
        return "Promoter Pledge"
    if any(x in s for x in ["appointment", "resignation", "md", "ceo"]):
        return "Management Change"
    if any(x in s for x in ["fund", "qip", "rights issue", "ncd", "bond"]):
        return "Fundraise"
    return "General"


# ── Price history via yfinance ────────────────────────────────────────────────

def fetch_price_history(ticker: str, period: str = "1y") -> pd.DataFrame:
    """
    Fetch OHLCV price history for a single NSE ticker via yfinance.
    ticker: NSE symbol without .NS suffix (e.g. "RELIANCE")
    period: "1mo", "3mo", "6mo", "1y", "2y", "5y"
    """
    try:
        import yfinance as yf
        sym = ticker.upper().rstrip(".NS") + ".NS"
        df = yf.Ticker(sym).history(period=period)
        if df.empty:
            return pd.DataFrame()
        df.index.name = "date"
        df = df.reset_index()
        df.columns = [c.lower() for c in df.columns]
        return df
    except Exception as e:
        logger.debug("yfinance fetch failed for %s: %s", ticker, e)
        return pd.DataFrame()


def fetch_bulk_prices(tickers: list[str], period: str = "1y") -> pd.DataFrame:
    """
    Download price data for multiple tickers via yfinance.
    Returns a DataFrame with columns: ticker, date, close, volume, return_1d, ...
    """
    try:
        import yfinance as yf
        syms = [t.upper().rstrip(".NS") + ".NS" for t in tickers]
        raw = yf.download(syms, period=period, interval="1d",
                          progress=False, group_by="ticker", auto_adjust=True)
        rows = []
        for ticker, sym in zip(tickers, syms):
            try:
                closes = raw[sym]["Close"].dropna() if len(syms) > 1 else raw["Close"].dropna()
                volumes = raw[sym]["Volume"].dropna() if len(syms) > 1 else raw["Volume"].dropna()
                if closes.empty:
                    continue
                df = pd.DataFrame({"close": closes, "volume": volumes})
                df["ticker"] = ticker.upper()
                df.index.name = "date"
                df = df.reset_index()
                rows.append(df)
            except Exception:
                continue
        if not rows:
            return pd.DataFrame()
        combined = pd.concat(rows, ignore_index=True)
        combined = combined.sort_values(["ticker","date"])
        combined["return_1d"] = combined.groupby("ticker")["close"].pct_change()
        return combined
    except Exception as e:
        logger.debug("Bulk price fetch failed: %s", e)
        return pd.DataFrame()


# ── Returns calculator ────────────────────────────────────────────────────────

def calculate_returns_from_bhavcopy(
    bhavcopy_today: pd.DataFrame,
    price_history: pd.DataFrame,
) -> pd.DataFrame:
    """
    Given today's bhavcopy and historical price data (from prices.csv or yfinance),
    compute multi-period returns and 52W high/low for each stock.
    """
    if bhavcopy_today.empty:
        return pd.DataFrame()

    df = bhavcopy_today[["SYMBOL","CLOSE","PREVCLOSE","HIGH","LOW","TOTTRDQTY"]].copy()
    df.columns = ["ticker","close","prev_close","day_high","day_low","volume"]
    df["return_1d"] = (df["close"] - df["prev_close"]) / df["prev_close"]

    if price_history.empty:
        return df

    # Compute 52W high/low from history
    if "date" in price_history.columns and "close" in price_history.columns:
        cutoff = pd.Timestamp.today() - pd.Timedelta(days=365)
        hist_yr = price_history[price_history["date"] >= cutoff]
        hi_lo = hist_yr.groupby("ticker")["close"].agg(
            high_52w="max", low_52w="min"
        ).reset_index()
        df = df.merge(hi_lo, on="ticker", how="left")
        df["dist_52w_high_pct"] = (df["close"] / df["high_52w"] - 1) * 100
        df["dist_52w_low_pct"]  = (df["close"] / df["low_52w"]  - 1) * 100

    return df

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime, date
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

import pandas as pd


logger = logging.getLogger(__name__)

IST = ZoneInfo("Asia/Kolkata")
ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"

UNIVERSE_CSV = DATA_DIR / "universe.csv"
PRICES_CSV = DATA_DIR / "prices.csv"
RETURNS_SNAPSHOT_CSV = DATA_DIR / "returns_snapshot.csv"
SECTOR_PERFORMANCE_CSV = DATA_DIR / "sector_performance.csv"
VOLUME_SHOCKS_CSV = DATA_DIR / "volume_shocks.csv"
FUNDAMENTALS_CSV = DATA_DIR / "fundamentals.csv"
FILINGS_CSV = DATA_DIR / "filings.csv"
NEWS_CSV = DATA_DIR / "news.csv"
CORPORATE_ACTIONS_CSV = DATA_DIR / "corporate_actions.csv"
DATA_QUALITY_LOG_CSV = DATA_DIR / "data_quality_log.csv"
FAILED_TICKERS_CSV = DATA_DIR / "failed_tickers.csv"


UNIVERSE_COLUMNS = [
    "ticker", "company_name", "sector", "industry",
    "index_membership", "isin", "bse_code", "nse_code",
    "source", "fetched_at",
]

PRICES_COLUMNS = [
    "ticker", "date", "open", "high", "low", "close", "adj_close",
    "prev_close", "volume", "avg_volume_30d", "volume_ratio_30d",
    "return_1d", "return_1w", "return_1m", "return_3m", "return_6m", "return_1y",
    "return_3y", "return_5y", "return_10y",
    "high_52w", "low_52w", "dist_52w_high_pct", "dist_52w_low_pct",
    "source", "price_timestamp", "updated_at",
]

RETURNS_SNAPSHOT_COLUMNS = [
    "ticker", "company_name", "sector", "industry", "index_membership",
    "price", "prev_close", "volume", "avg_volume_30d", "volume_ratio_30d",
    "return_1d", "return_1w", "return_1m", "return_3m", "return_6m", "return_1y",
    "return_3y", "return_5y", "return_10y",
    "quartile_1m", "quartile_3m", "quartile_6m", "quartile_1y", "quartile_3y", "quartile_5y", "quartile_10y",
    "high_52w", "low_52w", "dist_52w_high_pct", "dist_52w_low_pct",
    "market_cap_cr", "date", "price_source", "price_timestamp",
    "fundamentals_source", "fundamentals_as_of", "updated_at",
]

SECTOR_PERFORMANCE_COLUMNS = [
    "sector", "stock_count", "valid_return_count", "advancers", "decliners", "unchanged",
    "positive_pct", "negative_pct", "avg_return_1d", "median_return_1d",
    "avg_return_1w", "avg_return_1m", "market_cap_sum_cr",
    "price_source", "price_timestamp", "updated_at",
]

VOLUME_SHOCKS_COLUMNS = [
    "ticker", "company_name", "sector", "industry",
    "price", "volume", "avg_volume_30d", "volume_ratio_30d",
    "return_1d", "return_1w", "return_1m",
    "date", "price_source", "price_timestamp", "updated_at",
]

CORPORATE_ACTIONS_COLUMNS = [
    "ticker", "company_name", "action_type", "headline", "description",
    "announcement_date", "effective_date", "source", "source_url", "ingested_at",
]

FILINGS_COLUMNS = [
    "ticker", "company_name", "date", "time", "type", "subject",
    "exchange", "source", "source_url", "ai_summary", "sentiment",
    "is_material", "materiality_score", "affected_metrics", "ingested_at",
]

NEWS_COLUMNS = [
    "headline", "source", "date", "url", "tickers_mentioned", "sector",
    "sentiment", "ai_summary", "is_material", "materiality_score", "categories", "ingested_at",
    "source_type",
]

FAILED_TICKERS_COLUMNS = [
    "run_id", "dataset", "ticker", "stage", "source", "error_message", "failed_at",
]

DATA_QUALITY_LOG_COLUMNS = [
    "run_id", "dataset", "universe", "expected_rows", "loaded_rows",
    "valid_price_rows", "valid_1d_rows", "valid_sector_rows", "valid_market_cap_rows",
    "completeness_pct", "status", "source", "last_refresh_at", "details", "logged_at",
]


SECTOR_RULES = [
    ("Financial Services", ["bank", "financial", "nbfc", "insurance", "financing", "asset management", "capital market"]),
    ("IT Services", ["software", "it", "technology", "computers", "digital", "infotech"]),
    ("Pharma", ["pharma", "pharmaceutical", "drug", "healthcare", "biotech", "formulation"]),
    ("Autos", ["auto", "automobile", "vehicle", "tyres", "tractor", "two wheelers"]),
    ("Metals", ["steel", "aluminium", "metal", "mining", "copper", "zinc", "ore"]),
    ("Oil & Gas", ["oil", "gas", "petroleum", "refineries", "lubricant", "exploration"]),
    ("Power & Utilities", ["power", "electric", "utility", "generation", "distribution", "transmission"]),
    ("Telecom", ["telecom", "communication", "wireless"]),
    ("Consumer", ["fmcg", "consumer", "retail", "apparel", "footwear", "food", "beverages", "personal care"]),
    ("Cement", ["cement"]),
    ("Chemicals", ["chemicals", "fertiliser", "agro chemicals", "speciality chemicals", "pigments"]),
    ("Real Estate", ["real estate", "realty", "property", "housing"]),
    ("Capital Goods", ["industrial manufacturing", "capital goods", "engineering", "electrical equipment", "machinery", "infrastructure", "construction", "epc", "defence", "shipbuilding", "railway", "ems"]),
    ("Logistics", ["logistics", "shipping", "ports", "cargo", "transport", "warehousing"]),
    ("Hospitals", ["hospital", "diagnostic", "clinic"]),
    ("Media", ["media", "entertainment", "broadcast"]),
]


@dataclass
class QualitySnapshot:
    run_id: str
    dataset: str
    universe: str
    expected_rows: int
    loaded_rows: int
    valid_price_rows: int
    valid_1d_rows: int
    valid_sector_rows: int
    valid_market_cap_rows: int
    completeness_pct: float
    status: str
    source: str
    last_refresh_at: Optional[str]
    details: str


def now_ist() -> datetime:
    return datetime.now(tz=IST)


def now_ist_iso() -> str:
    return now_ist().isoformat()


def make_run_id(prefix: str) -> str:
    return f"{prefix}_{now_ist().strftime('%Y%m%d_%H%M%S')}"


def read_csv_safe(path: Path, **kwargs) -> pd.DataFrame:
    try:
        if path.exists() and path.stat().st_size > 0:
            return pd.read_csv(path, **kwargs)
    except Exception as exc:
        logger.warning("Failed to read %s: %s", path, exc)
    return pd.DataFrame()


def atomic_write_csv(df: pd.DataFrame, path: Path, columns: Optional[list[str]] = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    out = df.copy()
    if columns:
        for col in columns:
            if col not in out.columns:
                out[col] = pd.NA
        out = out[columns]
    tmp = path.with_suffix(path.suffix + ".tmp")
    out.to_csv(tmp, index=False)
    tmp.replace(path)


def ensure_data_files() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    templates = {
        RETURNS_SNAPSHOT_CSV: RETURNS_SNAPSHOT_COLUMNS,
        SECTOR_PERFORMANCE_CSV: SECTOR_PERFORMANCE_COLUMNS,
        VOLUME_SHOCKS_CSV: VOLUME_SHOCKS_COLUMNS,
        FILINGS_CSV: FILINGS_COLUMNS,
        NEWS_CSV: NEWS_COLUMNS,
        CORPORATE_ACTIONS_CSV: CORPORATE_ACTIONS_COLUMNS,
        FAILED_TICKERS_CSV: FAILED_TICKERS_COLUMNS,
        DATA_QUALITY_LOG_CSV: DATA_QUALITY_LOG_COLUMNS,
    }
    for path, cols in templates.items():
        if not path.exists():
            atomic_write_csv(pd.DataFrame(columns=cols), path, cols)


def append_failed_tickers(rows: list[dict]) -> None:
    if not rows:
        return
    existing = read_csv_safe(FAILED_TICKERS_CSV)
    df = pd.concat([existing, pd.DataFrame(rows)], ignore_index=True)
    atomic_write_csv(df, FAILED_TICKERS_CSV, FAILED_TICKERS_COLUMNS)


def append_quality_log(snapshot: QualitySnapshot) -> None:
    existing = read_csv_safe(DATA_QUALITY_LOG_CSV)
    df = pd.concat([existing, pd.DataFrame([asdict(snapshot)])], ignore_index=True)
    df["logged_at"] = df.get("logged_at", pd.Series(dtype=str))
    if "logged_at" in df.columns:
        df.loc[df["logged_at"].isna(), "logged_at"] = now_ist_iso()
    atomic_write_csv(df, DATA_QUALITY_LOG_CSV, DATA_QUALITY_LOG_COLUMNS)


def log_quality(
    *,
    run_id: str,
    dataset: str,
    universe: str,
    expected_rows: int,
    loaded_rows: int,
    valid_price_rows: int = 0,
    valid_1d_rows: int = 0,
    valid_sector_rows: int = 0,
    valid_market_cap_rows: int = 0,
    source: str = "",
    last_refresh_at: Optional[str] = None,
    details: str = "",
) -> QualitySnapshot:
    completeness_pct = round((loaded_rows / expected_rows) * 100, 2) if expected_rows else 0.0
    status = "fresh" if loaded_rows >= expected_rows * 0.95 else "failed"
    snap = QualitySnapshot(
        run_id=run_id,
        dataset=dataset,
        universe=universe,
        expected_rows=expected_rows,
        loaded_rows=loaded_rows,
        valid_price_rows=valid_price_rows,
        valid_1d_rows=valid_1d_rows,
        valid_sector_rows=valid_sector_rows,
        valid_market_cap_rows=valid_market_cap_rows,
        completeness_pct=completeness_pct,
        status=status,
        source=source,
        last_refresh_at=last_refresh_at,
        details=details,
    )
    append_quality_log(snap)
    return snap


def classify_sector(industry: object) -> str:
    text = str(industry or "").strip().lower()
    if not text or text == "nan":
        return ""
    for sector, needles in SECTOR_RULES:
        if any(n in text for n in needles):
            return sector
    return "Other"


def safe_pct_change(current: object, prior: object) -> object:
    try:
        current = float(current)
        prior = float(prior)
    except Exception:
        return pd.NA
    if pd.isna(current) or pd.isna(prior) or prior == 0:
        return pd.NA
    return (current / prior) - 1.0


def safe_ratio(num: object, den: object) -> object:
    try:
        num = float(num)
        den = float(den)
    except Exception:
        return pd.NA
    if pd.isna(num) or pd.isna(den) or den == 0:
        return pd.NA
    return num / den


def latest_trading_date_from_prices(df: pd.DataFrame) -> Optional[str]:
    if df.empty or "date" not in df.columns:
        return None
    ts = pd.to_datetime(df["date"], errors="coerce").max()
    if pd.isna(ts):
        return None
    return ts.strftime("%Y-%m-%d")


def live_label_allowed(last_refresh_at: Optional[str]) -> bool:
    if not last_refresh_at:
        return False
    try:
        ts = datetime.fromisoformat(last_refresh_at)
    except Exception:
        return False
    today = now_ist().date()
    return ts.astimezone(IST).date() == today


def parse_manual_universe_import(path: Path, index_label: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    rename = {
        "Company Name": "company_name",
        "Industry": "industry",
        "Symbol": "ticker",
        "ISIN Code": "isin",
    }
    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})
    if "ticker" not in df.columns:
        raise ValueError("Manual universe import is missing the Symbol/ticker column.")
    df["ticker"] = df["ticker"].astype(str).str.strip().str.upper()
    df["company_name"] = df.get("company_name", pd.Series(dtype=str)).astype(str).str.strip()
    df["industry"] = df.get("industry", pd.Series(dtype=str)).astype(str).str.strip()
    df["sector"] = df["industry"].map(classify_sector)
    df["index_membership"] = index_label
    df["isin"] = df.get("isin", pd.Series(dtype=str))
    df["bse_code"] = df.get("bse_code", "")
    df["nse_code"] = df.get("nse_code", df["ticker"])
    df["source"] = f"Manual Import:{path.name}"
    df["fetched_at"] = now_ist_iso()
    return df[UNIVERSE_COLUMNS].drop_duplicates(subset=["ticker"]).reset_index(drop=True)


def coerce_numeric(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    out = df.copy()
    for col in columns:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")
    return out


def dataframe_to_json_details(df: pd.DataFrame, limit: int = 25) -> str:
    if df.empty:
        return "[]"
    sample = df.head(limit).fillna("").to_dict(orient="records")
    return json.dumps(sample, ensure_ascii=True)

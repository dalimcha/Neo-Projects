"""
update_news.py

Canonical news ingestion for the India Markets Terminal.

Priority:
1. Manual CSV import from trusted sources
2. RSS aggregation from public market feeds

This script never invents news. If live RSS fetches fail, existing data stays in
place and the failure is logged via `failed_tickers.csv` / `data_quality_log.csv`.
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.pipeline import (
    NEWS_CSV,
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


NEWS_COLUMNS = [
    "headline",
    "source",
    "date",
    "url",
    "tickers_mentioned",
    "sector",
    "sentiment",
    "ai_summary",
    "is_material",
    "materiality_score",
    "categories",
    "ingested_at",
    "source_type",
]

RSS_FEEDS = {
    "Moneycontrol Markets": "https://www.moneycontrol.com/rss/marketreports.xml",
    "Google News India Markets": "https://news.google.com/rss/search?q=India+stock+market+OR+Nifty+OR+Sensex&hl=en-IN&gl=IN&ceid=IN:en",
    "Google News India Earnings": "https://news.google.com/rss/search?q=India+earnings+results+listed+companies&hl=en-IN&gl=IN&ceid=IN:en",
    "Google News Capital Markets": "https://news.google.com/rss/search?q=India+capital+markets+stocks+companies&hl=en-IN&gl=IN&ceid=IN:en",
}


def _clean_text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _infer_sentiment(headline: str) -> str:
    h = headline.lower()
    positive = ["wins", "approval", "surges", "upgrades", "beats", "strong", "growth", "order", "record", "raises"]
    negative = ["falls", "downgrade", "misses", "probe", "cuts", "weak", "decline", "drops", "loss", "delay"]
    if any(k in h for k in positive):
        return "positive"
    if any(k in h for k in negative):
        return "negative"
    return "neutral"


def _infer_categories(headline: str) -> str:
    h = headline.lower()
    tags = []
    mapping = {
        "results": ["result", "earnings", "q1", "q2", "q3", "q4"],
        "order_win": ["order", "contract", "wins", "award", "bagged"],
        "fundraise": ["qip", "rights issue", "fundraise", "ncd", "bond"],
        "management": ["ceo", "cfo", "appointment", "resignation"],
        "rating": ["rating", "upgrade", "downgrade"],
        "mna": ["acquisition", "merger", "stake", "buyout"],
        "sector_move": ["sector", "industry", "capex", "budget"],
    }
    for tag, words in mapping.items():
        if any(w in h for w in words):
            tags.append(tag)
    return ",".join(tags)


def _is_material(headline: str) -> bool:
    h = headline.lower()
    triggers = ["results", "earnings", "order", "contract", "fundraise", "rating", "merger", "stake", "guidance", "approval"]
    return any(k in h for k in triggers)


def _materiality_score(headline: str, sentiment: str, categories: str) -> int:
    score = 20
    cat_map = {
        "results": 35,
        "order_win": 30,
        "rating": 28,
        "fundraise": 24,
        "management": 20,
        "mna": 26,
        "sector_move": 14,
    }
    for cat, pts in cat_map.items():
        if cat in categories:
            score = max(score, pts)
    sentiment = str(sentiment or "").lower()
    if sentiment == "positive":
        score += 6
    elif sentiment == "negative":
        score += 8
    if _is_material(headline):
        score += 25
    return max(0, min(100, score))


def _build_company_matcher(universe: pd.DataFrame) -> list[tuple[str, str, str]]:
    suffix_strip = re.compile(
        r"\b(ltd|limited|industries|industry|corporation|corp|company|co|holdings|holding|services|service)\b",
        re.I,
    )
    rows = []
    for _, r in universe.iterrows():
        ticker = _clean_text(r.get("ticker", "")).upper()
        name = _clean_text(r.get("company_name", ""))
        sector = _clean_text(r.get("sector", ""))
        if ticker:
            rows.append((ticker, ticker, sector))
        if name:
            lowered = name.lower()
            rows.append((lowered, ticker, sector))
            stripped = _clean_text(suffix_strip.sub("", lowered))
            if stripped and stripped != lowered and len(stripped) >= 4:
                rows.append((stripped, ticker, sector))
            primary = stripped.split()[0] if stripped else ""
            if primary and len(primary) >= 5:
                rows.append((primary, ticker, sector))
    rows = sorted(set(rows), key=lambda x: (-len(x[0]), x[0]))
    return rows


def _map_tickers_and_sector(text: str, matcher: list[tuple[str, str, str]]) -> tuple[str, str]:
    hay = f" {text.lower()} "
    tickers = []
    sectors = []
    for needle, ticker, sector in matcher:
        token = needle.lower()
        if len(token) <= 2:
            continue
        if f" {token} " in hay or token in hay:
            tickers.append(ticker)
            if sector:
                sectors.append(sector)
    tickers = sorted(set([t for t in tickers if t]))
    sector = sectors[0] if sectors else ""
    return "|".join(tickers), sector


def fetch_rss_feed(source_name: str, url: str, matcher: list[tuple[str, str, str]], run_id: str) -> pd.DataFrame:
    try:
        resp = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
    except Exception as exc:
        append_failed_tickers([{
            "run_id": run_id,
            "dataset": "news",
            "ticker": source_name,
            "stage": "rss_fetch",
            "source": url,
            "error_message": str(exc),
            "failed_at": now_ist_iso(),
        }])
        logger.warning("RSS fetch failed for %s: %s", source_name, exc)
        return pd.DataFrame()

    try:
        root = ET.fromstring(resp.content)
    except Exception as exc:
        append_failed_tickers([{
            "run_id": run_id,
            "dataset": "news",
            "ticker": source_name,
            "stage": "rss_parse",
            "source": url,
            "error_message": str(exc),
            "failed_at": now_ist_iso(),
        }])
        return pd.DataFrame()

    items = []
    for item in root.findall(".//item"):
        headline = _clean_text(item.findtext("title", ""))
        link = _clean_text(item.findtext("link", ""))
        pub_date = _clean_text(item.findtext("pubDate", ""))
        if not headline:
            continue
        if source_name.startswith("Google News") and " - " in headline:
            headline = headline.rsplit(" - ", 1)[0].strip()
        tickers, sector = _map_tickers_and_sector(headline, matcher)
        sentiment = _infer_sentiment(headline)
        categories = _infer_categories(headline)
        items.append({
            "headline": headline,
            "source": source_name,
            "date": pub_date,
            "url": link,
            "tickers_mentioned": tickers,
            "sector": sector,
            "sentiment": sentiment,
            "ai_summary": "",
            "is_material": _is_material(headline),
            "materiality_score": _materiality_score(headline, sentiment, categories),
            "categories": categories,
            "ingested_at": now_ist_iso(),
            "source_type": "RSS",
        })
    return pd.DataFrame(items)


def import_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    rename = {
        "Headline": "headline",
        "headline": "headline",
        "Title": "headline",
        "title": "headline",
        "Source": "source",
        "source": "source",
        "Publisher": "source",
        "publisher": "source",
        "Date": "date",
        "date": "date",
        "Published At": "date",
        "published_at": "date",
        "URL": "url",
        "url": "url",
        "Link": "url",
        "link": "url",
        "Tickers": "tickers_mentioned",
        "tickers": "tickers_mentioned",
        "Ticker": "tickers_mentioned",
        "ticker": "tickers_mentioned",
        "Tickers Mentioned": "tickers_mentioned",
        "Sector": "sector",
        "sector": "sector",
        "Sentiment": "sentiment",
        "sentiment": "sentiment",
        "Summary": "ai_summary",
        "summary": "ai_summary",
        "AI Summary": "ai_summary",
        "Material": "is_material",
        "material": "is_material",
        "Is Material": "is_material",
        "Materiality Score": "materiality_score",
        "materiality_score": "materiality_score",
        "Score": "materiality_score",
        "Categories": "categories",
        "categories": "categories",
        "Category": "categories",
        "category": "categories",
    }
    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})
    if "headline" not in df.columns:
        raise ValueError("Manual news import requires a headline/title column.")
    if "date" not in df.columns:
        raise ValueError("Manual news import requires a date/published_at column.")
    for col in NEWS_COLUMNS:
        if col not in df.columns:
            df[col] = "" if col not in {"is_material"} else False
    df["headline"] = df["headline"].map(_clean_text)
    if "source" in df.columns:
        df["source"] = df["source"].map(_clean_text)
    if "url" in df.columns:
        df["url"] = df["url"].map(_clean_text)
    if "tickers_mentioned" in df.columns:
        df["tickers_mentioned"] = (
            df["tickers_mentioned"]
            .fillna("")
            .astype(str)
            .str.upper()
            .str.replace(",", "|")
            .str.replace(" ", "", regex=False)
        )
    if "sentiment" in df.columns:
        df["sentiment"] = df["sentiment"].fillna("").astype(str).str.lower().str.strip()
    if "categories" in df.columns:
        df["categories"] = df["categories"].fillna("").astype(str).str.strip()
    if "sector" in df.columns:
        df["sector"] = df["sector"].fillna("").astype(str).str.strip()
    if "ai_summary" in df.columns:
        df["ai_summary"] = df["ai_summary"].fillna("").astype(str).str.strip()
    if "is_material" in df.columns:
        df["is_material"] = (
            df["is_material"]
            .map(lambda x: str(x).strip().lower() in {"1", "true", "yes", "y"})
            .astype(bool)
        )
    df["ingested_at"] = now_ist_iso()
    df["source_type"] = "Manual CSV"
    if "materiality_score" in df.columns:
        df["materiality_score"] = pd.to_numeric(df["materiality_score"], errors="coerce").fillna(0)
    missing_sentiment = df["sentiment"].astype(str).str.strip() == ""
    df.loc[missing_sentiment, "sentiment"] = df.loc[missing_sentiment, "headline"].map(_infer_sentiment)
    missing_categories = df["categories"].astype(str).str.strip() == ""
    df.loc[missing_categories, "categories"] = df.loc[missing_categories, "headline"].map(_infer_categories)
    no_material = df["materiality_score"].fillna(0).eq(0)
    df.loc[no_material, "materiality_score"] = df.loc[no_material].apply(
        lambda r: _materiality_score(str(r.get("headline", "")), str(r.get("sentiment", "")), str(r.get("categories", ""))),
        axis=1,
    )
    no_flag = ~df["is_material"].astype(bool)
    df.loc[no_flag, "is_material"] = df.loc[no_flag, "headline"].map(_is_material)
    return df[NEWS_COLUMNS].copy()


def run(import_csv_path: str | None = None) -> int:
    ensure_data_files()
    run_id = make_run_id("news")
    existing = read_csv_safe(NEWS_CSV)

    if import_csv_path:
        logger.info("Importing manual news CSV: %s", import_csv_path)
        imported = import_csv(import_csv_path)
        combined = pd.concat([imported, existing], ignore_index=True)
    else:
        universe = load_universe()
        matcher = _build_company_matcher(universe)
        frames = []
        for name, url in RSS_FEEDS.items():
            df = fetch_rss_feed(name, url, matcher, run_id)
            if not df.empty:
                frames.append(df)
        if not frames:
            logger.warning("No RSS items fetched. Existing news retained.")
            log_quality(
                run_id=run_id,
                dataset="news",
                universe="Nifty500",
                expected_rows=0,
                loaded_rows=len(existing),
                source="RSS/manual",
                last_refresh_at=now_ist_iso() if not existing.empty else None,
                details="No RSS items fetched; retained existing file.",
                status_override="cached" if not existing.empty else "failed",
            )
            return 0
        combined = pd.concat(frames + [existing], ignore_index=True)

    combined["headline"] = combined["headline"].map(_clean_text)
    combined["source"] = combined["source"].map(_clean_text)
    combined["url"] = combined["url"].map(_clean_text)
    combined["date"] = pd.to_datetime(combined["date"], errors="coerce", utc=True).dt.tz_convert(None)
    combined = combined.dropna(subset=["headline", "date"], how="any")
    combined = combined.drop_duplicates(subset=["headline", "source", "date"], keep="first")
    combined = combined.sort_values("date", ascending=False).reset_index(drop=True)

    latest_article = pd.to_datetime(combined["date"], errors="coerce").max() if not combined.empty else pd.NaT
    status = "fresh"
    details = f"News rows stored: {len(combined)}"
    if pd.notna(latest_article):
        age_days = (pd.Timestamp.now() - latest_article).days
        if age_days > 30:
            status = "stale"
            details += f"; latest article date is stale ({latest_article.date()})"
        elif age_days > 7:
            status = "delayed"
            details += f"; latest article date is delayed ({latest_article.date()})"
    else:
        status = "failed"
        details += "; no valid article timestamps"

    atomic_write_csv(combined, NEWS_CSV, NEWS_COLUMNS)
    log_quality(
        run_id=run_id,
        dataset="news",
        universe="Nifty500",
        expected_rows=0,
        loaded_rows=len(combined),
        source="RSS/manual",
        last_refresh_at=now_ist_iso(),
        details=details,
        status_override=status,
    )
    logger.info("News update complete: %d rows written to %s", len(combined), NEWS_CSV)
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Update market/company news")
    parser.add_argument("--import-csv", help="Manual CSV import path")
    args = parser.parse_args()
    raise SystemExit(run(import_csv_path=args.import_csv))

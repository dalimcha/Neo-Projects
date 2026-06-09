"""
generate_ai_summaries.py
────────────────────────
Batch-processes unsummarised filings and news items through the
Anthropic Claude API and writes summaries back to the CSVs.

Run after update_filings.py:
    python scripts/generate_ai_summaries.py

Options:
    --max N         Max items to process per run (default: 50)
    --force         Re-summarise all items even if already summarised
    --filings-only  Process filings only
    --news-only     Process news only
"""

import sys, os, argparse, logging, time
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv(Path(__file__).parent.parent / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR    = Path(__file__).parent.parent / "data"
FILINGS_CSV = DATA_DIR / "filings.csv"
NEWS_CSV    = DATA_DIR / "news.csv"


def run(max_items=50, force=False, filings_only=False, news_only=False):
    logger.info("=== AI Summarisation Started ===")

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        logger.error("ANTHROPIC_API_KEY not set. Add it to .env and retry.")
        return

    import utils.ai_summarizer as ai

    total_processed = 0

    if not news_only:
        total_processed += _process_filings(ai, max_items - total_processed, force)

    if not filings_only and total_processed < max_items:
        total_processed += _process_news(ai, max_items - total_processed, force)

    logger.info("=== AI Summarisation Complete — %d items processed ===", total_processed)


def _process_filings(ai, remaining, force):
    if not FILINGS_CSV.exists():
        logger.info("No filings.csv found, skipping.")
        return 0

    df = pd.read_csv(FILINGS_CSV)
    if df.empty:
        return 0

    # Which rows need summarisation
    if force:
        to_process = df
    else:
        needs_summary = df["ai_summary"].isna() | (df["ai_summary"].astype(str).str.strip() == "")
        to_process = df[needs_summary]

    logger.info("Filings: %d rows to summarise (of %d total)", len(to_process), len(df))

    count = 0
    for idx in to_process.index:
        if count >= remaining:
            break

        row = df.loc[idx]
        ticker  = str(row.get("ticker", ""))
        company = str(row.get("company_name", ""))
        subject = str(row.get("subject", ""))
        ftype   = str(row.get("type", ""))

        try:
            result = ai.summarize_filing(
                ticker=ticker, company=company,
                subject=subject, filing_type=ftype,
            )
            df.at[idx, "ai_summary"]  = result.get("summary", "")
            df.at[idx, "sentiment"]   = result.get("sentiment", "neutral")
            df.at[idx, "is_material"] = result.get("is_material", False)
            count += 1
            logger.info("[%d] Summarised %s: %s…", count, ticker, subject[:60])
            # Polite rate limiting
            time.sleep(0.5)
        except Exception as e:
            logger.warning("Failed to summarise filing idx=%d: %s", idx, e)

    if count > 0:
        df.to_csv(FILINGS_CSV, index=False)
        logger.info("Saved %d summarised filings to %s", count, FILINGS_CSV)

    return count


def _process_news(ai, remaining, force):
    if not NEWS_CSV.exists():
        logger.info("No news.csv found, skipping.")
        return 0

    df = pd.read_csv(NEWS_CSV)
    if df.empty:
        return 0

    if force:
        to_process = df
    else:
        needs_summary = df["ai_summary"].isna() | (df["ai_summary"].astype(str).str.strip() == "")
        to_process = df[needs_summary]

    logger.info("News: %d rows to summarise (of %d total)", len(to_process), len(df))

    count = 0
    for idx in to_process.index:
        if count >= remaining:
            break

        row  = df.loc[idx]
        headline = str(row.get("headline", ""))
        source   = str(row.get("source", ""))
        content  = str(row.get("content", headline))  # fall back to headline if no body

        try:
            result = ai.summarize_news_item(
                headline=headline, source=source, content=content,
            )
            df.at[idx, "ai_summary"]         = result.get("summary", "")
            df.at[idx, "sentiment"]           = result.get("sentiment", "neutral")
            df.at[idx, "categories"]          = result.get("categories", "")
            df.at[idx, "tickers_mentioned"]   = result.get("tickers_mentioned", "")
            count += 1
            logger.info("[%d] Summarised news: %s…", count, headline[:60])
            time.sleep(0.5)
        except Exception as e:
            logger.warning("Failed to summarise news idx=%d: %s", idx, e)

    if count > 0:
        df.to_csv(NEWS_CSV, index=False)
        logger.info("Saved %d summarised news items to %s", count, NEWS_CSV)

    return count


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate AI summaries")
    parser.add_argument("--max",          type=int, default=50, help="Max items to process")
    parser.add_argument("--force",        action="store_true",  help="Re-summarise all items")
    parser.add_argument("--filings-only", action="store_true",  dest="filings_only")
    parser.add_argument("--news-only",    action="store_true",  dest="news_only")
    args = parser.parse_args()
    run(max_items=args.max, force=args.force,
        filings_only=args.filings_only, news_only=args.news_only)

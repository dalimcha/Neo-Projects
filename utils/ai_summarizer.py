"""
ai_summarizer.py
────────────────
Claude API integration for generating AI summaries.
All calls gracefully degrade if API key is not configured.
"""

from __future__ import annotations
import os, json, logging
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)

_CLIENT = None

def _get_client():
    global _CLIENT
    if _CLIENT is not None:
        return _CLIENT
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return None
    try:
        import anthropic
        _CLIENT = anthropic.Anthropic(api_key=api_key)
        return _CLIENT
    except ImportError:
        logger.warning("anthropic package not installed")
        return None


def _call(system: str, user: str, max_tokens: int = 600) -> Optional[str]:
    """Make a Claude API call. Returns text or None on failure."""
    client = _get_client()
    if client is None:
        return None
    try:
        msg = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return msg.content[0].text.strip()
    except Exception as e:
        logger.debug("AI call failed: %s", e)
        return None


# ── Market summary ────────────────────────────────────────────────────────────

def generate_market_summary(market_data: dict) -> str:
    """
    Generate a concise daily market narrative.
    market_data: dict with keys like nifty50_change, advancers, decliners,
                 top_gainers (list), top_losers (list), sector_moves (dict)
    """
    system = (
        "You are a senior India equity market analyst at a large institutional fund. "
        "Write a concise, professional morning market summary in 3-4 sentences. "
        "Use precise numbers. No emojis. No markdown headers. Institutional tone."
    )
    user = (
        f"Summarise today's Indian market based on:\n"
        f"Nifty 50 change: {market_data.get('nifty50_change', 'N/A')}\n"
        f"Advancers/Decliners: {market_data.get('advancers', '?')}/{market_data.get('decliners', '?')}\n"
        f"Top gainers: {', '.join(market_data.get('top_gainers', []))}\n"
        f"Top losers: {', '.join(market_data.get('top_losers', []))}\n"
        f"Sector moves: {json.dumps(market_data.get('sector_moves', {}))}\n"
        f"Date: {datetime.today().strftime('%d %b %Y')}"
    )
    result = _call(system, user, max_tokens=250)
    return result or "AI summary unavailable — configure ANTHROPIC_API_KEY in Settings."


def generate_what_changed(filings: list[dict], price_moves: list[dict]) -> str:
    """Generate 'What Changed Today' bullet points."""
    system = (
        "You are a senior India equity research analyst. "
        "Summarise the most important market developments from today's filings and price moves. "
        "Write 3-5 concise bullet points. Each bullet: 1 sentence, start with the company name. "
        "No emojis. Professional, precise language."
    )
    filings_str = "\n".join(
        f"- {f.get('ticker','')}: {f.get('subject','')}" for f in filings[:10]
    )
    moves_str = "\n".join(
        f"- {m.get('ticker','')}: {m.get('return_1d',0)*100:+.1f}%" for m in price_moves[:8]
    )
    user = f"Key filings today:\n{filings_str}\n\nNotable price moves:\n{moves_str}"
    result = _call(system, user, max_tokens=300)
    return result or "AI summary unavailable."


# ── Company analyst note ──────────────────────────────────────────────────────

def generate_company_note(company_data: dict) -> str:
    """
    Generate an AI analyst note for a specific company.
    company_data: merged dict of meta, price, fund, ob data.
    """
    ticker  = company_data.get("ticker", "")
    name    = company_data.get("company_name", ticker)
    sector  = company_data.get("sector", "")
    mcap    = company_data.get("market_cap_cr", "N/A")
    pe      = company_data.get("pe", "N/A")
    roe     = company_data.get("roe", "N/A")
    rev_g   = company_data.get("revenue_growth_1y", "N/A")
    ob      = company_data.get("order_book_cr", "N/A")
    ob_rev  = company_data.get("ob_revenue_ratio", "N/A")
    score   = company_data.get("ob_score", "N/A")
    cls     = company_data.get("classification", "N/A")

    system = (
        "You are a senior India equity analyst. Write a 3-4 sentence institutional analyst note "
        "covering investment thesis, key risks, and one thing to watch. "
        "No emojis. No bullet points. Pure prose. Analytical, precise."
    )
    user = (
        f"Company: {name} ({ticker})\n"
        f"Sector: {sector}\n"
        f"Market Cap: ₹{mcap} Cr\n"
        f"PE: {pe}x | ROE: {roe}%\n"
        f"Revenue Growth: {rev_g}%\n"
        f"Order Book: ₹{ob} Cr | OB/Rev: {ob_rev}x\n"
        f"OB Score: {score}/100 | Classification: {cls}"
    )
    result = _call(system, user, max_tokens=350)
    return result or "AI note unavailable — configure ANTHROPIC_API_KEY in Settings."


# ── Filing summariser ─────────────────────────────────────────────────────────

def summarize_filing(
    ticker: str,
    company: str,
    subject: str,
    full_text: str = "",
    filing_type: str = "",
) -> dict:
    """
    Summarise a corporate filing.
    Returns: {summary, sentiment, is_material, affected_metrics, watchlist_flag}
    """
    system = (
        "You are an India equity research analyst. "
        "Analyse this corporate filing. Respond ONLY in valid JSON with keys: "
        "summary (1-2 sentences), sentiment (positive/negative/neutral), "
        "is_material (true/false), affected_metrics (list of strings), "
        "watchlist_flag (true/false), why_flagged (1 sentence or empty string)."
    )
    body = full_text[:1500] if full_text else subject
    user = (
        f"Company: {company} ({ticker})\n"
        f"Filing type: {filing_type}\n"
        f"Subject: {subject}\n"
        f"Content: {body}"
    )
    raw = _call(system, user, max_tokens=400)
    if raw:
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass
    # Fallback
    return {
        "summary": subject,
        "sentiment": "neutral",
        "is_material": False,
        "affected_metrics": [],
        "watchlist_flag": False,
        "why_flagged": "",
    }


# ── Order-book extraction prompt ──────────────────────────────────────────────

def extract_order_book_from_text(
    company: str,
    ticker: str,
    source_text: str,
) -> dict:
    """
    Extract order book data from a concall transcript / investor presentation.
    Returns dict with: order_book_cr, order_inflow_cr, management_commentary,
                       confidence_score, extracted_snippets, warnings
    """
    system = (
        "You are an India equity analyst extracting order book data from a document. "
        "Respond ONLY in valid JSON with keys: "
        "order_book_cr (float or null), "
        "order_inflow_cr (float or null), "
        "management_commentary (key quote, max 100 words), "
        "extracted_snippets (list of verbatim quotes used), "
        "confidence_score (0-100, based on data clarity), "
        "warnings (list of data quality concerns). "
        "If a value is not clearly stated, set it to null. Do NOT infer or estimate numbers."
    )
    user = (
        f"Company: {company} ({ticker})\n\n"
        f"Source document excerpt:\n{source_text[:3000]}"
    )
    raw = _call(system, user, max_tokens=600)
    if raw:
        try:
            data = json.loads(raw)
            data.setdefault("confidence_score", 0)
            data.setdefault("warnings", ["AI extraction — requires manual verification"])
            data["manually_verified"] = False
            return data
        except json.JSONDecodeError:
            pass
    return {
        "order_book_cr": None,
        "order_inflow_cr": None,
        "management_commentary": "",
        "extracted_snippets": [],
        "confidence_score": 0,
        "warnings": ["Extraction failed — manual entry required"],
        "manually_verified": False,
    }


# ── Sector analysis ───────────────────────────────────────────────────────────

def generate_sector_analysis(
    sector_name: str,
    companies: list[str],
    recent_news: list[str],
) -> str:
    """Generate a sector cycle and outlook summary."""
    system = (
        "You are a senior India sector analyst. Write a 3-4 sentence sector outlook "
        "covering current cycle position, key demand drivers, and key risk. "
        "No emojis. Institutional tone."
    )
    user = (
        f"Sector: {sector_name}\n"
        f"Key listed companies: {', '.join(companies[:8])}\n"
        f"Recent headlines: {'; '.join(recent_news[:5])}"
    )
    result = _call(system, user, max_tokens=300)
    return result or "Sector analysis unavailable — configure ANTHROPIC_API_KEY in Settings."


# ── Daily email brief ─────────────────────────────────────────────────────────

def generate_evening_brief(
    market_summary: str,
    top_filings: list[dict],
    ob_flags: list[dict],
) -> str:
    """Generate the '5 things to know before tomorrow' evening brief."""
    system = (
        "You are a senior India equity analyst. "
        "Write exactly 5 concise bullet points summarising the most important things "
        "an institutional investor should know before tomorrow's market open. "
        "Each bullet: Company/Theme — key point. No emojis. Max 2 lines per bullet."
    )
    filings_str = "\n".join(
        f"- {f.get('ticker','')}: {f.get('subject','')}" for f in top_filings[:8]
    )
    flags_str = "\n".join(
        f"- {f.get('ticker','')}: {f.get('flag','')}" for f in ob_flags[:5]
    )
    user = (
        f"Market: {market_summary}\n\n"
        f"Key filings:\n{filings_str}\n\n"
        f"OB flags:\n{flags_str}"
    )
    result = _call(system, user, max_tokens=400)
    return result or "Evening brief unavailable — configure ANTHROPIC_API_KEY."

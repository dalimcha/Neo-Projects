"""
scoring.py
──────────
Order Book Mispricing Score — the core analytical model.

Score = weighted sum of 6 factors (0–100 scale)
  30% → Order Book / Revenue
  20% → Order Inflow Growth
  15% → Revenue Growth
  15% → Margin Stability
  10% → Valuation Discount to Peers
  10% → Balance Sheet Quality

Penalties applied after raw score:
  • Rising receivables vs revenue
  • Falling EBITDA margins
  • High debt
  • Slow execution cycle
  • Weak cash flow conversion
  • One-off orders (manual flag)
  • Customer concentration (manual flag)
  • Expensive valuation vs peers
"""

from __future__ import annotations
import pandas as pd
import numpy as np
from typing import Any


# ── Factor weights ────────────────────────────────────────────────────────────
FACTOR_WEIGHTS = {
    "ob_revenue":      0.30,
    "inflow_growth":   0.20,
    "revenue_growth":  0.15,
    "margin_stability":0.15,
    "valuation":       0.10,
    "balance_sheet":   0.10,
}


# ── Helper ────────────────────────────────────────────────────────────────────
def _get(row: Any, key: str, default=0):
    """Safely get a value from dict or pandas Series."""
    try:
        v = row[key] if isinstance(row, dict) else row.get(key, default)
        if v is None or (isinstance(v, float) and np.isnan(v)):
            return default
        return float(v)
    except (TypeError, ValueError, KeyError):
        return default


def _get_str(row: Any, key: str, default: str = "") -> str:
    try:
        v = row[key] if isinstance(row, dict) else row.get(key, default)
        return str(v) if v is not None else default
    except (KeyError, TypeError):
        return default


def _get_bool(row: Any, key: str) -> bool:
    try:
        v = row[key] if isinstance(row, dict) else row.get(key, False)
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.strip().lower() in ("true", "yes", "1", "y")
        return bool(v)
    except (KeyError, TypeError):
        return False


# ── Factor scoring (each returns 0–100 normalised to its weight) ─────────────

def score_ob_revenue(row) -> float:
    """
    30 pts max: OB / TTM Revenue
    """
    ob_rev = _get(row, "ob_revenue_ratio")
    if ob_rev >= 5:    return 30.0
    if ob_rev >= 4:    return 27.5
    if ob_rev >= 3.5:  return 25.0
    if ob_rev >= 3:    return 22.0
    if ob_rev >= 2.5:  return 18.0
    if ob_rev >= 2:    return 14.0
    if ob_rev >= 1.5:  return 9.0
    if ob_rev >= 1:    return 5.0
    return 0.0


def score_inflow_growth(row) -> float:
    """
    20 pts max: YoY order inflow growth %
    Also considers BTB (book-to-bill) momentum.
    """
    g = _get(row, "order_inflow_growth_pct")
    btb = _get(row, "btb_ratio", 1.0)

    raw = 0.0
    if g >= 60:    raw = 20.0
    elif g >= 40:  raw = 17.5
    elif g >= 25:  raw = 14.0
    elif g >= 15:  raw = 10.0
    elif g >= 5:   raw = 6.0
    elif g >= 0:   raw = 3.0
    elif g >= -10: raw = 1.0
    else:          raw = 0.0

    # BTB bonus/malus
    if btb >= 1.3:   raw = min(20, raw + 2)
    elif btb < 0.8:  raw = max(0, raw - 3)

    return raw


def score_revenue_growth(row) -> float:
    """15 pts max: TTM / 1Y revenue growth %"""
    g = _get(row, "revenue_growth_pct")
    if g >= 30:    return 15.0
    if g >= 20:    return 13.0
    if g >= 15:    return 10.0
    if g >= 10:    return 7.0
    if g >= 5:     return 4.0
    if g >= 0:     return 2.0
    return 0.0


def score_margin_stability(row) -> float:
    """
    15 pts max.
    Trend (improving/stable/declining) × absolute EBITDA margin level.
    """
    trend  = _get_str(row, "ebitda_margin_trend").lower()
    margin = _get(row, "ebitda_margin_pct")

    # Base score from trend
    if "improv" in trend:
        trend_score = 15.0
    elif "stable" in trend or trend == "":
        trend_score = 10.0 if margin >= 15 else 7.0
    elif "slight" in trend and "decl" in trend:
        trend_score = 4.0
    elif "decl" in trend:
        trend_score = 0.0
    else:
        trend_score = 5.0

    # Bonus for high absolute margin
    if margin >= 25:   trend_score = min(15, trend_score + 2)
    elif margin >= 20: trend_score = min(15, trend_score + 1)

    return trend_score


def score_valuation(row) -> float:
    """
    10 pts max: discount to sector peers on EV/EBITDA.
    Positive = cheap vs peers, negative = expensive.
    """
    company_ev = _get(row, "peer_ev_ebitda", None)
    sector_ev  = _get(row, "sector_ev_ebitda", None)

    # If no peer data, use ob/ev ratio as proxy (lower = better value)
    if not company_ev or not sector_ev:
        ob_ev = _get(row, "ob_ev_ratio")
        if ob_ev >= 1:    return 8.0  # OB > EV = very cheap
        if ob_ev >= 0.7:  return 6.0
        if ob_ev >= 0.5:  return 4.0
        return 2.0

    if sector_ev <= 0:
        return 5.0

    premium_pct = (company_ev - sector_ev) / sector_ev * 100

    if premium_pct <= -30:  return 10.0
    if premium_pct <= -20:  return 8.5
    if premium_pct <= -10:  return 7.0
    if premium_pct <= 0:    return 5.5
    if premium_pct <= 15:   return 3.0
    if premium_pct <= 30:   return 1.5
    return 0.0


def score_balance_sheet(row) -> float:
    """10 pts max: D/E, working capital days, CFO conversion."""
    de  = _get(row, "debt_equity")
    wcd = _get(row, "working_capital_days", 90)
    cfo = _get(row, "cfo_conversion", 0.75)

    bs = 0.0

    # D/E
    if de <= 0:     bs += 4.0
    elif de <= 0.3: bs += 3.5
    elif de <= 0.7: bs += 3.0
    elif de <= 1.0: bs += 2.0
    elif de <= 1.5: bs += 1.0

    # Working capital days
    if wcd <= 45:     bs += 3.5
    elif wcd <= 60:   bs += 3.0
    elif wcd <= 90:   bs += 2.0
    elif wcd <= 120:  bs += 1.0

    # CFO / PAT conversion
    if cfo >= 1.0:   bs += 2.5
    elif cfo >= 0.85:bs += 2.0
    elif cfo >= 0.70:bs += 1.5
    elif cfo >= 0.50:bs += 0.5

    return min(10.0, bs)


# ── Penalty engine ────────────────────────────────────────────────────────────

def apply_penalties(raw_score: float, row) -> tuple[float, list[str]]:
    """
    Apply penalty deductions to the raw score.
    Returns (adjusted_score, list_of_penalty_reasons).
    """
    score    = raw_score
    reasons: list[str] = []

    recv_g  = _get(row, "receivables_growth_pct")
    rev_g   = _get(row, "revenue_growth_pct")
    margin_t = _get_str(row, "ebitda_margin_trend").lower()
    de       = _get(row, "debt_equity")
    exec_cy  = _get(row, "execution_cycle_months", 18)
    cfo      = _get(row, "cfo_conversion", 0.75)
    one_off  = _get_bool(row, "one_off_order")
    cust_conc = _get_bool(row, "customer_concentration")
    margin   = _get(row, "ebitda_margin_pct")

    # Rising receivables vs revenue (suggests cash conversion issue)
    if recv_g > rev_g + 15:
        score -= 12; reasons.append("Receivables growing 15pp+ faster than revenue")
    elif recv_g > rev_g + 8:
        score -= 6;  reasons.append("Receivables growing faster than revenue")

    # Falling margins
    if "decl" in margin_t and "slight" not in margin_t:
        score -= 12; reasons.append("EBITDA margins in decline")
    elif "slight" in margin_t and "decl" in margin_t:
        score -= 5;  reasons.append("EBITDA margins slightly declining")

    # High debt
    if de > 2.5:
        score -= 12; reasons.append("Very high leverage (D/E > 2.5x)")
    elif de > 2.0:
        score -= 8;  reasons.append("High leverage (D/E > 2.0x)")
    elif de > 1.5:
        score -= 4;  reasons.append("Elevated leverage (D/E > 1.5x)")

    # Slow execution / order book may not translate
    if exec_cy > 48:
        score -= 10; reasons.append("Very slow execution cycle (>48 months)")
    elif exec_cy > 36:
        score -= 6;  reasons.append("Slow execution cycle (>36 months)")
    elif exec_cy > 30:
        score -= 3;  reasons.append("Above-average execution cycle")

    # Weak cash flow conversion
    if cfo < 0.3:
        score -= 10; reasons.append("Very weak CFO/PAT conversion (<30%)")
    elif cfo < 0.5:
        score -= 6;  reasons.append("Weak CFO/PAT conversion (<50%)")

    # One-off orders (manual flag)
    if one_off:
        score -= 10; reasons.append("Order book includes material one-off orders")

    # Customer concentration (manual flag)
    if cust_conc:
        score -= 6;  reasons.append("High customer concentration risk")

    # Very low absolute margins even if stable
    if margin < 5 and "decl" not in margin_t:
        score -= 5;  reasons.append("Low absolute EBITDA margin (<5%)")

    return max(0.0, min(100.0, score)), reasons


# ── Classification ────────────────────────────────────────────────────────────

def classify_stock(score: float, row) -> str:
    """
    Classify a stock based on its OB score and key qualitative metrics.
    """
    de        = _get(row, "debt_equity")
    margin_t  = _get_str(row, "ebitda_margin_trend").lower()
    pe        = _get(row, "pe", 0)
    sect_pe   = _get(row, "sector_pe", 30)
    ob_rev    = _get(row, "ob_revenue_ratio")
    rev_g     = _get(row, "revenue_growth_pct")
    recv_g    = _get(row, "receivables_growth_pct")
    cfo       = _get(row, "cfo_conversion", 0.75)

    # Momentum But Expensive: good order book, high valuation
    pe_premium = ((pe - sect_pe) / sect_pe) if sect_pe > 0 else 0
    if pe_premium > 0.5 and ob_rev >= 2 and rev_g >= 15:
        return "Momentum But Expensive"

    # Value Trap: cheap on surface but deteriorating fundamentals
    if pe > 0 and pe <= 12 and ("decl" in margin_t or cfo < 0.4):
        return "Value Trap"

    if recv_g > rev_g + 20 and de > 1.5:
        return "Value Trap"

    # Score-based classification
    if score >= 72:  return "High Conviction Idea"
    if score >= 58:  return "Watchlist Add"
    if score >= 42:  return "Needs More Research"
    if score >= 25:  return "Needs More Research"
    return "Avoid"


# ── Master scorer ─────────────────────────────────────────────────────────────

def calculate_ob_score(row) -> dict:
    """
    Run the full scoring pipeline on a single row (dict or pd.Series).
    Returns dict with score, factors, penalties, classification, score_breakdown.
    """
    factors = {
        "ob_revenue":       score_ob_revenue(row),
        "inflow_growth":    score_inflow_growth(row),
        "revenue_growth":   score_revenue_growth(row),
        "margin_stability": score_margin_stability(row),
        "valuation":        score_valuation(row),
        "balance_sheet":    score_balance_sheet(row),
    }
    raw_score = sum(factors.values())
    final_score, penalties = apply_penalties(raw_score, row)
    classification = classify_stock(final_score, row)

    return {
        "ob_score":      round(final_score, 1),
        "raw_score":     round(raw_score, 1),
        "classification": classification,
        "factors":       factors,
        "penalties":     penalties,
    }


# ── Batch scorer ──────────────────────────────────────────────────────────────

def score_order_book_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply calculate_ob_score to every row of an order_book DataFrame.
    Adds columns: ob_score, classification, and factor_* columns.
    Returns new DataFrame (does not mutate original).
    """
    if df.empty:
        return df.copy()

    out = df.copy()
    results = df.apply(lambda row: calculate_ob_score(row), axis=1)

    out["ob_score"]      = results.apply(lambda r: r["ob_score"])
    out["classification"] = results.apply(lambda r: r["classification"])
    out["raw_score"]     = results.apply(lambda r: r["raw_score"])

    for factor in FACTOR_WEIGHTS:
        out[f"f_{factor}"] = results.apply(lambda r: r["factors"].get(factor, 0))

    out["penalty_count"] = results.apply(lambda r: len(r["penalties"]))
    out["penalties_str"] = results.apply(lambda r: " | ".join(r["penalties"]))

    return out.sort_values("ob_score", ascending=False)


# ── Score metadata for display ────────────────────────────────────────────────

FACTOR_LABELS = {
    "ob_revenue":       "Order Book / Revenue  (30 pts)",
    "inflow_growth":    "Order Inflow Growth   (20 pts)",
    "revenue_growth":   "Revenue Growth        (15 pts)",
    "margin_stability": "Margin Stability      (15 pts)",
    "valuation":        "Valuation vs Peers    (10 pts)",
    "balance_sheet":    "Balance Sheet Quality (10 pts)",
}

FACTOR_MAX = {
    "ob_revenue":       30,
    "inflow_growth":    20,
    "revenue_growth":   15,
    "margin_stability": 15,
    "valuation":        10,
    "balance_sheet":    10,
}

CLASSIFICATION_ORDER = [
    "High Conviction Idea",
    "Watchlist Add",
    "Needs More Research",
    "Momentum But Expensive",
    "Value Trap",
    "Avoid",
]

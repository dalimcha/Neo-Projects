"""
New Ideas Engine
────────────────
Automated flagging of mispricing candidates using rules + order book scores.
Each idea gets: title, why flagged, key metrics, what market may be missing,
risks, next step, confidence level.
"""

import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(
    page_title="New Ideas — India Terminal",
    layout="wide", initial_sidebar_state="expanded",
)

from utils.formatting import (
    inject_css, page_header, section_label, kpi_card, fmt_pct,
    fmt_cr, fmt_ratio, info_block, warn_block, ok_block, ai_box,
    badge_html, score_bar, ACCENT, POS, NEG, TEXT3, BORDER, BG2,
)
from utils.data_loader import load_order_book, load_full_universe, load_news
from utils.scoring import score_order_book_df, CLASSIFICATION_ORDER

inject_css()

# ── Load data ─────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def _load_all():
    ob   = load_order_book()
    ob_s = score_order_book_df(ob) if not ob.empty else pd.DataFrame()
    uni  = load_full_universe()
    news = load_news()
    return ob_s, uni, news

ob_df, uni_df, news_df = _load_all()

page_header("New Ideas Engine", "Automated mispricing and opportunity flags")

# ── Sidebar filters ───────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="sec-label">Idea Filters</div>', unsafe_allow_html=True)
    idea_types = st.multiselect(
        "Flag Types",
        [
            "OB > 2x Revenue",
            "OB > Market Cap",
            "Strong Inflows + Weak Price",
            "Down >20% from High + Improving Fundamentals",
            "Improving Margins",
            "Recent Large Order Win",
            "High Score + Low Valuation",
        ],
        default=[
            "OB > 2x Revenue",
            "OB > Market Cap",
            "Strong Inflows + Weak Price",
            "High Score + Low Valuation",
        ],
    )
    min_conf = st.slider("Min Confidence (Order Book Data)", 0, 100, 50)


# ── Idea generator ────────────────────────────────────────────────────────────
def _make_idea(ticker, company, sector, flag_type, reason, metrics, what_missing,
               risks, next_step, confidence, action, score=None):
    return {
        "ticker": ticker, "company": company, "sector": sector,
        "flag_type": flag_type, "reason": reason, "metrics": metrics,
        "what_missing": what_missing, "risks": risks, "next_step": next_step,
        "confidence": confidence, "action": action, "score": score,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }


ideas = []

# ── Rule 1: OB > 2x Revenue ──────────────────────────────────────────────────
if "OB > 2x Revenue" in idea_types and not ob_df.empty:
    cands = ob_df[
        (ob_df.get("ob_revenue_ratio", pd.Series(dtype=float)) >= 2) &
        (ob_df.get("confidence_score", pd.Series(dtype=float)) >= min_conf)
    ].copy()
    for _, r in cands.iterrows():
        score = r.get("ob_score", 0)
        ob_rev = r.get("ob_revenue_ratio", 0)
        ideas.append(_make_idea(
            ticker    = r.get("ticker",""),
            company   = r.get("company_name",""),
            sector    = r.get("sector",""),
            flag_type = "OB > 2x Revenue",
            reason    = (
                f"Order book of {fmt_cr(r.get('order_book_cr'))} is "
                f"{fmt_ratio(ob_rev)} of TTM revenue, providing "
                f"{ob_rev:.1f} years of revenue visibility."
            ),
            metrics = {
                "Order Book": fmt_cr(r.get("order_book_cr")),
                "OB/Rev":     fmt_ratio(ob_rev),
                "OB/MCap":    fmt_ratio(r.get("ob_marketcap_ratio")),
                "Rev Gr %":   fmt_pct(r.get("revenue_growth_pct")),
                "OB Score":   f"{score:.0f}/100",
            },
            what_missing = (
                "The market may be pricing based on current revenue run-rate rather than "
                "the embedded revenue visibility from the order book. If execution pace "
                "improves, consensus estimates could see material upgrades."
            ),
            risks = (
                "Order execution risk, margin pressure from large fixed-price contracts, "
                "receivables build-up, customer concentration."
            ),
            next_step  = "Verify order book composition, margin profile per segment, and receivables trend.",
            confidence = int(r.get("confidence_score", 50)),
            action     = "Research" if score >= 55 else "Watch",
            score      = score,
        ))

# ── Rule 2: OB > Market Cap ──────────────────────────────────────────────────
if "OB > Market Cap" in idea_types and not ob_df.empty:
    cands = ob_df[
        (ob_df.get("ob_marketcap_ratio", pd.Series(dtype=float)) >= 1.0) &
        (ob_df.get("confidence_score", pd.Series(dtype=float)) >= min_conf)
    ].copy()
    for _, r in cands.iterrows():
        score = r.get("ob_score", 0)
        ideas.append(_make_idea(
            ticker    = r.get("ticker",""),
            company   = r.get("company_name",""),
            sector    = r.get("sector",""),
            flag_type = "OB > Market Cap",
            reason    = (
                f"Order book ({fmt_cr(r.get('order_book_cr'))}) exceeds market cap "
                f"({fmt_cr(r.get('market_cap_cr'))}). OB/MCap = "
                f"{fmt_ratio(r.get('ob_marketcap_ratio'))}."
            ),
            metrics = {
                "Order Book":   fmt_cr(r.get("order_book_cr")),
                "Market Cap":   fmt_cr(r.get("market_cap_cr")),
                "OB/MCap":      fmt_ratio(r.get("ob_marketcap_ratio")),
                "EV/EBITDA":    fmt_ratio(r.get("peer_ev_ebitda")),
                "OB Score":     f"{score:.0f}/100",
            },
            what_missing = (
                "Extreme disconnect between current market cap and embedded order book value. "
                "Even a modest improvement in execution and margins could generate "
                "multi-year earnings visibility that market is not pricing."
            ),
            risks = "Execution risk, working capital intensity, government-dependent revenue.",
            next_step  = "Analyse execution track record over last 3 years and working capital efficiency.",
            confidence = int(r.get("confidence_score", 50)),
            action     = "Research",
            score      = score,
        ))

# ── Rule 3: Strong Inflows + Weak Price ──────────────────────────────────────
if "Strong Inflows + Weak Price" in idea_types and not ob_df.empty:
    merged = ob_df.copy()
    if not uni_df.empty and "return_1y" in uni_df.columns:
        merged = merged.merge(
            uni_df[["ticker","return_1y"]].rename(columns={"return_1y":"price_ret_1y"}),
            on="ticker", how="left",
        )
    if "order_inflow_growth_pct" in merged.columns:
        ret_col = "price_ret_1y" if "price_ret_1y" in merged.columns else None
        if ret_col:
            cands = merged[
                (merged["order_inflow_growth_pct"] >= 20) &
                (merged[ret_col] < -0.10) &
                (merged.get("confidence_score", pd.Series(50, index=merged.index)) >= min_conf)
            ]
            for _, r in cands.iterrows():
                score = r.get("ob_score", 0)
                ideas.append(_make_idea(
                    ticker    = r.get("ticker",""),
                    company   = r.get("company_name",""),
                    sector    = r.get("sector",""),
                    flag_type = "Strong Inflows + Weak Price",
                    reason    = (
                        f"Order inflows growing {fmt_pct(r.get('order_inflow_growth_pct'))} YoY "
                        f"while stock is down {fmt_pct((r.get('price_ret_1y',0) or 0)*100)} in 1Y. "
                        "Potential divergence between fundamentals and price."
                    ),
                    metrics = {
                        "Inflow Gr":  fmt_pct(r.get("order_inflow_growth_pct")),
                        "OB/Rev":     fmt_ratio(r.get("ob_revenue_ratio")),
                        "1Y Return":  fmt_pct((r.get("price_ret_1y",0) or 0)*100),
                        "OB Score":   f"{score:.0f}/100",
                    },
                    what_missing = (
                        "Strong order inflow growth suggests business momentum is intact, "
                        "but the stock may be pricing in worst-case execution or macro fears. "
                        "Fundamental recovery + execution improvement could re-rate the stock."
                    ),
                    risks = "Earnings delivery risk, sector rotation, macro headwinds.",
                    next_step  = "Check recent concall for guidance and execution commentary.",
                    confidence = int(r.get("confidence_score", 50)),
                    action     = "Watch",
                    score      = score,
                ))

# ── Rule 4: High Score + Low Valuation ───────────────────────────────────────
if "High Score + Low Valuation" in idea_types and not ob_df.empty:
    cands = ob_df[
        (ob_df.get("ob_score", pd.Series(dtype=float)) >= 65) &
        (ob_df.get("ob_ev_ratio", pd.Series(dtype=float)) >= 0.7) &
        (ob_df.get("confidence_score", pd.Series(dtype=float)) >= min_conf)
    ]
    for _, r in cands.iterrows():
        score = r.get("ob_score", 0)
        ideas.append(_make_idea(
            ticker    = r.get("ticker",""),
            company   = r.get("company_name",""),
            sector    = r.get("sector",""),
            flag_type = "High Score + Low Valuation",
            reason    = (
                f"OB Score {score:.0f}/100 with OB/EV ratio of {fmt_ratio(r.get('ob_ev_ratio'))}. "
                f"Order book exceeds 70% of EV — indicating potential value embedded in backlog."
            ),
            metrics = {
                "OB Score":   f"{score:.0f}/100",
                "OB/EV":      fmt_ratio(r.get("ob_ev_ratio")),
                "OB/Rev":     fmt_ratio(r.get("ob_revenue_ratio")),
                "EV/EBITDA":  fmt_ratio(r.get("peer_ev_ebitda")),
            },
            what_missing = (
                "High-scoring company trading at a discount to peers on EV/EBITDA "
                "despite superior order book visibility. Potential re-rating as earnings upgrade cycle begins."
            ),
            risks = "Execution pace, margin normalisation, sector derating.",
            next_step  = "Build peer comparison table and DCF model.",
            confidence = int(r.get("confidence_score", 50)),
            action     = "Research",
            score      = score,
        ))

# ── Deduplicate ideas ─────────────────────────────────────────────────────────
seen_tickers: set = set()
unique_ideas = []
for idea in sorted(ideas, key=lambda x: (-(x.get("score") or 0), x["ticker"])):
    key = (idea["ticker"], idea["flag_type"])
    if key not in seen_tickers:
        seen_tickers.add(key)
        unique_ideas.append(idea)

# ── Summary KPIs ──────────────────────────────────────────────────────────────
section_label("Ideas Summary")
total  = len(unique_ideas)
n_res  = sum(1 for i in unique_ideas if i["action"] == "Research")
n_watch= sum(1 for i in unique_ideas if i["action"] == "Watch")
avg_sc = sum(i.get("score") or 0 for i in unique_ideas) / total if total else 0

kcols = st.columns(4)
kpi_data = [
    ("Total Ideas", str(total), ""),
    ("Research",    str(n_res),   "Actionable"),
    ("Watch",       str(n_watch), "Monitor"),
    ("Avg OB Score", f"{avg_sc:.0f}/100", ""),
]
for col, (l, v, s) in zip(kcols, kpi_data):
    with col:
        kpi_card(l, v, s)

st.markdown("<br>", unsafe_allow_html=True)

# ── Idea cards ────────────────────────────────────────────────────────────────
if not unique_ideas:
    if ob_df.empty:
        warn_block("Order book database is empty. Add companies in the Order Book Screener.")
    else:
        info_block("No ideas match current filters. Adjust thresholds in the sidebar.")
else:
    section_label(f"{total} Flagged Ideas")

    for idea in unique_ideas:
        score = idea.get("score") or 0
        action = idea.get("action", "Watch")
        card_cls = "hc" if score >= 70 else ("wl" if score >= 55 else "res")
        action_col = POS if action == "Research" else ACCENT if action == "Watch" else TEXT3

        metrics_html = "".join(
            f'<span class="idea-tag">{k}: {v}</span>'
            for k, v in idea["metrics"].items()
        )

        flag_badge_col = {
            "OB > 2x Revenue":                    "#2563eb",
            "OB > Market Cap":                    "#16a34a",
            "Strong Inflows + Weak Price":         "#d97706",
            "High Score + Low Valuation":          "#7c3aed",
            "Down >20% from High + Improving Fundamentals": "#0891b2",
        }.get(idea["flag_type"], "#475569")

        st.markdown(
            f"""<div class="idea-card {card_cls}">
              <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:0.4rem;">
                <div>
                  <span style="font-size:0.95rem;font-weight:600;color:#e2e8f0;">
                    {idea['ticker']}</span>
                  <span style="font-size:0.8rem;color:#64748b;margin-left:0.6rem;">
                    {idea['company']}</span>
                  <span style="font-size:0.72rem;color:#475569;margin-left:0.5rem;">
                    {idea['sector']}</span>
                </div>
                <div style="display:flex;gap:0.5rem;align-items:center;">
                  <span class="badge" style="background:#111827;border:1px solid {flag_badge_col};
                    color:{flag_badge_col};">{idea['flag_type']}</span>
                  <span class="badge" style="background:#111827;border:1px solid {action_col};
                    color:{action_col};">{action}</span>
                  {score_bar(score, width=60)}
                </div>
              </div>
              <div class="idea-body">
                <div style="margin-bottom:0.5rem;">{idea['reason']}</div>
                <div class="idea-grid">{metrics_html}</div>
                <div style="margin-top:0.6rem;display:grid;grid-template-columns:1fr 1fr;gap:0.5rem;">
                  <div>
                    <div style="font-size:0.62rem;color:#475569;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:0.2rem;">
                      What Market May Be Missing</div>
                    <div style="font-size:0.78rem;color:#94a3b8;">{idea['what_missing']}</div>
                  </div>
                  <div>
                    <div style="font-size:0.62rem;color:#475569;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:0.2rem;">
                      Key Risks</div>
                    <div style="font-size:0.78rem;color:#94a3b8;">{idea['risks']}</div>
                  </div>
                </div>
                <div style="margin-top:0.5rem;padding-top:0.4rem;border-top:1px solid #1e2d45;
                  display:flex;justify-content:space-between;align-items:center;">
                  <div style="font-size:0.75rem;color:#64748b;">
                    <span style="color:#475569;">Next Step:</span> {idea['next_step']}
                  </div>
                  <div style="font-size:0.7rem;color:#475569;font-family:'IBM Plex Mono',monospace;">
                    Confidence: {idea['confidence']}/100
                  </div>
                </div>
              </div>
            </div>""",
            unsafe_allow_html=True,
        )

# ── Recent order win news as quick ideas ─────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
section_label("Recent Order Wins from News Feed")

if not news_df.empty and "categories" in news_df.columns:
    order_news = news_df[
        news_df["categories"].astype(str).str.contains("order", case=False, na=False)
    ]
    if order_news.empty:
        info_block("No order win news in feed. Populate data/news.csv.")
    else:
        for _, row in order_news.head(5).iterrows():
            s = row.get("sentiment", "neutral")
            col_map = {"positive": "#22c55e", "negative": "#ef4444", "neutral": "#64748b"}
            c = col_map.get(str(s).lower(), "#64748b")
            st.markdown(
                f"""<div class="fil-row">
                      <div class="fil-time">{str(row.get('date',''))[:10]}</div>
                      <div class="fil-body">
                        <div class="fil-title">{row.get('headline','')}</div>
                        <div class="fil-meta">
                          {row.get('source','')} &nbsp;|&nbsp;
                          <span style="color:{c};">{str(s).upper()}</span>
                          &nbsp;|&nbsp; {row.get('tickers_mentioned','')}
                        </div>
                        <div class="fil-ai">{row.get('ai_summary','')}</div>
                      </div>
                    </div>""",
                unsafe_allow_html=True,
            )
else:
    info_block("Populate data/news.csv to see order win news here.")

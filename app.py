"""
India Public Markets Intelligence Terminal
──────────────────────────────────────────
Main entry point. Sets global page config and renders the home/landing screen.
"""

import streamlit as st
from datetime import datetime

st.set_page_config(
    page_title="India Markets Terminal",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)

from utils.formatting import inject_css
from utils.auth import require_password

inject_css()
require_password()

# ── Sidebar branding ──────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        """<div style="
            padding: 1.25rem 1rem 1rem;
            border-bottom: 1px solid #0f1929;
            margin-bottom: 0.75rem;
        ">
          <div style="
            font-size: 0.68rem; font-weight: 700; color: #1e3a5f;
            text-transform: uppercase; letter-spacing: 0.14em;
            margin-bottom: 0.25rem;
          ">India Markets Terminal</div>
          <div style="
            font-size: 0.72rem; color: #1a2840; letter-spacing: 0.01em;
          ">Institutional Research Platform</div>
          <div style="
            margin-top: 0.6rem; font-size: 0.62rem;
            font-family: 'IBM Plex Mono', monospace; color: #141e30;
          ">v1.0</div>
        </div>""",
        unsafe_allow_html=True,
    )

# ── Page header ───────────────────────────────────────────────────────────────
today = datetime.now()
day_str  = today.strftime("%A")
date_str = today.strftime("%d %B %Y")

st.markdown(
    f"""<div class="term-header">
          <div>
            <div class="term-title">India Public Markets<br>Intelligence Terminal</div>
            <div class="term-tagline">
              Institutional research platform for Indian listed equities
              &nbsp;&nbsp;&middot;&nbsp;&nbsp;
              {day_str}, {date_str}
            </div>
          </div>
          <div style="text-align:right;">
            <div class="status-dot" style="justify-content:flex-end;">System Online</div>
            <div style="
              font-family:'IBM Plex Mono',monospace; font-size:0.65rem;
              color: #141e30; margin-top: 0.4rem;
            ">{today.strftime("%H:%M IST")}</div>
          </div>
        </div>
        <div style="height:1px;background:linear-gradient(90deg,#1e2d45 0%,#0f1929 60%,transparent 100%);margin-bottom:1.75rem;"></div>
    """,
    unsafe_allow_html=True,
)

# ── Module grid ───────────────────────────────────────────────────────────────
MODULES = [
    {
        "title": "Market Command Center",
        "num":   "01",
        "desc":  "Daily market pulse — index snapshot, breadth, top movers, volume shocks, sector heatmap, and AI brief.",
        "tags":  ["Daily Driver", "Market Overview"],
    },
    {
        "title": "All Companies Database",
        "num":   "02",
        "desc":  "Nifty 500 universe with full return, valuation, fundamental, and institutional holding data.",
        "tags":  ["Screener", "Universe"],
    },
    {
        "title": "Order Book Mispricing Screener",
        "num":   "04",
        "desc":  "Core module. Proprietary 6-factor model scoring companies on order-book strength, execution quality, and valuation.",
        "tags":  ["Core Module", "Alpha Generation"],
        "primary": True,
        "primary_label": "Primary Investment Module",
    },
    {
        "title": "Company Detail Page",
        "num":   "03",
        "desc":  "Deep dive on individual companies — financials, valuation, peers, news, filings, AI note, and research notes.",
        "tags":  ["Deep Dive", "Research"],
    },
    {
        "title": "New Ideas Engine",
        "num":   "05",
        "desc":  "Automated flagging of stocks with OB > 2x revenue, strong inflows with weak price, and improving fundamentals.",
        "tags":  ["Ideas", "Alerts"],
    },
    {
        "title": "News & Filings",
        "num":   "06",
        "desc":  "NSE corporate announcements, order wins, and results — AI-classified by materiality and sentiment.",
        "tags":  ["News", "Filings"],
    },
    {
        "title": "Sector Intelligence",
        "num":   "07",
        "desc":  "Dedicated pages for 16 sectors — cycle position, key drivers, valuation comparison, and mispricing candidates.",
        "tags":  ["Sector", "Macro"],
    },
    {
        "title": "Settings & Data Management",
        "num":   "08",
        "desc":  "Configure API keys, email alerts, refresh data, manage universe, and run update scripts.",
        "tags":  ["Settings", "Admin"],
    },
]

cols = st.columns(2, gap="medium")

for i, mod in enumerate(MODULES):
    with cols[i % 2]:
        is_primary = mod.get("primary", False)
        primary_cls = "primary" if is_primary else ""
        num_cls     = "primary" if is_primary else ""
        name_cls    = "primary" if is_primary else ""

        tags_html = "".join(
            f'<span class="mod-tag">{t}</span>' for t in mod["tags"]
        )

        primary_badge = ""
        if is_primary:
            primary_badge = (
                '<span style="'
                'font-size:0.58rem;font-weight:700;text-transform:uppercase;'
                'letter-spacing:0.08em;color:#2563eb;'
                'background:rgba(37,99,235,0.1);border:1px solid #1e3a6b;'
                'border-radius:4px;padding:0.18rem 0.55rem;margin-left:0.6rem;'
                'vertical-align:middle;'
                '">Core Module</span>'
            )

        arrow_html = (
            '<span style="color:#1e3a5f;font-size:0.75rem;margin-left:auto;">→</span>'
            if is_primary else ""
        )

        st.markdown(
            f"""<div class="mod-card {primary_cls}">
                  <div class="mod-num {num_cls}" style="justify-content:space-between;">
                    <span>{mod['num']}</span>
                    {arrow_html}
                  </div>
                  <div class="mod-name {name_cls}">
                    {mod['title']}{primary_badge}
                  </div>
                  <div class="mod-desc">{mod['desc']}</div>
                  <div class="mod-tags">{tags_html}</div>
                </div>""",
            unsafe_allow_html=True,
        )

# ── Status bar ────────────────────────────────────────────────────────────────
from utils.data_loader import load_universe, load_order_book, load_fundamentals

@st.cache_data(ttl=60)
def _get_status():
    uni  = load_universe()
    ob   = load_order_book()
    fund = load_fundamentals()
    return len(uni), len(ob), len(fund)

n_uni, n_ob, n_fund = _get_status()

ob_verified = 0
try:
    import pandas as pd
    ob_df = load_order_book()
    if not ob_df.empty and "manually_verified" in ob_df.columns:
        ob_verified = int(ob_df["manually_verified"].astype(str).str.lower().isin(["true","1","yes"]).sum())
except Exception:
    pass

st.markdown(
    f"""<div class="data-bar">
          <div class="data-bar-item">
            <span>Universe</span>
            <span class="val">{n_uni} companies</span>
          </div>
          <span class="data-bar-sep">/</span>
          <div class="data-bar-item">
            <span>Order Book DB</span>
            <span class="val">{n_ob} entries</span>
            <span style="color:#166534;font-size:0.6rem;">&nbsp;({ob_verified} verified)</span>
          </div>
          <span class="data-bar-sep">/</span>
          <div class="data-bar-item">
            <span>Fundamentals</span>
            <span class="val">{n_fund} companies</span>
          </div>
          <span class="data-bar-sep">/</span>
          <div class="data-bar-item">
            <span>Data</span>
            <span class="val" style="color:#1e2d45;">india_terminal/data/</span>
          </div>
        </div>""",
    unsafe_allow_html=True,
)

st.markdown(
    """<div style="
        font-size:0.67rem; color:#1a2840; margin-top:0.5rem;
        font-family:'IBM Plex Mono',monospace; letter-spacing:0.02em;
    ">
      Use sidebar to navigate &nbsp;·&nbsp;
      Run <code style="color:#1e3a5f;background:none;padding:0;">scripts/update_prices.py --yf</code>
      to initialise price history &nbsp;·&nbsp;
      Configure Claude API key in Settings for AI features
    </div>""",
    unsafe_allow_html=True,
)

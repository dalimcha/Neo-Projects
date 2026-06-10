"""
India Public Markets Intelligence Terminal

Deployed entrypoint for the Streamlit multipage app.
Keep this file at repo root and point Streamlit Cloud to `app.py`.
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="India Markets Terminal",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)

from utils.auth import require_password
from utils.formatting import inject_css, page_header, section_label, kpi_card, info_block, warn_block
from utils.data_loader import (
    load_universe,
    load_returns_snapshot,
    load_fundamentals,
    load_data_quality_log,
    load_failed_tickers,
)
from utils.validation import build_universe_report, render_data_quality_panel


inject_css()
require_password()


def _latest_quality_status(log_df: pd.DataFrame, dataset: str = "prices") -> tuple[str | None, str | None]:
    if log_df.empty or "dataset" not in log_df.columns:
        return None, None
    sub = log_df[log_df["dataset"].astype(str) == dataset].copy()
    if sub.empty:
        return None, None
    if "last_refresh_at" in sub.columns:
        sub["last_refresh_at"] = pd.to_datetime(sub["last_refresh_at"], errors="coerce")
        sub = sub.sort_values("last_refresh_at")
    row = sub.iloc[-1]
    ts = row.get("last_refresh_at")
    ts_str = ts.strftime("%d %b %Y %H:%M") if pd.notna(ts) else None
    status = row.get("status")
    return status.title() if isinstance(status, str) else None, ts_str


def _latest_business_note(returns_df: pd.DataFrame) -> str:
    if returns_df.empty or "return_1d" not in returns_df.columns:
        return "No canonical returns snapshot loaded yet."
    ret = pd.to_numeric(returns_df["return_1d"], errors="coerce").dropna()
    if ret.empty:
        return "Returns snapshot exists, but no valid 1D return values are available."
    adv = int((ret > 0).sum())
    dec = int((ret < 0).sum())
    avg = ret.mean() * 100
    return f"Breadth currently shows {adv} advancers vs {dec} decliners, with average 1D move {avg:+.2f}%."


quality_log_df = load_data_quality_log()
universe_df = load_universe()
returns_df = load_returns_snapshot()
fund_df = load_fundamentals()
failed_df = load_failed_tickers()

report = build_universe_report(
    universe_label="Nifty 500",
    universe_df=universe_df,
    prices_df=returns_df.rename(columns={"price": "close"}),
    fundamentals_df=fund_df,
    failed_tickers=failed_df["ticker"].tolist() if not failed_df.empty and "ticker" in failed_df.columns else [],
    source_prices="returns_snapshot.csv",
    source_fundamentals="fundamentals.csv",
    source_news="filings.csv / news.csv",
)

status, ts = _latest_quality_status(quality_log_df, "prices")
page_header(
    "India Public Markets Intelligence Terminal",
    "Production entrypoint for the institutional tracker",
    data_status=status or report.fetch_status,
    data_ts=ts,
)

with st.sidebar:
    st.markdown(
        """
        <div style="padding:1rem 0.75rem 0.9rem;border-bottom:1px solid #0f1929;margin-bottom:0.75rem;">
          <div style="font-size:0.68rem;font-weight:700;color:#1e3a5f;text-transform:uppercase;letter-spacing:0.14em;">India Markets Terminal</div>
          <div style="font-size:0.72rem;color:#3d5270;margin-top:0.2rem;">Deployment target: repo root <code>app.py</code></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

section_label("Control Center")
render_data_quality_panel(report, compact=False)

cols = st.columns(4)
kpis = [
    ("Universe", f"{len(universe_df)}", "loaded tickers"),
    ("Valid Prices", f"{report.valid_price_rows}", "latest rows"),
    ("Fundamentals", f"{len(fund_df)}", "companies covered"),
    ("Snapshot Rows", f"{len(returns_df)}", "canonical rows"),
]
for col, (label, value, delta) in zip(cols, kpis):
    with col:
        kpi_card(label, value, delta)

st.markdown("<br>", unsafe_allow_html=True)

st.markdown(
    f"""
    <div class="surface">
      <div class="surface-title">Terminal Focus</div>
      <div class="surface-note">
        This system is now centered on three operational loops: daily market breadth and movers,
        event intelligence from filings and news, and a denser all-companies research grid for
        meeting preparation. Design density is being raised alongside data coverage, not ahead of it.
      </div>
      <div class="mini-grid" style="margin-top:0.85rem;">
        <div class="mini-stat">
          <div class="mini-stat-k">Universe</div>
          <div class="mini-stat-v">{len(universe_df)}</div>
          <div class="mini-stat-s">listed companies tracked</div>
        </div>
        <div class="mini-stat">
          <div class="mini-stat-k">Snapshot</div>
          <div class="mini-stat-v">{len(returns_df)}</div>
          <div class="mini-stat-s">canonical price rows</div>
        </div>
        <div class="mini-stat">
          <div class="mini-stat-k">Fundamentals</div>
          <div class="mini-stat-v">{len(fund_df)}</div>
          <div class="mini-stat-s">currently populated</div>
        </div>
        <div class="mini-stat">
          <div class="mini-stat-k">Status</div>
          <div class="mini-stat-v">{status or report.fetch_status}</div>
          <div class="mini-stat-s">{ts or 'timestamp unavailable'}</div>
        </div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

left, right = st.columns([1.2, 1.0], gap="large")

with left:
    section_label("Start Here")
    st.page_link("pages/1_Market_Command_Center.py", label="Open Market Command Center", icon=":material/monitoring:")
    st.page_link("pages/9_Data_Quality.py", label="Open Data Quality", icon=":material/fact_check:")
    st.page_link("pages/2_All_Companies.py", label="Open All Companies", icon=":material/table_view:")
    st.page_link("pages/6_News_and_Filings.py", label="Open News & Filings", icon=":material/feed:")

    section_label("What This App Is Using")
    st.markdown(
        """
        <div class="surface">
          <div class="surface-note">
            Canonical prices come from <code>data/returns_snapshot.csv</code>. Sector analytics use
            <code>data/sector_performance.csv</code>. Volume moves use <code>data/volume_shocks.csv</code>.
            Refresh monitoring uses <code>data/data_quality_log.csv</code>. The deployed entrypoint remains
            repo-root <code>app.py</code>.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with right:
    section_label("Operational Note")
    note = _latest_business_note(returns_df)
    if report.passes:
        info_block(
            f"{note} The tracker is using the Phase 1 canonical datasets. "
            "Next build priority is the All Companies screener and fundamentals ingestion."
        )
    else:
        warn_block(
            f"{note} The tracker is not yet trustworthy for downstream analytics because data quality gates are not passing."
        )

section_label("Immediate Next Build")
st.markdown(
    """
    <div class="surface">
      <div class="surface-title">Immediate Next Build</div>
      <div class="surface-note">
        1. Finish the event layer so biggest stock and sector movers always carry context.<br>
        2. Harden the all-companies research grid around merged returns, fundamentals, and filing metadata.<br>
        3. Import real fundamentals coverage from Screener, Trendlyne, or Bloomberg exports.<br>
        4. Keep pushing density and visual hierarchy once the data surface is materially richer.
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

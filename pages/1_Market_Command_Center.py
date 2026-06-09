"""
Market Command Center
─────────────────────
Daily market pulse: index snapshot, breadth, top movers,
volume shocks, 52W extremes, sector heatmap, AI brief.
"""

import streamlit as st
import pandas as pd
from datetime import datetime, date

st.set_page_config(
    page_title="Market Command Center — India Terminal",
    layout="wide", initial_sidebar_state="expanded",
)

from utils.formatting import (
    inject_css, page_header, section_label, kpi_card, index_card,
    fmt_pct, fmt_price, fmt_cr, fmt_vol, html_pct, table_wrap, ai_box,
    info_block, warn_block, score_bar,
)
from utils.data_loader import (
    load_full_universe, get_top_movers, get_volume_shocks,
    get_52w_extremes, get_sector_summary, load_filings, load_news,
)
from utils.nse_fetcher import fetch_index_snapshot, fetch_bhavcopy
from utils.charting import sector_heatmap, _empty_chart
import utils.ai_summarizer as ai

inject_css()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="sec-label">Filters</div>', unsafe_allow_html=True)
    index_filter = st.selectbox(
        "Index Universe",
        ["Nifty 500", "Nifty 50", "Nifty Next 50", "All"],
        index=0,
    )
    n_movers = st.slider("Movers to Show", 5, 20, 10)
    st.markdown("---")
    refresh = st.button("Refresh Data")

page_header("Market Command Center", "Live market pulse and daily brief")

# ── Index Snapshot ────────────────────────────────────────────────────────────
section_label("Index Snapshot")

with st.spinner("Fetching index data…"):
    try:
        indices = fetch_index_snapshot()
    except Exception:
        indices = {}

INDEX_CONFIG = [
    ("nifty50",    "Nifty 50"),
    ("niftyNext50","Nifty Next 50"),
    ("nifty500",   "Nifty 500"),
    ("bankNifty",  "Bank Nifty"),
    ("vix",        "India VIX"),
    ("sensex",     "Sensex"),
]

idx_cols = st.columns(len(INDEX_CONFIG))
for col, (key, label) in zip(idx_cols, INDEX_CONFIG):
    with col:
        if key in indices:
            d = indices[key]
            val = d["value"]
            chg = d["change_pct"]
            pts = d["change"]
            is_up = None if key == "vix" else (chg >= 0)
            index_card(
                name=label,
                value=f"{val:,.2f}",
                change=f"{chg:+.2f}%",
                pts=f"({pts:+.0f})",
                is_up=is_up,
            )
        else:
            index_card(label, "—", "—", "", None)

st.markdown("<br>", unsafe_allow_html=True)

# ── Breadth KPIs ──────────────────────────────────────────────────────────────
section_label("Market Breadth")

@st.cache_data(ttl=300)
def _get_universe():
    return load_full_universe()

df = _get_universe()

# Apply index filter
if not df.empty and "index_membership" in df.columns and index_filter != "All":
    df = df[df["index_membership"].str.contains(index_filter.replace(" ",""), na=False)]

if not df.empty and "return_1d" in df.columns:
    d_col = df["return_1d"].dropna()
    advancers  = (d_col > 0).sum()
    decliners  = (d_col < 0).sum()
    unchanged  = (d_col == 0).sum()
    avg_ret    = d_col.mean() * 100
    ad_ratio   = advancers / decliners if decliners > 0 else float("inf")
    n_52h = (df.get("dist_52w_high_pct", pd.Series(dtype=float)).abs() < 3).sum() if "dist_52w_high_pct" in df.columns else 0
    n_52l = (df.get("dist_52w_low_pct", pd.Series(dtype=float)).abs() < 3).sum() if "dist_52w_low_pct" in df.columns else 0
else:
    advancers = decliners = unchanged = n_52h = n_52l = 0
    avg_ret = ad_ratio = 0.0

kpi_cols = st.columns(6)
kpi_data = [
    ("Advancers",      str(advancers),             f"{advancers/(advancers+decliners+1)*100:.0f}% of universe",  True  if advancers > decliners else None),
    ("Decliners",      str(decliners),             "",                                                            False if advancers > decliners else None),
    ("A/D Ratio",      f"{ad_ratio:.2f}x",         "Advancers ÷ Decliners",                                       ad_ratio >= 1),
    ("Avg 1D Return",  fmt_pct(avg_ret),           "",                                                            avg_ret >= 0),
    ("Near 52W High",  str(n_52h),                 "Within 3% of 52W high",                                       None),
    ("Near 52W Low",   str(n_52l),                 "Within 3% of 52W low",                                        None),
]
for col, (lbl, val, sub, pos) in zip(kpi_cols, kpi_data):
    with col:
        kpi_card(lbl, val, sub, delta_pos=pos)

st.markdown("<br>", unsafe_allow_html=True)

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "Top Movers", "Volume Shocks", "52W Extremes",
    "Sector Heatmap", "AI Market Brief", "What Changed Today",
])

# ── TAB 1: Top Movers ─────────────────────────────────────────────────────────
with tab1:
    col_g, col_l = st.columns(2)

    def _movers_table(direction: str, title: str) -> None:
        section_label(title)
        if df.empty or "return_1d" not in df.columns:
            info_block("Price data not yet loaded. Run scripts/update_prices.py to populate.")
            return

        sub = df.dropna(subset=["return_1d"])
        if direction == "gainers":
            sub = sub.nlargest(n_movers, "return_1d")
        else:
            sub = sub.nsmallest(n_movers, "return_1d")

        rows = ""
        for _, r in sub.iterrows():
            ret = r.get("return_1d", 0) or 0
            cls = "pos" if ret > 0 else "neg"
            rows += (
                f"<tr>"
                f"<td class='ticker'>{r.get('ticker','')}</td>"
                f"<td class='name'>{r.get('company_name','')}</td>"
                f"<td>{r.get('sector','')}</td>"
                f"<td>{fmt_price(r.get('close', r.get('price','')))}</td>"
                f"<td class='{cls}'>{fmt_pct(ret*100 if abs(ret)<10 else ret)}</td>"
                f"<td>{fmt_vol(r.get('volume',''))}</td>"
                f"</tr>"
            )
        table_wrap(
            f"""<table class='trm'>
                <thead><tr>
                  <th class='left'>Ticker</th><th class='left'>Company</th>
                  <th class='left'>Sector</th><th>Price</th>
                  <th>1D %</th><th>Volume</th>
                </tr></thead>
                <tbody>{rows}</tbody>
              </table>""",
        )

    with col_g:
        _movers_table("gainers", "Top Gainers")
    with col_l:
        _movers_table("losers", "Top Losers")

# ── TAB 2: Volume Shocks ──────────────────────────────────────────────────────
with tab2:
    section_label("Volume Shocks — Unusual Activity")
    if df.empty or "volume" not in df.columns:
        info_block("Volume data not available. Requires NSE bhavcopy data.")
    else:
        vol_df = df.dropna(subset=["volume"]).nlargest(n_movers * 2, "volume")

        rows = ""
        for _, r in vol_df.iterrows():
            ret = r.get("return_1d", 0) or 0
            cls = "pos" if ret > 0 else "neg"
            vol_ratio = r.get("volume_ratio_20d", "—")
            vol_ratio_str = f"{vol_ratio:.1f}x" if isinstance(vol_ratio, (int, float)) else "—"
            rows += (
                f"<tr>"
                f"<td class='ticker'>{r.get('ticker','')}</td>"
                f"<td class='name'>{r.get('company_name','')}</td>"
                f"<td>{r.get('sector','')}</td>"
                f"<td>{fmt_price(r.get('close', r.get('price','')))}</td>"
                f"<td class='{cls}'>{fmt_pct(ret*100 if abs(ret)<10 else ret)}</td>"
                f"<td>{fmt_vol(r.get('volume',''))}</td>"
                f"<td>{vol_ratio_str}</td>"
                f"</tr>"
            )
        table_wrap(
            f"""<table class='trm'>
                <thead><tr>
                  <th class='left'>Ticker</th><th class='left'>Company</th>
                  <th class='left'>Sector</th><th>Price</th>
                  <th>1D %</th><th>Volume</th><th>Vol/20D Avg</th>
                </tr></thead>
                <tbody>{rows}</tbody>
              </table>""",
        )

# ── TAB 3: 52W Extremes ───────────────────────────────────────────────────────
with tab3:
    col_h, col_l = st.columns(2)
    extremes = get_52w_extremes()

    def _52w_table(data: pd.DataFrame, title: str, col_label: str) -> None:
        section_label(title)
        if data.empty:
            info_block("52W data not available. Requires price history.")
            return
        metric = "dist_52w_high_pct" if "High" in title else "dist_52w_low_pct"
        rows = ""
        for _, r in data.head(15).iterrows():
            d = r.get(metric, 0) or 0
            rows += (
                f"<tr>"
                f"<td class='ticker'>{r.get('ticker','')}</td>"
                f"<td class='name'>{r.get('company_name','')}</td>"
                f"<td>{fmt_price(r.get('close', r.get('price','')))}</td>"
                f"<td class='{'pos' if 'Low' in title else 'neg'}'>{fmt_pct(d)}</td>"
                f"</tr>"
            )
        table_wrap(
            f"""<table class='trm'>
                <thead><tr>
                  <th class='left'>Ticker</th><th class='left'>Company</th>
                  <th>Price</th><th>{col_label}</th>
                </tr></thead>
                <tbody>{rows}</tbody>
              </table>""",
        )

    with col_h:
        _52w_table(extremes["near_high"], "Near 52-Week High", "Dist from High")
    with col_l:
        _52w_table(extremes["near_low"],  "Near 52-Week Low",  "Dist from Low")

# ── TAB 4: Sector Heatmap ─────────────────────────────────────────────────────
with tab4:
    section_label("Sector Performance Heatmap")
    period = st.selectbox(
        "Return Period",
        ["return_1d", "return_1w", "return_1m", "return_3m", "return_1y"],
        format_func=lambda x: {"return_1d":"1 Day","return_1w":"1 Week",
                                "return_1m":"1 Month","return_3m":"3 Month",
                                "return_1y":"1 Year"}.get(x, x),
        key="heatmap_period",
    )
    sec_df = get_sector_summary()
    if not sec_df.empty and period in sec_df.columns:
        sec_df[period] = sec_df[period] * 100 if sec_df[period].abs().max() < 2 else sec_df[period]
        fig = sector_heatmap(sec_df, metric=period)
        st.plotly_chart(fig, use_container_width=True)

        # Sector table
        display_cols = ["sector", period, "num_stocks"]
        if "market_cap_cr" in sec_df.columns:
            display_cols.append("market_cap_cr")
        disp = sec_df[display_cols].sort_values(period, ascending=False).copy()
        disp.columns = ["Sector", "Return %", "# Stocks"] + (["Market Cap (Cr)"] if "market_cap_cr" in sec_df.columns else [])
        rows = ""
        for _, r in disp.iterrows():
            ret = r.iloc[1]
            cls = "pos" if ret > 0 else "neg"
            mcap = f"₹{r.iloc[3]/1e5:.1f}L Cr" if len(r) > 3 else "—"
            rows += (
                f"<tr>"
                f"<td class='left' style='color:#cbd5e1;'>{r.iloc[0]}</td>"
                f"<td class='{cls}'>{ret:+.2f}%</td>"
                f"<td>{r.iloc[2]:.0f}</td>"
                f"<td>{mcap}</td>"
                f"</tr>"
            )
        table_wrap(
            f"""<table class='trm'>
                <thead><tr>
                  <th class='left'>Sector</th><th>Return</th>
                  <th>Stocks</th><th>Mkt Cap</th>
                </tr></thead>
                <tbody>{rows}</tbody>
              </table>""",
            caption="Sector summary",
        )
    else:
        info_block("Sector data not available. Ensure universe.csv and prices.csv are populated.")

# ── TAB 5: AI Market Brief ────────────────────────────────────────────────────
with tab5:
    section_label("AI-Generated Market Summary")

    if not df.empty and "return_1d" in df.columns:
        d_col = df["return_1d"].dropna()
        gainers_list = df.nlargest(5, "return_1d")["ticker"].tolist() if not df.empty else []
        losers_list  = df.nsmallest(5, "return_1d")["ticker"].tolist() if not df.empty else []
        sec_summary  = {}
        if not sec_df.empty and "return_1d" in sec_df.columns:
            sec_summary = dict(zip(sec_df["sector"], sec_df["return_1d"].round(2)))

        market_data = {
            "nifty50_change": indices.get("nifty50", {}).get("change_pct", "N/A"),
            "advancers":      int(advancers),
            "decliners":      int(decliners),
            "top_gainers":    gainers_list,
            "top_losers":     losers_list,
            "sector_moves":   sec_summary,
        }

        if st.button("Generate AI Market Summary"):
            with st.spinner("Generating summary via Claude…"):
                summary = ai.generate_market_summary(market_data)
            ai_box(summary, "AI Market Summary")
        else:
            ai_box(
                "Click 'Generate AI Market Summary' to get an AI-written market brief. "
                "Requires ANTHROPIC_API_KEY in Settings.",
                "AI Market Summary"
            )
    else:
        warn_block("Load price data first to enable AI market summaries.")

# ── TAB 6: What Changed Today ─────────────────────────────────────────────────
with tab6:
    section_label("What Changed Today")

    filings = load_filings()
    news    = load_news()

    # Recent filings
    section_label("Corporate Filings — Last 48 Hours")
    if filings.empty:
        info_block("No filings loaded. Run scripts/update_filings.py to populate.")
    else:
        recent = filings.head(10)
        for _, row in recent.iterrows():
            sentiment = row.get("sentiment", "neutral")
            stype = row.get("type", "Filing")
            col_map = {"positive": "#22c55e", "negative": "#ef4444", "neutral": "#64748b"}
            col = col_map.get(str(sentiment).lower(), "#64748b")
            ai_sum = row.get("ai_summary", "")
            ai_html = f'<div class="fil-ai">{ai_sum}</div>' if ai_sum else ""
            st.markdown(
                f"""<div class="fil-row">
                      <div class="fil-time">{str(row.get('date',''))[:10]}</div>
                      <div class="fil-body">
                        <div class="fil-title">
                          <span style="color:#3b82f6;font-weight:600;">{row.get('ticker','')}</span>
                          &nbsp;—&nbsp;{row.get('subject','')}
                        </div>
                        <div class="fil-meta">
                          <span style="color:{col};">{str(sentiment).upper()}</span>
                          &nbsp;|&nbsp;{stype}
                          {' &nbsp;|&nbsp; <span style="color:#f59e0b;">MATERIAL</span>' if row.get('is_material') else ''}
                        </div>
                        {ai_html}
                      </div>
                    </div>""",
                unsafe_allow_html=True,
            )

    st.markdown("<br>", unsafe_allow_html=True)
    section_label("Key News — Last 48 Hours")
    if news.empty:
        info_block("No news loaded. Populate data/news.csv.")
    else:
        for _, row in news.head(8).iterrows():
            stype = row.get("sentiment", "neutral")
            col_map = {"positive": "#22c55e", "negative": "#ef4444", "neutral": "#64748b"}
            col = col_map.get(str(stype).lower(), "#64748b")
            st.markdown(
                f"""<div class="fil-row">
                      <div class="fil-time">{str(row.get('date',''))[:10]}</div>
                      <div class="fil-body">
                        <div class="fil-title">{row.get('headline','')}</div>
                        <div class="fil-meta">
                          {row.get('source','')} &nbsp;|&nbsp;
                          <span style="color:{col};">{str(stype).upper()}</span>
                          &nbsp;|&nbsp; {row.get('sector','')}
                        </div>
                        <div class="fil-ai">{row.get('ai_summary','')}</div>
                      </div>
                    </div>""",
                unsafe_allow_html=True,
            )

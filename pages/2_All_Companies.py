"""
All Companies Database
──────────────────────
Full Nifty 500 universe with sortable columns for returns,
valuations, fundamentals, and holdings.
"""

import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(
    page_title="All Companies — India Terminal",
    layout="wide", initial_sidebar_state="expanded",
)

from utils.formatting import (
    inject_css, page_header, section_label, fmt_pct, fmt_price,
    fmt_cr, fmt_ratio, style_pct_col, base_table_style, info_block,
    warn_block, POS, NEG, ACCENT, TEXT3, BORDER, BG2,
)
from utils.data_loader import load_full_universe, load_universe

inject_css()

# ── Load data ─────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def _load():
    return load_full_universe()

df = _load()

# ── Sidebar filters ───────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="sec-label">Filters</div>', unsafe_allow_html=True)

    sectors = ["All Sectors"]
    if not df.empty and "sector" in df.columns:
        sectors += sorted(df["sector"].dropna().unique().tolist())
    sector_f = st.selectbox("Sector", sectors)

    index_opts = ["All", "Nifty50", "NiftyNext50", "Nifty500"]
    index_f = st.selectbox("Index", index_opts)

    mcap_opts = ["All", ">1L Cr (Large)", ">10K Cr (Mid)", ">2K Cr (Small)"]
    mcap_f = st.selectbox("Market Cap", mcap_opts)

    st.markdown("---")
    st.markdown('<div class="sec-label">Return Filters</div>', unsafe_allow_html=True)
    ret1y_min = st.slider("Min 1Y Return %", -100, 200, -100)
    ret1y_max = st.slider("Max 1Y Return %", -100, 300, 300)

    st.markdown("---")
    sort_col = st.selectbox(
        "Sort by",
        ["return_1d","return_1w","return_1m","return_3m","return_6m","return_1y",
         "market_cap_cr","pe","roe","revenue_growth_1y"],
        index=5,
    )
    sort_asc = st.checkbox("Ascending", value=False)

    st.markdown("---")
    show_cols = st.multiselect(
        "Column Groups",
        ["Returns", "Valuations", "Fundamentals", "Holdings"],
        default=["Returns", "Valuations"],
    )

page_header("All Companies Database", f"{len(df)} companies loaded")

# ── Apply filters ─────────────────────────────────────────────────────────────
fdf = df.copy()

if sector_f != "All Sectors" and "sector" in fdf.columns:
    fdf = fdf[fdf["sector"] == sector_f]

if index_f != "All" and "index_membership" in fdf.columns:
    fdf = fdf[fdf["index_membership"].str.contains(index_f, na=False)]

if "market_cap_cr" in fdf.columns:
    if mcap_f == ">1L Cr (Large)":
        fdf = fdf[fdf["market_cap_cr"] >= 100000]
    elif mcap_f == ">10K Cr (Mid)":
        fdf = fdf[fdf["market_cap_cr"] >= 10000]
    elif mcap_f == ">2K Cr (Small)":
        fdf = fdf[fdf["market_cap_cr"] >= 2000]

if "return_1y" in fdf.columns:
    ret1y = fdf["return_1y"]
    # Handle both decimal (0.25) and percentage (25) format
    if ret1y.dropna().abs().max() <= 5:
        ret1y = ret1y * 100
    fdf = fdf[(ret1y >= ret1y_min) & (ret1y <= ret1y_max)]

if sort_col in fdf.columns:
    fdf = fdf.sort_values(sort_col, ascending=sort_asc)

# ── Build display DataFrame ───────────────────────────────────────────────────
RETURN_COLS  = ["return_1d","return_1w","return_1m","return_3m","return_6m","return_1y",
                "dist_52w_high_pct","dist_52w_low_pct"]
VALUATION_COLS = ["pe","ev_ebitda","pb","ps","roe","roce","debt_equity"]
FUNDAMENTAL_COLS = ["revenue_growth_1y","ebitda_margin","pat_margin","pat_growth_1y"]
HOLDING_COLS = ["promoter_holding","fii_holding","dii_holding"]

base_cols = ["ticker","company_name","sector"]
if "market_cap_cr" in fdf.columns:
    base_cols.append("market_cap_cr")
if "close" in fdf.columns:
    base_cols.append("close")
elif "price" in fdf.columns:
    base_cols.append("price")

selected_cols = base_cols[:]
if "Returns" in show_cols:
    selected_cols += [c for c in RETURN_COLS if c in fdf.columns]
if "Valuations" in show_cols:
    selected_cols += [c for c in VALUATION_COLS if c in fdf.columns]
if "Fundamentals" in show_cols:
    selected_cols += [c for c in FUNDAMENTAL_COLS if c in fdf.columns]
if "Holdings" in show_cols:
    selected_cols += [c for c in HOLDING_COLS if c in fdf.columns]

# Deduplicate while preserving order
seen = set()
final_cols = [c for c in selected_cols if c not in seen and not seen.add(c)]
display = fdf[[c for c in final_cols if c in fdf.columns]].copy()

# ── Format for display ────────────────────────────────────────────────────────
RENAME = {
    "ticker": "Ticker", "company_name": "Company", "sector": "Sector",
    "market_cap_cr": "MCap (Cr)", "close": "Price", "price": "Price",
    "return_1d": "1D %", "return_1w": "1W %", "return_1m": "1M %",
    "return_3m": "3M %", "return_6m": "6M %", "return_1y": "1Y %",
    "dist_52w_high_pct": "52W Hi Dist", "dist_52w_low_pct": "52W Lo Dist",
    "pe": "P/E", "ev_ebitda": "EV/EBITDA", "pb": "P/B", "ps": "P/S",
    "roe": "ROE %", "roce": "ROCE %", "debt_equity": "D/E",
    "revenue_growth_1y": "Rev Gr %", "ebitda_margin": "EBITDA Mg",
    "pat_margin": "PAT Mg", "pat_growth_1y": "PAT Gr %",
    "promoter_holding": "Promoter", "fii_holding": "FII", "dii_holding": "DII",
}

display = display.rename(columns={k: v for k, v in RENAME.items() if k in display.columns})

# Normalise return columns to percentage
RET_DISPLAY = ["1D %","1W %","1M %","3M %","6M %","1Y %","52W Hi Dist","52W Lo Dist",
               "Rev Gr %","ROE %","ROCE %","EBITDA Mg","PAT Mg","PAT Gr %",
               "Promoter","FII","DII"]
for col in RET_DISPLAY:
    if col in display.columns:
        vals = pd.to_numeric(display[col], errors="coerce")
        if vals.dropna().abs().max() < 5:
            display[col] = vals * 100

# Summary row
st.markdown(
    f'<div style="font-size:0.72rem;color:#475569;margin-bottom:0.75rem;">'
    f'Showing <span style="color:#e2e8f0;font-weight:600;">{len(fdf)}</span> companies'
    f' &nbsp;|&nbsp; Sorted by <span style="color:#3b82f6;">{sort_col}</span>'
    f'</div>',
    unsafe_allow_html=True,
)

# ── Styled dataframe ──────────────────────────────────────────────────────────
if display.empty:
    info_block("No companies match the current filters.")
else:
    # Build styler
    def _color_cell(val):
        try:
            v = float(val)
            if v > 3:    return f"color:{POS}"
            if v > 0:    return f"color:#86efac"
            if v < -3:   return f"color:{NEG}"
            if v < 0:    return f"color:#fca5a5"
            return f"color:{TEXT3}"
        except (TypeError, ValueError):
            return ""

    style = base_table_style(display)

    pct_cols = [c for c in display.columns if c in RET_DISPLAY]
    for col in pct_cols:
        style = style.map(_color_cell, subset=[col])

    fmt_dict = {}
    for col in display.columns:
        if col in ["MCap (Cr)"]:
            fmt_dict[col] = lambda v: f"₹{v:,.0f}" if pd.notna(v) else "—"
        elif col == "Price":
            fmt_dict[col] = lambda v: f"₹{v:,.2f}" if pd.notna(v) else "—"
        elif col in pct_cols:
            fmt_dict[col] = lambda v: f"{v:+.1f}%" if pd.notna(v) else "—"
        elif col in ["P/E","EV/EBITDA","P/B","P/S","D/E"]:
            fmt_dict[col] = lambda v: f"{v:.1f}x" if pd.notna(v) else "—"

    try:
        styled = style.format(fmt_dict, na_rep="—")
        st.dataframe(styled, width="stretch", height=600)
    except Exception:
        st.dataframe(display, width="stretch", height=600)

    # ── Export ────────────────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2 = st.columns([1, 5])
    with col1:
        csv = display.to_csv(index=False)
        st.download_button(
            "Export CSV",
            data=csv,
            file_name=f"india_terminal_companies_{pd.Timestamp.today().date()}.csv",
            mime="text/csv",
        )

# ── Sector Summary ────────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
section_label("Sector Distribution")

if not df.empty and "sector" in df.columns:
    sec_counts = df["sector"].value_counts().reset_index()
    sec_counts.columns = ["Sector", "Count"]
    if "market_cap_cr" in df.columns:
        sec_mcap = df.groupby("sector")["market_cap_cr"].sum().reset_index()
        sec_mcap.columns = ["Sector", "Total MCap (Cr)"]
        sec_counts = sec_counts.merge(sec_mcap, on="Sector", how="left")

    rows = ""
    for _, r in sec_counts.iterrows():
        mcap_str = f"₹{r['Total MCap (Cr)']/1e5:.1f}L Cr" if "Total MCap (Cr)" in r and pd.notna(r["Total MCap (Cr)"]) else "—"
        rows += (
            f"<tr>"
            f"<td class='left' style='color:#cbd5e1;'>{r['Sector']}</td>"
            f"<td>{r['Count']}</td>"
            f"<td>{mcap_str}</td>"
            f"</tr>"
        )

    from utils.formatting import table_wrap
    table_wrap(
        f"""<table class='trm'>
            <thead><tr>
              <th class='left'>Sector</th><th>Companies</th><th>Market Cap</th>
            </tr></thead>
            <tbody>{rows}</tbody>
          </table>""",
        caption="Sector breakdown",
    )

from __future__ import annotations

import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Return Quartiles — India Terminal",
    layout="wide",
    initial_sidebar_state="expanded",
)

from utils.formatting import inject_css, page_header, section_label, kpi_card, info_block, warn_block, html_block
from utils.data_loader import load_full_universe


inject_css()


PERIODS = ["1M", "3M", "6M", "1Y", "3Y", "5Y", "10Y"]
QMAP = {
    "1M": "quartile_1m",
    "3M": "quartile_3m",
    "6M": "quartile_6m",
    "1Y": "quartile_1y",
    "3Y": "quartile_3y",
    "5Y": "quartile_5y",
    "10Y": "quartile_10y",
}
RMAP = {
    "1M": "return_1m",
    "3M": "return_3m",
    "6M": "return_6m",
    "1Y": "return_1y",
    "3Y": "return_3y",
    "5Y": "return_5y",
    "10Y": "return_10y",
}


@st.cache_data(ttl=300)
def _load() -> pd.DataFrame:
    return load_full_universe()


df = _load()

page_header("", "")

if df.empty:
    warn_block("No merged universe available. Refresh prices first.")
    st.stop()

with st.sidebar:
    html_block('<div class="sec-label">Quartile Filters</div>')
    sectors = ["All"] + sorted(df["sector"].dropna().astype(str).unique().tolist()) if "sector" in df.columns else ["All"]
    sector_f = st.selectbox("Sector", sectors)
    drill_period = st.selectbox("Drilldown Period", PERIODS, index=3)
    drill_quartile = st.selectbox("Drilldown Quartile", ["Q1", "Q2", "Q3", "Q4"], index=0)
    transition_left = st.selectbox("Transition A", PERIODS, index=0)
    transition_right = st.selectbox("Transition B", PERIODS, index=1)

fdf = df.copy()
if sector_f != "All" and "sector" in fdf.columns:
    fdf = fdf[fdf["sector"] == sector_f]

html_block(
    """
    <div class="hero-panel">
      <div class="hero-sub" style="text-transform:uppercase;letter-spacing:0.10em;font-size:0.62rem;">Return Quartiles</div>
      <div class="hero-title">Relative Performance Matrix</div>
    </div>
    """
)

section_label("Matrix")
matrix = []
for period in PERIODS:
    qcol = QMAP[period]
    row = {"Period": period}
    for q in ["Q1", "Q2", "Q3", "Q4"]:
        row[q] = int((fdf.get(qcol) == q).sum()) if qcol in fdf.columns else 0
    matrix.append(row)
matrix_df = pd.DataFrame(matrix)
st.dataframe(matrix_df.set_index("Period"), width="stretch")

cols = st.columns(4)
with cols[0]:
    kpi_card("Universe", str(len(fdf)), sector_f if sector_f != "All" else "all sectors")
with cols[1]:
    kpi_card("Q1 1Y", str(int((fdf.get("quartile_1y") == "Q1").sum())), "top quartile")
with cols[2]:
    kpi_card("Q4 3Y", str(int((fdf.get("quartile_3y") == "Q4").sum())), "bottom quartile")
with cols[3]:
    kpi_card("Q1 10Y", str(int((fdf.get("quartile_10y") == "Q1").sum())), "durable winners")

section_label("Drilldown")
qcol = QMAP[drill_period]
drill_df = fdf[fdf.get(qcol) == drill_quartile].copy() if qcol in fdf.columns else pd.DataFrame()
if drill_df.empty:
    info_block("No companies in this quartile selection.")
else:
    keep = [
        "ticker", "company_name", "sector", "price",
        RMAP[drill_period], "return_1y", "return_3y", "return_5y", "return_10y",
        "pe", "roe", "roce", "market_cap_cr", "ob_marketcap_ratio", "ob_revenue_ratio",
    ]
    keep = [c for c in keep if c in drill_df.columns]
    out = drill_df[keep].copy().sort_values(RMAP[drill_period], ascending=(drill_quartile != "Q1"), na_position="last")
    out = out.rename(columns={
        "ticker": "Ticker",
        "company_name": "Company",
        "sector": "Sector",
        "price": "Price",
        RMAP[drill_period]: f"{drill_period} %",
        "return_1y": "1Y %",
        "return_3y": "3Y %",
        "return_5y": "5Y %",
        "return_10y": "10Y %",
        "pe": "P/E",
        "roe": "ROE %",
        "roce": "ROCE %",
        "market_cap_cr": "MCap (Cr)",
        "ob_marketcap_ratio": "OB/MCap",
        "ob_revenue_ratio": "OB/Rev",
    })
    st.dataframe(
        out,
        hide_index=True,
        width="stretch",
        height=520,
        column_config={
            "Price": st.column_config.NumberColumn(format="₹ %.2f"),
            f"{drill_period} %": st.column_config.NumberColumn(format="%.1f%%"),
            "1Y %": st.column_config.NumberColumn(format="%.1f%%"),
            "3Y %": st.column_config.NumberColumn(format="%.1f%%"),
            "5Y %": st.column_config.NumberColumn(format="%.1f%%"),
            "10Y %": st.column_config.NumberColumn(format="%.1f%%"),
            "P/E": st.column_config.NumberColumn(format="%.1f"),
            "ROE %": st.column_config.NumberColumn(format="%.1f%%"),
            "ROCE %": st.column_config.NumberColumn(format="%.1f%%"),
            "MCap (Cr)": st.column_config.NumberColumn(format="₹ %.0f"),
            "OB/MCap": st.column_config.NumberColumn(format="%.2fx"),
            "OB/Rev": st.column_config.NumberColumn(format="%.2fx"),
        },
    )

section_label("Quartile Transitions")
left_col = QMAP[transition_left]
right_col = QMAP[transition_right]
if left_col in fdf.columns and right_col in fdf.columns:
    rise = fdf[(fdf[left_col] == "Q4") & (fdf[right_col] == "Q1")].copy()
    fall = fdf[(fdf[left_col] == "Q1") & (fdf[right_col] == "Q4")].copy()
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"**Q4 → Q1 ({transition_left} vs {transition_right})**")
        if rise.empty:
            info_block("No upward quartile reversals.")
        else:
            st.dataframe(
                rise[["ticker", "company_name", "sector", RMAP.get(transition_left, "return_1m"), RMAP.get(transition_right, "return_3m")]].rename(columns={
                    "ticker": "Ticker", "company_name": "Company", "sector": "Sector",
                    RMAP.get(transition_left, "return_1m"): f"{transition_left} %",
                    RMAP.get(transition_right, "return_3m"): f"{transition_right} %",
                }),
                hide_index=True,
                width="stretch",
                height=220,
            )
    with c2:
        st.markdown(f"**Q1 → Q4 ({transition_left} vs {transition_right})**")
        if fall.empty:
            info_block("No broken momentum names.")
        else:
            st.dataframe(
                fall[["ticker", "company_name", "sector", RMAP.get(transition_left, "return_1m"), RMAP.get(transition_right, "return_3m")]].rename(columns={
                    "ticker": "Ticker", "company_name": "Company", "sector": "Sector",
                    RMAP.get(transition_left, "return_1m"): f"{transition_left} %",
                    RMAP.get(transition_right, "return_3m"): f"{transition_right} %",
                }),
                hide_index=True,
                width="stretch",
                height=220,
            )
else:
    info_block("Quartile transitions will populate after the returns snapshot is rebuilt with quartile columns.")

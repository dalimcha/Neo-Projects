from __future__ import annotations

import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="All Companies — India Terminal",
    layout="wide",
    initial_sidebar_state="expanded",
)

from utils.formatting import inject_css, page_header, section_label, kpi_card, info_block, table_wrap, html_block
from utils.data_loader import load_full_universe, load_data_quality_log


inject_css()


@st.cache_data(ttl=300)
def _load() -> pd.DataFrame:
    return load_full_universe()


def _latest_ts(log_df: pd.DataFrame, dataset: str) -> str | None:
    if log_df.empty or "dataset" not in log_df.columns:
        return None
    sub = log_df[log_df["dataset"].astype(str) == dataset].copy()
    if sub.empty:
        return None
    sub["last_refresh_at"] = pd.to_datetime(sub["last_refresh_at"], errors="coerce")
    sub = sub.sort_values("last_refresh_at")
    ts = sub.iloc[-1]["last_refresh_at"]
    return ts.strftime("%d %b %Y %H:%M") if pd.notna(ts) else None


def _normalize_pct(series: pd.Series) -> pd.Series:
    vals = pd.to_numeric(series, errors="coerce")
    if vals.dropna().empty:
        return vals
    if vals.dropna().abs().max() <= 5:
        return vals * 100
    return vals


def _bucket_mcap(v: float) -> str:
    if pd.isna(v):
        return "N/A"
    if v >= 100000:
        return "Large Cap"
    if v >= 10000:
        return "Mid Cap"
    return "Small Cap"


df = _load()
quality_log = load_data_quality_log()
price_ts = _latest_ts(quality_log, "prices")
fund_ts = _latest_ts(quality_log, "fundamentals")

page_header(
    "",
    "",
    data_status="Fresh" if len(df) >= 475 else "Delayed",
    data_ts=price_ts,
)

if df.empty:
    info_block("No merged universe available. Refresh universe, prices, and fundamentals first.")
    st.stop()

df = df.copy()

for col in [
    "return_1d", "return_1w", "return_1m", "return_3m", "return_6m", "return_1y",
    "return_3y", "return_5y", "return_10y",
    "dist_52w_high_pct", "dist_52w_low_pct", "roe", "roce", "ebitda_margin",
    "pat_margin", "revenue_growth_1y", "pat_growth_1y", "promoter_holding",
    "fii_holding", "dii_holding",
]:
    if col in df.columns:
        df[col] = _normalize_pct(df[col])

if "market_cap_cr" in df.columns:
    df["mcap_bucket"] = df["market_cap_cr"].apply(_bucket_mcap)

fund_coverage = int((df["pe"].notna() | df["roe"].notna()).sum()) if "pe" in df.columns else 0
filing_coverage = int(df["latest_filing_date"].notna().sum()) if "latest_filing_date" in df.columns else 0

html_block(
    f"""
    <div class="hero-panel">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:1rem;flex-wrap:wrap;">
        <div>
          <div class="hero-sub" style="text-transform:uppercase;letter-spacing:0.10em;font-size:0.62rem;">All Companies</div>
          <div class="hero-title">Core Research Grid</div>
        </div>
        <div style="display:flex;gap:0.55rem;flex-wrap:wrap;justify-content:flex-end;">
          <span class="pill-chip"><strong>Rows</strong>{len(df)}</span>
          <span class="pill-chip"><strong>Fundamentals</strong>{fund_coverage}</span>
          <span class="pill-chip"><strong>Filings</strong>{filing_coverage}</span>
          <span class="pill-chip"><strong>Snapshot</strong>{price_ts or 'N/A'}</span>
        </div>
      </div>
    </div>
    """
)

with st.sidebar:
    html_block('<div class="sec-label">Filters</div>')
    sectors = ["All"] + sorted(df["sector"].dropna().astype(str).unique().tolist()) if "sector" in df.columns else ["All"]
    industries = ["All"] + sorted(df["industry"].dropna().astype(str).unique().tolist()) if "industry" in df.columns else ["All"]
    sector_f = st.selectbox("Sector", sectors)
    industry_f = st.selectbox("Industry", industries)

    universe_f = st.selectbox("Universe", ["All", "Nifty50", "Nifty100", "Nifty500"])
    mcap_f = st.selectbox("Market Cap", ["All", "Large Cap", "Mid Cap", "Small Cap"])
    fundamentals_only = st.checkbox("Fundamentals Available Only", value=False)

    st.markdown("---")
    ret_min = st.slider("1Y Return Min %", -100, 250, -100)
    ret_max = st.slider("1Y Return Max %", -100, 300, 300)
    pe_max = st.slider("Max P/E", 0, 100, 100)
    min_roe = st.slider("Min ROE %", -20, 40, -20)

    st.markdown("---")
    quartile_period_a = st.selectbox("Quartile Period A", ["Off", "1M", "3M", "6M", "1Y", "3Y", "5Y", "10Y"], index=0)
    quartile_period_b = st.selectbox("Quartile Period B", ["Off", "1M", "3M", "6M", "1Y", "3Y", "5Y", "10Y"], index=0)
    quartile_show = st.multiselect("Show Quartiles", ["Q1", "Q2", "Q3", "Q4"], default=["Q1", "Q2", "Q3", "Q4"])

    st.markdown("---")
    sort_col = st.selectbox(
        "Sort By",
        [
            "market_cap_cr", "return_1d", "return_1w", "return_1m", "return_3m",
            "return_6m", "return_1y", "return_3y", "return_5y", "return_10y",
            "volume_ratio_30d", "pe", "roe",
            "revenue_growth_1y", "pat_growth_1y",
        ],
        index=6,
    )
    sort_asc = st.checkbox("Ascending", value=False)

fdf = df.copy()
if sector_f != "All" and "sector" in fdf.columns:
    fdf = fdf[fdf["sector"] == sector_f]
if industry_f != "All" and "industry" in fdf.columns:
    fdf = fdf[fdf["industry"] == industry_f]
if universe_f != "All" and "index_membership" in fdf.columns:
    fdf = fdf[fdf["index_membership"].astype(str).str.contains(universe_f, na=False)]
if mcap_f != "All" and "mcap_bucket" in fdf.columns:
    fdf = fdf[fdf["mcap_bucket"] == mcap_f]
if fundamentals_only:
    fdf = fdf[fdf["pe"].notna() | fdf["roe"].notna() | fdf["market_cap_cr"].notna()]
if "return_1y" in fdf.columns:
    fdf = fdf[(fdf["return_1y"].fillna(-9999) >= ret_min) & (fdf["return_1y"].fillna(9999) <= ret_max)]
if "pe" in fdf.columns:
    fdf = fdf[(fdf["pe"].isna()) | (fdf["pe"] <= pe_max)]
if "roe" in fdf.columns:
    fdf = fdf[(fdf["roe"].isna()) | (fdf["roe"] >= min_roe)]
period_to_col = {
    "1M": "quartile_1m",
    "3M": "quartile_3m",
    "6M": "quartile_6m",
    "1Y": "quartile_1y",
    "3Y": "quartile_3y",
    "5Y": "quartile_5y",
    "10Y": "quartile_10y",
}
if quartile_period_a != "Off":
    qa_col = period_to_col[quartile_period_a]
    if qa_col in fdf.columns:
        fdf = fdf[fdf[qa_col].isin(quartile_show)]
if quartile_period_b != "Off":
    qb_col = period_to_col[quartile_period_b]
    if qb_col in fdf.columns:
        fdf = fdf[fdf[qb_col].isin(quartile_show)]
if sort_col in fdf.columns:
    fdf = fdf.sort_values(sort_col, ascending=sort_asc, na_position="last")

cov_cols = st.columns(5)
with cov_cols[0]:
    kpi_card("Displayed", str(len(fdf)), "after filters")
with cov_cols[1]:
    kpi_card("Universe", str(len(df)), "merged rows")
with cov_cols[2]:
    kpi_card("With Fundamentals", str(fund_coverage), fund_ts or "No refresh log")
with cov_cols[3]:
    kpi_card("With Filing Date", str(filing_coverage), "event context")
with cov_cols[4]:
    kpi_card("Price Snapshot", price_ts or "N/A", "latest refresh")

if fund_coverage < 100:
    info_block(
        f"Price coverage is strong, but only {fund_coverage}/{len(df)} names currently have fundamentals. "
        "This is why valuation, growth, and holding columns still look sparse. Import the Screener export to unlock the full research grid."
    )

if quartile_period_a != "Off" and quartile_period_b != "Off":
    section_label("Quartile Crosstab")
    qa_col = period_to_col[quartile_period_a]
    qb_col = period_to_col[quartile_period_b]
    if qa_col in df.columns and qb_col in df.columns:
        ctab = (
            df.dropna(subset=[qa_col, qb_col])
            .groupby([qa_col, qb_col]).size()
            .unstack(fill_value=0)
            .reindex(index=["Q1", "Q2", "Q3", "Q4"], columns=["Q1", "Q2", "Q3", "Q4"], fill_value=0)
        )
        st.dataframe(ctab, width="stretch")
        reversion = df[(df.get(qa_col) == "Q4") & (df.get(qb_col) == "Q1")].head(5)
        compound = df[(df.get(qa_col) == "Q1") & (df.get(qb_col) == "Q1")].head(5)
        c1, c2 = st.columns(2)
        with c1:
            info_block("Reversion candidates: " + (", ".join(reversion["ticker"].astype(str).tolist()) if not reversion.empty else "None"))
        with c2:
            info_block("Durable compounders: " + (", ".join(compound["ticker"].astype(str).tolist()) if not compound.empty else "None"))

section_label("Table")

info_block("Price, fundamentals, filings, and long-duration return quartiles are merged into one research grid.")

display_cols = [
    "ticker", "company_name", "sector", "industry", "mcap_bucket", "market_cap_cr", "price",
    "return_1d", "return_1w", "return_1m", "return_3m", "return_6m", "return_1y",
    "return_3y", "return_5y", "return_10y",
    "quartile_1m", "quartile_3m", "quartile_6m", "quartile_1y", "quartile_3y", "quartile_5y", "quartile_10y",
    "dist_52w_high_pct", "dist_52w_low_pct", "volume_ratio_30d",
    "pe", "ev_ebitda", "pb", "roe", "roce", "debt_equity",
    "revenue_growth_1y", "pat_growth_1y", "ebitda_margin",
    "promoter_holding", "fii_holding", "dii_holding",
    "latest_result_date", "latest_filing_date", "latest_filing_type", "latest_news_headline",
]
display_cols = [c for c in display_cols if c in fdf.columns]
table_df = fdf[display_cols].copy()
table_df = table_df.rename(columns={
    "ticker": "Ticker",
    "company_name": "Company",
    "sector": "Sector",
    "industry": "Industry",
    "mcap_bucket": "MCap Bucket",
    "market_cap_cr": "MCap (Cr)",
    "price": "Price",
    "return_1d": "1D %",
    "return_1w": "1W %",
    "return_1m": "1M %",
    "return_3m": "3M %",
    "return_6m": "6M %",
    "return_1y": "1Y %",
    "return_3y": "3Y %",
    "return_5y": "5Y %",
    "return_10y": "10Y %",
    "quartile_1m": "Q 1M",
    "quartile_3m": "Q 3M",
    "quartile_6m": "Q 6M",
    "quartile_1y": "Q 1Y",
    "quartile_3y": "Q 3Y",
    "quartile_5y": "Q 5Y",
    "quartile_10y": "Q 10Y",
    "dist_52w_high_pct": "52W High Dist %",
    "dist_52w_low_pct": "52W Low Dist %",
    "volume_ratio_30d": "Vol/30D",
    "pe": "P/E",
    "ev_ebitda": "EV/EBITDA",
    "pb": "P/B",
    "roe": "ROE %",
    "roce": "ROCE %",
    "debt_equity": "D/E",
    "revenue_growth_1y": "Revenue Growth %",
    "pat_growth_1y": "PAT Growth %",
    "ebitda_margin": "EBITDA Margin %",
    "promoter_holding": "Promoter %",
    "fii_holding": "FII %",
    "dii_holding": "DII %",
    "latest_result_date": "Latest Result",
    "latest_filing_date": "Latest Filing",
    "latest_filing_type": "Filing Type",
    "latest_news_headline": "Latest News",
})

html_block(
    f"""<div style="font-size:0.72rem;color:#64748b;margin-bottom:0.6rem;">
    Showing <span style="color:#e2e8f0;font-weight:600;">{len(table_df)}</span> companies
    &nbsp;|&nbsp; Sorted by <span style="color:#60a5fa;">{sort_col}</span>
    &nbsp;|&nbsp; Fundamentals coverage <span style="color:#e2e8f0;font-weight:600;">{fund_coverage}/{len(df)}</span>
    </div>""",
)

if table_df.empty:
    info_block("No companies match the current filters.")
else:
    st.dataframe(
        table_df,
        hide_index=True,
        width="stretch",
        height=760,
        column_config={
            "MCap (Cr)": st.column_config.NumberColumn(format="₹ %.0f"),
            "Price": st.column_config.NumberColumn(format="₹ %.2f"),
            "1D %": st.column_config.NumberColumn(format="%.1f%%"),
            "1W %": st.column_config.NumberColumn(format="%.1f%%"),
            "1M %": st.column_config.NumberColumn(format="%.1f%%"),
            "3M %": st.column_config.NumberColumn(format="%.1f%%"),
            "6M %": st.column_config.NumberColumn(format="%.1f%%"),
            "1Y %": st.column_config.NumberColumn(format="%.1f%%"),
            "3Y %": st.column_config.NumberColumn(format="%.1f%%"),
            "5Y %": st.column_config.NumberColumn(format="%.1f%%"),
            "10Y %": st.column_config.NumberColumn(format="%.1f%%"),
            "52W High Dist %": st.column_config.NumberColumn(format="%.1f%%"),
            "52W Low Dist %": st.column_config.NumberColumn(format="%.1f%%"),
            "Vol/30D": st.column_config.NumberColumn(format="%.2fx"),
            "P/E": st.column_config.NumberColumn(format="%.1f"),
            "EV/EBITDA": st.column_config.NumberColumn(format="%.1f"),
            "P/B": st.column_config.NumberColumn(format="%.1f"),
            "ROE %": st.column_config.NumberColumn(format="%.1f%%"),
            "ROCE %": st.column_config.NumberColumn(format="%.1f%%"),
            "D/E": st.column_config.NumberColumn(format="%.2f"),
            "Revenue Growth %": st.column_config.NumberColumn(format="%.1f%%"),
            "PAT Growth %": st.column_config.NumberColumn(format="%.1f%%"),
            "EBITDA Margin %": st.column_config.NumberColumn(format="%.1f%%"),
            "Promoter %": st.column_config.NumberColumn(format="%.1f%%"),
            "FII %": st.column_config.NumberColumn(format="%.1f%%"),
            "DII %": st.column_config.NumberColumn(format="%.1f%%"),
        },
    )
    st.download_button(
        "Export Current View CSV",
        data=table_df.to_csv(index=False),
        file_name=f"all_companies_view_{pd.Timestamp.today().date()}.csv",
        mime="text/csv",
    )

section_label("Sector Snapshot")
if "sector" in fdf.columns:
    sec = (
        fdf.groupby("sector", dropna=False)
        .agg(
            companies=("ticker", "count"),
            avg_1d=("return_1d", "mean"),
            avg_1m=("return_1m", "mean"),
            mcap=("market_cap_cr", "sum"),
        )
        .reset_index()
        .sort_values("mcap", ascending=False)
    )
    rows = ""
    for _, r in sec.iterrows():
        rows += (
            "<tr>"
            f"<td class='left' style='color:#cbd5e1;'>{r['sector']}</td>"
            f"<td>{int(r['companies'])}</td>"
            f"<td>{'—' if pd.isna(r['avg_1d']) else f'{r['avg_1d']:.1f}%'}"  # noqa: E999
            f"</td>"
            f"<td>{'—' if pd.isna(r['avg_1m']) else f'{r['avg_1m']:.1f}%'}"  # noqa: E999
            f"</td>"
            f"<td>{'—' if pd.isna(r['mcap']) else f'₹{r['mcap']:,.0f}'}"  # noqa: E999
            f"</td>"
            "</tr>"
        )
    table_wrap(
        f"""<table class='trm'>
            <thead><tr>
                <th class='left'>Sector</th>
                <th>Companies</th>
                <th>Avg 1D</th>
                <th>Avg 1M</th>
                <th>MCap</th>
            </tr></thead>
            <tbody>{rows}</tbody>
        </table>""",
        caption="Sector distribution in current filtered view",
        caption_right="Based on current filters",
    )

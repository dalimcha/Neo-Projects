"""
Company Detail Page
───────────────────
Deep dive on any company in the universe:
financials, valuation, peers, news, filings, AI analyst note, research notes.
"""

import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="Company Detail — India Terminal",
    layout="wide", initial_sidebar_state="expanded",
)

from utils.formatting import (
    inject_css, page_header, section_label, kpi_card, fmt_pct,
    fmt_price, fmt_cr, fmt_ratio, info_block, warn_block, ai_box,
    table_wrap, badge_html, sentiment_badge, POS, NEG, ACCENT, TEXT3, BG2, html_block,
)
from utils.data_loader import (
    load_universe, load_order_book, load_fundamentals,
    load_filings, load_news, load_notes, save_note, get_company_detail,
    get_company_quarterly, pivot_quarterly_metric, load_full_universe,
    compute_quarterly_yoy, quarterly_summary_stats, QUARTER_ORDER,
)
from utils.charting import (
    price_chart, return_waterfall, peer_comparison_bar, margin_trend_line, _empty_chart,
    quarterly_comparison_bar, quarterly_yoy_growth_line, quarterly_margin_chart,
    quarterly_heatmap,
)
from utils.nse_fetcher import fetch_price_history
import utils.ai_summarizer as ai

inject_css()

# ── Sidebar: company selector ─────────────────────────────────────────────────
uni = load_universe()

with st.sidebar:
    html_block('<div class="sec-label">Company</div>')
    if uni.empty:
        st.warning("Universe not loaded")
        ticker = st.text_input("Enter ticker manually")
    else:
        tickers = sorted(uni["ticker"].tolist())
        labels  = []
        for t in tickers:
            name_row = uni[uni["ticker"] == t]
            name = name_row["company_name"].values[0] if not name_row.empty else t
            labels.append(f"{t} — {name}")
        sel = st.selectbox("Select Company", labels, index=0)
        ticker = sel.split(" — ")[0] if sel else ""

    period_map = {"1 Month": "1mo", "3 Months": "3mo", "6 Months": "6mo",
                  "1 Year": "1y", "2 Years": "2y", "5 Years": "5y"}
    price_period = st.selectbox("Price Chart Period", list(period_map.keys()), index=3)

if not ticker:
    info_block("Select a company from the sidebar.")
    st.stop()

# ── Load data ─────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def _detail(t):
    return get_company_detail(t)

detail = _detail(ticker)
meta   = detail.get("meta", {})
fund   = detail.get("fund", {})
price  = detail.get("price", {})
ob     = detail.get("ob", pd.DataFrame())
fil    = detail.get("filings", pd.DataFrame())
news_d = detail.get("news", pd.DataFrame())

company_name = meta.get("company_name", ticker)
sector       = meta.get("sector", "")
industry     = meta.get("industry", "")

# ── Page header ───────────────────────────────────────────────────────────────
close_price = price.get("close") or price.get("price")
ret_1d      = price.get("return_1d", 0) or 0
if abs(ret_1d) < 5: ret_1d *= 100
page_header("", "")

latest_filing_subject = ""
latest_filing_date = ""
if not fil.empty:
    tmp_fil = fil.copy()
    if "date" in tmp_fil.columns:
        tmp_fil["date"] = pd.to_datetime(tmp_fil["date"], errors="coerce")
        tmp_fil = tmp_fil.sort_values("date", ascending=False)
    latest_filing = tmp_fil.iloc[0]
    latest_filing_subject = str(latest_filing.get("subject", "")).strip()
    latest_filing_date = str(latest_filing.get("date", ""))[:10]

latest_news_headline = ""
latest_news_date = ""
if not news_d.empty:
    tmp_news = news_d.copy()
    if "date" in tmp_news.columns:
        tmp_news["date"] = pd.to_datetime(tmp_news["date"], errors="coerce")
        tmp_news = tmp_news.sort_values("date", ascending=False)
    latest_news = tmp_news.iloc[0]
    latest_news_headline = str(latest_news.get("headline", "")).strip()
    latest_news_date = str(latest_news.get("date", ""))[:10]

html_block(
    f"""<div class="hero-panel">
          <div class="hero-kicker">Company Detail</div>
          <div class="hero-title">{company_name}</div>
          <div class="hero-sub">{ticker} · {sector or 'Sector N/A'} · {industry or 'Industry N/A'}</div>
          <div style="margin-top:0.55rem;display:flex;gap:0.45rem;flex-wrap:wrap;">
            <span class="chip">Price {fmt_price(close_price)}</span>
            <span class="chip">1D {fmt_pct(ret_1d)}</span>
            <span class="chip">MCap {fmt_cr(mcap) if mcap else '—'}</span>
            <span class="chip">P/E {fmt_ratio(pe) if pe else '—'}</span>
            <span class="chip">Latest Filing {latest_filing_date or '—'}</span>
            <span class="chip">Latest News {latest_news_date or '—'}</span>
          </div>
        </div>"""
)

# ── KPI row ───────────────────────────────────────────────────────────────────
mcap    = fund.get("market_cap_cr") or meta.get("market_cap_cr_approx")
ev      = fund.get("enterprise_value_cr")
pe      = fund.get("pe")
roe     = fund.get("roe")
de      = fund.get("debt_equity")
rev_ttm = fund.get("revenue_ttm")
ebitda  = fund.get("ebitda_margin")

kpi_cols = st.columns(6)
kpi_data = [
    ("Last Price",     fmt_price(close_price), fmt_pct(ret_1d), ret_1d >= 0),
    ("Market Cap",     fmt_cr(mcap) if mcap else "—", "", None),
    ("P / E",          f"{pe:.1f}x" if pe else "—", "", None),
    ("ROE",            fmt_pct(roe) if roe else "—", "", roe and roe > 15),
    ("D / E",          fmt_ratio(de) if de is not None else "—", "", de is not None and de < 1),
    ("TTM Revenue",    fmt_cr(rev_ttm) if rev_ttm else "—", "", None),
]
for col, (lbl, val, sub, pos) in zip(kpi_cols, kpi_data):
    with col:
        kpi_card(lbl, val, sub, delta_pos=pos)

st.write("")

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_names = ["Overview", "Financials", "Quarterly", "Valuation", "Special Situations",
             "News & Filings", "AI Analyst Note", "Research Notes"]
tabs = st.tabs(tab_names)

# ── TAB 1: Overview ───────────────────────────────────────────────────────────
with tabs[0]:
    col_a, col_b = st.columns([3, 2])

    with col_a:
        section_label("Business Summary")
        business_desc = meta.get("description", "")
        if business_desc:
            st.markdown(f'<p>{business_desc}</p>', unsafe_allow_html=True)
        else:
            info_block(
                f"{company_name} is a {sector} company listed on NSE/BSE. "
                "Add a description to data/universe.csv or use the AI summary below."
            )

        section_label("Latest Public Context")
        context_rows = []
        if latest_filing_subject:
            context_rows.append(
                f"<tr><td class='left' style='color:#64748b;'>Latest Filing</td><td class='left'>{latest_filing_subject}</td><td>{latest_filing_date or '—'}</td></tr>"
            )
        if latest_news_headline:
            context_rows.append(
                f"<tr><td class='left' style='color:#64748b;'>Latest News</td><td class='left'>{latest_news_headline}</td><td>{latest_news_date or '—'}</td></tr>"
            )
        if context_rows:
            table_wrap(
                f"""<table class='trm'>
                <thead><tr><th class='left'>Type</th><th class='left'>Headline / Subject</th><th>Date</th></tr></thead>
                <tbody>{''.join(context_rows)}</tbody></table>""",
                caption="Most recent linked events",
            )

        # Price chart
        section_label("Price Chart")
        with st.spinner("Fetching price history…"):
            ph = fetch_price_history(ticker, period_map[price_period])
        if not ph.empty:
            fig = price_chart(ph, ticker, price_period)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.plotly_chart(_empty_chart(f"Price chart — {ticker}"), use_container_width=True)

    with col_b:
        section_label("Return Profile")
        ret_periods = ["1D","1W","1M","3M","6M","1Y","3Y","5Y","10Y"]
        ret_cols    = ["return_1d","return_1w","return_1m","return_3m","return_6m","return_1y","return_3y","return_5y","return_10y"]
        ret_vals    = []
        for rc in ret_cols:
            v = price.get(rc)
            if v is None:
                v = 0.0
            v = float(v)
            if abs(v) < 5:
                v *= 100
            ret_vals.append(v)

        fig = return_waterfall(ret_periods, ret_vals, ticker)
        st.plotly_chart(fig, use_container_width=True)

        section_label("Sector Peer Snapshot")
        full_uni = load_full_universe()
        peer_rows = pd.DataFrame()
        if not full_uni.empty and sector and "sector" in full_uni.columns:
            peer_rows = full_uni[full_uni["sector"] == sector].copy()
            if "market_cap_cr" in peer_rows.columns:
                peer_rows = peer_rows.sort_values("market_cap_cr", ascending=False)
            peer_rows = peer_rows[peer_rows["ticker"] != ticker].head(5)
        if not peer_rows.empty:
            rows = ""
            for _, pr in peer_rows.iterrows():
                r1y = pd.to_numeric(pr.get("return_1y"), errors="coerce")
                if pd.notna(r1y) and abs(r1y) < 5:
                    r1y *= 100
                rows += (
                    f"<tr><td class='ticker'>{pr.get('ticker','')}</td>"
                    f"<td class='name'>{pr.get('company_name','')}</td>"
                    f"<td>{fmt_cr(pr.get('market_cap_cr'))}</td>"
                    f"<td>{fmt_ratio(pr.get('pe'))}</td>"
                    f"<td>{fmt_pct(r1y) if pd.notna(r1y) else '—'}</td></tr>"
                )
            table_wrap(
                f"""<table class='trm'><thead><tr>
                <th class='left'>Ticker</th><th class='left'>Company</th><th>MCap</th><th>P/E</th><th>1Y</th>
                </tr></thead><tbody>{rows}</tbody></table>""",
                caption="Top 5 same-sector peers",
            )
        else:
            info_block("No same-sector peers available.")

        section_label("Key Metrics")
        metrics = {
            "P/E Ratio": f"{pe:.1f}x" if pe else "—",
            "EV/EBITDA": f"{fund.get('ev_ebitda', 0):.1f}x" if fund.get("ev_ebitda") else "—",
            "P/B Ratio": f"{fund.get('pb', 0):.1f}x" if fund.get("pb") else "—",
            "ROE":        fmt_pct(roe) if roe else "—",
            "ROCE":       fmt_pct(fund.get("roce")) if fund.get("roce") else "—",
            "D/E":        fmt_ratio(de) if de is not None else "—",
            "Rev Growth (1Y)": fmt_pct(fund.get("revenue_growth_1y")) if fund.get("revenue_growth_1y") else "—",
            "EBITDA Margin":   fmt_pct(ebitda) if ebitda else "—",
            "Promoter Holding": fmt_pct(fund.get("promoter_holding")) if fund.get("promoter_holding") else "—",
        }
        rows = "".join(
            f"<tr><td class='left' style='color:#64748b;'>{k}</td>"
            f"<td style='text-align:right;color:#cbd5e1;'>{v}</td></tr>"
            for k, v in metrics.items()
        )
        table_wrap(
            f"""<table class='trm'>
                <tbody>{rows}</tbody>
              </table>""",
        )

# ── TAB 2: Financials ─────────────────────────────────────────────────────────
with tabs[1]:
    col1, col2 = st.columns(2)

    with col1:
        section_label("Income Statement — TTM")
        inc_data = {
            "Revenue (TTM)":       fmt_cr(fund.get("revenue_ttm")),
            "EBITDA (TTM)":        fmt_cr(fund.get("ebitda_ttm")),
            "PAT (TTM)":           fmt_cr(fund.get("pat_ttm")),
            "EBITDA Margin":       fmt_pct(fund.get("ebitda_margin")) if fund.get("ebitda_margin") else "—",
            "PAT Margin":          fmt_pct(fund.get("pat_margin")) if fund.get("pat_margin") else "—",
            "Revenue Growth (1Y)": fmt_pct(fund.get("revenue_growth_1y")) if fund.get("revenue_growth_1y") else "—",
            "Revenue Growth (3Y)": fmt_pct(fund.get("revenue_growth_3y")) if fund.get("revenue_growth_3y") else "—",
            "EBITDA Growth (1Y)":  fmt_pct(fund.get("ebitda_growth_1y")) if fund.get("ebitda_growth_1y") else "—",
            "PAT Growth (1Y)":     fmt_pct(fund.get("pat_growth_1y")) if fund.get("pat_growth_1y") else "—",
        }
        rows = "".join(
            f"<tr><td class='left' style='color:#64748b;'>{k}</td>"
            f"<td style='text-align:right;color:#cbd5e1;'>{v}</td></tr>"
            for k, v in inc_data.items()
        )
        table_wrap(
            f"<table class='trm'><tbody>{rows}</tbody></table>",
            caption="Income Statement",
        )

    with col2:
        section_label("Balance Sheet")
        bs_data = {
            "Cash & Equivalents":    fmt_cr(fund.get("cash")),
            "Total Debt":            fmt_cr(fund.get("total_debt")),
            "Net Debt":              fmt_cr((fund.get("total_debt") or 0) - (fund.get("cash") or 0)),
            "Debt / Equity":         fmt_ratio(fund.get("debt_equity")) if fund.get("debt_equity") is not None else "—",
            "Current Ratio":         f"{fund.get('current_ratio', 0):.1f}x" if fund.get("current_ratio") else "—",
            "Interest Coverage":     f"{fund.get('interest_coverage', 0):.1f}x" if fund.get("interest_coverage") else "—",
            "Working Capital Days":  f"{fund.get('working_capital_days', 0):.0f}" if fund.get("working_capital_days") else "—",
            "CFO (TTM)":             fmt_cr(fund.get("cfo_ttm")),
            "ROE":                   fmt_pct(fund.get("roe")) if fund.get("roe") else "—",
            "ROCE":                  fmt_pct(fund.get("roce")) if fund.get("roce") else "—",
        }
        rows = "".join(
            f"<tr><td class='left' style='color:#64748b;'>{k}</td>"
            f"<td style='text-align:right;color:#cbd5e1;'>{v}</td></tr>"
            for k, v in bs_data.items()
        )
        table_wrap(
            f"<table class='trm'><tbody>{rows}</tbody></table>",
            caption="Balance Sheet",
        )

    section_label("Shareholder Pattern")
    sh_data = {
        "Promoters":   fmt_pct(fund.get("promoter_holding")) if fund.get("promoter_holding") else "—",
        "FII / FPI":   fmt_pct(fund.get("fii_holding")) if fund.get("fii_holding") else "—",
        "DII":         fmt_pct(fund.get("dii_holding")) if fund.get("dii_holding") else "—",
        "Public":      fmt_pct(fund.get("public_holding")) if fund.get("public_holding") else "—",
        "Last Result": str(fund.get("latest_result_date", "—"))[:10],
        "Quarter":     str(fund.get("result_quarter", "—")),
    }
    sh_cols = st.columns(6)
    for col, (k, v) in zip(sh_cols, sh_data.items()):
        with col:
            kpi_card(k, v)

# ── TAB 3: Quarterly Performance ──────────────────────────────────────────────
with tabs[2]:
    qdf = get_company_quarterly(ticker)

    if qdf.empty:
        info_block(
            f"No quarterly data for {ticker}. "
            "Add rows to data/quarterly_financials.csv with columns: "
            "ticker, fiscal_year, quarter, period_end, revenue_cr, ebitda_cr, "
            "ebitda_margin_pct, pat_cr, pat_margin_pct, order_inflow_cr, "
            "order_book_cr, ebitda_yoy_pct, revenue_yoy_pct, pat_yoy_pct."
        )
    else:
        # ── Header KPIs: latest quarter snapshot ─────────────────────────────
        latest = qdf.iloc[-1]
        latest_label = f"{latest.get('quarter','')} {latest.get('fiscal_year','')}"

        section_label(f"Latest Reported Quarter — {latest_label}")
        q_kpi_cols = st.columns(6)
        rev_yoy   = latest.get("revenue_yoy_pct")
        ebd_yoy   = latest.get("ebitda_yoy_pct")
        pat_yoy   = latest.get("pat_yoy_pct")
        q_kpi_data = [
            ("Revenue",       fmt_cr(latest.get("revenue_cr")),
             fmt_pct(rev_yoy) + " YoY" if pd.notna(rev_yoy) else "", pd.notna(rev_yoy) and rev_yoy > 0),
            ("EBITDA",        fmt_cr(latest.get("ebitda_cr")),
             fmt_pct(ebd_yoy) + " YoY" if pd.notna(ebd_yoy) else "", pd.notna(ebd_yoy) and ebd_yoy > 0),
            ("EBITDA Margin", fmt_pct(latest.get("ebitda_margin_pct"), sign=False),
             "", None),
            ("PAT",           fmt_cr(latest.get("pat_cr")),
             fmt_pct(pat_yoy) + " YoY" if pd.notna(pat_yoy) else "", pd.notna(pat_yoy) and pat_yoy > 0),
            ("PAT Margin",    fmt_pct(latest.get("pat_margin_pct"), sign=False),
             "", None),
            ("Order Inflow",  fmt_cr(latest.get("order_inflow_cr"))
             if pd.notna(latest.get("order_inflow_cr")) and latest.get("order_inflow_cr") > 0 else "—",
             "", None),
        ]
        for col, (lbl, val, sub, pos) in zip(q_kpi_cols, q_kpi_data):
            with col:
                kpi_card(lbl, val, sub, delta_pos=pos)

        st.write("")

        # ── Selectable metric for the cross-year comparison ──────────────────
        section_label("Quarter-on-Quarter Across Years")
        st.markdown(
            '<p style="color:#3d5270;font-size:0.74rem;margin-top:-0.3rem;">'
            'Side-by-side comparison of the same quarter across multiple fiscal years. '
            'Reveals seasonality and structural growth.'
            '</p>', unsafe_allow_html=True
        )

        METRIC_OPTIONS = {
            "Revenue (Cr)":      ("revenue_cr",         "Revenue (₹ Cr)"),
            "EBITDA (Cr)":       ("ebitda_cr",          "EBITDA (₹ Cr)"),
            "EBITDA Margin %":   ("ebitda_margin_pct",  "EBITDA Margin (%)"),
            "PAT (Cr)":          ("pat_cr",             "PAT (₹ Cr)"),
            "PAT Margin %":      ("pat_margin_pct",     "PAT Margin (%)"),
            "Order Inflow (Cr)": ("order_inflow_cr",    "Order Inflow (₹ Cr)"),
            "Order Book (Cr)":   ("order_book_cr",      "Order Book (₹ Cr)"),
        }
        m_col, _ = st.columns([1, 3])
        with m_col:
            metric_label = st.selectbox(
                "Metric", list(METRIC_OPTIONS.keys()), index=0,
                key=f"q_metric_{ticker}",
            )
        metric_col, metric_ylabel = METRIC_OPTIONS[metric_label]

        # Skip metric if it's all zeros (e.g. order book for non-OB cos)
        if metric_col in qdf.columns and qdf[metric_col].fillna(0).sum() == 0:
            warn_block(
                f"{metric_label} has no data for {ticker} "
                "(likely not an order-book business)."
            )
        else:
            col_chart, col_heat = st.columns([3, 2])

            with col_chart:
                fig = quarterly_comparison_bar(
                    qdf, metric_col, ticker,
                    title=f"{metric_label} — by Quarter × Year",
                    y_label=metric_ylabel,
                )
                st.plotly_chart(fig, use_container_width=True)

            with col_heat:
                fig = quarterly_heatmap(qdf, metric_col, ticker)
                st.plotly_chart(fig, use_container_width=True)

            # ── Pivot table with YoY columns ─────────────────────────────────
            pv = compute_quarterly_yoy(qdf, metric_col)
            if not pv.empty:
                rows_html = ""
                for q in QUARTER_ORDER:
                    if q not in pv.index:
                        continue
                    row = pv.loc[q]
                    cells = f"<td class='left' style='color:#cbd5e1;font-weight:600;'>{q}</td>"
                    for col in pv.columns:
                        v = row.get(col)
                        if pd.isna(v):
                            cells += "<td style='color:#1e2d45;'>—</td>"
                        elif "%" in str(col) and "→" in str(col):
                            # YoY %% growth column
                            cls = "pos" if v > 0 else ("neg" if v < 0 else "neu")
                            sign = "+" if v > 0 else ""
                            cells += (
                                f"<td class='{cls}' style='font-weight:600;'>"
                                f"{sign}{v:.1f}%</td>"
                            )
                        else:
                            if abs(v) >= 100:
                                cells += f"<td style='color:#94a3b8;'>{v:,.0f}</td>"
                            else:
                                cells += f"<td style='color:#94a3b8;'>{v:,.2f}</td>"
                    rows_html += f"<tr>{cells}</tr>"

                col_headers = ""
                for c in pv.columns:
                    is_yoy = "→" in str(c)
                    style  = "color:#22c55e;" if is_yoy else "color:#3d5270;"
                    col_headers += f"<th style='{style}'>{c}</th>"

                table_wrap(
                    f"""<table class='trm'>
                        <thead><tr>
                          <th class='left'>Quarter</th>
                          {col_headers}
                        </tr></thead>
                        <tbody>{rows_html}</tbody>
                      </table>""",
                    caption=f"{metric_label} — Pivot with YoY Growth",
                    caption_right=f"{ticker}",
                )

        st.write("")

        # ── YoY growth trajectory (Revenue/EBITDA/PAT) ───────────────────────
        col_a, col_b = st.columns(2)
        with col_a:
            section_label("YoY Growth Trajectory")
            fig = quarterly_yoy_growth_line(qdf, ticker)
            st.plotly_chart(fig, use_container_width=True)

        with col_b:
            section_label("Margin Trend (Quarterly)")
            fig = quarterly_margin_chart(qdf, ticker)
            st.plotly_chart(fig, use_container_width=True)

        st.write("")

        # ── Per-quarter summary cards (Q1/Q2/Q3/Q4 over multiple years) ──────
        section_label("Per-Quarter Multi-Year Summary — Revenue")
        st.markdown(
            '<p style="color:#3d5270;font-size:0.74rem;margin-top:-0.3rem;">'
            'How each quarter has evolved over multiple fiscal years. '
            'CAGR is computed across all reported years for that quarter.'
            '</p>', unsafe_allow_html=True
        )

        stats = quarterly_summary_stats(qdf, "revenue_cr")
        if stats:
            q_summary_cols = st.columns(len(stats))
            trend_arrow = {"up": "▲", "down": "▼", "flat": "►"}
            trend_color = {"up": "#22c55e", "down": "#ef4444", "flat": "#475569"}

            for col, (q, s) in zip(q_summary_cols, stats.items()):
                with col:
                    yoy_html = ""
                    if s.get("yoy_pct") is not None:
                        yc = "pos" if s["yoy_pct"] > 0 else "neg"
                        yoy_html = (
                            f'<div style="font-size:0.71rem;color:#3d5270;margin-top:0.5rem;">'
                            f'YoY: <span class="{yc}" style="font-family:\'JetBrains Mono\',monospace;">'
                            f'{s["yoy_pct"]:+.1f}%</span></div>'
                        )
                    cagr_html = ""
                    if s.get("cagr_pct") is not None:
                        cagr_html = (
                            f'<div style="font-size:0.71rem;color:#3d5270;">'
                            f'{s["n_years"]}Y CAGR: '
                            f'<span style="color:#60a5fa;font-family:\'JetBrains Mono\',monospace;">'
                            f'{s["cagr_pct"]:+.1f}%</span></div>'
                        )
                    arrow = trend_arrow.get(s.get("trend", "flat"), "►")
                    arrow_c = trend_color.get(s.get("trend", "flat"), "#475569")

                    st.markdown(
                        f"""<div class="kpi">
                              <div class="kpi-lbl">
                                {q} ({s.get('latest_fy','')})
                                <span style="float:right;color:{arrow_c};font-size:0.85rem;">{arrow}</span>
                              </div>
                              <div class="kpi-val">{fmt_cr(s.get('latest'))}</div>
                              {yoy_html}
                              {cagr_html}
                            </div>""",
                        unsafe_allow_html=True,
                    )

        st.write("")
        section_label("Vs Peers — Same Quarter")
        full_uni = load_full_universe()
        if full_uni.empty or "sector" not in full_uni.columns or not sector:
            info_block("Peer quarter comparison unavailable because sector peers could not be resolved.")
        else:
            peers = full_uni[full_uni["sector"] == sector].copy()
            if "market_cap_cr" in peers.columns:
                peers = peers.sort_values("market_cap_cr", ascending=False)
            peer_tickers = [t for t in peers["ticker"].astype(str).tolist() if t != ticker][:5]
            latest_q = str(latest.get("quarter", ""))
            latest_fy = str(latest.get("fiscal_year", ""))
            rows = []
            for pt in [ticker] + peer_tickers:
                pq = get_company_quarterly(pt)
                if pq.empty:
                    continue
                hit = pq[(pq["quarter"] == latest_q) & (pq["fiscal_year"] == latest_fy)]
                if hit.empty:
                    continue
                r = hit.iloc[-1]
                rows.append({
                    "Ticker": pt,
                    "Revenue (Cr)": r.get("revenue_cr"),
                    "EBITDA Margin %": r.get("ebitda_margin_pct"),
                    "PAT YoY %": r.get("pat_yoy_pct"),
                })
            peer_df = pd.DataFrame(rows)
            if peer_df.empty:
                info_block(f"No peer data found for {latest_q} {latest_fy}.")
            else:
                st.dataframe(
                    peer_df,
                    hide_index=True,
                    width="stretch",
                    column_config={
                        "Revenue (Cr)": st.column_config.NumberColumn(format="₹ %.0f"),
                        "EBITDA Margin %": st.column_config.NumberColumn(format="%.1f%%"),
                        "PAT YoY %": st.column_config.NumberColumn(format="%.1f%%"),
                    },
                )

# ── TAB 4: Valuation ──────────────────────────────────────────────────────────
with tabs[3]:
    col1, col2 = st.columns(2)

    with col1:
        section_label("Valuation Multiples")
        val_data = {
            "P/E (TTM)":    f"{fund.get('pe', 0):.1f}x" if fund.get("pe") else "—",
            "P/E (Fwd)":    "—",
            "EV/EBITDA":    f"{fund.get('ev_ebitda', 0):.1f}x" if fund.get("ev_ebitda") else "—",
            "P/B":          f"{fund.get('pb', 0):.1f}x" if fund.get("pb") else "—",
            "P/S":          f"{fund.get('ps', 0):.1f}x" if fund.get("ps") else "—",
            "Market Cap":   fmt_cr(fund.get("market_cap_cr")),
            "Enterprise Val": fmt_cr(fund.get("enterprise_value_cr")),
        }
        rows = "".join(
            f"<tr><td class='left' style='color:#64748b;'>{k}</td>"
            f"<td style='text-align:right;color:#cbd5e1;'>{v}</td></tr>"
            for k, v in val_data.items()
        )
        table_wrap(f"<table class='trm'><tbody>{rows}</tbody></table>", caption="Valuation")

    with col2:
        section_label("Peer Comparison")
        # Load sector peers from universe
        uni_full = load_universe()
        if not uni_full.empty and sector:
            peers = uni_full[uni_full["sector"] == sector]["ticker"].tolist()
            peers = [p for p in peers if p != ticker][:8]
        else:
            peers = []

        if peers:
            fund_all = load_fundamentals()
            if not fund_all.empty:
                peer_fund = fund_all[fund_all["ticker"].isin(peers + [ticker])]
                if not peer_fund.empty:
                    fig = peer_comparison_bar(peer_fund, metric="ev_ebitda", highlight=ticker)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    info_block("Peer valuation data not loaded.")
            else:
                info_block("Fundamentals not loaded for peer comparison.")
        else:
            info_block("No peers found in same sector.")

# ── TAB 4: Special Situations ─────────────────────────────────────────────────
with tabs[4]:
    if ob.empty:
        warn_block(
            f"{ticker} is not in the optional order-book dataset. "
            "Add it via the Special Situations page."
        )
    else:
        from utils.scoring import FACTOR_LABELS, FACTOR_MAX, calculate_ob_score
        from utils.charting import ob_score_breakdown
        from utils.formatting import score_bar, badge_html

        latest = ob.iloc[-1]
        result = calculate_ob_score(latest)
        score  = result["ob_score"]
        cls    = result["classification"]

        col1, col2 = st.columns([2, 1])

        with col1:
            section_label("Special Situations Intelligence")
            ob_data = {
                "Order Book (Cr)":        fmt_cr(latest.get("order_book_cr")),
                "Order Inflow (Cr, TTM)": fmt_cr(latest.get("order_inflow_cr")),
                "TTM Revenue (Cr)":       fmt_cr(latest.get("ttm_revenue_cr")),
                "OB / Revenue":           fmt_ratio(latest.get("ob_revenue_ratio")),
                "OB / Market Cap":        fmt_ratio(latest.get("ob_marketcap_ratio")),
                "OB / EV":               fmt_ratio(latest.get("ob_ev_ratio")),
                "BTB Ratio":             fmt_ratio(latest.get("btb_ratio")),
                "Order Inflow Growth":   fmt_pct(latest.get("order_inflow_growth_pct")) if latest.get("order_inflow_growth_pct") else "—",
                "Execution Cycle (mo)":  f"{latest.get('execution_cycle_months', 0):.0f}" if latest.get("execution_cycle_months") else "—",
            }
            rows = "".join(
                f"<tr><td class='left' style='color:#64748b;'>{k}</td>"
                f"<td style='text-align:right;color:#cbd5e1;'>{v}</td></tr>"
                for k, v in ob_data.items()
            )
            table_wrap(f"<table class='trm'><tbody>{rows}</tbody></table>", caption="Order Book Metrics")

            section_label("Management Commentary")
            commentary = latest.get("management_commentary", "")
            if commentary:
                ai_box(commentary, "Management Commentary")
            section_label("Source Traceability")
            src = {
                "Source Document": latest.get("source_document", "—"),
                "Source Date": str(latest.get("source_date", "—"))[:10],
                "Confidence Score": f"{latest.get('confidence_score', 0):.0f}/100",
                "Manually Verified": "Yes" if latest.get("manually_verified") else "No — review required",
            }
            rows = "".join(
                f"<tr><td class='left' style='color:#64748b;'>{k}</td>"
                f"<td style='text-align:right;color:#cbd5e1;'>{v}</td></tr>"
                for k, v in src.items()
            )
            table_wrap(f"<table class='trm'><tbody>{rows}</tbody></table>")

        with col2:
            section_label("OB Score")
            sc = score_bar(score, width=160)
            st.markdown(
                f'<div style="margin-bottom:0.75rem;">{sc}</div>'
                f'<div style="margin-bottom:1rem;">{badge_html(cls)}</div>',
                unsafe_allow_html=True,
            )
            fig = ob_score_breakdown(result["factors"], FACTOR_MAX, ticker)
            st.plotly_chart(fig, use_container_width=True)

            if result["penalties"]:
                section_label("Penalty Flags")
                for p in result["penalties"]:
                    st.markdown(
                        f'<div style="font-size:0.75rem;color:#ef4444;'
                        f'padding:0.2rem 0;border-bottom:1px solid #1a2840;">'
                        f'{p}</div>',
                        unsafe_allow_html=True,
                    )

# ── TAB 5: News & Filings ─────────────────────────────────────────────────────
with tabs[5]:
    col1, col2 = st.columns(2)

    with col1:
        section_label("Recent Filings")
        if fil.empty:
            info_block("No filings found for this company.")
        else:
            for _, row in fil.head(15).iterrows():
                s = row.get("sentiment", "neutral")
                col_map = {"positive":"#22c55e","negative":"#ef4444","neutral":"#64748b"}
                c = col_map.get(str(s).lower(), "#64748b")
                ai_s = row.get("ai_summary", "")
                ai_html = f'<div class="fil-ai">{ai_s}</div>' if ai_s else ""
                st.markdown(
                    f"""<div class="fil-row">
                          <div class="fil-time">{str(row.get('date',''))[:10]}</div>
                          <div class="fil-body">
                            <div class="fil-title">{row.get('subject','')}</div>
                            <div class="fil-meta"><span style="color:{c};">{str(s).upper()}</span>
                              &nbsp;|&nbsp; {row.get('type','Filing')}</div>
                            {ai_html}
                          </div>
                        </div>""",
                    unsafe_allow_html=True,
                )

    with col2:
        section_label("Related News")
        if news_d.empty:
            info_block("No news items found for this company.")
        else:
            for _, row in news_d.head(10).iterrows():
                s = row.get("sentiment", "neutral")
                col_map = {"positive":"#22c55e","negative":"#ef4444","neutral":"#64748b"}
                c = col_map.get(str(s).lower(), "#64748b")
                st.markdown(
                    f"""<div class="fil-row">
                          <div class="fil-time">{str(row.get('date',''))[:10]}</div>
                          <div class="fil-body">
                            <div class="fil-title">{row.get('headline','')}</div>
                            <div class="fil-meta">{row.get('source','')}
                              &nbsp;|&nbsp; <span style="color:{c};">{str(s).upper()}</span></div>
                            <div class="fil-ai">{row.get('ai_summary','')}</div>
                          </div>
                        </div>""",
                    unsafe_allow_html=True,
                )

# ── TAB 6: AI Analyst Note ────────────────────────────────────────────────────
with tabs[6]:
    section_label("AI-Generated Analyst Note")
    if st.button("Generate AI Analyst Note"):
        company_data = {**meta, **fund, **price}
        if not ob.empty:
            company_data.update(ob.iloc[-1].to_dict())
        with st.spinner("Generating analyst note via Claude…"):
            note = ai.generate_company_note(company_data)
        ai_box(note, f"Analyst Note — {company_name}")
        st.session_state[f"ai_note_{ticker}"] = note
    elif f"ai_note_{ticker}" in st.session_state:
        ai_box(st.session_state[f"ai_note_{ticker}"], f"Analyst Note — {company_name}")
    else:
        info_block(
            "Click 'Generate AI Analyst Note' to get a Claude-generated investment brief. "
            "Requires ANTHROPIC_API_KEY in Settings."
        )

    section_label("Key Risks")
    risks = meta.get("key_risks", "")
    if risks:
        for r in str(risks).split(";"):
            if r.strip():
                st.markdown(
                    f'<div style="font-size:0.8rem;color:#94a3b8;'
                    f'padding:0.35rem 0;border-bottom:1px solid #0d1825;">• {r.strip()}</div>',
                    unsafe_allow_html=True,
                )
    else:
        info_block("Add key_risks column to universe.csv for structured risk display.")

# ── TAB 7: Research Notes ─────────────────────────────────────────────────────
with tabs[7]:
    section_label("Your Research Notes")

    notes = load_notes(ticker)
    if not notes.empty:
        for _, row in notes.iterrows():
            date_str = str(row.get("date", ""))[:16]
            tags = row.get("tags", "")
            tags_html = ""
            if tags:
                tags_html = "".join(
                    f'<span style="background:#111827;border:1px solid #1e2d45;'
                    f'padding:0.12rem 0.4rem;border-radius:2px;font-size:0.62rem;'
                    f'color:#475569;margin-right:0.3rem;">{t.strip()}</span>'
                    for t in str(tags).split(",") if t.strip()
                )
            st.markdown(
                f"""<div style="background:#0f1929;border:1px solid #1e2d45;
                    border-radius:4px;padding:0.8rem 1rem;margin-bottom:0.5rem;">
                    <div style="display:flex;justify-content:space-between;margin-bottom:0.35rem;">
                      <div>{tags_html}</div>
                      <div style="font-size:0.65rem;color:#475569;font-family:'JetBrains Mono',monospace;">
                        {date_str}</div>
                    </div>
                    <div style="font-size:0.82rem;color:#94a3b8;line-height:1.65;">
                      {str(row.get('content',''))}</div>
                  </div>""",
                unsafe_allow_html=True,
            )

    st.markdown("---")
    section_label("Add New Note")
    new_note    = st.text_area("Research note", height=120, placeholder="Enter your research notes here…")
    new_tags    = st.text_input("Tags (comma-separated)", placeholder="defence, high-conviction, order-book")
    if st.button("Save Note"):
        if new_note.strip():
            save_note(ticker, new_note.strip(), new_tags.strip())
            st.success("Note saved.")
            st.rerun()
        else:
            st.warning("Note is empty.")

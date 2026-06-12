"""
Market Command Center

Canonical front page wired only to Phase 1 datasets:
- returns_snapshot.csv
- sector_performance.csv
- volume_shocks.csv
- data_quality_log.csv
- failed_tickers.csv
"""

from __future__ import annotations

from datetime import datetime
from html import escape

import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Market Command Center — India Terminal",
    layout="wide",
    initial_sidebar_state="expanded",
)

from utils.formatting import (
    inject_css,
    page_header,
    section_label,
    kpi_card,
    index_card,
    info_block,
    warn_block,
    ai_box,
    table_wrap,
    html_block,
    fmt_price,
    fmt_pct,
    fmt_cr,
    fmt_ratio,
)
from utils.data_loader import (
    build_morning_brief,
    load_universe,
    load_fundamentals,
    load_returns_snapshot,
    load_sector_performance,
    load_volume_shocks,
    load_filings,
    load_news,
    load_data_quality_log,
    load_failed_tickers,
)
from utils.validation import build_universe_report, gate, UNIVERSE_SPECS
from utils.nse_fetcher import fetch_index_snapshot
from utils.charting import sector_heatmap, _empty_chart
import utils.ai_summarizer as ai


inject_css()


def _filter_universe(df: pd.DataFrame, universe_label: str) -> pd.DataFrame:
    if df.empty or universe_label == "All":
        return df
    if "index_membership" not in df.columns:
        return df
    token_map = {
        "Nifty 50": "Nifty50",
        "Nifty 100": "Nifty100",
        "Nifty 500": "Nifty500",
        "Top 1000": "Top1000",
    }
    token = token_map.get(universe_label, universe_label.replace(" ", ""))
    return df[df["index_membership"].astype(str).str.contains(token, na=False)].copy()


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
    return row.get("status"), ts_str


def _safe_ad_ratio(advancers: int, decliners: int) -> str:
    if decliners == 0:
        return "N/A"
    return f"{advancers / decliners:.2f}x"


def _event_maps(filings_df: pd.DataFrame, news_df: pd.DataFrame) -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    filing_map: dict[str, str] = {}
    news_map: dict[str, str] = {}
    catalyst_map: dict[str, str] = {}

    if not filings_df.empty and "ticker" in filings_df.columns:
        tmp = filings_df.copy()
        if "date" in tmp.columns:
            tmp["date"] = pd.to_datetime(tmp["date"], errors="coerce")
            tmp = tmp.sort_values("date", ascending=False)
        for _, r in tmp.iterrows():
            t = str(r.get("ticker", "")).upper().strip()
            if t and t not in filing_map:
                filing_map[t] = str(r.get("subject", "")).strip()
                filing_type = str(r.get("type", "")).strip()
                if filing_type:
                    catalyst_map[t] = filing_type

    if not news_df.empty and "tickers_mentioned" in news_df.columns:
        tmp = news_df.copy()
        if "date" in tmp.columns:
            tmp["date"] = pd.to_datetime(tmp["date"], errors="coerce")
            tmp = tmp.sort_values("date", ascending=False)
        for _, r in tmp.iterrows():
            tickers = [x.strip().upper() for x in str(r.get("tickers_mentioned", "")).split("|") if x.strip()]
            headline = str(r.get("headline", "")).strip()
            for t in tickers:
                if t and t not in news_map:
                    news_map[t] = headline
                    if t not in catalyst_map and headline:
                        catalyst_map[t] = "News-driven"

    return filing_map, news_map, catalyst_map


def _actionability_tag(row: pd.Series, catalyst_map: dict[str, str]) -> str:
    ticker = str(row.get("ticker", "")).upper()
    volume_ratio = pd.to_numeric(row.get("volume_ratio_30d"), errors="coerce")
    ret_1d = pd.to_numeric(row.get("return_1d"), errors="coerce")

    if ticker in catalyst_map:
        raw = catalyst_map[ticker].lower()
        if "result" in raw:
            return "Result-driven"
        if "order" in raw:
            return "News-driven"
        if "board" in raw or "management" in raw or "fundraise" in raw:
            return "Needs research"
        if "news" in raw:
            return "News-driven"

    if pd.notna(volume_ratio) and volume_ratio >= 3 and pd.notna(ret_1d) and abs(ret_1d) >= 0.03:
        return "Technical breakout"
    if pd.notna(ret_1d) and ret_1d < -0.04:
        return "Reversal candidate"
    return "No clear catalyst"


def _confidence_label(row: pd.Series, filing_map: dict[str, str], news_map: dict[str, str]) -> str:
    ticker = str(row.get("ticker", "")).upper()
    if ticker in filing_map and ticker in news_map:
        return "High"
    if ticker in filing_map or ticker in news_map:
        return "Medium"
    return "Low"


def _render_movers_table(title: str, df: pd.DataFrame, n: int, ascending: bool, filing_map: dict[str, str], news_map: dict[str, str], catalyst_map: dict[str, str]) -> None:
    section_label(title)
    if df.empty:
        info_block("No valid move data available.")
        return

    sub = df.dropna(subset=["return_1d"]).sort_values("return_1d", ascending=ascending).head(n).copy()

    rows = ""
    for _, r in sub.iterrows():
        ticker = str(r.get("ticker", ""))
        event = filing_map.get(ticker) or news_map.get(ticker) or "No public event linked"
        tag = _actionability_tag(r, catalyst_map)
        conf = _confidence_label(r, filing_map, news_map)
        move = pd.to_numeric(r.get("return_1d"), errors="coerce")
        move_cls = "pos" if pd.notna(move) and move >= 0 else "neg"
        rows += (
            "<tr>"
            f"<td class='ticker'>{ticker}</td>"
            f"<td class='name'>{r.get('company_name', '')}</td>"
            f"<td>{r.get('sector', 'N/A')}</td>"
            f"<td>{fmt_pct((move * 100) if pd.notna(move) else pd.NA)}</td>"
            f"<td>{fmt_pct(pd.to_numeric(r.get('return_1w'), errors='coerce') * 100)}</td>"
            f"<td>{fmt_pct(pd.to_numeric(r.get('return_1m'), errors='coerce') * 100)}</td>"
            f"<td>{fmt_ratio(r.get('volume_ratio_30d'))}</td>"
            f"<td>{fmt_cr(r.get('market_cap_cr'))}</td>"
            f"<td style='text-align:left;max-width:320px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;'>{event}</td>"
            f"<td style='text-align:left;' class='{move_cls}'>{tag}</td>"
            f"<td>{conf}</td>"
            "</tr>"
        )

    table_wrap(
        f"""<table class='trm'>
            <thead><tr>
              <th class='left'>Ticker</th>
              <th class='left'>Company</th>
              <th class='left'>Sector</th>
              <th>1D</th>
              <th>1W</th>
              <th>1M</th>
              <th>Vol/30D</th>
              <th>MCap</th>
              <th class='left'>Latest News/Filing</th>
              <th class='left'>Actionability</th>
              <th>Conf.</th>
            </tr></thead>
            <tbody>{rows}</tbody>
           </table>""",
        caption=f"{len(sub)} stocks",
        caption_right="Canonical source: returns_snapshot.csv + filings/news",
    )


def _render_52w_table(title: str, df: pd.DataFrame, col_name: str, ascending: bool = True, limit: int = 12) -> None:
    section_label(title)
    if df.empty or col_name not in df.columns:
        info_block("No 52-week proximity data available.")
        return
    sub = df.dropna(subset=[col_name]).sort_values(col_name, ascending=ascending).head(limit)
    rows = ""
    for _, r in sub.iterrows():
        rows += (
            "<tr>"
            f"<td class='ticker'>{r.get('ticker','')}</td>"
            f"<td class='name'>{r.get('company_name','')}</td>"
            f"<td>{r.get('sector','N/A')}</td>"
            f"<td>{fmt_price(r.get('price'))}</td>"
            f"<td>{fmt_pct(r.get(col_name))}</td>"
            f"<td>{fmt_pct(pd.to_numeric(r.get('return_1m'), errors='coerce') * 100)}</td>"
            "</tr>"
        )
    table_wrap(
        f"""<table class='trm'>
            <thead><tr>
                <th class='left'>Ticker</th>
                <th class='left'>Company</th>
                <th class='left'>Sector</th>
                <th>Price</th>
                <th>Distance</th>
                <th>1M</th>
            </tr></thead>
            <tbody>{rows}</tbody>
        </table>"""
    )


def _build_narrative(indices: dict, snapshot: pd.DataFrame, sector_df: pd.DataFrame) -> dict:
    ret = pd.to_numeric(snapshot.get("return_1d"), errors="coerce").dropna()
    adv = int((ret > 0).sum())
    dec = int((ret < 0).sum())
    top_g = snapshot.dropna(subset=["return_1d"]).nlargest(5, "return_1d")["ticker"].tolist() if not snapshot.empty else []
    top_l = snapshot.dropna(subset=["return_1d"]).nsmallest(5, "return_1d")["ticker"].tolist() if not snapshot.empty else []
    sector_moves = {}
    if not sector_df.empty and "avg_return_1d" in sector_df.columns:
        sector_moves = {
            r["sector"]: round(float(r["avg_return_1d"]) * 100, 2)
            for _, r in sector_df.head(6).iterrows()
            if pd.notna(r.get("avg_return_1d"))
        }
    nifty50_change = indices.get("nifty50", {}).get("change_pct")
    if nifty50_change is not None:
        nifty50_change = f"{nifty50_change:+.2f}%"
    return {
        "nifty50_change": nifty50_change or "N/A",
        "advancers": adv,
        "decliners": dec,
        "top_gainers": top_g,
        "top_losers": top_l,
        "sector_moves": sector_moves,
    }


def _deterministic_market_text(indices: dict, snapshot: pd.DataFrame, sector_df: pd.DataFrame) -> str:
    ret = pd.to_numeric(snapshot.get("return_1d"), errors="coerce").dropna()
    if ret.empty:
        return "No valid return data available."
    adv = int((ret > 0).sum())
    dec = int((ret < 0).sum())
    avg = ret.mean() * 100
    leaders = []
    laggards = []
    if not sector_df.empty and "avg_return_1d" in sector_df.columns:
        s = sector_df.dropna(subset=["avg_return_1d"]).copy()
        leaders = s.nlargest(3, "avg_return_1d")["sector"].tolist()
        laggards = s.nsmallest(3, "avg_return_1d")["sector"].tolist()
    idx = indices.get("nifty50", {})
    idx_text = f"Nifty 50 {idx.get('change_pct', 0):+.2f}%" if idx else "Index data unavailable"
    return (
        f"{idx_text}; breadth was {adv} advancers versus {dec} decliners, with average 1-day move {avg:+.2f}%. "
        f"Sector leadership came from {', '.join(leaders) if leaders else 'N/A'}, while laggards included "
        f"{', '.join(laggards) if laggards else 'N/A'}."
    )


universe_options = list(UNIVERSE_SPECS.keys()) + ["All"]

with st.sidebar:
    html_block('<div class="sec-label">Universe</div>')
    universe_label = st.selectbox("Selected Universe", universe_options, index=2)
    movers_n = st.slider("Rows", 5, 20, 10)

returns_df = load_returns_snapshot()
sector_df = load_sector_performance()
volume_df = load_volume_shocks()
filings_df = load_filings()
news_df = load_news()
quality_log_df = load_data_quality_log()
failed_df = load_failed_tickers()
universe_df = load_universe()
fund_df = load_fundamentals()

filtered_returns = _filter_universe(returns_df, universe_label)
filtered_universe = _filter_universe(universe_df, universe_label)
filtered_volume = _filter_universe(volume_df, universe_label)

quality_report = build_universe_report(
    universe_label=universe_label if universe_label in UNIVERSE_SPECS else "Nifty 500",
    universe_df=filtered_universe,
    prices_df=filtered_returns.rename(columns={"price": "close"}),
    fundamentals_df=fund_df,
    news_df=news_df,
    failed_tickers=failed_df["ticker"].tolist() if not failed_df.empty and "ticker" in failed_df.columns else [],
    source_prices="returns_snapshot.csv",
    source_fundamentals="fundamentals.csv",
    source_news="filings.csv / news.csv",
)

status, last_ts = _latest_quality_status(quality_log_df, dataset="prices")
page_header(
    "Market Command Center",
    "Real-time operating surface for breadth, movers, sectors, and catalyst-linked tape.",
    data_status=(status.title() if isinstance(status, str) else quality_report.fetch_status),
    stamp_text=f"{universe_label} · {quality_report.valid_price_rows}/{quality_report.expected_count} · Updated {last_ts or 'N/A'} IST",
    paused_message=None if quality_report.passes else f"Universe incomplete ({quality_report.valid_price_rows}/{quality_report.expected_count}) — analytics paused",
)

section_label("Index Snapshot")
try:
    indices = fetch_index_snapshot() or {}
except Exception:
    indices = {}

index_config = [
    ("nifty50", "Nifty 50", "NSE"),
    ("niftyNext50", "Nifty Next 50", "NSE"),
    ("nifty500", "Nifty 500", "NSE"),
    ("bankNifty", "Bank Nifty", "NSE"),
    ("sensex", "Sensex", "BSE"),
    ("vix", "India VIX", "NSE"),
]
visible = [(k, l, s) for (k, l, s) in index_config if k in indices and indices[k].get("value") is not None]
if not visible:
    warn_block("Index APIs returned no values. This does not affect the canonical price datasets, but live index cards are unavailable right now.")
else:
    cols = st.columns(len(visible))
    for col, (key, label, source) in zip(cols, visible):
        with col:
            d = indices[key]
            index_card(
                name=label,
                value=f"{d.get('value', 0):,.2f}",
                change=f"{d.get('change_pct', 0):+.2f}%",
                pts=f"{float(d.get('change', 0) or 0):+,.0f}" if d.get("change") is not None else "",
                is_up=None if key == "vix" else (float(d.get("change_pct", 0) or 0) >= 0),
                source=source,
                data_ts=last_ts or "",
            )

brief_lines = build_morning_brief(filtered_returns, sector_df, indices, filings_df, news_df)
html_block(
    f"""
    <div class="hero-panel">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:1rem;flex-wrap:wrap;">
        <div>
          <div class="hero-kicker">Command Center</div>
          <div class="hero-title">Opening Read on the Market</div>
          <div class="hero-sub">Above-the-fold signal before detail: index tone, breadth quality, sector leadership, and the catalysts actually driving tape.</div>
        </div>
        <div style="display:flex;gap:0.55rem;flex-wrap:wrap;justify-content:flex-end;">
          <span class="pill-chip"><strong>Universe</strong>{quality_report.valid_price_rows}/{quality_report.expected_count}</span>
          <span class="pill-chip"><strong>Filings</strong>{len(filings_df)}</span>
          <span class="pill-chip"><strong>News</strong>{len(news_df)}</span>
        </div>
      </div>
    </div>
    """
)
html_block(
    "<div class='surface-box'>"
    "<div class='surface-title'>Deterministic Market Brief</div>"
    "<div class='surface-note'>" + "<br>".join(escape(line) for line in brief_lines) + "</div>"
    "</div>"
)
st.download_button("Copy Morning Brief", data="\n".join(brief_lines), file_name="morning_brief.txt", mime="text/plain")

section_label("Market Breadth")
if not gate(quality_report, "breadth"):
    warn_block("Universe incomplete. Analytics disabled until data quality passes.")
else:
    ret = pd.to_numeric(filtered_returns["return_1d"], errors="coerce").dropna()
    advancers = int((ret > 0).sum())
    decliners = int((ret < 0).sum())
    unchanged = int((ret == 0).sum())
    total = advancers + decliners + unchanged
    near_high = int(filtered_returns["dist_52w_high_pct"].abs().lt(3).sum()) if "dist_52w_high_pct" in filtered_returns.columns else 0
    near_low = int(filtered_returns["dist_52w_low_pct"].abs().lt(3).sum()) if "dist_52w_low_pct" in filtered_returns.columns else 0
    kpis = [
        ("Advancers", str(advancers), f"{(advancers / total * 100):.0f}% positive" if total else "", advancers > decliners),
        ("Decliners", str(decliners), f"{(decliners / total * 100):.0f}% negative" if total else "", decliners > advancers),
        ("Unchanged", str(unchanged), "", None),
        ("A/D Ratio", _safe_ad_ratio(advancers, decliners), "Advancers ÷ Decliners", None),
        ("New 52W Highs", str(near_high), "Within 3% of high", None),
        ("New 52W Lows", str(near_low), "Within 3% of low", None),
    ]
    cols = st.columns(6)
    for col, (label, value, delta, delta_pos) in zip(cols, kpis):
        with col:
            kpi_card(label, value, delta, delta_pos)

tabs = st.tabs([
    "Market Narrative",
    "Top Movers",
    "Volume Shocks",
    "52W Extremes",
    "Sector Intelligence",
    "What Changed Today",
])

filing_map, news_map, catalyst_map = _event_maps(filings_df, news_df)

with tabs[0]:
    section_label("Today's Market Narrative")
    if not gate(quality_report, "ai_summary"):
        warn_block("Narrative disabled because data quality does not pass the 90% gate.")
    else:
        payload = _build_narrative(indices, filtered_returns, sector_df)
        deterministic = _deterministic_market_text(indices, filtered_returns, sector_df)
        ai_text = ai.generate_market_summary(payload)
        ai_box(ai_text if "unavailable" not in ai_text.lower() else deterministic, label="Market Summary")

        section_label("Meeting Talking Points")
        if filtered_returns.empty:
            info_block("No snapshot data available.")
        else:
            top_g = filtered_returns.dropna(subset=["return_1d"]).nlargest(3, "return_1d")
            top_l = filtered_returns.dropna(subset=["return_1d"]).nsmallest(3, "return_1d")
            top_s = sector_df.dropna(subset=["avg_return_1d"]).nlargest(3, "avg_return_1d") if not sector_df.empty else pd.DataFrame()
            points = []
            for _, r in top_s.iterrows():
                points.append(f"{r['sector']} led with average 1D return {r['avg_return_1d'] * 100:+.2f}% across {int(r['valid_return_count'])} stocks.")
            for _, r in top_g.iterrows():
                points.append(f"{r['ticker']} outperformed at {r['return_1d'] * 100:+.2f}% with volume at {fmt_ratio(r.get('volume_ratio_30d'))} of 30D average.")
            for _, r in top_l.iterrows():
                points.append(f"{r['ticker']} lagged at {r['return_1d'] * 100:+.2f}% and should be checked for results, ratings, or management updates.")
            questions = [
                "Which top movers had a clear public catalyst versus pure price action?",
                "Are sector leaders supported by breadth or carried by a few heavyweights?",
                "Which weak names have improving fundamentals despite poor 1M/3M momentum?",
            ]
            st.markdown("\n".join([f"- {p}" for p in points[:9] + questions]), unsafe_allow_html=False)

with tabs[1]:
    if not gate(quality_report, "top_movers"):
        warn_block("Universe incomplete. Top movers disabled until data quality passes.")
    else:
        left, right = st.columns(2)
        with left:
            _render_movers_table("Top Gainers", filtered_returns, movers_n, False, filing_map, news_map, catalyst_map)
        with right:
            _render_movers_table("Top Losers", filtered_returns, movers_n, True, filing_map, news_map, catalyst_map)

with tabs[2]:
    section_label("Volume Shocks")
    if not gate(quality_report, "volume_shocks"):
        warn_block("Volume shock analytics disabled until valid volume coverage reaches the threshold.")
    elif filtered_volume.empty:
        info_block("No volume shocks above threshold.")
    else:
        sub = filtered_volume.sort_values("volume_ratio_30d", ascending=False).head(max(20, movers_n))
        rows = ""
        for _, r in sub.iterrows():
            rows += (
                "<tr>"
                f"<td class='ticker'>{r.get('ticker','')}</td>"
                f"<td class='name'>{r.get('company_name','')}</td>"
                f"<td>{r.get('sector','N/A')}</td>"
                f"<td>{fmt_price(r.get('price'))}</td>"
                f"<td>{fmt_ratio(r.get('volume_ratio_30d'))}</td>"
                f"<td>{fmt_pct(pd.to_numeric(r.get('return_1d'), errors='coerce') * 100)}</td>"
                f"<td>{filing_map.get(str(r.get('ticker','')).upper()) or news_map.get(str(r.get('ticker','')).upper()) or 'No public event linked'}</td>"
                "</tr>"
            )
        table_wrap(
            f"""<table class='trm'>
                <thead><tr>
                    <th class='left'>Ticker</th>
                    <th class='left'>Company</th>
                    <th class='left'>Sector</th>
                    <th>Price</th>
                    <th>Vol/30D</th>
                    <th>1D</th>
                    <th class='left'>Latest News/Filing</th>
                </tr></thead>
                <tbody>{rows}</tbody>
            </table>""",
            caption=f"{len(sub)} qualifying names",
            caption_right="Threshold: volume >= 2x 30D average",
        )

with tabs[3]:
    if not gate(quality_report, "52w_extremes"):
        warn_block("52-week extreme analytics disabled until price coverage reaches the threshold.")
    else:
        left, right = st.columns(2)
        with left:
            _render_52w_table("Near 52-Week High", filtered_returns, "dist_52w_high_pct", ascending=False, limit=12)
        with right:
            _render_52w_table("Near 52-Week Low", filtered_returns, "dist_52w_low_pct", ascending=True, limit=12)

with tabs[4]:
    section_label("Sector Performance")
    if not gate(quality_report, "sector_heatmap"):
        warn_block("Sector heatmap disabled until sector labels and return coverage reach the threshold.")
    elif sector_df.empty:
        info_block("No sector performance file available.")
    else:
        fig = sector_heatmap(sector_df.rename(columns={"avg_return_1d": "return_1d", "market_cap_sum_cr": "market_cap_cr"}), metric="return_1d", title="Sector Performance")
        st.plotly_chart(fig, use_container_width=True)

        rows = ""
        for _, r in sector_df.sort_values("avg_return_1d", ascending=False).iterrows():
            rows += (
                "<tr>"
                f"<td class='name'>{r.get('sector','')}</td>"
                f"<td>{int(r.get('stock_count', 0) or 0)}</td>"
                f"<td>{int(r.get('advancers', 0) or 0)}</td>"
                f"<td>{int(r.get('decliners', 0) or 0)}</td>"
                f"<td>{fmt_pct(pd.to_numeric(r.get('avg_return_1d'), errors='coerce') * 100)}</td>"
                f"<td>{fmt_pct(pd.to_numeric(r.get('avg_return_1w'), errors='coerce') * 100)}</td>"
                f"<td>{fmt_pct(pd.to_numeric(r.get('avg_return_1m'), errors='coerce') * 100)}</td>"
                f"<td>{fmt_cr(r.get('market_cap_sum_cr'))}</td>"
                "</tr>"
            )
        table_wrap(
            f"""<table class='trm'>
                <thead><tr>
                    <th class='left'>Sector</th>
                    <th>Stocks</th>
                    <th>Adv.</th>
                    <th>Dec.</th>
                    <th>Avg 1D</th>
                    <th>Avg 1W</th>
                    <th>Avg 1M</th>
                    <th>MCap</th>
                </tr></thead>
                <tbody>{rows}</tbody>
            </table>"""
        )

with tabs[5]:
    section_label("What Changed Today")
    if filtered_returns.empty:
        info_block("No canonical snapshot available.")
    else:
        top_moves = filtered_returns.dropna(subset=["return_1d"]).copy()
        top_moves = pd.concat([top_moves.nlargest(5, "return_1d"), top_moves.nsmallest(5, "return_1d")]).drop_duplicates("ticker")
        bullets = []
        for _, r in top_moves.iterrows():
            ticker = str(r.get("ticker", "")).upper()
            event = filing_map.get(ticker) or news_map.get(ticker) or "No clear public catalyst found."
            bullets.append(f"- {ticker}: {r['return_1d'] * 100:+.2f}% — {event}")
        recent_filings = filings_df.head(5) if not filings_df.empty else pd.DataFrame()
        for _, r in recent_filings.iterrows():
            ticker = str(r.get("ticker", "")).upper()
            bullets.append(f"- {ticker}: filing — {r.get('subject','')}")
        st.markdown("\n".join(bullets[:12]) if bullets else "No material public changes found.", unsafe_allow_html=False)

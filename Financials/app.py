"""
Neo Secondaries Intelligence Platform
Internal research tool — Neo Multi Family Office
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

from utils.styling import (
    inject_css, render_kpi_card, render_section_header, render_analyst_note,
    render_insight_card, render_warning_badge, render_source_confidence_badge,
    render_manager_card, render_segment_card, render_playbook_item,
    render_product_card, format_usd_bn, format_pct, format_multiple,
    get_plotly_layout, GOLD, BLUE, RED, GREEN, AMBER, BORDER, TEXT, TEXT2,
    TEXT3, CARD, BG2, STRATEGY_COLORS, PURPLE, SLATE,
)
from utils.data_loader import (
    load_funds, load_performance, load_manager_profiles,
    load_market_segments, load_sources, load_deals, load_lp_commitments,
    save_csv, funds_with_performance,
)
from utils.analytics import apply_flags_to_df, to_num, is_na
from utils.memo_generator import generate_weekly_memo

# ── Config ────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Neo Secondaries Intelligence Platform",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon=None,
)
inject_css()

# ── Load data ─────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def get_data():
    funds = load_funds()
    perf = load_performance()
    managers = load_manager_profiles()
    segments = load_market_segments()
    sources = load_sources()
    deals = load_deals()
    lp = load_lp_commitments()
    if not perf.empty and not funds.empty:
        perf = apply_flags_to_df(perf, funds)
    return funds, perf, managers, segments, sources, deals, lp

funds_df, perf_df, managers_df, segments_df, sources_df, deals_df, lp_df = get_data()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"""
    <div style="padding:16px 0 20px 0;border-bottom:1px solid {BORDER};margin-bottom:20px;">
        <div style="font-size:13px;font-weight:700;color:{TEXT};
                    letter-spacing:0.04em;">NEO</div>
        <div style="font-size:10px;color:{GOLD};font-weight:700;
                    text-transform:uppercase;letter-spacing:0.1em;margin-top:2px;">
            Secondaries Intelligence Platform</div>
        <div style="font-size:10px;color:{TEXT3};margin-top:6px;">
            Internal Research Tool</div>
    </div>""", unsafe_allow_html=True)

    PAGES = [
        "Executive Brief",
        "Fund Universe",
        "Performance Quality",
        "Manager Strategy",
        "Market Map",
        "Neo Playbook",
        "Source Library",
        "Data Import",
        "Weekly Memo",
    ]
    page = st.radio("", PAGES, label_visibility="collapsed")

    st.markdown(f"""
    <div style="margin-top:32px;padding-top:16px;border-top:1px solid {BORDER};">
        <div style="font-size:10px;color:{TEXT3};line-height:1.7;">
            <div style="font-weight:700;color:{TEXT3};text-transform:uppercase;
                        letter-spacing:0.07em;margin-bottom:8px;">Data Status</div>
            <div>Funds tracked: {len(funds_df)}</div>
            <div>Performance records: {len(perf_df)}</div>
            <div>Sources logged: {len(sources_df)}</div>
            <div style="margin-top:8px;color:{AMBER};">
                LP-reported data only.<br>Not official fund returns.</div>
        </div>
    </div>""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# PAGE 1: EXECUTIVE BRIEF
# ─────────────────────────────────────────────────────────────────────────────
def page_executive_brief():
    st.markdown(f"""
    <div style="margin-bottom:24px;">
        <div style="font-size:22px;font-weight:700;color:{TEXT};
                    letter-spacing:-0.01em;">Global Secondaries Intelligence</div>
        <div style="font-size:13px;color:{TEXT2};margin-top:6px;">
            Fundraising scale, performance quality, strategy mix, and implications for Neo.
            &nbsp;|&nbsp; As of {datetime.now().strftime("%d %B %Y")}
        </div>
    </div>""", unsafe_allow_html=True)

    # KPI row
    perf_fund_ids = funds_with_performance(funds_df, perf_df)
    needs_review_count = len(funds_df[
        funds_df["source_confidence"].isin(["Low", "Medium"]) |
        funds_df["target_size_usd_bn"].isin(["NEEDS_MANUAL_REVIEW", "NOT_AVAILABLE_PUBLICLY"])
    ]) if not funds_df.empty else 0
    total_aum = funds_df["fund_size_usd_bn"].dropna().sum() if not funds_df.empty else 0
    closed_count = len(funds_df[funds_df["status"] == "Closed"]) if not funds_df.empty else 0
    market_count = len(funds_df[funds_df["status"] == "Fundraising"]) if not funds_df.empty else 0

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1: st.markdown(render_kpi_card("Funds Tracked", str(len(funds_df))), unsafe_allow_html=True)
    with c2: st.markdown(render_kpi_card("Total AUM Tracked", f"${total_aum:.0f}bn"), unsafe_allow_html=True)
    with c3: st.markdown(render_kpi_card("Closed Funds", str(closed_count)), unsafe_allow_html=True)
    with c4: st.markdown(render_kpi_card("In Market", str(market_count), "fundraising"), unsafe_allow_html=True)
    with c5: st.markdown(render_kpi_card("With Performance Data", str(len(perf_fund_ids)), "LP-reported"), unsafe_allow_html=True)
    with c6: st.markdown(render_kpi_card("Require Review", str(needs_review_count), "medium/low confidence"), unsafe_allow_html=True)

    st.markdown("<hr>", unsafe_allow_html=True)

    col_left, col_right = st.columns([3, 2])

    with col_left:
        st.markdown(render_section_header("What Matters Now",
            "Key analytical signals for the Neo secondaries strategy"), unsafe_allow_html=True)
        signals = [
            ("Mega-fund scale is accelerating, but scale may pressure future returns.",
             "As Ardian, Lexington, and Blackstone raise $20–30bn vehicles, deployment pressure "
             "and narrower discounts become structural risks. Neo should not compete on scale.", "warning"),
            ("DPI matters more than headline IRR for mature secondaries funds.",
             "DPI reflects actual cash returned to LPs. A 27% IRR with 0.08x DPI (Ardian ASF IX) "
             "is mostly paper. A 13% IRR with 1.07x DPI (Ardian ASF VII) is real cash in hand.", "neutral"),
            ("GP-led continuation vehicles are now a core part of the secondaries market.",
             "ICG Strategic Equity V raised $11bn at 83% above target. GP-led is not a niche — "
             "it is now a standalone institutional strategy.", "neutral"),
            ("Private wealth access is becoming strategically important.",
             "AlpInvest, Goldman, and Lexington are all packaging institutional secondaries for "
             "HNI and family-office clients. Neo's differentiation window is narrowing.", "warning"),
            ("Neo should copy discipline, not scale.",
             "Data discipline, co-investment access, reporting quality, and India-specific sourcing "
             "are the levers Neo controls. $30bn fund replication is not.", "positive"),
        ]
        for title, body, level in signals:
            st.markdown(render_insight_card(f"<strong>{title}</strong><br>{body}", level),
                       unsafe_allow_html=True)

    with col_right:
        st.markdown(render_section_header("This Week's Watchlist"), unsafe_allow_html=True)

        if not funds_df.empty:
            in_market = funds_df[funds_df["status"] == "Fundraising"]
            if len(in_market):
                st.markdown(f'<div style="font-size:10px;color:{TEXT3};font-weight:700;'
                           f'text-transform:uppercase;letter-spacing:0.07em;margin-bottom:6px;">'
                           f'Funds in Market</div>', unsafe_allow_html=True)
                for _, r in in_market.iterrows():
                    size = f"${r['fund_size_usd_bn']:.1f}bn" if pd.notna(r.get("fund_size_usd_bn")) else "TBC"
                    st.markdown(
                        f'<div style="background:{BG2};border:1px solid {BORDER};border-radius:3px;'
                        f'padding:8px 12px;margin:4px 0;font-size:11px;color:{TEXT2};">'
                        f'<span style="color:{TEXT};font-weight:600;">{r["fund_name"]}</span>'
                        f' &nbsp;·&nbsp; {size}'
                        f' &nbsp;·&nbsp; {render_source_confidence_badge(r.get("source_confidence","?"))}'
                        f'</div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        if not perf_df.empty:
            flags_of_interest = perf_df[
                perf_df["quality_flag"].str.contains("limited cash realization|NAV-heavy|Too young", na=False)
            ]
            if len(flags_of_interest):
                st.markdown(f'<div style="font-size:10px;color:{TEXT3};font-weight:700;'
                           f'text-transform:uppercase;letter-spacing:0.07em;margin-bottom:6px;">'
                           f'Performance Flags</div>', unsafe_allow_html=True)
                for _, r in flags_of_interest.head(5).iterrows():
                    label = r.get("fund_label") or r.get("fund_id")
                    irr = format_pct(r.get("net_irr_pct"))
                    dpi = format_multiple(r.get("dpi"))
                    flag_short = r["quality_flag"].split(" | ")[0][:50]
                    st.markdown(
                        f'<div style="background:{BG2};border:1px solid {BORDER};'
                        f'border-left:3px solid {AMBER};border-radius:0 3px 3px 0;'
                        f'padding:8px 12px;margin:4px 0;">'
                        f'<div style="font-size:11px;color:{TEXT};font-weight:600;">{label}</div>'
                        f'<div style="font-size:10px;color:{TEXT3};">IRR {irr} · DPI {dpi}</div>'
                        f'<div style="font-size:10px;color:{AMBER};margin-top:2px;">{flag_short}</div>'
                        f'</div>', unsafe_allow_html=True)

        missing_perf = funds_df[
            ~funds_df["fund_id"].isin(perf_fund_ids) & (funds_df["status"] == "Closed")
        ] if not funds_df.empty else pd.DataFrame()
        if len(missing_perf):
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown(f'<div style="font-size:10px;color:{TEXT3};font-weight:700;'
                       f'text-transform:uppercase;letter-spacing:0.07em;margin-bottom:6px;">'
                       f'No Performance Data (closed funds)</div>', unsafe_allow_html=True)
            for _, r in missing_perf.head(4).iterrows():
                st.markdown(
                    f'<div style="background:{BG2};border:1px solid {BORDER};'
                    f'border-left:3px solid {RED};border-radius:0 3px 3px 0;'
                    f'padding:7px 12px;margin:3px 0;font-size:11px;color:{TEXT2};">'
                    f'{r["fund_name"]} — {render_warning_badge("NEEDS DATA","red")}'
                    f'</div>', unsafe_allow_html=True)

    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown(render_section_header("Strategic Read"), unsafe_allow_html=True)
    st.markdown(f"""
    <div style="background:{CARD};border:1px solid {BORDER};border-left:4px solid {GOLD};
                padding:20px 24px;border-radius:0 4px 4px 0;max-width:900px;">
        <div style="font-size:13px;color:{TEXT};line-height:1.8;font-style:italic;">
        "The secondaries market is no longer just a discount-to-NAV trade. The best platforms
        combine sourcing advantage, data depth, pricing discipline, GP access, and cash
        realization. For Neo, the opportunity is not to replicate a $20–30bn global fund.
        The opportunity is to build a sharper intelligence and access layer for family-office
        clients: global manager access, India-specific secondary sourcing, co-investment
        sidecars, and transparent DPI/TVPI reporting."
        </div>
    </div>""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# PAGE 2: FUND UNIVERSE
# ─────────────────────────────────────────────────────────────────────────────
def page_fund_universe():
    st.markdown(f'<div style="font-size:20px;font-weight:700;color:{TEXT};">'
               f'Fund Universe</div>', unsafe_allow_html=True)
    st.markdown(f'<div style="font-size:12px;color:{TEXT2};margin-bottom:20px;">'
               f'All tracked global private equity secondaries funds. '
               f'Missing values are explicit — not hidden.</div>', unsafe_allow_html=True)

    if funds_df.empty:
        st.error("funds.csv not found. Add data/funds.csv to the repository.")
        return

    # Filters
    with st.expander("Filters", expanded=True):
        fc1, fc2, fc3, fc4 = st.columns(4)
        with fc1:
            gps = ["All"] + sorted(funds_df["gp_name"].dropna().unique().tolist())
            sel_gp = st.selectbox("GP", gps)
        with fc2:
            strats = ["All"] + sorted(funds_df["strategy_type"].dropna().unique().tolist())
            sel_strat = st.selectbox("Strategy", strats)
        with fc3:
            statuses = ["All"] + sorted(funds_df["status"].dropna().unique().tolist())
            sel_status = st.selectbox("Status", statuses)
        with fc4:
            confs = ["All", "High", "Medium", "Low"]
            sel_conf = st.selectbox("Source Confidence", confs)

    df = funds_df.copy()
    if sel_gp != "All": df = df[df["gp_name"] == sel_gp]
    if sel_strat != "All": df = df[df["strategy_type"] == sel_strat]
    if sel_status != "All": df = df[df["status"] == sel_status]
    if sel_conf != "All": df = df[df["source_confidence"] == sel_conf]

    perf_ids = funds_with_performance(funds_df, perf_df)

    # Table
    st.markdown(render_section_header(f"Fund Table — {len(df)} funds"), unsafe_allow_html=True)
    display = df[[
        "gp_name", "fund_name", "vintage_year", "fund_size_usd_bn",
        "target_size_usd_bn", "percent_above_target", "status",
        "final_close_date", "strategy_type", "source_confidence", "neo_takeaway",
    ]].copy()
    display.columns = [
        "GP", "Fund", "Vintage", "Size ($bn)", "Target ($bn)",
        "% Above Target", "Status", "Close Date", "Strategy",
        "Confidence", "Neo Takeaway",
    ]
    display["Size ($bn)"] = display["Size ($bn)"].apply(
        lambda v: f"{float(v):.1f}" if pd.notna(v) else "—"
    )
    st.dataframe(display, use_container_width=True, height=360)
    st.download_button("Export Fund Table CSV",
                       data=df.to_csv(index=False),
                       file_name="neo_funds.csv", mime="text/csv")

    st.markdown("<hr>", unsafe_allow_html=True)

    # Charts
    chart_df = df[df["fund_size_usd_bn"].notna()].sort_values("fund_size_usd_bn")
    c1, c2 = st.columns([3, 2])
    with c1:
        st.markdown(render_section_header("Fund Size by Fund (USD bn)"), unsafe_allow_html=True)
        if len(chart_df):
            chart_df["color"] = chart_df["strategy_type"].map(STRATEGY_COLORS).fillna(TEXT3)
            fig = go.Figure()
            for strat, grp in chart_df.groupby("strategy_type"):
                fig.add_trace(go.Bar(
                    y=grp["fund_name"],
                    x=grp["fund_size_usd_bn"],
                    orientation="h",
                    name=strat,
                    marker_color=STRATEGY_COLORS.get(strat, TEXT3),
                    text=grp["fund_size_usd_bn"].apply(lambda v: f"${v:.1f}bn"),
                    textposition="outside",
                    textfont=dict(size=10, color=TEXT2),
                    hovertemplate="<b>%{y}</b><br>Size: $%{x:.1f}bn<extra></extra>",
                ))
            layout = get_plotly_layout()
            layout.update(barmode="stack", height=480, showlegend=True,
                         title=dict(text="", font=dict(size=12)))
            fig.update_layout(**layout)
            fig.update_xaxes(title="USD bn")
            fig.update_yaxes(title="")
            st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.markdown(render_section_header("AUM by Strategy (USD bn)"), unsafe_allow_html=True)
        strat_aum = df.groupby("strategy_type")["fund_size_usd_bn"].sum().reset_index()
        strat_aum = strat_aum[strat_aum["fund_size_usd_bn"] > 0].sort_values("fund_size_usd_bn", ascending=False)
        if len(strat_aum):
            fig2 = go.Figure(go.Bar(
                x=strat_aum["strategy_type"],
                y=strat_aum["fund_size_usd_bn"],
                marker_color=[STRATEGY_COLORS.get(s, TEXT3) for s in strat_aum["strategy_type"]],
                text=strat_aum["fund_size_usd_bn"].apply(lambda v: f"${v:.0f}bn"),
                textposition="outside",
                textfont=dict(size=10, color=TEXT2),
            ))
            layout2 = get_plotly_layout()
            layout2.update(height=480, showlegend=False)
            fig2.update_layout(**layout2)
            fig2.update_xaxes(tickangle=25, tickfont=dict(size=9))
            fig2.update_yaxes(title="USD bn")
            st.plotly_chart(fig2, use_container_width=True)

    st.markdown(render_analyst_note(
        "Fund size is not the same as fund quality. In secondaries, scale helps with sourcing "
        "and execution, but excessive fund size can pressure deployment and reduce discount "
        "capture. This page should be used to understand market power, not to rank investment "
        "attractiveness mechanically."
    ), unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# PAGE 3: PERFORMANCE QUALITY
# ─────────────────────────────────────────────────────────────────────────────
def page_performance_quality():
    st.markdown(f'<div style="font-size:20px;font-weight:700;color:{TEXT};">'
               f'Performance Quality</div>', unsafe_allow_html=True)

    st.markdown(f"""
    <div style="background:{BG2};border:1px solid {AMBER};border-radius:4px;
                padding:12px 16px;margin-bottom:20px;">
        <div style="font-size:10px;color:{AMBER};font-weight:700;
                    text-transform:uppercase;letter-spacing:0.08em;margin-bottom:4px;">
            Data Integrity Warning</div>
        <div style="font-size:12px;color:{TEXT2};">
            All performance data is sourced from the <strong>CalSTRS LP-level capital account
            table (June 30, 2025)</strong>. These are a single LP's capital account returns,
            not official fund-level GP performance. Do not cite as fund returns.
            Predecessor benchmarks are labeled separately.
        </div>
    </div>""", unsafe_allow_html=True)

    if perf_df.empty:
        st.warning("No performance data loaded. Add data/performance.csv.")
        return

    merged = perf_df.copy()
    if not funds_df.empty:
        fund_map = funds_df.set_index("fund_id")[["gp_name", "fund_name", "vintage_year"]].to_dict("index")
        merged["gp_name"] = merged["fund_id"].map(lambda x: fund_map.get(x, {}).get("gp_name", ""))
        merged["f_name"] = merged["fund_id"].map(lambda x: fund_map.get(x, {}).get("fund_name", ""))
        merged["vintage_year"] = merged["fund_id"].map(lambda x: fund_map.get(x, {}).get("vintage_year"))

    is_pred = merged.get("is_predecessor_benchmark", pd.Series(["No"] * len(merged)))
    direct = merged[is_pred.isin(["No", "FALSE", "False", "false", "0", ""])]
    predecessors = merged[~is_pred.isin(["No", "FALSE", "False", "false", "0", ""])]

    tab1, tab2 = st.tabs(["Direct Fund Performance", "Predecessor Benchmarks"])

    def render_perf_table(df_in):
        if df_in.empty:
            st.info("No records.")
            return
        cols_map = {
            "fund_label": "Fund (LP Label)", "gp_name": "GP",
            "vintage_year": "Vintage", "net_irr_pct": "Net IRR %",
            "dpi": "DPI", "rvpi": "RVPI", "tvpi": "TVPI",
            "as_of_date": "As-of", "source_type": "Source",
            "confidence_level": "Confidence", "quality_flag": "Quality Flag",
        }
        display_cols = [c for c in cols_map if c in df_in.columns]
        out = df_in[display_cols].rename(columns=cols_map).copy()
        for col in ["Net IRR %", "DPI", "RVPI", "TVPI"]:
            if col in out.columns:
                out[col] = out[col].apply(lambda v: f"{float(v):.2f}" if pd.notna(v) else "—")
        st.dataframe(out, use_container_width=True, height=320)
        st.download_button("Export CSV", data=df_in.to_csv(index=False),
                           file_name="neo_performance.csv", mime="text/csv")

    with tab1:
        render_perf_table(direct)
    with tab2:
        st.markdown(f'<div style="font-size:11px;color:{AMBER};padding:8px 0;">'
                   f'These are predecessor funds used as strategy benchmarks. '
                   f'They are NOT the same as the tracked funds in the Fund Universe.</div>',
                   unsafe_allow_html=True)
        render_perf_table(predecessors)

    st.markdown("<hr>", unsafe_allow_html=True)

    # Scatter charts
    scatter_df = merged.copy()
    scatter_df["irr_n"] = pd.to_numeric(scatter_df["net_irr_pct"], errors="coerce")
    scatter_df["dpi_n"] = pd.to_numeric(scatter_df["dpi"], errors="coerce")
    scatter_df["tvpi_n"] = pd.to_numeric(scatter_df["tvpi"], errors="coerce")
    scatter_df["size_n"] = scatter_df["fund_id"].map(
        funds_df.set_index("fund_id")["fund_size_usd_bn"].to_dict()
        if not funds_df.empty else {}
    )
    scatter_df["label"] = scatter_df.apply(
        lambda r: r.get("fund_label") or r.get("fund_id"), axis=1
    )
    scatter_df["is_pred"] = is_pred.values

    sc1, sc2 = st.columns(2)

    with sc1:
        st.markdown(render_section_header("Net IRR vs DPI",
            "High IRR + Low DPI = mostly paper return"), unsafe_allow_html=True)
        s1 = scatter_df.dropna(subset=["irr_n", "dpi_n"])
        if len(s1):
            fig = go.Figure()
            for pred_flag, grp in s1.groupby("is_pred"):
                marker_sym = "diamond" if pred_flag not in ("No", "FALSE", "False", "false", "0", "") else "circle"
                name = "Predecessor Benchmark" if pred_flag not in ("No", "FALSE", "False", "false", "0", "") else "Direct Fund"
                fig.add_trace(go.Scatter(
                    x=grp["dpi_n"], y=grp["irr_n"],
                    mode="markers+text",
                    name=name,
                    text=grp["label"],
                    textposition="top center",
                    textfont=dict(size=9, color=TEXT2),
                    marker=dict(
                        size=grp["size_n"].fillna(8).clip(6, 20).astype(float),
                        color=GOLD if pred_flag not in ("No", "FALSE", "False", "false", "0", "") else BLUE,
                        symbol=marker_sym,
                        line=dict(color=BORDER, width=1),
                    ),
                    customdata=grp[["gp_name", "vintage_year", "source_type", "quality_flag"]].fillna("").values,
                    hovertemplate=(
                        "<b>%{text}</b><br>"
                        "GP: %{customdata[0]}<br>"
                        "Vintage: %{customdata[1]}<br>"
                        "DPI: %{x:.2f}x<br>IRR: %{y:.1f}%<br>"
                        "Source: %{customdata[2]}<br>"
                        "Flag: %{customdata[3]}<extra></extra>"
                    ),
                ))
            layout = get_plotly_layout()
            layout.update(height=420, title=dict(text=""))
            fig.update_layout(**layout)
            fig.add_hline(y=15, line_dash="dot", line_color=TEXT3, line_width=1,
                         annotation_text="15% IRR", annotation_font_size=9)
            fig.add_vline(x=0.5, line_dash="dot", line_color=TEXT3, line_width=1,
                         annotation_text="0.5x DPI", annotation_font_size=9)
            fig.add_vline(x=1.0, line_dash="dash", line_color=GREEN, line_width=1,
                         annotation_text="1.0x (returned)", annotation_font_size=9)
            fig.update_xaxes(title="DPI (x)")
            fig.update_yaxes(title="Net IRR (%)")
            st.plotly_chart(fig, use_container_width=True)
            st.markdown(f'<div style="font-size:10px;color:{TEXT3};">'
                       f'Top-left = high paper IRR, low realization. '
                       f'Marker size = fund size. Diamond = predecessor benchmark.</div>',
                       unsafe_allow_html=True)

    with sc2:
        st.markdown(render_section_header("TVPI vs DPI",
            "Gap between TVPI and DPI = unrealized NAV"), unsafe_allow_html=True)
        s2 = scatter_df.dropna(subset=["tvpi_n", "dpi_n"])
        if len(s2):
            fig2 = go.Figure()
            for pred_flag, grp in s2.groupby("is_pred"):
                marker_sym = "diamond" if pred_flag not in ("No", "FALSE", "False", "false", "0", "") else "circle"
                name = "Predecessor" if pred_flag not in ("No", "FALSE", "False", "false", "0", "") else "Direct Fund"
                fig2.add_trace(go.Scatter(
                    x=grp["dpi_n"], y=grp["tvpi_n"],
                    mode="markers+text",
                    name=name,
                    text=grp["label"],
                    textposition="top center",
                    textfont=dict(size=9, color=TEXT2),
                    marker=dict(
                        size=grp["size_n"].fillna(8).clip(6, 20).astype(float),
                        color=GOLD if pred_flag not in ("No", "FALSE", "False", "false", "0", "") else BLUE,
                        symbol=marker_sym,
                        line=dict(color=BORDER, width=1),
                    ),
                    customdata=grp[["gp_name", "vintage_year", "quality_flag"]].fillna("").values,
                    hovertemplate=(
                        "<b>%{text}</b><br>"
                        "DPI: %{x:.2f}x<br>TVPI: %{y:.2f}x<br>"
                        "GP: %{customdata[0]}<br>"
                        "Flag: %{customdata[2]}<extra></extra>"
                    ),
                ))
            layout2 = get_plotly_layout()
            layout2.update(height=420)
            fig2.update_layout(**layout2)
            fig2.add_shape(type="line", x0=0, y0=0, x1=2, y1=2,
                          line=dict(dash="dot", color=TEXT3, width=1))
            fig2.add_vline(x=1.0, line_dash="dash", line_color=GREEN, line_width=1,
                          annotation_text="1.0x DPI", annotation_font_size=9)
            fig2.update_xaxes(title="DPI (x)")
            fig2.update_yaxes(title="TVPI (x)")
            st.plotly_chart(fig2, use_container_width=True)
            st.markdown(f'<div style="font-size:10px;color:{TEXT3};">'
                       f'Distance above diagonal = unrealized NAV component. '
                       f'Closer to diagonal = more realized.</div>',
                       unsafe_allow_html=True)

    st.markdown(render_analyst_note(
        "Secondaries funds can show attractive IRR because they buy mature assets and may "
        "receive distributions quickly. DPI is the harder test because it measures actual cash "
        "returned. A high-IRR, low-DPI fund may still be mostly mark-driven, while a slightly "
        "lower-IRR fund with strong DPI may be more valuable for family-office clients seeking "
        "liquidity, recycling, and evidence of realization."
    ), unsafe_allow_html=True)

    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown(render_section_header("Why DPI Matters"), unsafe_allow_html=True)
    dpi_points = [
        ("IRR is timing-sensitive",
         "IRR calculations are sensitive to when capital is called and when distributions arrive. "
         "A fund that calls capital late and distributes early will show an artificially high IRR."),
        ("TVPI includes unrealized NAV",
         "TVPI = (Distributed + NAV) / Contributed. The NAV component is a mark, not cash. "
         "It may be revised down in a correction."),
        ("DPI is realized cash",
         "DPI = Distributed / Contributed. This is cash back in the LP's account. "
         "It cannot be revised away by a revaluation."),
        ("Mature secondaries should outperform buyout on DPI",
         "Because secondaries buy seasoned portfolios, they should return capital faster "
         "than primary funds. Low DPI on a mature secondaries fund is a warning sign."),
        ("For Neo clients, DPI and transparency matter most",
         "Family-office clients care about actual cash realization, portfolio transparency, "
         "and evidence of execution. Paper marks are not bankable."),
    ]
    for title, body in dpi_points:
        st.markdown(render_playbook_item(title, body), unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# PAGE 4: MANAGER STRATEGY
# ─────────────────────────────────────────────────────────────────────────────
def page_manager_strategy():
    st.markdown(f'<div style="font-size:20px;font-weight:700;color:{TEXT};">'
               f'Manager Strategy</div>', unsafe_allow_html=True)
    st.markdown(f'<div style="font-size:12px;color:{TEXT2};margin-bottom:20px;">'
               f'Strategic assessment of each GP — what they do best, the risks, and what Neo can learn.'
               f'</div>', unsafe_allow_html=True)

    if managers_df.empty:
        st.error("data/manager_profiles.csv not found.")
        return

    aum_by_gp = funds_df.groupby("gp_name")["fund_size_usd_bn"].sum().to_dict() if not funds_df.empty else {}
    count_by_gp = funds_df.groupby("gp_name")["fund_id"].count().to_dict() if not funds_df.empty else {}

    for _, row in managers_df.iterrows():
        gp = row.get("gp_name", "")
        st.markdown(render_manager_card(
            gp_name=gp,
            archetype=row.get("archetype", ""),
            edge=row.get("edge", ""),
            risk=row.get("risk", ""),
            neo_copy=row.get("neo_copy", ""),
            neo_avoid=row.get("neo_avoid", ""),
            analyst_note=row.get("analyst_note", ""),
            fund_count=count_by_gp.get(gp, 0),
            total_aum=aum_by_gp.get(gp, 0),
        ), unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# PAGE 5: MARKET MAP
# ─────────────────────────────────────────────────────────────────────────────
def page_market_map():
    st.markdown(f'<div style="font-size:20px;font-weight:700;color:{TEXT};">'
               f'Secondaries Market Map</div>', unsafe_allow_html=True)
    st.markdown(f'<div style="font-size:12px;color:{TEXT2};margin-bottom:20px;">'
               f'Strategic landscape of secondaries sub-strategies — definition, growth drivers, '
               f'return profile, key risks, and Neo relevance.</div>', unsafe_allow_html=True)

    if segments_df.empty:
        st.error("data/market_segments.csv not found.")
        return

    for _, row in segments_df.iterrows():
        st.markdown(render_segment_card(
            segment=row.get("segment", ""),
            definition=row.get("definition", ""),
            growth_driver=row.get("growth_driver", ""),
            return_driver=row.get("return_driver", ""),
            key_risk=row.get("key_risk", ""),
            neo_relevance=row.get("neo_relevance", ""),
        ), unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# PAGE 6: NEO PLAYBOOK
# ─────────────────────────────────────────────────────────────────────────────
def page_neo_playbook():
    st.markdown(f'<div style="font-size:20px;font-weight:700;color:{TEXT};">'
               f'Neo Playbook</div>', unsafe_allow_html=True)
    st.markdown(f'<div style="font-size:12px;color:{TEXT2};margin-bottom:20px;">'
               f'How to build a high-quality secondaries capability at Neo — '
               f'principles, product architecture, IC checklists, and mistakes to avoid.</div>',
               unsafe_allow_html=True)

    tab_a, tab_b, tab_c, tab_d, tab_e = st.tabs([
        "What Makes a Fund Successful", "What Neo Should Build",
        "Product Architecture", "IC Checklists", "Mistakes to Avoid",
    ])

    with tab_a:
        st.markdown(render_section_header("What Makes a Secondaries Fund Successful"), unsafe_allow_html=True)
        items = [
            ("Sourcing Advantage",
             "Access to deal flow before it becomes widely competitive. The best platforms have "
             "direct LP relationships, GP coverage, and intermediary networks built over decades."),
            ("Data Advantage",
             "Proprietary benchmarking databases, NAV history, and performance tracking across "
             "hundreds of GPs and thousands of fund interests. Data advantage drives pricing edge."),
            ("Pricing Discipline",
             "The ability to value a portfolio of fund interests accurately and hold firm on "
             "discount requirements. Pricing discipline protects downside more than any other factor."),
            ("DPI Realization",
             "Ultimately, cash returned to LPs is the measure of execution. A fund with consistent "
             "DPI delivery proves the underwriting model, not just the mark-to-market."),
            ("GP Relationship Access",
             "Direct GP relationships enable co-investment, early deal access, and information "
             "advantage in GP-led transactions where the sponsor controls the process."),
            ("Portfolio Construction",
             "Vintage diversification, manager diversification, and sector/geography balance reduce "
             "idiosyncratic risk across a large portfolio of fund interests."),
            ("Conflict Management in GP-led Deals",
             "GP-led transactions involve structural conflicts between the GP's interest and LP "
             "liquidity rights. Best-in-class managers require fairness opinions and competitive processes."),
            ("Ability to Underwrite NAV Quality",
             "Stale marks, aggressive valuations, and overstated NAVs are the primary underwriting "
             "risk in secondaries. The ability to independently assess NAV quality is a core competency."),
            ("Unfunded Commitment Management",
             "LP-led portfolio transactions include unfunded commitments to existing funds. "
             "Managing the timing and size of these future draws requires active modeling."),
            ("Reporting Transparency",
             "LPs increasingly demand look-through transparency on underlying portfolio exposures, "
             "DPI attribution, and data source quality. Transparency is a competitive advantage."),
        ]
        for title, body in items:
            st.markdown(render_playbook_item(title, body), unsafe_allow_html=True)

    with tab_b:
        st.markdown(render_section_header("What Neo Should Implement"), unsafe_allow_html=True)
        bullets = [
            "Build a proprietary secondaries intelligence database tracking confirmed public data and paid-database data separately.",
            "Maintain source-confidence tags for every data point. Never present unverified data as fact.",
            "Start with curated access and co-investments rather than a blind mega-fund allocation.",
            "Build India-specific sourcing through AIF stakes, VC fund extensions, founder and employee liquidity, and family-office fund interests.",
            "Create separate IC templates for LP-led and GP-led secondaries — the risk frameworks are materially different.",
            "Report DPI, TVPI, RVPI, and data source quality clearly in all LP-facing materials.",
            "Build a quarterly Neo Secondaries Intelligence Report for internal and client education.",
            "Establish a systematic GP coverage program tracking the top 50 Indian and 20 global GPs for secondaries opportunities.",
        ]
        for b in bullets:
            st.markdown(render_insight_card(b, "positive"), unsafe_allow_html=True)

    with tab_c:
        st.markdown(render_section_header("Recommended Neo Product Architecture"), unsafe_allow_html=True)
        products = [
            ("Core Diversified Secondaries Allocation",
             "Global diversified exposure through established managers (Ardian, Lexington, AlpInvest).",
             "Lower-risk private markets allocation; institutional LP clients.",
             "Fee layers, limited look-through control, no India-specific exposure."),
            ("India Private Markets Liquidity Sleeve",
             "Source India-specific AIF, VC, and family-office fund interests seeking liquidity.",
             "Clients wanting differentiated India-specific private markets exposure.",
             "Sourcing depth, valuation opacity, legal and regulatory complexity."),
            ("Deal-by-Deal Co-Investment Club",
             "Give larger family-office clients access to high-conviction secondaries deals alongside top-tier funds.",
             "Sophisticated family offices with $5m+ allocation capacity.",
             "Concentration risk, deal selection discipline required."),
            ("Quarterly Secondaries Intelligence Product",
             "Build Neo's credibility as a secondaries advisor through transparent, source-tagged research.",
             "All alternatives clients and prospects.",
             "Requires sustained research discipline and rigorous source quality."),
        ]
        for title, purpose, fit, risk in products:
            st.markdown(render_product_card(title, purpose, fit, risk), unsafe_allow_html=True)

    with tab_d:
        st.markdown(render_section_header("Investment Committee Checklists"), unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f'<div style="font-size:11px;font-weight:700;color:{GOLD};'
                       f'text-transform:uppercase;letter-spacing:0.07em;margin-bottom:10px;">'
                       f'LP-Led Secondaries Checklist</div>', unsafe_allow_html=True)
            lp_items = [
                "Why is the seller selling?",
                "What is the NAV date and how stale are marks?",
                "What discount or premium is being paid to stated NAV?",
                "What are the unfunded commitments and timing?",
                "What is the vintage mix of the underlying portfolio?",
                "Which GPs and funds dominate the exposure?",
                "What is the sector and geography concentration?",
                "What distributions are expected over 12/24/36 months?",
                "What is the downside scenario analysis?",
                "What are the legal, tax, and transfer constraints?",
                "What are the management fees and carried interest on the portfolio?",
            ]
            for item in lp_items:
                st.markdown(
                    f'<div style="background:{CARD};border:1px solid {BORDER};'
                    f'border-radius:3px;padding:8px 12px;margin:4px 0;font-size:11px;color:{TEXT2};">'
                    f'<span style="color:{BLUE};margin-right:8px;">&#9633;</span>{item}</div>',
                    unsafe_allow_html=True)

        with col2:
            st.markdown(f'<div style="font-size:11px;font-weight:700;color:{GOLD};'
                       f'text-transform:uppercase;letter-spacing:0.07em;margin-bottom:10px;">'
                       f'GP-Led Secondaries Checklist</div>', unsafe_allow_html=True)
            gp_items = [
                "Was there a competitive process with multiple bidders?",
                "Was there an independent fairness opinion?",
                "How were rolling LPs treated — pricing, information access?",
                "Is the GP committing fresh capital alongside incoming investors?",
                "Are economics reset fairly — new carry threshold vs. old?",
                "What is the asset-level growth profile and path to exit?",
                "What is the primary exit route and expected timeline?",
                "Is the valuation supported by third-party bids?",
                "Are conflicts of interest disclosed clearly and managed?",
                "Is the continuation period reasonable given the asset stage?",
                "What is the governance structure in the continuation vehicle?",
            ]
            for item in gp_items:
                st.markdown(
                    f'<div style="background:{CARD};border:1px solid {BORDER};'
                    f'border-radius:3px;padding:8px 12px;margin:4px 0;font-size:11px;color:{TEXT2};">'
                    f'<span style="color:{GOLD};margin-right:8px;">&#9633;</span>{item}</div>',
                    unsafe_allow_html=True)

    with tab_e:
        st.markdown(render_section_header("Mistakes Neo Should Avoid"), unsafe_allow_html=True)
        mistakes = [
            "Chasing famous manager names without understanding look-through exposure.",
            "Overweighting IRR and ignoring DPI as the primary evidence of cash realization.",
            "Mixing LP-reported capital account returns with official fund-level performance when presenting to clients.",
            "Treating NAV as cash — unrealized portfolio marks can be revised significantly in a downturn.",
            "Launching a secondaries product before sourcing discipline and IC process are proven.",
            "Underestimating legal, tax, transfer, and operational complexity, particularly for Indian-domiciled fund interests.",
            "Selling secondaries as 'safe private equity' without explaining J-curve, liquidity, and concentration risks.",
            "Building fund-of-funds exposure without transparent look-through reporting to clients.",
        ]
        for m in mistakes:
            st.markdown(render_insight_card(m, "risk"), unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# PAGE 7: SOURCE LIBRARY
# ─────────────────────────────────────────────────────────────────────────────
def page_source_library():
    st.markdown(f'<div style="font-size:20px;font-weight:700;color:{TEXT};">'
               f'Source Library</div>', unsafe_allow_html=True)

    st.markdown(f"""
    <div style="background:{BG2};border:1px solid {AMBER};border-radius:4px;
                padding:12px 16px;margin-bottom:20px;">
        <div style="font-size:10px;color:{AMBER};font-weight:700;
                    text-transform:uppercase;margin-bottom:4px;">Data Integrity Warning</div>
        <div style="font-size:12px;color:{TEXT2};">
            Fund-level private markets performance is often not public. This platform distinguishes
            between official fund-level returns, LP-reported capital account data, manager-reported
            data, subscription-required fields, and unavailable data. Every data point in this
            platform should have a logged source.
        </div>
    </div>""", unsafe_allow_html=True)

    if not sources_df.empty:
        display = sources_df.copy()
        if "source_url" in display.columns:
            display["source_url"] = display["source_url"].apply(
                lambda x: x[:60] + "..." if len(str(x)) > 60 and str(x) not in ("NEEDS_MANUAL_REVIEW",) else x
            )
        st.dataframe(display, use_container_width=True, height=360)
        st.download_button("Export Sources CSV", data=sources_df.to_csv(index=False),
                           file_name="neo_sources.csv", mime="text/csv")
    else:
        st.warning("data/sources.csv not found.")

    st.markdown("<hr>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(render_section_header("Source Confidence Rules"), unsafe_allow_html=True)
        confidence_rules = [
            (GREEN, "High Confidence",
             "GP press release confirming fund size or final close. Public LP report or pension "
             "board report with audited capital account data. SEC filing. Official GP DDQ."),
            (AMBER, "Medium Confidence",
             "Reputable news article (Reuters, WSJ, FT). Consultant report. Paywalled article "
             "summary that requires verification against a primary source."),
            (RED, "Low Confidence",
             "Unverified market report. Screenshot. Manual entry without a primary source. "
             "Social media or informal communication."),
        ]
        for color, label, desc in confidence_rules:
            st.markdown(
                f'<div style="background:{CARD};border:1px solid {BORDER};'
                f'border-left:3px solid {color};border-radius:0 4px 4px 0;'
                f'padding:12px 16px;margin:8px 0;">'
                f'<div style="font-size:11px;font-weight:700;color:{color};margin-bottom:4px;">{label}</div>'
                f'<div style="font-size:11px;color:{TEXT2};">{desc}</div>'
                f'</div>', unsafe_allow_html=True)

    with col2:
        st.markdown(render_section_header("Data Integrity Rules"), unsafe_allow_html=True)
        rules = [
            "Every number must have a logged source with a confidence level.",
            "Every performance number must have an as-of date.",
            "Every performance number must specify whether it is fund-level or LP-level.",
            "Missing data must be tagged with an explicit marker, not left blank.",
            "Young fund IRRs (vintage < 3 years) must be flagged as not yet meaningful.",
            "LP-reported capital account data must not be cited as official fund performance.",
            "Subscription-required data must be tagged as SUBSCRIPTION_REQUIRED.",
            "Data older than 18 months must be tagged as STALE pending re-verification.",
        ]
        for r in rules:
            st.markdown(
                f'<div style="background:{CARD};border:1px solid {BORDER};'
                f'border-radius:3px;padding:8px 12px;margin:5px 0;font-size:11px;color:{TEXT2};">'
                f'<span style="color:{GOLD};margin-right:8px;">—</span>{r}</div>',
                unsafe_allow_html=True)

    st.markdown(render_analyst_note(
        "Most fund-level secondaries performance data is private or paywalled. This platform "
        "tracks confirmed public data, LP-reported capital account data, manager-reported data, "
        "and missing-data gaps separately. It should not be treated as a complete performance "
        "database unless supplemented with PitchBook, Preqin, Burgiss, Cambridge Associates, "
        "MSCI Private Capital, GP DDQs, or official LP reports."
    ), unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# PAGE 8: DATA IMPORT
# ─────────────────────────────────────────────────────────────────────────────
def page_data_import():
    st.markdown(f'<div style="font-size:20px;font-weight:700;color:{TEXT};">'
               f'Data Import</div>', unsafe_allow_html=True)
    st.markdown(f'<div style="font-size:12px;color:{TEXT2};margin-bottom:20px;">'
               f'Import from PitchBook, Preqin, Burgiss, pension LP reports, or manual CSVs. '
               f'Always verify source_confidence and source_type after importing.</div>',
               unsafe_allow_html=True)

    TABLE_SCHEMAS = {
        "funds": ["fund_id", "gp_name", "fund_name", "vintage_year", "fund_size_usd_bn",
                  "status", "strategy_type", "source_confidence", "last_updated"],
        "performance": ["performance_id", "fund_id", "as_of_date", "net_irr_pct",
                        "dpi", "rvpi", "tvpi", "source_type", "confidence_level"],
        "deals": ["deal_id", "fund_id", "deal_name", "deal_type", "source_url"],
        "lp_commitments": ["commitment_id", "fund_id", "lp_name", "commitment_amount_usd_m"],
        "sources": ["source_id", "fund_id", "source_type", "source_name", "confidence_level"],
    }

    target = st.selectbox("Target Table", list(TABLE_SCHEMAS.keys()))
    uploaded = st.file_uploader("Upload CSV", type=["csv"])

    if uploaded:
        try:
            df_upload = pd.read_csv(uploaded, dtype=str)
            df_upload = df_upload.dropna(how="all")

            st.markdown(render_section_header(f"Preview — {len(df_upload)} rows"), unsafe_allow_html=True)
            st.dataframe(df_upload.head(5), use_container_width=True)

            # Validation
            required = TABLE_SCHEMAS[target]
            missing_cols = [c for c in required if c not in df_upload.columns]
            warnings = []

            if missing_cols:
                st.error(f"Missing required columns: {', '.join(missing_cols)}")
                return

            if target == "performance":
                if "source_url" not in df_upload.columns or df_upload["source_url"].isna().all():
                    warnings.append("source_url is missing for all rows — source tracking will be incomplete")
                if "as_of_date" not in df_upload.columns or df_upload["as_of_date"].isna().all():
                    warnings.append("as_of_date is missing — performance data requires an as-of date")

            if target == "funds" and not funds_df.empty:
                dupe_names = df_upload[df_upload["fund_name"].isin(funds_df["fund_name"].tolist())]
                if len(dupe_names):
                    warnings.append(f"{len(dupe_names)} fund name(s) already exist: "
                                   f"{', '.join(dupe_names['fund_name'].tolist()[:3])}")

            for w in warnings:
                st.warning(w)

            if st.button("Import to Database", type="primary"):
                filename_map = {
                    "funds": "funds.csv",
                    "performance": "performance.csv",
                    "deals": "deals.csv",
                    "lp_commitments": "lp_commitments.csv",
                    "sources": "sources.csv",
                }
                existing = _load_raw(filename_map[target])
                combined = pd.concat([existing, df_upload], ignore_index=True) if not existing.empty else df_upload
                save_csv(combined, filename_map[target])
                st.success(f"Imported {len(df_upload)} rows into {target}. "
                          f"Total rows now: {len(combined)}. Reload the app to see updates.")
                st.download_button("Download Merged CSV", data=combined.to_csv(index=False),
                                  file_name=f"neo_{target}_merged.csv", mime="text/csv")
        except Exception as e:
            st.error(f"Import error: {e}")

    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown(render_section_header("Required Column Schemas"), unsafe_allow_html=True)

    for table, cols in TABLE_SCHEMAS.items():
        with st.expander(table):
            st.code(", ".join(cols))

    st.markdown(render_section_header("Import Guide by Source"), unsafe_allow_html=True)
    guide = [
        ("PitchBook",
         "Export: Funds → Private Equity → Secondary. Map Fund Name → fund_name, "
         "Fund Size → fund_size_usd_bn (divide by 1000). "
         "Set source_type = SUBSCRIPTION_REQUIRED, source_confidence = Medium."),
        ("Preqin",
         "Preqin collects from GPs — set source_type = MANAGER_REPORTED, confidence = Medium. "
         "Fill performance_scope with 'Preqin manager-reported fund-level'."),
        ("Burgiss",
         "LP-reported data. Set source_type = LP_REPORTED, confidence = High. "
         "Fill performance_scope with 'Burgiss pooled LP universe'."),
        ("Pension LP Reports",
         "Download public performance PDFs (CalSTRS, CalPERS, Oregon PERS). Parse tables. "
         "Set source_type = LP_REPORTED, reported_by = [LP name], "
         "performance_scope = '[LP] LP-level capital account'."),
        ("Secondaries Investor / PEI",
         "Set source_type = News/paywalled, confidence = Medium. "
         "Note subscription requirement in the notes column."),
    ]
    for source, desc in guide:
        st.markdown(render_playbook_item(source, desc), unsafe_allow_html=True)

    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown(render_section_header("Download Template CSVs"), unsafe_allow_html=True)
    tc1, tc2, tc3 = st.columns(3)
    with tc1:
        t = pd.DataFrame(columns=["fund_id", "gp_name", "fund_name", "short_name",
                                   "vintage_year", "fund_size_usd_bn", "target_size_usd_bn",
                                   "status", "strategy_type", "source_url",
                                   "source_type", "source_confidence", "notes", "last_updated"])
        st.download_button("Fund Template", data=t.to_csv(index=False),
                          file_name="template_funds.csv", mime="text/csv")
    with tc2:
        t2 = pd.DataFrame(columns=["performance_id", "fund_id", "as_of_date",
                                    "contributed_usd_m", "distributed_usd_m", "market_value_usd_m",
                                    "net_irr_pct", "dpi", "rvpi", "tvpi",
                                    "source_type", "confidence_level", "performance_scope",
                                    "is_lp_level", "is_predecessor_benchmark", "notes"])
        st.download_button("Performance Template", data=t2.to_csv(index=False),
                          file_name="template_performance.csv", mime="text/csv")
    with tc3:
        t3 = pd.DataFrame(columns=["deal_id", "fund_id", "deal_name", "deal_type",
                                    "seller_or_sponsor", "underlying_company_or_fund",
                                    "transaction_size_usd_m", "date_closed",
                                    "source_url", "confidence_level", "notes"])
        st.download_button("Deals Template", data=t3.to_csv(index=False),
                          file_name="template_deals.csv", mime="text/csv")


def _load_raw(filename):
    from utils.data_loader import DATA_DIR
    import os
    path = os.path.join(DATA_DIR, filename)
    if os.path.exists(path):
        try:
            return pd.read_csv(path, dtype=str).dropna(how="all")
        except Exception:
            return pd.DataFrame()
    return pd.DataFrame()


# ─────────────────────────────────────────────────────────────────────────────
# PAGE 9: WEEKLY MEMO
# ─────────────────────────────────────────────────────────────────────────────
def page_weekly_memo():
    st.markdown(f'<div style="font-size:20px;font-weight:700;color:{TEXT};">'
               f'Neo Secondaries Weekly Intelligence Brief</div>', unsafe_allow_html=True)
    st.markdown(f'<div style="font-size:12px;color:{TEXT2};margin-bottom:20px;">'
               f'Generate a structured weekly briefing based on current platform data. '
               f'Download as .txt for distribution.</div>', unsafe_allow_html=True)

    col1, col2 = st.columns([2, 1])
    with col1:
        as_of = st.text_input("As-of date for memo header",
                             value=datetime.now().strftime("%d %B %Y"))
    with col2:
        generate = st.button("Generate Brief", type="primary")

    if generate or True:
        memo = generate_weekly_memo(funds_df, perf_df, as_of=as_of)

        st.markdown(render_section_header("Generated Memo — Review Before Distribution"), unsafe_allow_html=True)
        st.text_area("", memo, height=600, label_visibility="collapsed")

        st.download_button(
            label="Download as .txt",
            data=memo,
            file_name=f"neo_secondaries_brief_{datetime.now().strftime('%Y%m%d')}.txt",
            mime="text/plain",
        )

    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown(render_section_header("Memo Structure"), unsafe_allow_html=True)
    sections = [
        ("1. Market Signal", "Key analytical context — what matters in the current cycle."),
        ("2. Fundraising Updates", "Closed funds, in-market funds, source confidence levels."),
        ("3. Performance Quality Updates", "LP-reported data with flags and source labels."),
        ("4. Funds Requiring Manual Research", "NEEDS_MANUAL_REVIEW and low-confidence items."),
        ("5. Neo Implications", "Standing analytical points relevant to Neo's strategy."),
        ("6. Analyst Action Items", "Checklist of manual follow-up tasks for the week."),
    ]
    for title, desc in sections:
        st.markdown(render_playbook_item(title, desc), unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# ROUTING
# ─────────────────────────────────────────────────────────────────────────────
if page == "Executive Brief":
    page_executive_brief()
elif page == "Fund Universe":
    page_fund_universe()
elif page == "Performance Quality":
    page_performance_quality()
elif page == "Manager Strategy":
    page_manager_strategy()
elif page == "Market Map":
    page_market_map()
elif page == "Neo Playbook":
    page_neo_playbook()
elif page == "Source Library":
    page_source_library()
elif page == "Data Import":
    page_data_import()
elif page == "Weekly Memo":
    page_weekly_memo()

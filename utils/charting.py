"""
charting.py
───────────
Plotly chart factory for the India Markets Terminal.
All charts use the same dark terminal palette.
"""

from __future__ import annotations
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from typing import Optional

# ── Palette ───────────────────────────────────────────────────────────────────
BG      = "#0c1320"
BG2     = "#111827"
BG3     = "#0f1929"
BORDER  = "#1e2d45"
TEXT    = "#e2e8f0"
TEXT2   = "#94a3b8"
TEXT3   = "#64748b"
ACCENT  = "#3b82f6"
POS     = "#22c55e"
NEG     = "#ef4444"
WARN    = "#f59e0b"
PURPLE  = "#a78bfa"
TEAL    = "#2dd4bf"

_LAYOUT_BASE = dict(
    paper_bgcolor="#0a1020",
    plot_bgcolor="#0c1622",
    font=dict(family="'Inter', sans-serif", color=TEXT2, size=11),
    margin=dict(l=52, r=20, t=40, b=42),
    legend=dict(
        bgcolor="rgba(10,16,32,0.8)",
        bordercolor="#141e30",
        borderwidth=1,
        font=dict(size=10, color=TEXT3),
    ),
    xaxis=dict(
        showgrid=True, gridcolor="#111827", gridwidth=1,
        linecolor="#141e30",
        tickfont=dict(size=10, color="#3d5270", family="'JetBrains Mono', monospace"),
        zeroline=False,
    ),
    yaxis=dict(
        showgrid=True, gridcolor="#111827", gridwidth=1,
        linecolor="#141e30",
        tickfont=dict(size=10, color="#3d5270", family="'JetBrains Mono', monospace"),
        zeroline=False,
    ),
    hoverlabel=dict(
        bgcolor="#111827",
        bordercolor="#1e2d45",
        font=dict(size=11, color=TEXT2, family="'JetBrains Mono', monospace"),
    ),
)


def _apply_base(fig: go.Figure, title: str = "", height: int = 360) -> go.Figure:
    layout = {**_LAYOUT_BASE, "height": height}
    if title:
        layout["title"] = dict(
            text=title,
            font=dict(size=11, color="#64748b", family="'Inter', sans-serif"),
            x=0, xanchor="left", y=0.98,
        )
    fig.update_layout(**layout)
    # Make axes lines consistent
    fig.update_xaxes(showline=True, linecolor="#141e30", mirror=False)
    fig.update_yaxes(showline=False, mirror=False)
    return fig


# ── Price chart ───────────────────────────────────────────────────────────────

def price_chart(df: pd.DataFrame, ticker: str, period_label: str = "1Y") -> go.Figure:
    """
    OHLCV candlestick + volume bars for a single stock.
    df must have columns: date, open, high, low, close, volume
    """
    if df.empty:
        return _empty_chart(f"{ticker} — No price data")

    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.75, 0.25],
    )

    # Candlestick
    fig.add_trace(
        go.Candlestick(
            x=df["date"],
            open=df["open"],  high=df["high"],
            low=df["low"],    close=df["close"],
            name="Price",
            increasing_line_color=POS,  increasing_fillcolor=POS,
            decreasing_line_color=NEG,  decreasing_fillcolor=NEG,
            line=dict(width=1),
        ),
        row=1, col=1,
    )

    # 50-day MA
    if len(df) >= 20:
        ma20 = df["close"].rolling(20).mean()
        fig.add_trace(
            go.Scatter(
                x=df["date"], y=ma20, name="20D MA",
                line=dict(color=ACCENT, width=1.2, dash="solid"),
                opacity=0.7,
            ),
            row=1, col=1,
        )

    if len(df) >= 50:
        ma50 = df["close"].rolling(50).mean()
        fig.add_trace(
            go.Scatter(
                x=df["date"], y=ma50, name="50D MA",
                line=dict(color=WARN, width=1, dash="dot"),
                opacity=0.7,
            ),
            row=1, col=1,
        )

    # Volume bars
    colors = [POS if c >= o else NEG
              for c, o in zip(df["close"], df["open"])]
    fig.add_trace(
        go.Bar(
            x=df["date"], y=df["volume"], name="Volume",
            marker_color=colors, opacity=0.5,
        ),
        row=2, col=1,
    )

    fig.update_layout(
        xaxis_rangeslider_visible=False,
        showlegend=True,
        **{k: v for k, v in _LAYOUT_BASE.items() if k != "xaxis"},
        height=420,
        title=dict(
            text=f"{ticker}  |  {period_label}",
            font=dict(size=12, color=TEXT2), x=0, xanchor="left",
        ),
    )
    fig.update_yaxes(row=1, col=1, tickprefix="₹",
                     gridcolor=BORDER, tickfont=dict(size=10, color=TEXT3))
    fig.update_yaxes(row=2, col=1, gridcolor=BORDER,
                     tickfont=dict(size=9, color=TEXT3))
    fig.update_xaxes(gridcolor=BORDER, tickfont=dict(size=10, color=TEXT3))

    return fig


# ── Sector heatmap ────────────────────────────────────────────────────────────

def sector_heatmap(
    df: pd.DataFrame,
    metric: str = "return_1d",
    title: str = "Sector Performance",
) -> go.Figure:
    """
    Treemap-style heatmap of sectors coloured by chosen return metric.
    df must have: sector, {metric}, num_stocks (optional)
    """
    if df.empty or "sector" not in df.columns:
        return _empty_chart("Sector heatmap — no data")

    df = df.copy().dropna(subset=[metric])
    df["pct_str"] = df[metric].apply(lambda v: f"{v:+.1f}%")
    df["size"] = df.get("market_cap_cr", pd.Series(100.0, index=df.index)).fillna(100)

    fig = px.treemap(
        df,
        path=["sector"],
        values="size",
        color=metric,
        color_continuous_scale=[
            [0.0,  "#7f1d1d"],
            [0.3,  "#991b1b"],
            [0.45, "#374151"],
            [0.55, "#374151"],
            [0.7,  "#14532d"],
            [1.0,  "#166534"],
        ],
        color_continuous_midpoint=0,
        custom_data=["pct_str", "sector"],
    )
    fig.update_traces(
        texttemplate="<b>%{customdata[1]}</b><br>%{customdata[0]}",
        hovertemplate="<b>%{customdata[1]}</b><br>%{metric}: %{customdata[0]}<extra></extra>",
        marker_line_color=BG,
        marker_line_width=2,
        textfont=dict(size=12, color="white"),
    )
    _apply_base(fig, title, height=320)
    fig.update_layout(coloraxis_showscale=False)
    return fig


# ── Return waterfall ──────────────────────────────────────────────────────────

def return_waterfall(
    periods: list[str],
    returns: list[float],
    ticker: str = "",
) -> go.Figure:
    """Horizontal bar chart of returns across multiple periods."""
    colors = [POS if r >= 0 else NEG for r in returns]
    fig = go.Figure(go.Bar(
        x=returns,
        y=periods,
        orientation="h",
        marker_color=colors,
        text=[f"{r:+.1f}%" for r in returns],
        textposition="outside",
        textfont=dict(size=11, color=TEXT2),
    ))
    _apply_base(fig, f"{ticker} Return Profile" if ticker else "Return Profile", height=280)
    fig.update_xaxes(ticksuffix="%", zeroline=True, zerolinecolor=BORDER, zerolinewidth=1)
    return fig


# ── OB Score breakdown bar ────────────────────────────────────────────────────

def ob_score_breakdown(factors: dict, maxes: dict, ticker: str = "") -> go.Figure:
    """
    Horizontal stacked bar showing each factor's contribution vs maximum.
    factors: {factor_name: actual_score}
    maxes:   {factor_name: max_score}
    """
    labels  = list(factors.keys())
    actuals = [factors[k] for k in labels]
    gaps    = [maxes.get(k, 10) - factors[k] for k in labels]

    # Clean labels
    clean_labels = [k.replace("_", " ").title() for k in labels]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Score",
        y=clean_labels,
        x=actuals,
        orientation="h",
        marker_color=ACCENT,
        marker_line_width=0,
        hovertemplate="%{x:.1f} pts<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        name="Gap to Max",
        y=clean_labels,
        x=gaps,
        orientation="h",
        marker_color=BORDER,
        marker_line_width=0,
        hovertemplate="Gap: %{x:.1f} pts<extra></extra>",
    ))
    _apply_base(fig, f"Score Breakdown — {ticker}" if ticker else "Score Breakdown", height=300)
    fig.update_layout(barmode="stack", showlegend=False)
    fig.update_xaxes(range=[0, 100], ticksuffix=" pts")
    return fig


# ── OB score scatter ──────────────────────────────────────────────────────────

def ob_score_scatter(df: pd.DataFrame) -> go.Figure:
    """
    Scatter: OB/Revenue ratio (x) vs OB Score (y), sized by market cap.
    """
    req = ["ob_revenue_ratio", "ob_score", "ticker"]
    if df.empty or not all(c in df.columns for c in req):
        return _empty_chart("OB Score vs OB/Revenue — no data")

    df = df.dropna(subset=req)
    size_col = "market_cap_cr" if "market_cap_cr" in df.columns else None

    color_map = {
        "High Conviction Idea":   POS,
        "Watchlist Add":          ACCENT,
        "Needs More Research":    WARN,
        "Momentum But Expensive": PURPLE,
        "Value Trap":             TEXT3,
        "Avoid":                  NEG,
    }
    df["color"] = df.get("classification", pd.Series(dtype=str)).map(color_map).fillna(TEXT3)

    fig = go.Figure()
    for cls, grp in df.groupby("classification") if "classification" in df.columns else [(None, df)]:
        c = color_map.get(str(cls), TEXT3)
        sizes = (grp[size_col] / grp[size_col].max() * 30 + 8) if size_col else pd.Series(12, index=grp.index)
        fig.add_trace(go.Scatter(
            x=grp["ob_revenue_ratio"],
            y=grp["ob_score"],
            mode="markers+text",
            name=str(cls) or "Unknown",
            text=grp["ticker"],
            textposition="top center",
            textfont=dict(size=9, color=TEXT3),
            marker=dict(color=c, size=sizes, line=dict(width=1, color=BG)),
            hovertemplate=(
                "<b>%{text}</b><br>"
                "OB/Rev: %{x:.1f}x<br>"
                "Score: %{y:.0f}<extra></extra>"
            ),
        ))

    _apply_base(fig, "Order Book Score vs OB/Revenue Ratio", height=380)
    fig.update_xaxes(title_text="OB / TTM Revenue", ticksuffix="x")
    fig.update_yaxes(title_text="OB Score", range=[0, 105])
    # Quadrant lines
    fig.add_hline(y=60, line_dash="dot", line_color=BORDER, line_width=1)
    fig.add_vline(x=2,  line_dash="dot", line_color=BORDER, line_width=1)
    return fig


# ── Classification donut ──────────────────────────────────────────────────────

def classification_donut(df: pd.DataFrame) -> go.Figure:
    """Donut chart of OB screener classifications."""
    if df.empty or "classification" not in df.columns:
        return _empty_chart("Classification — no data")

    counts = df["classification"].value_counts().reset_index()
    counts.columns = ["cls", "count"]

    color_map = {
        "High Conviction Idea":    POS,
        "Watchlist Add":           ACCENT,
        "Needs More Research":     WARN,
        "Momentum But Expensive":  PURPLE,
        "Value Trap":              TEXT3,
        "Avoid":                   NEG,
    }
    colors = [color_map.get(c, TEXT3) for c in counts["cls"]]

    fig = go.Figure(go.Pie(
        labels=counts["cls"],
        values=counts["count"],
        hole=0.55,
        marker=dict(colors=colors, line=dict(color=BG, width=2)),
        textfont=dict(size=10, color=TEXT2),
        hovertemplate="<b>%{label}</b><br>%{value} companies<extra></extra>",
    ))
    _apply_base(fig, "Classification Breakdown", height=300)
    fig.update_layout(
        legend=dict(orientation="v", x=1.0, y=0.5),
        showlegend=True,
    )
    return fig


# ── Performance scatter ───────────────────────────────────────────────────────

def performance_scatter(
    df: pd.DataFrame,
    x_col: str = "return_1y",
    y_col: str = "return_3m",
    size_col: str = "market_cap_cr",
    color_col: str = "sector",
) -> go.Figure:
    """Scatter of two return periods, sized by market cap, coloured by sector."""
    if df.empty:
        return _empty_chart("Performance Scatter — no data")

    df = df.dropna(subset=[x_col, y_col])
    if df.empty:
        return _empty_chart("Performance Scatter — insufficient data")

    # Build figure manually for terminal aesthetics
    sectors = df[color_col].unique() if color_col in df.columns else ["All"]
    palette = [ACCENT, POS, NEG, WARN, PURPLE, TEAL,
               "#f97316","#ec4899","#14b8a6","#64748b"]

    fig = go.Figure()
    for i, sect in enumerate(sectors):
        grp = df[df[color_col] == sect] if color_col in df.columns else df
        size_vals = (
            (grp[size_col] / grp[size_col].max() * 25 + 5)
            if size_col in grp.columns else pd.Series(10, index=grp.index)
        )
        fig.add_trace(go.Scatter(
            x=grp[x_col] * 100 if grp[x_col].abs().max() <= 2 else grp[x_col],
            y=grp[y_col] * 100 if grp[y_col].abs().max() <= 2 else grp[y_col],
            mode="markers",
            name=str(sect),
            text=grp.get("ticker", grp.index).astype(str),
            marker=dict(
                size=size_vals,
                color=palette[i % len(palette)],
                opacity=0.75,
                line=dict(width=0.5, color=BG),
            ),
            hovertemplate=f"<b>%{{text}}</b><br>{x_col}: %{{x:.1f}}%<br>{y_col}: %{{y:.1f}}%<extra></extra>",
        ))

    _apply_base(fig, "Performance Scatter", height=400)
    fig.update_xaxes(title_text=_col_label(x_col), ticksuffix="%",
                     zeroline=True, zerolinecolor=BORDER)
    fig.update_yaxes(title_text=_col_label(y_col), ticksuffix="%",
                     zeroline=True, zerolinecolor=BORDER)
    return fig


def _col_label(col: str) -> str:
    labels = {
        "return_1d": "1D Return", "return_1w": "1W Return",
        "return_1m": "1M Return", "return_3m": "3M Return",
        "return_6m": "6M Return", "return_1y": "1Y Return",
    }
    return labels.get(col, col.replace("_", " ").title())


# ── Peer comparison bar ───────────────────────────────────────────────────────

def peer_comparison_bar(
    peers: pd.DataFrame,
    metric: str = "ev_ebitda",
    highlight: str = "",
) -> go.Figure:
    """Horizontal bar chart comparing a metric across peers."""
    if peers.empty or metric not in peers.columns:
        return _empty_chart("Peer comparison — no data")

    peers = peers.dropna(subset=[metric]).sort_values(metric)
    colors = [POS if t == highlight else ACCENT for t in peers.get("ticker", peers.index)]

    fig = go.Figure(go.Bar(
        x=peers[metric],
        y=peers.get("ticker", peers.index.astype(str)),
        orientation="h",
        marker_color=colors,
        text=[f"{v:.1f}x" for v in peers[metric]],
        textposition="outside",
        textfont=dict(size=10, color=TEXT2),
    ))
    _apply_base(fig, _col_label(metric), height=max(200, len(peers) * 35 + 60))
    return fig


# ── Margin trend line ─────────────────────────────────────────────────────────

def margin_trend_line(
    quarterly_df: pd.DataFrame,
    ticker: str = "",
) -> go.Figure:
    """Line chart of EBITDA/PAT margins over quarters."""
    if quarterly_df.empty:
        return _empty_chart("Margin trend — no data")

    fig = go.Figure()
    if "ebitda_margin" in quarterly_df.columns:
        fig.add_trace(go.Scatter(
            x=quarterly_df.get("quarter", quarterly_df.index),
            y=quarterly_df["ebitda_margin"],
            name="EBITDA Margin",
            line=dict(color=ACCENT, width=2),
            mode="lines+markers",
            marker=dict(size=5),
        ))
    if "pat_margin" in quarterly_df.columns:
        fig.add_trace(go.Scatter(
            x=quarterly_df.get("quarter", quarterly_df.index),
            y=quarterly_df["pat_margin"],
            name="PAT Margin",
            line=dict(color=POS, width=2),
            mode="lines+markers",
            marker=dict(size=5),
        ))
    _apply_base(fig, f"{ticker} Margin Trend" if ticker else "Margin Trend", height=300)
    fig.update_yaxes(ticksuffix="%")
    return fig


# ── Utility ───────────────────────────────────────────────────────────────────

def _empty_chart(msg: str = "No data available", height: int = 200) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(
        text=msg, xref="paper", yref="paper",
        x=0.5, y=0.5, showarrow=False,
        font=dict(size=11, color="#2d3f5a", family="'Inter', sans-serif"),
    )
    _apply_base(fig, height=height)
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return fig


# ── Quarterly performance charts ──────────────────────────────────────────────

def quarterly_comparison_bar(
    qdf: pd.DataFrame, metric: str, ticker: str = "",
    title: str = "", y_label: str = "",
) -> go.Figure:
    """
    Grouped bar chart: each x-tick is a quarter (Q1/Q2/Q3/Q4),
    one bar per fiscal year. Lets you see Q1 across FY23/FY24/FY25 side-by-side.
    """
    if qdf.empty or metric not in qdf.columns:
        return _empty_chart(f"{ticker} — No quarterly data")

    pv = qdf.pivot_table(
        index="quarter", columns="fiscal_year",
        values=metric, aggfunc="first",
    ).reindex(["Q1", "Q2", "Q3", "Q4"])

    fy_cols = sorted(pv.columns, key=str)

    # Year-coded colour ramp (older = darker)
    YEAR_PALETTE = ["#1e3a5f", "#1d4ed8", "#3b82f6", "#60a5fa", "#93c5fd"]
    fig = go.Figure()

    for i, fy in enumerate(fy_cols):
        col = YEAR_PALETTE[i % len(YEAR_PALETTE)]
        vals = pv[fy].tolist()
        fig.add_trace(go.Bar(
            name=str(fy),
            x=pv.index.tolist(),
            y=vals,
            marker=dict(
                color=col,
                line=dict(color=col, width=0),
            ),
            hovertemplate=(
                "<b>%{x} " + str(fy) + "</b><br>"
                + (y_label or metric) + ": %{y:,.1f}<extra></extra>"
            ),
            text=[f"{v:,.0f}" if v and v >= 100 else (f"{v:.1f}" if v else "") for v in vals],
            textposition="outside",
            textfont=dict(size=9, color="#64748b"),
        ))

    fig.update_layout(
        barmode="group",
        bargap=0.25, bargroupgap=0.05,
        showlegend=True,
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02,
            xanchor="right", x=1,
            bgcolor="rgba(0,0,0,0)",
            font=dict(size=10, color="#94a3b8"),
        ),
    )
    fig.update_yaxes(title_text=y_label or metric,
                     title_font=dict(size=10, color="#3d5270"))
    _apply_base(fig, title=title or f"{metric} by Quarter — {ticker}", height=340)
    return fig


def quarterly_yoy_growth_line(
    qdf: pd.DataFrame, ticker: str = "", title: str = "",
) -> go.Figure:
    """
    Line chart showing YoY %% growth in revenue, EBITDA, and PAT across quarters.
    Each line traces the YoY change at Q1 / Q2 / Q3 / Q4 over time.
    """
    if qdf.empty:
        return _empty_chart(f"{ticker} — No YoY data")

    sorted_df = qdf.copy()
    if "period_end" in sorted_df.columns:
        sorted_df = sorted_df.sort_values("period_end")

    x = sorted_df.apply(
        lambda r: f"{r.get('quarter','')} {str(r.get('fiscal_year',''))[-2:]}", axis=1
    ).tolist()

    fig = go.Figure()
    series = [
        ("revenue_yoy_pct", "Revenue YoY",  "#60a5fa"),
        ("ebitda_yoy_pct",  "EBITDA YoY",   "#22c55e"),
        ("pat_yoy_pct",     "PAT YoY",      "#a78bfa"),
    ]
    for col, name, c in series:
        if col not in sorted_df.columns:
            continue
        y = sorted_df[col].tolist()
        fig.add_trace(go.Scatter(
            x=x, y=y, name=name,
            mode="lines+markers",
            line=dict(color=c, width=2),
            marker=dict(size=6, color=c, line=dict(color="#0c1320", width=1)),
            hovertemplate=f"<b>%{{x}}</b><br>{name}: %{{y:+.1f}}%<extra></extra>",
        ))

    fig.add_hline(y=0, line=dict(color="#1e2d45", width=1, dash="dot"))
    fig.update_layout(
        showlegend=True,
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02,
            xanchor="right", x=1,
            bgcolor="rgba(0,0,0,0)",
            font=dict(size=10, color="#94a3b8"),
        ),
    )
    fig.update_yaxes(title_text="YoY Growth (%)",
                     title_font=dict(size=10, color="#3d5270"),
                     ticksuffix="%")
    _apply_base(fig, title=title or f"YoY Growth Trajectory — {ticker}", height=320)
    return fig


def quarterly_margin_chart(qdf: pd.DataFrame, ticker: str = "") -> go.Figure:
    """
    Line chart of EBITDA margin % and PAT margin % across quarters (chronological).
    """
    if qdf.empty:
        return _empty_chart(f"{ticker} — No margin data")

    sorted_df = qdf.copy()
    if "period_end" in sorted_df.columns:
        sorted_df = sorted_df.sort_values("period_end")

    x = sorted_df.apply(
        lambda r: f"{r.get('quarter','')} {str(r.get('fiscal_year',''))[-2:]}", axis=1
    ).tolist()

    fig = go.Figure()
    if "ebitda_margin_pct" in sorted_df.columns:
        y = sorted_df["ebitda_margin_pct"].tolist()
        fig.add_trace(go.Scatter(
            x=x, y=y, name="EBITDA Margin",
            mode="lines+markers",
            line=dict(color="#22c55e", width=2.5, shape="spline", smoothing=0.4),
            marker=dict(size=6, color="#22c55e", line=dict(color="#0c1320", width=1)),
            fill="tozeroy", fillcolor="rgba(34,197,94,0.08)",
            hovertemplate="<b>%{x}</b><br>EBITDA Margin: %{y:.2f}%<extra></extra>",
        ))
    if "pat_margin_pct" in sorted_df.columns:
        y = sorted_df["pat_margin_pct"].tolist()
        fig.add_trace(go.Scatter(
            x=x, y=y, name="PAT Margin",
            mode="lines+markers",
            line=dict(color="#a78bfa", width=2.5, shape="spline", smoothing=0.4),
            marker=dict(size=6, color="#a78bfa", line=dict(color="#0c1320", width=1)),
            hovertemplate="<b>%{x}</b><br>PAT Margin: %{y:.2f}%<extra></extra>",
        ))

    fig.update_layout(
        showlegend=True,
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02,
            xanchor="right", x=1,
            bgcolor="rgba(0,0,0,0)",
            font=dict(size=10, color="#94a3b8"),
        ),
    )
    fig.update_yaxes(title_text="Margin (%)",
                     title_font=dict(size=10, color="#3d5270"),
                     ticksuffix="%")
    _apply_base(fig, title=f"Margin Trend — {ticker}", height=300)
    return fig


def quarterly_heatmap(qdf: pd.DataFrame, metric: str, ticker: str = "") -> go.Figure:
    """
    Heatmap: rows = fiscal years, cols = quarters, cells = metric value.
    Quickly spot seasonality and the strongest year.
    """
    if qdf.empty or metric not in qdf.columns:
        return _empty_chart(f"{ticker} — No data")

    pv = qdf.pivot_table(
        index="fiscal_year", columns="quarter",
        values=metric, aggfunc="first",
    )[["Q1","Q2","Q3","Q4"]] if all(q in qdf.get("quarter", pd.Series()).unique() for q in ["Q1","Q2"]) else qdf.pivot_table(
        index="fiscal_year", columns="quarter",
        values=metric, aggfunc="first",
    )

    # Format cell text
    z_values = pv.values
    text = [[f"{v:,.0f}" if pd.notna(v) and abs(v) >= 100 else (f"{v:.1f}" if pd.notna(v) else "")
             for v in row] for row in z_values]

    fig = go.Figure(data=go.Heatmap(
        z=z_values,
        x=list(pv.columns),
        y=list(pv.index),
        text=text,
        texttemplate="%{text}",
        textfont=dict(size=11, color="#e2e8f0", family="'JetBrains Mono', monospace"),
        colorscale=[
            [0.0, "#1c1917"],
            [0.3, "#0f1929"],
            [0.6, "#1d4ed8"],
            [1.0, "#3b82f6"],
        ],
        showscale=False,
        hovertemplate="<b>%{y} %{x}</b><br>" + metric + ": %{z:,.1f}<extra></extra>",
        xgap=3, ygap=3,
    ))
    _apply_base(fig, title=f"{metric} — Yearly × Quarterly", height=260)
    fig.update_xaxes(side="top", showgrid=False)
    fig.update_yaxes(autorange="reversed", showgrid=False)
    return fig

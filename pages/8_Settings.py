"""
Settings & Data Management
──────────────────────────
Configure API keys, email settings, and data refresh controls.
"""

import streamlit as st
import pandas as pd
import subprocess
import sys
from pathlib import Path

st.set_page_config(
    page_title="Settings — India Terminal",
    layout="wide", initial_sidebar_state="expanded",
)

from utils.formatting import (
    inject_css, page_header, section_label, kpi_card,
    info_block, warn_block, ok_block,
)
from utils.data_loader import load_settings, save_settings, load_universe, load_order_book

inject_css()

ROOT = Path(__file__).parent.parent

page_header("Settings & Data Management")

settings = load_settings()

# ── Tabs ──────────────────────────────────────────────────────────────────────
tabs = st.tabs(["API Keys", "Email Config", "Data Management", "Universe Editor", "About"])

# ── TAB 1: API Keys ───────────────────────────────────────────────────────────
with tabs[0]:
    section_label("API Configuration")
    info_block(
        "Your API keys are stored in india_terminal/.env and loaded as environment variables. "
        "They are never uploaded to any server."
    )

    with st.form("api_keys_form"):
        anthropic_key = st.text_input(
            "Anthropic API Key",
            value=settings.get("ANTHROPIC_API_KEY", ""),
            type="password",
            help="Required for AI market summaries, analyst notes, and filing summaries. "
                 "Get yours at https://console.anthropic.com/",
        )
        submitted = st.form_submit_button("Save API Keys")
        if submitted:
            settings["ANTHROPIC_API_KEY"] = anthropic_key
            save_settings(settings)
            ok_block("API keys saved.")

    # Test connection
    if st.button("Test Claude API Connection"):
        key = settings.get("ANTHROPIC_API_KEY", "")
        if not key:
            warn_block("No API key configured.")
        else:
            import os
            os.environ["ANTHROPIC_API_KEY"] = key
            try:
                import anthropic
                client = anthropic.Anthropic(api_key=key)
                msg = client.messages.create(
                    model="claude-opus-4-5", max_tokens=20,
                    messages=[{"role":"user","content":"Say OK"}],
                )
                ok_block(f"API connection successful. Response: {msg.content[0].text}")
            except Exception as e:
                warn_block(f"API connection failed: {e}")

# ── TAB 2: Email Config ───────────────────────────────────────────────────────
with tabs[1]:
    section_label("Daily Email Brief Configuration")
    info_block(
        "Configure SMTP credentials to receive daily market briefs at 8:30 AM and 4:30 PM IST. "
        "For Gmail, use App Passwords (not your main password) with 2FA enabled."
    )

    with st.form("email_form"):
        email_from = st.text_input("From Email", value=settings.get("EMAIL_FROM",""))
        email_to   = st.text_input("To Email(s)", value=settings.get("EMAIL_TO",""),
                                   help="Comma-separated for multiple recipients")
        email_pass = st.text_input("SMTP Password / App Password",
                                   value=settings.get("EMAIL_PASSWORD",""), type="password")
        smtp_host  = st.text_input("SMTP Host", value=settings.get("SMTP_HOST","smtp.gmail.com"))
        smtp_port  = st.text_input("SMTP Port", value=settings.get("SMTP_PORT","587"))

        col1, col2 = st.columns(2)
        with col1:
            morning_time = st.text_input("Morning Brief Time (IST)", value="08:30",
                                         help="24-hour format, e.g. 08:30")
        with col2:
            evening_time = st.text_input("Evening Brief Time (IST)", value="16:30")

        submitted = st.form_submit_button("Save Email Settings")
        if submitted:
            settings.update({
                "EMAIL_FROM": email_from, "EMAIL_TO": email_to,
                "EMAIL_PASSWORD": email_pass, "SMTP_HOST": smtp_host,
                "SMTP_PORT": smtp_port, "MORNING_TIME": morning_time,
                "EVENING_TIME": evening_time,
            })
            save_settings(settings)
            ok_block("Email settings saved.")

    if st.button("Send Test Email"):
        try:
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "send_daily_email.py"), "--test"],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                ok_block("Test email sent successfully.")
            else:
                warn_block(f"Email failed: {result.stderr}")
        except Exception as e:
            warn_block(f"Could not run email script: {e}")

# ── TAB 3: Data Management ────────────────────────────────────────────────────
with tabs[2]:
    section_label("Data Sources & Status")

    DATA = ROOT / "data"
    files = {
        "universe.csv":     "Master company list (static — edit manually)",
        "prices.csv":       "Daily prices (run update_prices.py daily)",
        "fundamentals.csv": "Fundamental data (export from Screener.in)",
        "order_book.csv":   "Order book database (manually maintained)",
        "filings.csv":      "Corporate filings (auto-fetched from NSE)",
        "news.csv":         "News feed (auto-fetched or manual)",
        "sectors.csv":      "Sector metadata (static)",
        "notes.csv":        "Research notes (auto-saved)",
    }

    rows = ""
    for fname, desc in files.items():
        fpath = DATA / fname
        if fpath.exists():
            size = fpath.stat().st_size
            size_str = f"{size/1024:.1f} KB"
            try:
                df = pd.read_csv(fpath)
                n_rows = len(df)
            except Exception:
                n_rows = "?"
            status = f'<span style="color:#22c55e;">&#10003; {n_rows} rows</span>'
        else:
            size_str = "—"
            status = '<span style="color:#ef4444;">Missing</span>'
        rows += (
            f"<tr>"
            f"<td class='left' style='color:#3b82f6;font-family:\"IBM Plex Mono\",monospace;'>{fname}</td>"
            f"<td class='left' style='color:#64748b;'>{desc}</td>"
            f"<td>{size_str}</td>"
            f"<td>{status}</td>"
            f"</tr>"
        )

    from utils.formatting import table_wrap
    table_wrap(
        f"""<table class='trm'>
            <thead><tr>
              <th class='left'>File</th><th class='left'>Description</th>
              <th>Size</th><th>Status</th>
            </tr></thead>
            <tbody>{rows}</tbody>
          </table>""",
        caption="Data files",
    )

    st.markdown("<br>", unsafe_allow_html=True)
    section_label("Update Data")

    col1, col2, col3 = st.columns(3)

    def _run_script(script_name, label):
        script = ROOT / "scripts" / script_name
        if not script.exists():
            warn_block(f"{script_name} not found.")
            return
        with st.spinner(f"Running {label}…"):
            result = subprocess.run(
                [sys.executable, str(script)],
                capture_output=True, text=True, timeout=120
            )
        if result.returncode == 0:
            ok_block(f"{label} completed.")
        else:
            warn_block(f"{label} failed: {result.stderr[:200]}")

    with col1:
        if st.button("Update Prices (NSE Bhavcopy)"):
            _run_script("update_prices.py", "Price Update")
        if st.button("Update Filings (NSE)"):
            _run_script("update_filings.py", "Filings Update")

    with col2:
        if st.button("Update Fundamentals (Screener)"):
            info_block(
                "Fundamental data should be exported from Screener.in and placed in "
                "data/fundamentals.csv. See README for export format."
            )
        if st.button("Score Order Book DB"):
            from utils.data_loader import load_order_book, save_order_book
            from utils.scoring import score_order_book_df
            ob = load_order_book()
            if ob.empty:
                warn_block("Order book is empty.")
            else:
                scored = score_order_book_df(ob)
                save_order_book(scored)
                ok_block(f"Scored {len(scored)} companies.")

    with col3:
        if st.button("Generate AI Summaries"):
            _run_script("generate_ai_summaries.py", "AI Summaries")
        if st.button("Clear All Caches"):
            st.cache_data.clear()
            ok_block("Caches cleared.")

    st.markdown("<br>", unsafe_allow_html=True)
    section_label("Upload Screener CSV")
    info_block(
        "Export your Screener.in company list as CSV and upload here. "
        "Required columns: Ticker, PE, EV/EBITDA, ROE, ROCE, D/E, Rev Gr %, etc."
    )
    uploaded = st.file_uploader("Upload Screener Export", type="csv")
    if uploaded:
        try:
            df_up = pd.read_csv(uploaded)
            st.dataframe(df_up.head(10), width="stretch")
            if st.button("Import to Fundamentals"):
                col_map = {
                    "Ticker": "ticker", "Name": "company_name",
                    "PE": "pe", "EV/EBITDA": "ev_ebitda", "PB": "pb",
                    "ROE": "roe", "ROCE": "roce", "D/E": "debt_equity",
                    "Revenue Gr %": "revenue_growth_1y",
                    "PAT Gr %": "pat_growth_1y",
                    "EBITDA Margin %": "ebitda_margin",
                    "Promoter Holding %": "promoter_holding",
                    "FII Holding %": "fii_holding",
                    "DII Holding %": "dii_holding",
                }
                df_up = df_up.rename(columns={k: v for k, v in col_map.items() if k in df_up.columns})
                df_up["as_of_date"] = str(pd.Timestamp.today().date())
                existing_fund = pd.read_csv(ROOT / "data" / "fundamentals.csv") if (ROOT / "data" / "fundamentals.csv").exists() else pd.DataFrame()
                merged = pd.concat([existing_fund, df_up], ignore_index=True)
                merged.to_csv(ROOT / "data" / "fundamentals.csv", index=False)
                ok_block(f"Imported {len(df_up)} rows into fundamentals.csv.")
        except Exception as e:
            warn_block(f"Import failed: {e}")

# ── TAB 4: Universe Editor ────────────────────────────────────────────────────
with tabs[3]:
    section_label("Universe Management")
    uni = load_universe()
    if not uni.empty:
        st.dataframe(uni, width="stretch", height=400)
        csv = uni.to_csv(index=False)
        st.download_button("Download Universe CSV", csv, "universe.csv", "text/csv")
    else:
        warn_block("Universe not loaded.")

    st.markdown("---")
    section_label("Add Company to Universe")
    with st.form("add_universe"):
        col1, col2 = st.columns(2)
        with col1:
            u_ticker  = st.text_input("NSE Ticker*")
            u_name    = st.text_input("Company Name*")
            u_sector  = st.text_input("Sector")
            u_industry = st.text_input("Industry")
        with col2:
            u_index   = st.text_input("Index Membership", value="Nifty500",
                                       help="e.g. Nifty50|NiftyNext50|Nifty500")
            u_isin    = st.text_input("ISIN")
            u_bse     = st.text_input("BSE Code")

        if st.form_submit_button("Add to Universe"):
            if not u_ticker or not u_name:
                st.error("Ticker and Company Name are required.")
            else:
                new_row = {
                    "ticker": u_ticker.upper(), "company_name": u_name,
                    "sector": u_sector, "industry": u_industry,
                    "index_membership": u_index, "isin": u_isin,
                    "bse_code": u_bse, "nse_code": u_ticker.upper(),
                }
                combined = pd.concat([uni, pd.DataFrame([new_row])], ignore_index=True)
                combined.to_csv(ROOT / "data" / "universe.csv", index=False)
                ok_block(f"{u_ticker.upper()} added to universe.")
                st.rerun()

# ── TAB 5: About ──────────────────────────────────────────────────────────────
with tabs[4]:
    section_label("About this Terminal")
    st.markdown(
        """
**India Public Markets Intelligence Terminal**

An institutional-grade research platform for Indian listed equities.
Built for investment professionals managing exposure to the top listed companies in India.

**Core Modules:**
- Market Command Center — daily market pulse
- All Companies Database — Nifty 500 universe screener
- Company Detail — deep dive with financials, filings, and AI notes
- Order Book Mispricing Screener — proprietary 6-factor scoring model
- New Ideas Engine — automated opportunity flagging
- News & Filings — NSE announcements with AI classification
- Sector Intelligence — sector cycle and valuation analysis
- Daily Email Brief — morning + evening automated briefings

**Data Sources:**
- NSE Bhavcopy (daily price data)
- Screener.in CSV exports (fundamentals)
- NSE Corporate Announcements API (filings)
- Manual order book data entry (with source traceability)
- Anthropic Claude API (AI summaries)

**Order Book Scoring Model:**
- 30% Order Book / Revenue
- 20% Order Inflow Growth
- 15% Revenue Growth
- 15% Margin Stability
- 10% Valuation vs Peers
- 10% Balance Sheet Quality

**Important Note on Order Book Data:**
Order book numbers are manually entered and must be sourced from verified documents
(concall transcripts, investor presentations, quarterly results). Every entry requires:
source document, source date, extracted text snippet, confidence score, and
manual verification flag. Do not rely on AI-extracted numbers without verification.

**Version:** 1.0.0 | **Built with:** Streamlit, Pandas, Plotly, Anthropic Claude
""",
        unsafe_allow_html=False,
    )

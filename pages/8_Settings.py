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
            f"<td class='left' style='color:#3b82f6;font-family:\"JetBrains Mono\",monospace;'>{fname}</td>"
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

    st.write("")
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
        if st.button("Update Fundamentals (Manual Import)"):
            info_block(
                "Use the upload section below to import Screener, Trendlyne, or Bloomberg exports "
                "into data/fundamentals.csv via scripts/update_fundamentals.py."
            )

    with col3:
        if st.button("Generate AI Summaries"):
            _run_script("generate_ai_summaries.py", "AI Summaries")
        if st.button("Clear All Caches"):
            st.cache_data.clear()
            ok_block("Caches cleared.")

    st.write("")
    section_label("Upload Fundamentals File")
    info_block(
        "Upload a Screener, Trendlyne, or Bloomberg export. "
        "The importer will normalize available columns into data/fundamentals.csv. "
        "Missing fields remain blank; nothing is fabricated."
    )
    source_type = st.selectbox("Source Type", ["screener", "trendlyne", "bloomberg"])
    merge_mode = st.checkbox("Merge with existing fundamentals", value=True)
    uploaded = st.file_uploader("Upload Fundamentals Export", type=["csv", "xlsx", "xls"])
    if uploaded:
        try:
            if uploaded.name.lower().endswith((".xlsx", ".xls")):
                df_up = pd.read_excel(uploaded)
            else:
                df_up = pd.read_csv(uploaded)
            st.dataframe(df_up.head(10), width="stretch")
            if st.button("Import to Fundamentals"):
                upload_path = ROOT / "data" / f"_uploaded_fundamentals{Path(uploaded.name).suffix.lower()}"
                with open(upload_path, "wb") as f:
                    f.write(uploaded.getbuffer())
                cmd = [
                    sys.executable,
                    str(ROOT / "scripts" / "update_fundamentals.py"),
                    "--import-csv",
                    str(upload_path),
                    "--source",
                    source_type,
                ]
                if merge_mode:
                    cmd.append("--merge")
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                if result.returncode == 0:
                    ok_block("Fundamentals import completed.")
                    st.cache_data.clear()
                else:
                    warn_block(f"Fundamentals import failed: {result.stderr[:300]}")
        except Exception as e:
            warn_block(f"Import failed: {e}")

    st.write("")
    section_label("Upload Trusted News File")
    info_block(
        "Use this when public feeds are stale or incomplete. "
        "Accepted columns are flexible. Recommended fields: headline/title, date/published_at, "
        "source/publisher, url/link, ticker/tickers, sector, sentiment, summary, materiality score."
    )
    news_uploaded = st.file_uploader("Upload News CSV", type=["csv"], key="news_upload")
    if news_uploaded:
        try:
            news_preview = pd.read_csv(news_uploaded)
            st.dataframe(news_preview.head(10), width="stretch")
            template_df = pd.DataFrame(
                [
                    {
                        "headline": "L&T wins major EPC order for transmission corridor",
                        "date": "2026-06-12 08:45:00",
                        "source": "Manual Research",
                        "url": "https://example.com/article",
                        "tickers": "LT",
                        "sector": "Capital Goods",
                        "sentiment": "positive",
                        "summary": "Large domestic T&D award adds to execution visibility.",
                        "is_material": True,
                        "materiality_score": 84,
                        "categories": "order_win",
                    }
                ]
            )
            st.download_button(
                "Download News Template",
                data=template_df.to_csv(index=False).encode("utf-8"),
                file_name="news_import_template.csv",
                mime="text/csv",
            )
            if st.button("Import to News Feed"):
                upload_path = ROOT / "data" / "_uploaded_news.csv"
                with open(upload_path, "wb") as f:
                    f.write(news_uploaded.getbuffer())
                cmd = [
                    sys.executable,
                    str(ROOT / "scripts" / "update_news.py"),
                    "--import-csv",
                    str(upload_path),
                ]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                if result.returncode == 0:
                    ok_block("News import completed.")
                    st.cache_data.clear()
                else:
                    warn_block(f"News import failed: {result.stderr[:300]}")
        except Exception as e:
            warn_block(f"News upload failed: {e}")

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
- News & Filings — event intelligence for explaining moves
- New Ideas Engine — automated opportunity flagging
- Sector Intelligence — sector cycle and valuation analysis
- Daily Email Brief — morning + evening automated briefings

**Data Sources:**
- NSE Bhavcopy (daily price data)
- Screener.in CSV exports (fundamentals)
- NSE Corporate Announcements API (filings)
- Anthropic Claude API (AI summaries)

**Version:** 1.0.0 | **Built with:** Streamlit, Pandas, Plotly, Anthropic Claude
""",
        unsafe_allow_html=False,
    )

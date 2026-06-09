"""
send_daily_email.py
───────────────────
Sends institutional-quality daily email briefs via SMTP.

Morning brief (default 08:30 IST):  global cues, index setup, key events
Evening brief  (default 16:30 IST):  market summary, top movers, new ideas

Usage:
    python scripts/send_daily_email.py                  # auto-detect morning/evening
    python scripts/send_daily_email.py --brief morning
    python scripts/send_daily_email.py --brief evening
    python scripts/send_daily_email.py --test           # send test email regardless of time

Schedule via cron (example):
    30 3  * * 1-5  /path/to/python /path/to/scripts/send_daily_email.py --brief morning
    00 11 * * 1-5  /path/to/python /path/to/scripts/send_daily_email.py --brief evening
(IST = UTC+5:30, so 08:30 IST = 03:00 UTC, 16:30 IST = 11:00 UTC)
"""

import sys, os, smtplib, argparse, logging
from pathlib import Path
from datetime import datetime, timezone, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import pandas as pd
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv(Path(__file__).parent.parent / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"

# ── IST timezone ──────────────────────────────────────────────────────────────
IST = timezone(timedelta(hours=5, minutes=30))


def _ist_now():
    return datetime.now(IST)


def _detect_brief_type():
    """Determine if we're in morning or evening window."""
    now = _ist_now()
    hour = now.hour
    if 6 <= hour < 12:
        return "morning"
    elif 14 <= hour < 20:
        return "evening"
    return "morning"  # default


# ── CSS for email ─────────────────────────────────────────────────────────────
_EMAIL_CSS = """
  body { margin:0; padding:0; background:#0c1320; font-family:'IBM Plex Sans',Arial,sans-serif;
         color:#e2e8f0; font-size:14px; }
  .wrap { max-width:720px; margin:0 auto; padding:24px 16px; }
  .hdr { background:#111827; border-bottom:2px solid #2563eb; padding:20px 24px;
         border-radius:8px 8px 0 0; }
  .hdr-title { font-size:1.1rem; font-weight:700; color:#e2e8f0; letter-spacing:0.05em; }
  .hdr-sub { font-size:0.75rem; color:#64748b; margin-top:4px; }
  .section { background:#111827; border:1px solid #1e2d45; border-radius:6px;
             padding:16px 20px; margin:12px 0; }
  .sec-title { font-size:0.65rem; font-weight:700; letter-spacing:0.12em;
               color:#64748b; text-transform:uppercase; margin-bottom:12px;
               border-bottom:1px solid #1e2d45; padding-bottom:6px; }
  table.tbl { width:100%; border-collapse:collapse; }
  table.tbl th { font-size:0.62rem; font-weight:600; color:#64748b;
                 text-transform:uppercase; letter-spacing:0.08em;
                 padding:4px 8px; border-bottom:1px solid #1e2d45; text-align:right; }
  table.tbl th.l { text-align:left; }
  table.tbl td { font-size:0.78rem; padding:5px 8px; color:#e2e8f0;
                 border-bottom:1px solid #0f1929; text-align:right; }
  table.tbl td.l { text-align:left; }
  table.tbl td.tick { color:#3b82f6; font-weight:600;
                      font-family:'IBM Plex Mono',monospace; text-align:left; }
  .pos { color:#22c55e; }
  .neg { color:#ef4444; }
  .neu { color:#94a3b8; }
  .badge { display:inline-block; font-size:0.6rem; font-weight:700; letter-spacing:0.08em;
           padding:2px 6px; border-radius:3px; text-transform:uppercase; }
  .idx-row { display:flex; gap:12px; flex-wrap:wrap; }
  .idx-card { flex:1; min-width:120px; background:#0f1929; border:1px solid #1e2d45;
              border-radius:6px; padding:10px 14px; }
  .idx-name { font-size:0.62rem; color:#64748b; font-weight:600;
              letter-spacing:0.08em; text-transform:uppercase; }
  .idx-val  { font-size:1.05rem; font-weight:700; color:#e2e8f0; margin-top:3px; }
  .idx-chg  { font-size:0.75rem; margin-top:1px; }
  .idea-card { border-left:3px solid #2563eb; padding:10px 14px;
               background:#0f1929; border-radius:0 6px 6px 0; margin:8px 0; }
  .ai-box { background:#0a1020; border:1px solid #1e2d45; border-radius:6px;
            padding:14px 16px; color:#94a3b8; font-size:0.8rem; line-height:1.6; }
  .footer { font-size:0.68rem; color:#475569; text-align:center; padding:16px;
            border-top:1px solid #1e2d45; margin-top:16px; }
"""


# ── Data helpers ──────────────────────────────────────────────────────────────

def _load_prices():
    p = DATA_DIR / "prices.csv"
    return pd.read_csv(p) if p.exists() else pd.DataFrame()


def _load_filings(days=1):
    p = DATA_DIR / "filings.csv"
    if not p.exists():
        return pd.DataFrame()
    df = pd.read_csv(p)
    if "date" not in df.columns:
        return df
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    cutoff = pd.Timestamp.now() - pd.Timedelta(days=days)
    return df[df["date"] >= cutoff]


def _load_order_book_scored():
    p = DATA_DIR / "order_book.csv"
    if not p.exists():
        return pd.DataFrame()
    from utils.scoring import score_order_book_df
    return score_order_book_df(pd.read_csv(p))


def _load_universe():
    p = DATA_DIR / "universe.csv"
    return pd.read_csv(p) if p.exists() else pd.DataFrame()


# ── Index snapshot ────────────────────────────────────────────────────────────

def _index_snapshot_html():
    try:
        from utils.nse_fetcher import fetch_index_snapshot
        indices = fetch_index_snapshot()
    except Exception:
        indices = []

    if not indices:
        return "<p style='color:#64748b;'>Index data unavailable.</p>"

    cards = ""
    for idx in indices[:6]:
        name  = idx.get("name", "")
        val   = idx.get("last", 0)
        chg   = idx.get("change_pct", 0)
        sign  = "+" if chg >= 0 else ""
        cls   = "pos" if chg >= 0 else "neg"
        cards += f"""
        <div class="idx-card">
          <div class="idx-name">{name}</div>
          <div class="idx-val">{val:,.0f}</div>
          <div class="idx-chg {cls}">{sign}{chg:.2f}%</div>
        </div>"""
    return f'<div class="idx-row">{cards}</div>'


# ── Top movers table ──────────────────────────────────────────────────────────

def _top_movers_html(prices_df, n=8):
    if prices_df.empty or "return_1d" not in prices_df.columns:
        return "<p style='color:#64748b;'>Price data unavailable.</p>"

    uni = _load_universe()
    name_map = {}
    if not uni.empty and "company_name" in uni.columns:
        name_map = uni.set_index("ticker")["company_name"].to_dict()

    df = prices_df.copy()
    df["return_1d"] = pd.to_numeric(df["return_1d"], errors="coerce")
    gainers = df.nlargest(n // 2, "return_1d")
    losers  = df.nsmallest(n // 2, "return_1d")
    combined = pd.concat([gainers, losers])

    rows = ""
    for _, r in combined.iterrows():
        ret  = r.get("return_1d", 0) * 100 if abs(r.get("return_1d", 0)) < 1 else r.get("return_1d", 0)
        sign = "+" if ret >= 0 else ""
        cls  = "pos" if ret >= 0 else "neg"
        name = name_map.get(r.get("ticker", ""), "")[:28]
        rows += f"""
        <tr>
          <td class="tick">{r.get('ticker','')}</td>
          <td class="l" style="color:#94a3b8;">{name}</td>
          <td style="font-family:'IBM Plex Mono',monospace;">
            {r.get('close', 0):,.1f}</td>
          <td class="{cls}" style="font-family:'IBM Plex Mono',monospace;">
            {sign}{ret:.2f}%</td>
        </tr>"""

    return f"""<table class="tbl">
      <thead><tr>
        <th class="l">Ticker</th><th class="l">Company</th>
        <th>Price</th><th>1D Chg</th>
      </tr></thead>
      <tbody>{rows}</tbody>
    </table>"""


# ── Filings table ─────────────────────────────────────────────────────────────

def _filings_html(filings_df, n=10):
    if filings_df.empty:
        return "<p style='color:#64748b;'>No material filings in the last 24 hours.</p>"

    mat = filings_df[filings_df.get("is_material", pd.Series(dtype=bool))] if "is_material" in filings_df.columns else filings_df
    mat = mat.head(n)
    rows = ""
    for _, r in mat.iterrows():
        s = str(r.get("sentiment", "neutral")).lower()
        cls = "pos" if s == "positive" else ("neg" if s == "negative" else "neu")
        rows += f"""
        <tr>
          <td class="tick">{r.get('ticker','')}</td>
          <td class="l" style="color:#94a3b8;">{str(r.get('subject',''))[:70]}</td>
          <td class="l"><span class="{cls}">{s.upper()}</span></td>
        </tr>"""
    return f"""<table class="tbl">
      <thead><tr>
        <th class="l">Ticker</th><th class="l">Announcement</th><th class="l">Sentiment</th>
      </tr></thead>
      <tbody>{rows}</tbody>
    </table>"""


# ── Top OB ideas ──────────────────────────────────────────────────────────────

def _ideas_html(ob_df, n=5):
    if ob_df.empty or "ob_score" not in ob_df.columns:
        return "<p style='color:#64748b;'>Order book data unavailable.</p>"

    top = ob_df.nlargest(n, "ob_score")
    html = ""
    for _, r in top.iterrows():
        cls = r.get("classification", "Research")
        score = r.get("ob_score", 0)
        ob_rev = r.get("ob_revenue_ratio", 0)
        html += f"""
        <div class="idea-card">
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <div>
              <span style="color:#3b82f6;font-weight:700;font-family:'IBM Plex Mono',monospace;">
                {r.get('ticker','')}</span>
              <span style="color:#94a3b8;font-size:0.75rem;margin-left:8px;">
                {r.get('company_name','')}</span>
            </div>
            <div>
              <span style="color:#e2e8f0;font-weight:700;">{score:.0f}</span>
              <span style="color:#64748b;font-size:0.7rem;"> / 100</span>
            </div>
          </div>
          <div style="font-size:0.72rem;color:#64748b;margin-top:4px;">
            OB/Rev: {ob_rev:.1f}x &nbsp;|&nbsp; {cls} &nbsp;|&nbsp; {r.get('sector','')}
          </div>
        </div>"""
    return html


# ── AI market brief ───────────────────────────────────────────────────────────

def _ai_brief_html(brief_type):
    try:
        from utils.ai_summarizer import generate_market_summary
        prices = _load_prices()
        filings = _load_filings(days=1)
        result = generate_market_summary(prices, filings, {})
        text = result if isinstance(result, str) else result.get("summary", "")
        return f'<div class="ai-box">{text}</div>' if text else ""
    except Exception:
        return ""


# ── Email builders ────────────────────────────────────────────────────────────

def build_morning_email(date_str):
    index_html  = _index_snapshot_html()
    filings_df  = _load_filings(days=1)
    filings_html = _filings_html(filings_df)
    ob_df       = _load_order_book_scored()
    ideas_html  = _ideas_html(ob_df, n=3)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>{_EMAIL_CSS}</style>
</head>
<body>
<div class="wrap">

  <div class="hdr">
    <div class="hdr-title">India Markets Intelligence Terminal</div>
    <div class="hdr-sub">Morning Brief &mdash; {date_str}</div>
  </div>

  <div class="section">
    <div class="sec-title">Index Snapshot</div>
    {index_html}
  </div>

  <div class="section">
    <div class="sec-title">Key Events Today</div>
    {filings_html}
  </div>

  <div class="section">
    <div class="sec-title">Top Order Book Opportunities</div>
    {ideas_html}
  </div>

  <div class="footer">
    India Public Markets Intelligence Terminal &mdash; Internal Use Only<br>
    <span style="color:#1e2d45;">Not investment advice. Do your own research.</span>
  </div>

</div>
</body>
</html>"""
    return html


def build_evening_email(date_str):
    prices_df    = _load_prices()
    movers_html  = _top_movers_html(prices_df, n=10)
    filings_df   = _load_filings(days=1)
    filings_html = _filings_html(filings_df, n=15)
    ob_df        = _load_order_book_scored()
    ideas_html   = _ideas_html(ob_df, n=5)
    ai_html      = _ai_brief_html("evening")

    # Breadth KPIs
    breadth_html = "<p style='color:#64748b;'>Price data unavailable.</p>"
    if not prices_df.empty and "return_1d" in prices_df.columns:
        ret = pd.to_numeric(prices_df["return_1d"], errors="coerce")
        ret_pct = ret.apply(lambda x: x * 100 if abs(x) < 1 else x)
        adv  = (ret_pct > 0).sum()
        dec  = (ret_pct < 0).sum()
        avg  = ret_pct.mean()
        sign = "+" if avg >= 0 else ""
        cls  = "pos" if avg >= 0 else "neg"
        breadth_html = f"""
        <div style="display:flex;gap:20px;">
          <div><div class="idx-name">Advancers</div>
               <div class="idx-val pos">{adv}</div></div>
          <div><div class="idx-name">Decliners</div>
               <div class="idx-val neg">{dec}</div></div>
          <div><div class="idx-name">A/D Ratio</div>
               <div class="idx-val">{adv/(dec or 1):.1f}</div></div>
          <div><div class="idx-name">Avg Return</div>
               <div class="idx-val {cls}">{sign}{avg:.2f}%</div></div>
        </div>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>{_EMAIL_CSS}</style>
</head>
<body>
<div class="wrap">

  <div class="hdr">
    <div class="hdr-title">India Markets Intelligence Terminal</div>
    <div class="hdr-sub">Evening Brief &mdash; {date_str}</div>
  </div>

  <div class="section">
    <div class="sec-title">Market Breadth</div>
    {breadth_html}
  </div>

  <div class="section">
    <div class="sec-title">Top Movers</div>
    {movers_html}
  </div>

  <div class="section">
    <div class="sec-title">Corporate Filings</div>
    {filings_html}
  </div>

  <div class="section">
    <div class="sec-title">Order Book Leaderboard</div>
    {ideas_html}
  </div>

  {"<div class='section'><div class='sec-title'>AI Market Summary</div>" + ai_html + "</div>" if ai_html else ""}

  <div class="footer">
    India Public Markets Intelligence Terminal &mdash; Internal Use Only<br>
    <span style="color:#1e2d45;">Not investment advice. Do your own research.</span>
  </div>

</div>
</body>
</html>"""
    return html


# ── SMTP send ─────────────────────────────────────────────────────────────────

def send_email(subject, html_body, recipients):
    smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    email_from = os.environ.get("EMAIL_FROM", "")
    email_pass = os.environ.get("EMAIL_PASSWORD", "")

    if not email_from or not email_pass:
        logger.error("EMAIL_FROM and EMAIL_PASSWORD must be set in .env")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = email_from
    msg["To"]      = ", ".join(recipients)
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.ehlo()
            server.starttls()
            server.login(email_from, email_pass)
            server.sendmail(email_from, recipients, msg.as_string())
        logger.info("Email sent to %s", recipients)
        return True
    except Exception as e:
        logger.error("SMTP error: %s", e)
        return False


# ── Main ──────────────────────────────────────────────────────────────────────

def run(brief_type=None, test_mode=False):
    now      = _ist_now()
    date_str = now.strftime("%A, %d %B %Y — %I:%M %p IST")

    if brief_type is None:
        brief_type = _detect_brief_type()

    logger.info("Sending %s brief (%s)", brief_type, date_str)

    if brief_type == "morning":
        subject = f"[India Terminal] Morning Brief — {now.strftime('%d %b %Y')}"
        html    = build_morning_email(date_str)
    else:
        subject = f"[India Terminal] Evening Brief — {now.strftime('%d %b %Y')}"
        html    = build_evening_email(date_str)

    if test_mode:
        subject = "[TEST] " + subject

    email_to_raw = os.environ.get("EMAIL_TO", "")
    if not email_to_raw:
        logger.error("EMAIL_TO not set in .env")
        return

    recipients = [e.strip() for e in email_to_raw.split(",") if e.strip()]
    success = send_email(subject, html, recipients)

    if success:
        logger.info("=== %s Brief Sent Successfully ===", brief_type.title())
    else:
        logger.error("=== %s Brief FAILED ===", brief_type.title())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Send daily email brief")
    parser.add_argument("--brief", choices=["morning", "evening"], default=None)
    parser.add_argument("--test",  action="store_true", help="Mark as test email")
    args = parser.parse_args()
    run(brief_type=args.brief, test_mode=args.test)

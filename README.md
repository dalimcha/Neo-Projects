# India Public Markets Intelligence Terminal

An institutional-grade research and monitoring platform for Indian listed equities. Built for investment professionals tracking Nifty 500 companies, order book-driven businesses, and sector cycles.

---

## Architecture

```
india_terminal/
├── app.py                          # Home page (module cards, status bar)
├── pages/
│   ├── 1_Market_Command_Center.py  # Index snapshot, breadth, movers, heatmap
│   ├── 2_All_Companies.py          # Full Nifty 500 screener with 30+ columns
│   ├── 3_Company_Detail.py         # Deep dive: financials, OB, AI note
│   ├── 4_Order_Book_Screener.py    # 6-factor OB scoring model (PRIMARY MODULE)
│   ├── 5_New_Ideas.py              # Automated opportunity flagging
│   ├── 6_News_and_Filings.py       # NSE announcements with AI classification
│   ├── 7_Sector_Intelligence.py    # Sector cycle and valuation
│   └── 8_Settings.py               # API keys, email, data management
├── utils/
│   ├── formatting.py               # Visual identity, CSS injection, HTML builders
│   ├── data_loader.py              # Central I/O: CSV reads, caching, computed tables
│   ├── nse_fetcher.py              # NSE bhavcopy, yfinance, corporate announcements
│   ├── scoring.py                  # 6-factor order book scoring model
│   ├── charting.py                 # Plotly chart builders
│   └── ai_summarizer.py            # Anthropic Claude API wrappers
├── scripts/
│   ├── update_prices.py            # Daily price update (NSE bhavcopy or yfinance)
│   ├── update_filings.py           # Fetch NSE corporate announcements
│   ├── generate_ai_summaries.py    # Batch AI summarisation of filings
│   └── send_daily_email.py         # Morning (8:30 AM) + evening (4:30 PM) briefings
├── data/
│   ├── universe.csv                # Master company list (manually maintained)
│   ├── prices.csv                  # Daily price history + multi-period returns
│   ├── fundamentals.csv            # PE, EV/EBITDA, ROE, ROCE, etc. (Screener.in)
│   ├── order_book.csv              # Order book database (manually maintained)
│   ├── filings.csv                 # NSE corporate announcements
│   ├── news.csv                    # News feed
│   ├── sectors.csv                 # Sector metadata
│   └── notes.csv                   # Research notes
└── .streamlit/
    └── config.toml                 # Dark theme settings
```

---

## Quick Start

### 1. Prerequisites

- Python 3.10 or newer
- pip

### 2. Create and activate a virtual environment

```bash
cd /Users/devalimchandani/Documents/Claude/Projects/Financials/india_terminal
python -m venv .venv
source .venv/bin/activate          # macOS/Linux
# .venv\Scripts\activate           # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment

Copy the template and fill in your keys:

```bash
cp .env.example .env
```

Edit `.env`:

```ini
ANTHROPIC_API_KEY=sk-ant-...      # Required for AI features
EMAIL_FROM=you@gmail.com          # Optional — for daily emails
EMAIL_TO=you@gmail.com            # Optional — comma-separated
EMAIL_PASSWORD=xxxx xxxx xxxx     # Gmail App Password (not your main password)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
MORNING_TIME=08:30
EVENING_TIME=16:30
```

### 5. Launch the terminal

```bash
streamlit run app.py
```

Open http://localhost:8501 in your browser.

---

## Initial Data Setup

The terminal ships with sample data for ~130 companies. For live market data, run the update scripts in this order:

### Step 1 — Full price history (run once)

```bash
python scripts/update_prices.py --yf
```

This downloads 1 year of price history for all tickers in `data/universe.csv` via yfinance. Takes 3–5 minutes for 130+ tickers. After the initial run, the daily incremental update is much faster.

### Step 2 — Daily price update (run after market close)

```bash
python scripts/update_prices.py
```

Fetches NSE bhavcopy (official EOD data). Falls back to yfinance if bhavcopy is unavailable.

### Step 3 — Fetch corporate filings

```bash
python scripts/update_filings.py --days 3
```

Fetches NSE corporate announcements for the last 3 days and appends to `data/filings.csv`.

### Step 4 — Generate AI summaries (optional, requires Claude API key)

```bash
python scripts/generate_ai_summaries.py
```

Processes all unsummarised filings through Claude. Adds AI summaries, sentiment, and materiality flags.

### Step 5 — Test email delivery (optional)

```bash
python scripts/send_daily_email.py --test
```

---

## Cron Schedule (recommended)

Add to crontab (`crontab -e`) — all times are IST (UTC+5:30):

```cron
# NSE bhavcopy: 4:30 PM IST (11:00 UTC) Mon–Fri
00 11 * * 1-5  cd /path/to/india_terminal && /path/to/.venv/bin/python scripts/update_prices.py

# Filings: 5:00 PM IST (11:30 UTC) Mon–Fri
30 11 * * 1-5  cd /path/to/india_terminal && /path/to/.venv/bin/python scripts/update_filings.py

# AI summaries: 5:30 PM IST (12:00 UTC) Mon–Fri
00 12 * * 1-5  cd /path/to/india_terminal && /path/to/.venv/bin/python scripts/generate_ai_summaries.py

# Morning email: 8:30 AM IST (03:00 UTC) Mon–Fri
00 03 * * 1-5  cd /path/to/india_terminal && /path/to/.venv/bin/python scripts/send_daily_email.py --brief morning

# Evening email: 4:30 PM IST (11:00 UTC) Mon–Fri
00 11 * * 1-5  cd /path/to/india_terminal && /path/to/.venv/bin/python scripts/send_daily_email.py --brief evening
```

---

## Updating Fundamentals from Screener.in

The terminal reads fundamental data (PE, ROCE, D/E, revenue growth, etc.) from `data/fundamentals.csv`. The easiest workflow:

1. Go to [Screener.in](https://www.screener.in)
2. Create a custom screen or use the Nifty 500 list
3. Export as CSV
4. In the terminal, go to **Settings → Data Management → Upload Screener CSV**
5. Map the columns and click **Import to Fundamentals**

### Required Screener columns

| Screener Column    | Maps to                |
|--------------------|------------------------|
| Ticker             | ticker                 |
| Name               | company_name           |
| PE                 | pe                     |
| EV/EBITDA          | ev_ebitda              |
| PB                 | pb                     |
| ROE                | roe                    |
| ROCE               | roce                   |
| D/E                | debt_equity            |
| Revenue Gr %       | revenue_growth_1y      |
| PAT Gr %           | pat_growth_1y          |
| EBITDA Margin %    | ebitda_margin          |
| Promoter Holding % | promoter_holding       |
| FII Holding %      | fii_holding            |
| DII Holding %      | dii_holding            |

---

## Order Book Data Entry Guide

Order book data is manually entered. This is intentional — the terminal never hallucinates order book numbers.

### Adding a new company

Go to **Order Book Screener → Add New Company**. Fill in:

| Field             | Required | Description |
|-------------------|----------|-------------|
| Ticker            | Yes      | NSE ticker (e.g. LT, HAL) |
| Company Name      | Yes      | Full name |
| Sector            | Yes      | Sector classification |
| Order Book (Cr)   | Yes      | Total order backlog in Rs Crore |
| Revenue TTM (Cr)  | Yes      | Trailing 12-month revenue in Rs Crore |
| Source Document   | Yes      | E.g. "Q3FY25 Investor Presentation" |
| Source Date       | Yes      | Date of the source document |
| Extracted Text    | Yes      | Verbatim quote from the document |
| Confidence Score  | Yes      | 60–90. Use 90 for management guidance, 75 for analyst estimates |
| Manually Verified | Yes      | Check only after reading the source document yourself |

### Confidence score guide

| Score | Meaning |
|-------|---------|
| 85–90 | Management guidance in concall transcript or results press release |
| 75–84 | Investor presentation; number clearly stated |
| 65–74 | Analyst report citing company data; not yet cross-checked |
| 60–64 | News article; unconfirmed |

### What counts as an order book entry

- Signed contracts / confirmed orders: always include
- LOIs (Letters of Intent): include with confidence ≤70 and note in extracted_text
- Pipeline / potential orders: do NOT include in order_book.csv

### Updating existing entries

Edit `data/order_book.csv` directly. Keep the full source traceability columns for every row. Never delete old rows — instead add a new row with the updated date and mark the old one with an `archived` column.

---

## Order Book Scoring Model

The screener uses a 6-factor model. Maximum score is 100 before penalties.

| Factor                  | Weight | What it measures |
|-------------------------|--------|-----------------|
| OB / Revenue Ratio      | 30%    | Earnings visibility (>3x = full marks) |
| Order Inflow Growth     | 20%    | Demand acceleration (btb_ratio growth) |
| Revenue Growth          | 15%    | Whether the book is converting |
| Margin Stability        | 15%    | EBITDA margin consistency |
| Valuation Discount      | 10%    | PE vs sector peers |
| Balance Sheet Quality   | 10%    | D/E, CFO coverage |

### Classifications

| Label                    | Score Range | Meaning |
|--------------------------|-------------|---------|
| High Conviction          | ≥72         | Strong across all factors |
| Watchlist                | 58–71       | Good setup, needs monitoring |
| Research                 | 42–57       | Worth digging into |
| Momentum But Expensive   | Any         | Good OB + PE premium >50% vs peers |
| Value Trap               | Any         | Cheap PE + falling margins |
| Avoid                    | <42         | Multiple red flags |

### Penalties (applied after raw score)

| Condition                                    | Penalty |
|----------------------------------------------|---------|
| Receivables rising >8pp vs revenue           | −6 pts  |
| EBITDA margins falling >5pp                  | −12 pts |
| D/E > 2x                                     | −8 pts  |
| Execution cycle > 36 months                  | −6 pts  |
| CFO < 50% of net profit                      | −6 pts  |
| One-off / lumpsum order (not annuity)        | −10 pts |
| Customer concentration > 50% (single client) | −6 pts  |

---

## Required API Keys

| Key                  | Required | Purpose | Where to get |
|----------------------|----------|---------|--------------|
| ANTHROPIC_API_KEY    | Optional | AI market summaries, analyst notes, filing summaries | [console.anthropic.com](https://console.anthropic.com/) |
| EMAIL_PASSWORD       | Optional | Gmail App Password for daily email briefs | [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords) |

The terminal works fully without the Anthropic API key — all AI sections degrade gracefully with informational messages.

---

## Sample Data Files

### data/universe.csv (minimum columns)

```csv
ticker,company_name,sector,industry,index_membership,isin,bse_code,nse_code
LT,Larsen & Toubro Ltd,Capital Goods,EPC & Construction,Nifty50|Nifty500,INE018A01030,500510,LT
HAL,Hindustan Aeronautics Ltd,Capital Goods,Aerospace & Defence,NiftyNext50|Nifty500,INE066F01020,541154,HAL
```

### data/order_book.csv (minimum columns)

```csv
ticker,company_name,sector,order_book_cr,revenue_ttm_cr,ob_revenue_ratio,source_document,source_date,extracted_text,confidence_score,manually_verified
LT,Larsen & Toubro Ltd,Capital Goods,560000,220000,2.55,"Q3FY25 Investor Presentation",2025-01-23,"Order book stood at Rs 5.6 lakh crore as of December 2024",90,true
```

### data/fundamentals.csv (minimum columns)

```csv
ticker,company_name,pe,ev_ebitda,pb,roe,roce,debt_equity,ebitda_margin,revenue_growth_1y,pat_growth_1y,promoter_holding,fii_holding,dii_holding,as_of_date
LT,Larsen & Toubro Ltd,32.5,20.1,4.2,14.8,18.2,0.8,12.5,15.2,18.1,51.5,15.2,22.3,2024-12-31
```

---

## Daily Email Briefs (Sample)

**Morning Brief (8:30 AM IST):**
- Index snapshot (Nifty 50, Bank Nifty, Nifty IT, Sensex, VIX)
- Key corporate events today (results, order wins, board meetings)
- Top 3 order book opportunities from the screener

**Evening Brief (4:30 PM IST):**
- Market breadth (advancers / decliners / A-D ratio / average return)
- Top movers (4 gainers + 4 losers)
- Material filings of the day
- Order book leaderboard (top 5 by OB score)
- AI-generated market summary (if Claude API is configured)

---

## Known Limitations

1. **NSE bhavcopy**: The NSE website uses Cloudflare protection. If bhavcopy fetches fail consistently, the script automatically falls back to yfinance.

2. **NSE corporate announcements API**: NSE may change their session cookie requirements without notice. If the live fetch button fails in the News & Filings page, use `python scripts/update_filings.py` from the command line, which establishes a proper browser-like session.

3. **Screener.in**: No public API. Fundamentals must be exported manually as CSV. Recommend updating monthly or after quarterly results.

4. **Order book data**: All order book numbers are manually entered. The terminal will never auto-populate order book data via scraping or AI. Every entry requires a verified source document.

5. **yfinance**: yfinance is a third-party library scraping Yahoo Finance. It may break without warning. NSE bhavcopy is the authoritative source for price data.

6. **AI features**: Requires an active Anthropic API key. All AI-generated text is labelled clearly. AI-extracted order book numbers are marked `manually_verified = false` by default and must be human-verified before use in investment decisions.

---

## Next Steps / Roadmap

- [ ] Connect Screener.in via their premium API (when available)
- [ ] Add BSE corporate announcements (currently NSE only)
- [ ] Sector rotation signal: add sector-level price momentum vs fundamentals scatter
- [ ] Portfolio tracker: P&L against order book score changes
- [ ] Quarterly results calendar: scheduled results dates with alerts
- [ ] Export to PDF: one-click institutional-quality report for a company or sector
- [ ] Mobile view: responsive CSS overrides for tablet/phone usage

---

## Troubleshooting

**App won't start:**
```bash
pip install -r requirements.txt
streamlit run app.py
```

**All data shows as empty:**
Run `python scripts/update_prices.py --yf` first to populate prices.csv.

**AI summaries not working:**
Check that `ANTHROPIC_API_KEY` is set in `.env`. Verify via Settings → API Keys → Test Claude API Connection.

**Email not sending:**
- For Gmail: use an App Password, not your account password
- Enable 2-factor authentication on your Google account first
- App Passwords: myaccount.google.com/apppasswords

**NSE bhavcopy not loading:**
The script tries the last 5 business days. If all fail, it falls back to yfinance automatically. NSE may have a public holiday or network issue.

**Streamlit theme not applying:**
Ensure `.streamlit/config.toml` exists. The file should be in the same directory as `app.py`.

---

## Version

1.0.0 — Initial release  
Built with: Streamlit 1.35+, Pandas 2.0+, Plotly 5.18+, Anthropic Python SDK 0.25+

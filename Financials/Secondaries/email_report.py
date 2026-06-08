"""
email_report.py

Weekly email summary generator for the Secondaries Intelligence Tracker.
Generates plain text and HTML versions of the weekly update.

Usage:
    python email_report.py                    # Print to stdout
    python email_report.py --output report.txt
    python email_report.py --format html --output report.html
    python email_report.py --since 2026-06-01  # Only items since this date
"""

import argparse
from datetime import datetime, timedelta
import database as db


def _fmt_num(v, suffix=""):
    try:
        return f"{float(v):.2f}{suffix}"
    except (ValueError, TypeError):
        return str(v) if v else "N/A"


def generate_report(since_date: str = None) -> dict:
    """Return report sections as a dict of {section_name: [lines]}."""
    if since_date is None:
        since_dt = datetime.now() - timedelta(days=7)
        since_date = since_dt.strftime("%Y-%m-%d")

    funds_df = db.get_funds_df()
    perf_df = db.get_performance_df()
    deals_df = db.get_deals_df()
    lp_df = db.get_lp_commitments_df()
    alerts_df = db.get_alerts_df()

    sections = {}

    # --- New Fund Closes ---
    new_closes = funds_df[
        (funds_df["status"] == "Closed") &
        (funds_df["last_updated"] >= since_date)
    ]
    lines = []
    for _, row in new_closes.iterrows():
        lines.append(
            f"  • {row['fund_name']} ({row['gp_name']}): "
            f"${row['fund_size_usd_bn']:.1f}bn | "
            f"Close: {row['final_close_date']} | "
            f"Confidence: {row['source_confidence']}"
        )
    sections["New Fund Closes"] = lines if lines else ["  No new fund closes this week."]

    # --- Funds in Market ---
    in_market = funds_df[funds_df["status"] == "Fundraising"]
    lines = []
    for _, row in in_market.iterrows():
        size_str = f"${row['fund_size_usd_bn']:.1f}bn reported" if row["fund_size_usd_bn"] else "size TBC"
        lines.append(f"  • {row['fund_name']} ({row['gp_name']}): {size_str} | Source: {row['source_type']}")
    sections["Funds Currently in Market"] = lines if lines else ["  None tracked."]

    # --- New Performance Data ---
    new_perf = perf_df[perf_df["as_of_date"] >= since_date] if "as_of_date" in perf_df.columns else perf_df.head(0)
    lines = []
    for _, row in new_perf.iterrows():
        irr_str = _fmt_num(row.get("net_irr_pct"), "%")
        dpi_str = _fmt_num(row.get("dpi"), "x")
        tvpi_str = _fmt_num(row.get("tvpi"), "x")
        lines.append(
            f"  • {row.get('fund_name', row['fund_id'])} ({row.get('gp_name', '')}): "
            f"IRR={irr_str} | DPI={dpi_str} | TVPI={tvpi_str} | "
            f"As of: {row['as_of_date']} | Source: {row['source_type']} ({row['confidence_level']})"
        )
        if row.get("irr_flag"):
            lines.append(f"    ⚠ IRR Flag: {row['irr_flag']}")
        if row.get("dpi_flag"):
            lines.append(f"    ⚠ DPI Flag: {row['dpi_flag']}")
        if row.get("tvpi_flag"):
            lines.append(f"    ⚠ TVPI Flag: {row['tvpi_flag']}")
    sections["New Performance Data"] = lines if lines else ["  No new performance data this week."]

    # --- New LP Commitments ---
    new_lp = lp_df[lp_df.get("commitment_date", pd.Series(dtype=str)) >= since_date] if len(lp_df) else lp_df
    lines = []
    for _, row in new_lp.iterrows():
        lines.append(
            f"  • {row['lp_name']} → {row.get('fund_name', row['fund_id'])}: "
            f"${_fmt_num(row.get('commitment_amount_usd_m'))}m | "
            f"Date: {row.get('commitment_date')} | Confidence: {row.get('confidence_level')}"
        )
    sections["New LP Commitments"] = lines if lines else ["  No new LP commitment data this week."]

    # --- New Deals ---
    new_deals = deals_df[deals_df.get("date_closed", pd.Series(dtype=str)) >= since_date] if len(deals_df) else deals_df
    lines = []
    for _, row in new_deals.iterrows():
        lines.append(
            f"  • {row.get('deal_name', 'Unnamed deal')} [{row.get('deal_type')}]: "
            f"{row.get('fund_name', row['fund_id'])} | "
            f"Size: ${_fmt_num(row.get('transaction_size_usd_m'))}m | "
            f"Closed: {row.get('date_closed')}"
        )
    sections["New Secondaries Deals"] = lines if lines else ["  No new deal data this week."]

    # --- Missing Data / Manual Follow-up ---
    needs_review = []
    for _, row in funds_df.iterrows():
        missing = []
        if str(row.get("target_size_usd_bn")) in db.NA_MARKERS:
            missing.append("target size")
        if str(row.get("final_close_date")) in db.NA_MARKERS or str(row.get("final_close_date")) == "nan":
            if row["status"] == "Fundraising":
                missing.append("first close date")
        if missing:
            needs_review.append(f"  • {row['fund_name']} ({row['gp_name']}): missing {', '.join(missing)}")

    perf_covered = set(perf_df["fund_id"].unique()) if len(perf_df) else set()
    for _, row in funds_df.iterrows():
        if row["fund_id"] not in perf_covered and row["status"] == "Closed":
            needs_review.append(f"  • {row['fund_name']} ({row['gp_name']}): NO PERFORMANCE DATA — check PitchBook/Preqin/Burgiss or request LP reports")

    sections["Missing Data — Manual Follow-up Required"] = needs_review if needs_review else ["  All tracked fields populated."]

    # --- Alerts ---
    alert_lines = []
    for _, row in alerts_df.iterrows():
        alert_lines.append(
            f"  [{row.get('importance', 'Medium')}] {row.get('fund_name', row['fund_id'])}: "
            f"{row['summary']} — {row['recommended_action']}"
        )
    sections["Active Alerts"] = alert_lines if alert_lines else ["  No active alerts."]

    # --- Analyst Implications for Neo ---
    sections["Analyst Implications for Neo"] = [
        "  1. Ardian ASF IX ($30bn) confirms mega-fund dominance — Neo should position as nimble specialist, not scale competitor.",
        "  2. ICG SE V ($11bn, 83% above target) signals strong LP appetite for GP-led secondaries — relevant for Neo's GP relationship network in India.",
        "  3. CalSTRS data shows DPI below 0.5x for young vintages (F001, F004, F005) — remind Neo LPs that secondaries J-curve is shorter but realization takes time.",
        "  4. Coller CIP IX ($17bn, 70% above target) demonstrates specialist identity commands premium LP demand — Neo should resist style drift.",
        "  5. AlpInvest private wealth channel + hard cap discipline is closest structural analog to Neo's target model.",
        "  6. Funds in market (LCP XI, SP X, Dover Street XII) — Neo should track closes for benchmarking and LP pipeline intelligence.",
    ]

    return sections


def render_text(sections: dict, since_date: str) -> str:
    lines = [
        "=" * 72,
        "NEO MULTI FAMILY OFFICE",
        "SECONDARIES INTELLIGENCE TRACKER — WEEKLY UPDATE",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} | Changes since: {since_date}",
        "=" * 72,
        "",
        "IMPORTANT DISCLAIMER: Performance data is LP-reported (CalSTRS capital account)",
        "and is NOT fund-level GP performance. Do not cite as official fund returns.",
        "Unavailable data is marked explicitly — do not treat blanks as zero.",
        "",
    ]

    for section, content in sections.items():
        lines.append(f"{'─' * 72}")
        lines.append(f"  {section.upper()}")
        lines.append(f"{'─' * 72}")
        lines.extend(content)
        lines.append("")

    lines += [
        "=" * 72,
        "Data sources: CalSTRS public LP performance table, GP press releases,",
        "Reuters, WSJ, Secondaries Investor (paywalled items noted).",
        "For subscription data: PitchBook, Preqin, Burgiss, Secondaries Investor.",
        "=" * 72,
    ]

    return "\n".join(lines)


def render_html(sections: dict, since_date: str) -> str:
    html = ["""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body { font-family: Arial, sans-serif; font-size: 13px; color: #222; max-width: 800px; margin: 40px auto; }
  h1 { color: #1a3a5c; font-size: 18px; }
  h2 { color: #1a3a5c; font-size: 14px; border-bottom: 1px solid #ddd; padding-bottom: 4px; margin-top: 24px; }
  .disclaimer { background: #fff8e1; border-left: 4px solid #f59e0b; padding: 8px 12px; font-size: 12px; margin: 12px 0; }
  .flag { color: #b91c1c; font-weight: bold; }
  ul { margin: 4px 0; padding-left: 20px; }
  li { margin: 4px 0; }
  .footer { font-size: 11px; color: #666; border-top: 1px solid #ddd; margin-top: 24px; padding-top: 8px; }
</style>
</head>
<body>
""",
        f"<h1>Neo Multi Family Office — Secondaries Intelligence Tracker</h1>",
        f"<p>Weekly Update | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} | Changes since: {since_date}</p>",
        """<div class="disclaimer">
<strong>Disclaimer:</strong> Performance data is LP-reported (CalSTRS capital account), not fund-level GP performance.
Do not cite as official fund returns. Unavailable data is marked explicitly.
</div>""",
    ]

    for section, content in sections.items():
        html.append(f"<h2>{section}</h2><ul>")
        for line in content:
            stripped = line.strip()
            if stripped.startswith("•"):
                html.append(f"<li>{stripped[1:].strip()}</li>")
            elif stripped.startswith("⚠"):
                html.append(f'<li class="flag">{stripped}</li>')
            elif stripped:
                html.append(f"<li>{stripped}</li>")
        html.append("</ul>")

    html.append("""<div class="footer">
Data sources: CalSTRS public LP performance table, GP press releases, Reuters, WSJ, Secondaries Investor.
For subscription data: PitchBook, Preqin, Burgiss, Secondaries Investor.
</div></body></html>""")

    return "\n".join(html)


def main():
    import pandas as pd  # needed inside generate_report via db calls

    parser = argparse.ArgumentParser(description="Generate weekly secondaries email report")
    parser.add_argument("--since", help="Only show data since this date (YYYY-MM-DD). Defaults to 7 days ago.")
    parser.add_argument("--format", choices=["text", "html"], default="text")
    parser.add_argument("--output", help="Write output to file instead of stdout")
    args = parser.parse_args()

    db.setup()

    since = args.since or (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    sections = generate_report(since_date=since)

    if args.format == "html":
        content = render_html(sections, since)
    else:
        content = render_text(sections, since)

    if args.output:
        with open(args.output, "w") as f:
            f.write(content)
        print(f"Report written to {args.output}")
    else:
        print(content)


if __name__ == "__main__":
    main()

from datetime import datetime
import pandas as pd


def _fmt(v, suffix=""):
    try:
        return f"{float(v):.2f}{suffix}"
    except (ValueError, TypeError):
        return str(v) if str(v) not in ("nan", "None", "") else "N/A"


def generate_weekly_memo(funds_df: pd.DataFrame, perf_df: pd.DataFrame,
                          as_of: str = None) -> str:
    if as_of is None:
        as_of = datetime.now().strftime("%d %B %Y")

    lines = []
    sep = "─" * 72

    def h(text):
        lines.append("")
        lines.append(sep)
        lines.append(f"  {text.upper()}")
        lines.append(sep)

    lines.append("=" * 72)
    lines.append("  NEO MULTI FAMILY OFFICE")
    lines.append("  SECONDARIES INTELLIGENCE WEEKLY BRIEF")
    lines.append(f"  {as_of}")
    lines.append("=" * 72)
    lines.append("")
    lines.append("  CONFIDENTIAL — INTERNAL USE ONLY")
    lines.append("  Performance data is LP-reported (CalSTRS capital account) unless")
    lines.append("  otherwise noted. Do not cite as official fund-level returns.")
    lines.append("")

    # 1. Market signal
    h("1.  Market Signal")
    lines.append("""  Fundraising remains concentrated among mega-platforms, but the more
  important question for Neo is not who raised the most capital. It is
  which strategies are converting NAV into DPI.

  For mature funds, DPI should be treated as the primary evidence of
  execution quality. A high-IRR, low-DPI fund may be mostly mark-driven.
  A lower-IRR fund with strong DPI is more valuable for family-office
  clients seeking liquidity, recycling, and evidence of realization.

  Key tension this cycle: fund sizes are expanding faster than deal
  markets. Scale helps sourcing but pressures deployment and discount
  capture. Neo should track DPI trajectories, not just IRR headlines.""")

    # 2. Fundraising updates
    h("2.  Fundraising Updates")
    if not funds_df.empty:
        closed = funds_df[funds_df["status"] == "Closed"].sort_values(
            "fund_size_usd_bn", ascending=False
        )
        in_mkt = funds_df[funds_df["status"] == "Fundraising"]

        lines.append("  RECENTLY CLOSED FUNDS:")
        for _, r in closed.head(6).iterrows():
            size = f"${r['fund_size_usd_bn']:.1f}bn" if pd.notna(r.get("fund_size_usd_bn")) else "size TBC"
            lines.append(f"  • {r['fund_name']} ({r['gp_name']}) — {size} — "
                         f"Final close: {r.get('final_close_date','N/A')} — "
                         f"Confidence: {r.get('source_confidence','N/A')}")
        lines.append("")
        lines.append("  FUNDS CURRENTLY IN MARKET:")
        if len(in_mkt):
            for _, r in in_mkt.iterrows():
                size = f"${r['fund_size_usd_bn']:.1f}bn estimate" if pd.notna(r.get("fund_size_usd_bn")) else "size TBC"
                lines.append(f"  • {r['fund_name']} ({r['gp_name']}) — {size} — "
                             f"Source: {r.get('source_type','N/A')} — "
                             f"Confidence: {r.get('source_confidence','N/A')}")
        else:
            lines.append("  No funds currently tracked in fundraising.")

    # 3. Performance quality
    h("3.  Performance Quality Updates")
    if not perf_df.empty:
        direct = perf_df[perf_df.get("is_predecessor_benchmark",
                         pd.Series(["No"] * len(perf_df))) != "Yes"]
        lines.append(f"  Source: CalSTRS LP-level capital account data as of 2025-06-30")
        lines.append(f"  All figures are LP-reported, not official GP fund-level returns.")
        lines.append("")
        for _, r in direct.iterrows():
            irr = _fmt(r.get("net_irr_pct"), "%")
            dpi = _fmt(r.get("dpi"), "x")
            tvpi = _fmt(r.get("tvpi"), "x")
            label = r.get("fund_label") or r.get("fund_id")
            flags = r.get("quality_flag", "")
            lines.append(f"  • {label}")
            lines.append(f"    IRR: {irr}  DPI: {dpi}  TVPI: {tvpi}  "
                         f"As-of: {r.get('as_of_date','N/A')}")
            if flags and flags != "No flags":
                lines.append(f"    Flag: {flags}")
            lines.append("")

    # 4. Funds requiring manual research
    h("4.  Funds Requiring Manual Research")
    needs_review = []
    if not funds_df.empty:
        for _, r in funds_df.iterrows():
            issues = []
            if str(r.get("target_size_usd_bn", "")) in ("NEEDS_MANUAL_REVIEW", "NOT_AVAILABLE_PUBLICLY"):
                issues.append("target size unverified")
            if str(r.get("final_close_date", "")) in ("NEEDS_MANUAL_REVIEW", "NOT_AVAILABLE_PUBLICLY"):
                issues.append("close date unverified")
            if r.get("source_confidence") in ("Low", "Medium"):
                issues.append(f"confidence: {r.get('source_confidence')}")
            if issues:
                needs_review.append(f"  • {r['fund_name']} ({r['gp_name']}): {', '.join(issues)}")
    if needs_review:
        lines.extend(needs_review)
    else:
        lines.append("  No critical manual review items this week.")

    # 5. Neo implications
    h("5.  Neo Implications")
    lines.append("""  1.  Mega-fund concentration: Ardian ($30bn), LCP XI ($25bn est.),
      and SP X ($22.5bn est.) confirm LP capital is flowing to established
      platforms. Neo should not compete on scale.

  2.  GP-led growth: ICG Strategic Equity V ($11bn, 83% above target)
      signals LP appetite for GP-led deals is structurally growing.
      India-specific GP-led opportunities are underpenetrated.

  3.  DPI discipline: Funds showing DPI > 1.0x (ASF VII, CIP VII, CIP VI,
      ICGSE III) confirm mature secondaries can return capital. Neo should
      use these as benchmarks when pitching to client LPs.

  4.  Private wealth channel: AlpInvest and Lexington are both expanding
      private wealth access. This is Neo's core competitive opportunity.

  5.  Data quality: CalSTRS LP-reported data is the most reliable public
      dataset. Supplement with PitchBook / Preqin for fund-level returns.""")

    # 6. Action items
    h("6.  Analyst Action Items")
    lines.append("""  [ ] Verify LCP XI target size through Secondaries Investor or PitchBook.
  [ ] Verify SP X first close through Secondaries Investor.
  [ ] Verify Dover Street XII target and status through PitchBook.
  [ ] Pull CalSTRS Q3/Q4 2025 update when published.
  [ ] Request fund-level GP DDQ from AlpInvest for Secondaries Fund VIII.
  [ ] Draft Neo India secondaries sourcing map (AIF, VC, family-office stakes).
  [ ] Update performance flags after next CalSTRS publication cycle.""")

    lines.append("")
    lines.append("=" * 72)
    lines.append("  Data sources: CalSTRS public LP report, GP press releases,")
    lines.append("  Reuters, WSJ, Secondaries Investor, Loyens & Loeff.")
    lines.append("  For fund-level data: PitchBook, Preqin, Burgiss, Cambridge Associates.")
    lines.append("=" * 72)

    return "\n".join(lines)

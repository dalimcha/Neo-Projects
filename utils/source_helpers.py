"""
source_helpers.py
─────────────────
Tag every number that reaches the UI with its source and timestamp.

Rule: if a number is shown without a `SourceTag`, the calling code is wrong.
"""

from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class SourceTag:
    """Where a single number / row came from."""
    source:        str                 = "—"
    fetched_at:    Optional[datetime]  = None
    snippet:       str                 = ""        # optional verbatim quote
    confidence:    Optional[int]       = None      # 0-100, None if not applicable
    manually_verified: bool            = False

    def short(self) -> str:
        ts = self.fetched_at.strftime("%d %b %H:%M") if self.fetched_at else "—"
        return f"{self.source} · {ts}"

    def html(self) -> str:
        col = "#16a34a" if self.manually_verified else "#3d5270"
        verif = "&#10003; Verified" if self.manually_verified else "Unverified"
        conf = (f' · <span style="color:#60a5fa;">conf {self.confidence}</span>'
                if self.confidence is not None else "")
        return (
            f'<span style="font-family:\'JetBrains Mono\',monospace;'
            f'font-size:0.65rem;color:{col};letter-spacing:0.02em;">'
            f'{self.source} · {self.fetched_at.strftime("%d %b %H:%M") if self.fetched_at else "—"}'
            f'{conf} · {verif}'
            f'</span>'
        )


def na(label: str = "N/A", source: SourceTag | None = None) -> str:
    """Standard rendering for a missing value."""
    if source:
        return (
            f'<span style="color:#475569;font-family:\'JetBrains Mono\',monospace;">'
            f'{label}</span>'
            f'<div style="font-size:0.6rem;color:#2d3f5a;margin-top:2px;">{source.short()}</div>'
        )
    return f'<span style="color:#475569;font-family:\'JetBrains Mono\',monospace;">{label}</span>'


def safe_div(num, den, fallback: str = "N/A") -> float | str:
    """Divide, returning a sentinel rather than inf or NaN on zero/None."""
    try:
        n = float(num) if num is not None else None
        d = float(den) if den is not None else None
        if n is None or d is None:
            return fallback
        if d == 0:
            return fallback
        return n / d
    except (TypeError, ValueError):
        return fallback


def safe_pct_change(curr, base, fallback: str = "N/A") -> float | str:
    """((curr - base) / base) * 100, with explicit fallback on bad inputs."""
    r = safe_div(curr, base, fallback=None)
    if r is None or r is False:
        return fallback
    try:
        return (float(r) - 1) * 100
    except (TypeError, ValueError):
        return fallback

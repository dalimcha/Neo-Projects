from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from utils.data_loader import build_morning_brief, load_returns_snapshot, load_sector_performance, load_filings, load_news


def test_morning_brief_format():
    lines = build_morning_brief(
        load_returns_snapshot(),
        load_sector_performance(),
        {},
        load_filings(),
        load_news(),
    )
    assert lines
    for line in lines:
        assert len(line) <= 110
        lowered = line.lower()
        assert "nan" not in lowered
        assert "inf" not in lowered
        assert "(+0)" not in line

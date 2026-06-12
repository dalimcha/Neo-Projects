from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from utils.formatting import _validate_html_fragment


def test_validator_rejects_broken_html():
    assert _validate_html_fragment("<div><span>ok</span></div>")
    assert not _validate_html_fragment("</div>")
    assert not _validate_html_fragment("<div><span>broken</div>")


def test_core_pages_do_not_contain_lone_closing_div_text():
    paths = [
        ROOT / "app.py",
        ROOT / "pages" / "1_Market_Command_Center.py",
        ROOT / "pages" / "2_All_Companies.py",
        ROOT / "pages" / "5_New_Ideas.py",
        ROOT / "pages" / "9_Return_Quartiles.py",
    ]
    for path in paths:
        text = path.read_text()
        assert '">/div<' not in text
        assert "> </div>" not in text

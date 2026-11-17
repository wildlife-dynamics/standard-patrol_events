from pathlib import Path

from ecoscope_workflows_ext_standard_patrol_events.tasks import load_report_template, set_report_blocks


def test_packaged_template_exists():
    path = Path(load_report_template())
    assert path.is_file() and path.suffix == ".docx"


def test_report_blocks_defaults_follow_mrd_core_optional_split():
    b = set_report_blocks()
    assert b["show_headline_stats"] == "true" and b["show_conclusions"] == "true"
    assert b["show_personnel"] == "false" and b["show_category_priority"] == "false"
    assert all(v in ("true", "false") for v in b.values()) and len(b) == 9


def test_report_blocks_override():
    assert set_report_blocks(personnel=True)["show_personnel"] == "true"

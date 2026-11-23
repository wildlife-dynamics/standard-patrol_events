from pathlib import Path

from ecoscope_workflows_ext_standard_patrol_events.tasks import load_report_template, set_report_blocks


def test_packaged_template_exists():
    path = Path(load_report_template())
    assert path.is_file() and path.suffix == ".docx"


def test_report_blocks_all_on_by_default():
    b = set_report_blocks()
    assert all(v == "true" for v in b.values()) and len(b) == 9


def test_report_blocks_override():
    b = set_report_blocks(sections=["personnel"])
    assert b["show_personnel"] == "true" and b["show_headline_stats"] == "false"


def test_images_options():
    from ecoscope_workflows_ext_standard_patrol_events.tasks import set_images_options

    assert set_images_options() == {"list_only": False, "max_images": 50}
    assert set_images_options(skip_download=True, max_images=5) == {"list_only": True, "max_images": 5}


def test_images_options_skip():
    from ecoscope_workflows_ext_standard_patrol_events.tasks import set_images_options

    assert set_images_options(skip_download=True)["list_only"] is True

"""Renders the packaged template through ext-custom create_docx, as the workflow does.
Runs only in the ext-custom env (importorskip); the data package env skips it."""

from pathlib import Path

import pytest

pytest.importorskip("ecoscope_workflows_ext_custom")

import pandas as pd  # noqa: E402
from docx import Document  # noqa: E402
from ecoscope_workflows_ext_custom.tasks.localization import get_report_labels  # noqa: E402
from ecoscope_workflows_ext_custom.tasks.results import (  # noqa: E402
    ImageContextItem, ImageListContextItem, TableContextItem, TableListContextItem,
    TemplateContext, TextContextItem, create_docx,
)
from PIL import Image  # noqa: E402

from ecoscope_workflows_ext_standard_patrol_events.tasks import set_report_blocks  # noqa: E402

TEMPLATE = Path(__file__).parent.parent / "ecoscope_workflows_ext_standard_patrol_events/data/standard_patrol_events.docx"
L = get_report_labels("es")
MAPS = ("tracks_map", "time_density_map", "event_density_map", "events_bar", "monthly_chart")


def _text(doc):
    parts = [p.text for p in doc.paragraphs]
    for t in doc.tables:
        parts += [c.text for row in t.rows for c in row.cells]
    return "\n".join(parts)


def _render(tmp_path, *, blocks=None, effort=None, detail_mode="general", photo=None, personnel=None):
    png = tmp_path / "t.png"
    Image.new("RGB", (40, 30), "red").save(png)
    df = pd.DataFrame({"a": ["x1", "x2"], "b": ["y1", "y2"]})
    text = {"title": "TITLE", "subtitle": "SUB", "area": "AREA", "period": "PERIOD", "generated_by": "GENBY",
            "date_generated": "DATE", "n_patrols": "11", "total_km": "22", "total_hours": "33",
            "patrol_days": "9", "n_events": "44", "detail_intro": "INTRO",
            "detail_mode": detail_mode}
    items = [TextContextItem(key=k, value=v) for k, v in text.items()]
    items += [ImageContextItem(key=k, value=str(png), width_inches=2) for k in MAPS]
    items += [TableContextItem(key=k, value=df) for k in ("events_by_type", "category_priority", "event_details")]
    items += [TableContextItem(key="personnel", value=df if personnel is None else personnel)]
    items += [
        TableContextItem(key="effort", value=df if effort is None else effort),
        TableListContextItem(key="event_detail_tables", value=[{"heading": "CAT", "title": "TYPE (2)", "table": df}]),
        ImageListContextItem(key="images", value=pd.DataFrame({"caption": ["CAP1", "CAP2"], "image_path": [str(photo or png)] * 2}),
                             width_inches=1),
        ImageListContextItem(key="logos", value=pd.DataFrame({"caption": [""], "image_path": [str(png)]}), width_inches=1),
    ]
    out = create_docx(template_path=str(TEMPLATE), context=TemplateContext(items=items), output_dir=str(tmp_path),
                      extra_text=[L, set_report_blocks(personnel=True, monthly_chart=True, category_priority=True,
                                                       **(blocks or {}))])
    return Document(out)


def test_full_render_uses_language_labels_and_leaves_no_tags(tmp_path):
    doc = _render(tmp_path)
    text = _text(doc)
    for key in ("L_patrol_effort", "L_maps", "L_event_summary", "L_event_details", "L_images", "L_conclusions",
                "L_personnel", "L_category_priority", "L_fig_tracks", "L_fig_monthly", "L_period"):
        assert L[key] in text, key
    assert L["L_footer"] in doc.sections[0].footer.paragraphs[0].text
    assert "{{" not in text and "{%" not in text
    assert "CAP1" in text and "x1" in text and L["no_data"] not in text
    assert len(doc.inline_shapes) == len(MAPS) + 2 + 1  # maps/charts + 2 photos + 1 logo


def test_blocks_off_and_empty_table(tmp_path):
    doc = _render(tmp_path, blocks={"time_density": False, "conclusions": False}, effort=pd.DataFrame())
    text = _text(doc)
    assert L["L_fig_time_density"] not in text and L["L_conclusions"] not in text
    assert L["no_data"] in text  # empty effort table


def test_images_blank_mode_keeps_captions_without_photos(tmp_path):
    doc = _render(tmp_path, photo=tmp_path / "not-downloaded.jpg")
    assert "CAP1" in _text(doc)
    assert len(doc.inline_shapes) == len(MAPS) + 1


def test_per_type_detail_mode(tmp_path):
    text = _text(_render(tmp_path, detail_mode="per_type"))
    assert "CAT · TYPE (2)" in text


def test_personnel_number_and_date_merge_per_patrol(tmp_path):
    cols = [L[k] for k in ("patrol", "date", "patrol_type", "schedule", "leader", "members")]
    rows = [["70", "11/11/2026", "Pedestre", "09:08 – 09:10", "X", "Y"],
            ["70", "11/11/2026", "Camioneta", "09:10 – 09:11", "X", "Y"],
            ["72", "11/11/2026", "Pedestre", "10:00 – 11:00", "Z", "W"]]  # same date, other patrol
    doc = _render(tmp_path, personnel=pd.DataFrame(rows, columns=cols))
    table = next(t for t in doc.tables if t.rows[0].cells[0].text == L["patrol"])
    xml = table._tbl.xml
    assert xml.count('w:val="continue"') == 2  # number and date of #70's second leg
    assert xml.count('w:val="restart"') == 4  # number and date of #70 and of #72
    assert xml.count(">70<") == 1 and xml.count(">72<") == 1 and xml.count("11/11/2026") == 2
    assert [c.text for c in table.rows[0].cells] == cols


def test_rendered_report_keeps_word_schema_order(tmp_path):
    # Word refuses a file whose tblPr children are out of schema order (python-docx doesn't)
    from docx.oxml.ns import qn

    doc = _render(tmp_path)
    for t in doc.tables:
        tags = [c.tag.split("}")[1] for c in t._tbl.tblPr]
        if "tblBorders" in tags and "tblLook" in tags:
            assert tags.index("tblBorders") < tags.index("tblLook"), tags
    zoom = doc.settings.element.find(qn("w:zoom"))
    assert zoom is None or zoom.get(qn("w:percent"))

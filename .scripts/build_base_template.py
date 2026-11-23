"""Builds the packaged report template (docxtpl/Jinja). Every heading and caption
is a label variable (L_*, from get_report_labels), so one layout serves en/es/pt;
block switches (show_*) come from set_report_blocks; detail_mode
is the form value. Logos come in as an image list.

  pixi run --manifest-path $M python .scripts/build_base_template.py

docxtpl rules: {%p %} alone in its paragraph, {%tr %} alone in its row, {%tc %} alone in its cell.
"""

from pathlib import Path
import subprocess
import os

from docx import Document
from docx.enum.section import WD_ORIENT, WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

# The data package lives in a wd-partner-tasks checkout next to this repo (or $PARTNER_TASKS).
_W = Path(subprocess.check_output(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"], text=True).strip()).parents[1]
PARTNER_PKG = Path(os.environ.get("PARTNER_TASKS", _W / "wd-partner-tasks-standard-patrol-events")) / "src/ecoscope-workflows-ext-standard-patrol-events"
OUT = PARTNER_PKG / "ecoscope_workflows_ext_standard_patrol_events/data/standard_patrol_events.docx"
ACCENT = RGBColor(0x1F, 0x4E, 0x46)  # deep green
MUTED = RGBColor(0x6B, 0x72, 0x80)
TABLE_STYLE = "Light List Accent 1"

doc = Document()
sec = doc.sections[0]
sec.page_height, sec.page_width = Cm(29.7), Cm(21.0)
for side in ("left_margin", "right_margin"):
    setattr(sec, side, Cm(2))
sec.top_margin, sec.bottom_margin = Cm(1.8), Cm(1.8)

base = doc.styles["Normal"]
base.font.name, base.font.size = "Calibri", Pt(10)
for name, size in (("Title", 22), ("Heading 1", 14), ("Heading 2", 11)):
    st = doc.styles[name]
    st.font.name, st.font.size, st.font.color.rgb, st.font.bold = "Calibri", Pt(size), ACCENT, True
doc.styles["Title"].font.bold = False


def p(text="", style=None, size=None, color=None, align=None, bold=False, space_after=None):
    para = doc.add_paragraph(style=style)
    if text:
        run = para.add_run(text)
        run.bold = bold
        if size:
            run.font.size = Pt(size)
        if color:
            run.font.color.rgb = color
    if align is not None:
        para.alignment = align
    if space_after is not None:
        para.paragraph_format.space_after = Pt(space_after)
    return para


def tag(text):
    para = doc.add_paragraph(text)
    para.paragraph_format.space_after = Pt(0)


def on(flag):
    return f"{{%p if {flag}|string|lower in ('true', '1') %}}"


def shade(cell, hex_fill):
    tcpr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:fill"), hex_fill)
    tcpr.append(shd)


def borders(table, color="D1D5DB"):
    tblpr = table._tbl.tblPr
    b = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        e = OxmlElement(f"w:{edge}")
        e.set(qn("w:val"), "single")
        e.set(qn("w:sz"), "4")
        e.set(qn("w:color"), color)
        b.append(e)
    # Word rejects the file when tblPr children are out of schema order: tblBorders goes
    # before shd / tblLayout / tblCellMar / tblLook / tblCaption / tblDescription.
    after = ("shd", "tblLayout", "tblCellMar", "tblLook", "tblCaption", "tblDescription")
    nxt = next((c for c in tblpr if c.tag.split("}")[1] in after), None)
    tblpr.insert(list(tblpr).index(nxt), b) if nxt is not None else tblpr.append(b)


def full_width(table):
    """Span the text width (python-docx tables default to autofit-to-content)."""
    table.autofit = False
    tblw = table._tbl.tblPr.find(qn("w:tblW"))
    if tblw is None:
        tblw = OxmlElement("w:tblW")
        table._tbl.tblPr.append(tblw)
    tblw.set(qn("w:type"), "pct")
    tblw.set(qn("w:w"), "5000")


def dynamic_table(var):
    """Dynamic columns and rows; header shaded, light borders, last row (totals) bold via data."""
    t = doc.add_table(rows=4, cols=3)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    borders(t)
    full_width(t)
    head = t.rows[0].cells
    head[0].text, head[1].text, head[2].text = f"{{%tc for col in {var}.col_labels %}}", "{{ col }}", "{%tc endfor %}"
    for c in head:
        shade(c, "1F4E46")
        for r in c.paragraphs[0].runs:
            r.font.color.rgb, r.font.bold, r.font.size = RGBColor(0xFF, 0xFF, 0xFF), True, Pt(9)
    t.rows[1].cells[0].text = f"{{%tr for item in {var}.tbl_contents %}}"
    row = t.rows[2].cells
    row[0].text, row[1].text, row[2].text = "{%tc for col in item.cols %}", "{{ col }}", "{%tc endfor %}"
    for c in row:
        for r in c.paragraphs[0].runs:
            r.font.size = Pt(9)
    t.rows[3].cells[0].text = "{%tr endfor %}"


def header_row(cells, texts):
    for c, text in zip(cells, texts):
        c.text = text
        shade(c, "1F4E46")
        for r in c.paragraphs[0].runs:
            r.font.color.rgb, r.font.bold, r.font.size = RGBColor(0xFF, 0xFF, 0xFF), True, Pt(9)


def fixed_table(var, widths_cm, merge_cols=0):
    """Known columns with set widths (narrow ID, wide details), ICMBio-style; dynamic_table
    can only make equal columns. merge_cols: the first N columns merge down over rows
    that share the first column's value (a patrol's number and date over its legs), via
    a vMerge whose value Jinja decides per row."""
    t = doc.add_table(rows=4, cols=len(widths_cm))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    borders(t)
    header_row(t.rows[0].cells, [f"{{{{ {var}.col_labels[{i}] }}}}" for i in range(len(widths_cm))])
    t.rows[1].cells[0].text = f"{{%tr for item in {var}.tbl_contents %}}"
    for i, c in enumerate(t.rows[2].cells):
        c.text = f"{{{{ item.cols[{i}] }}}}"
        if i < merge_cols:  # docxtpl's {% vm %} merges the whole column, not per group
            same = "loop.previtem and loop.previtem.cols[0] == item.cols[0]"
            c.text = f"{{% if not ({same}) %}}{{{{ item.cols[{i}] }}}}{{% endif %}}"
            vm = OxmlElement("w:vMerge")
            vm.set(qn("w:val"), f"{{% if {same} %}}continue{{% else %}}restart{{% endif %}}")
            c._tc.get_or_add_tcPr().append(vm)
        for r in c.paragraphs[0].runs:
            r.font.size = Pt(8.5)
    t.rows[3].cells[0].text = "{%tr endfor %}"
    for row in t.rows:
        for c, w in zip(row.cells, widths_cm):
            c.width = Cm(w)


def table_block(var, widths_cm=None, merge_cols=0):
    tag(f"{{%p if {var}.tbl_contents %}}")
    fixed_table(var, widths_cm, merge_cols) if widths_cm else dynamic_table(var)
    tag("{%p else %}")
    p("{{ no_data }}", color=MUTED)
    tag("{%p endif %}")


def figure(var, caption_var):
    tag(f"{{%p if {var} %}}")
    p(f"{{{{ {var} }}}}", align=WD_ALIGN_PARAGRAPH.CENTER, space_after=2)
    p(f"{{{{ {caption_var} }}}}", size=8.5, color=MUTED, align=WD_ALIGN_PARAGRAPH.CENTER)
    tag("{%p else %}")
    p("{{ no_data }}", color=MUTED)
    tag("{%p endif %}")


def section(flag, title_var, body):
    if flag:
        tag(on(flag))
    doc.add_heading(f"{{{{ {title_var} }}}}", 1)
    body()
    if flag:
        tag("{%p endif %}")


# ── cover ─────────────────────────────────────────────────────────────────────
# No logos would leave a table with no columns and a row with no cells, which Word
# refuses to open (schema validators accept it), so the table only exists with logos.
tag("{%p if logos %}")
logos = doc.add_table(rows=1, cols=3)
logos.alignment = WD_TABLE_ALIGNMENT.CENTER
c = logos.rows[0].cells
c[0].text, c[1].text, c[2].text = "{%tc for l in logos %}", "{{ l.image }}", "{%tc endfor %}"
tag("{%p endif %}")
doc.add_paragraph("{{ title }}", style="Title")
p("{{ subtitle }}", size=12, color=MUTED, space_after=10)

meta = doc.add_table(rows=4, cols=2)
borders(meta)
full_width(meta)
for row, (lbl, val) in zip(meta.rows, [("L_area", "area"), ("L_period", "period"),
                                        ("L_generated_by", "generated_by"), ("L_date_generated", "date_generated")]):
    # Site is left blank for the user to fill in (the report covers the area they choose)
    row.cells[0].text, row.cells[1].text = f"{{{{ {lbl} }}}}", "" if val == "area" else f"{{{{ {val} }}}}"
    shade(row.cells[0], "F3F4F6")
    row.cells[0].paragraphs[0].runs[0].bold = True
    row.cells[0].width, row.cells[1].width = Cm(5), Cm(12)
p()

# ── headline stats ─────────────────────────────────────────────────────────────
tag(on("show_headline_stats"))
# Area covered and person-days show only when chosen as effort columns: docxtpl drops the
# {%tc %} cells, so the figure's column exists only when its value is non-empty.
figures = [("n_patrols", "L_patrols"), ("total_km", "L_distance"), ("total_hours", "L_hours"),
           ("patrol_days", "L_patrol_days"), ("{%tc if area_km2 %}", None), ("area_km2", "area_covered"),
           ("{%tc endif %}", None), ("{%tc if person_days %}", None), ("person_days", "member_days"),
           ("{%tc endif %}", None), ("n_events", "L_events")]
stats = doc.add_table(rows=2, cols=len(figures))
borders(stats, "E5E7EB")
full_width(stats)
for i, (val, lbl) in enumerate(figures):
    v, l_ = stats.rows[0].cells[i], stats.rows[1].cells[i]
    if lbl is None:
        v.text = l_.text = val
        continue
    v.text, l_.text = f"{{{{ {val} }}}}", f"{{{{ {lbl} }}}}"
    for cell, size, color, bold in ((v, 18, ACCENT, True), (l_, 8.5, MUTED, False)):
        para = cell.paragraphs[0]
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = para.runs[0]
        run.font.size, run.font.color.rgb, run.bold = Pt(size), color, bold
        shade(cell, "F9FAFB")
p()
tag("{%p endif %}")

# ── body ──────────────────────────────────────────────────────────────────────
# Who went on patrol: number and date merged over a patrol's legs; patrol type, time,
# leader, members per leg.
section(None, "L_patrol_effort", lambda: (p("{{ L_effort_intro }}", color=MUTED), table_block("effort")))
section("show_personnel", "L_personnel", lambda: table_block(
    "personnel", widths_cm=[1.6, 2.2, 3.0, 2.6, 2.6, 5.0], merge_cols=2))
section(None, "L_maps", lambda: (
    figure("tracks_map", "L_fig_tracks"),
    tag(on("show_time_density")), figure("time_density_map", "L_fig_time_density"), tag("{%p endif %}"),
    tag(on("show_event_density")), figure("event_density_map", "L_fig_event_density"), tag("{%p endif %}"),
))
section(None, "L_event_summary", lambda: (
    table_block("events_by_type"),
    tag(on("show_events_chart")), figure("events_bar", "L_fig_events_bar"), tag("{%p endif %}"),
    tag(on("show_monthly_chart")), figure("monthly_chart", "L_fig_monthly"), tag("{%p endif %}"),
    tag(on("show_category_priority")), doc.add_heading("{{ L_category_priority }}", 2),
    table_block("category_priority"), tag("{%p endif %}"),
))


def page(orientation):
    """Start a new page in this orientation; margins and the footer carry over."""
    s = doc.add_section(WD_SECTION.NEW_PAGE)
    s.orientation = orientation
    landscape = orientation == WD_ORIENT.LANDSCAPE
    s.page_width, s.page_height = (Cm(29.7), Cm(21.0)) if landscape else (Cm(21.0), Cm(29.7))


def details():
    p("{{ detail_intro }}", color=MUTED)
    tag("{%p if detail_mode == 'per_type' %}")
    tag("{%p for t in event_detail_tables %}")
    doc.add_heading("{{ t.heading }} · {{ t.title }}", 2)
    dynamic_table("t")
    tag("{%p endfor %}")
    tag("{%p else %}")
    # landscape: 25.7 cm of text width, most of it for the details (every field, ' | ' between)
    table_block("event_details", widths_cm=[1.6, 4.0, 4.2, 15.9])  # ID, type, when/where, details
    tag("{%p endif %}")


# Event details on their own landscape pages, then back to portrait.
page(WD_ORIENT.LANDSCAPE)
section(None, "L_event_details", details)
page(WD_ORIENT.PORTRAIT)


def images():
    tag("{%p if images %}")
    t = doc.add_table(rows=4, cols=2)
    borders(t, "E5E7EB")
    full_width(t)
    # ICMBio's layout: information on the left, the photo on the right
    header_row(t.rows[0].cells, ["{{ info }}", "{{ image }}"])
    t.rows[1].cells[0].text = "{%tr for r in images %}"
    t.rows[2].cells[0].text = "{{ r.caption }}"
    t.rows[2].cells[1].text = "{{ r.image }}"
    for row in t.rows:
        row.cells[0].width, row.cells[1].width = Cm(7), Cm(10)
    t.rows[3].cells[0].text = "{%tr endfor %}"
    tag("{%p else %}")
    p("{{ no_data }}", color=MUTED)
    tag("{%p endif %}")


section("show_images", "L_images", images)


def conclusions():
    box = doc.add_table(rows=1, cols=1)
    borders(box, "9CA3AF")
    full_width(box)
    cell = box.rows[0].cells[0]
    for _ in range(6):
        cell.add_paragraph("")


section("show_conclusions", "L_conclusions", conclusions)

# ── footer: text + page number ───────────────────────────────────────────────
fp = sec.footer.paragraphs[0]
fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = fp.add_run("{{ L_footer }} · ")
run.font.size, run.font.color.rgb = Pt(8), MUTED
r2 = fp.add_run()
for kind, text in (("begin", None), (None, "PAGE"), ("end", None)):
    if kind:
        el = OxmlElement("w:fldChar")
        el.set(qn("w:fldCharType"), kind)
    else:
        el = OxmlElement("w:instrText")
        el.set(qn("xml:space"), "preserve")
        el.text = text
    r2._r.append(el)
r2.font.size = Pt(8)

OUT.parent.mkdir(parents=True, exist_ok=True)
# python-docx's default settings carry <w:zoom/> without the required percent.
_zoom = doc.settings.element.find(qn("w:zoom"))
if _zoom is not None and _zoom.get(qn("w:percent")) is None:
    _zoom.set(qn("w:percent"), "100")
doc.save(OUT)
print(f"wrote {OUT}")

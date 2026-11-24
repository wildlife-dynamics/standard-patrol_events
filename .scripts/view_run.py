"""Assemble a compiled-workflow run into one local dashboard page, laid out
per layout.json (10-column grid), for reviewing outputs outside Ecoscope.
When the run is grouped (e.g. by year), a dropdown switches views the way
the Ecoscope dashboard filter does.

  python .scripts/view_run.py [/tmp/standard_patrol_events/costaecuador] [--no-open]

Writes <output>/dashboard.html and opens it.
"""

import html
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
args = [a for a in sys.argv[1:] if not a.startswith("--")]
OUTPUT = Path(args[0] if args else "/tmp/standard_patrol_events/costaecuador")
ROW_PX = 44

result = json.loads((OUTPUT / "result.json").read_text())
if result.get("error"):
    sys.exit(f"Workflow failed: {result['error']}")
dash = result["result"]
layout = {item["widget_id"]: item for item in json.loads((REPO / "layout.json").read_text())}


def view_label(key: str) -> str:
    return ", ".join(str(v) for v in json.loads(key).values())


def cell_body(w: dict) -> str:
    if w["widget_type"] == "text":
        items = "".join(f"<li>{html.escape(line.lstrip('- '))}</li>" for line in (w["data"] or "").splitlines())
        return f'<ul class="text">{items}</ul>'
    if not w.get("data"):
        return '<p class="empty">No data for this selection</p>'
    if not str(w["data"]).endswith(".html"):  # single-value widget
        return f'<p class="stat">{html.escape(str(w["data"]))}</p>'
    return f'<iframe src="{Path(w["data"]).name}" loading="lazy"></iframe>'


views = {}
for key, widgets in sorted(dash["views"].items(), key=lambda kv: view_label(kv[0])):
    cells = []
    if isinstance(widgets, dict):  # newer results nest the widgets under "dashboard"
        widgets = widgets["dashboard"]
    for i, w in enumerate(widgets):
        pos = layout.get(w.get("id", i), {"x": 0, "y": 1000 + i, "w": 10, "h": 10})
        style = f"grid-column:{pos['x'] + 1}/span {pos['w']};grid-row:{pos['y'] + 1}/span {pos['h']}"
        cells.append(f'<div class="card" style="{style}"><h3>{html.escape(w["title"])}</h3>{cell_body(w)}</div>')
    views[view_label(key)] = "".join(cells)

labels = list(views)
options = "".join(f'<option value="{html.escape(v)}">{html.escape(v)}</option>' for v in labels)
selector = (
    f'<label class="sel">View <select id="view" onchange="show(this.value)">{options}</select></label>'
    if len(labels) > 1
    else ""
)
meta = dash["metadata"]
page = f"""<!doctype html><html><head><meta charset="utf-8"><title>{html.escape(meta["title"])}</title>
<style>
body{{font-family:Inter,Helvetica,Arial,sans-serif;margin:0;background:#f3f4f6;color:#222}}
header{{background:#fff;border-bottom:1px solid #e5e7eb;padding:14px 24px;display:flex;align-items:center;gap:24px}}
header h1{{margin:0;font-size:20px}} header p{{margin:4px 0 0;color:#666;font-size:13px}}
.sel{{margin-left:auto;font-size:13px;color:#444}} .sel select{{margin-left:6px;padding:4px 8px;font-size:13px}}
.grid{{display:grid;grid-template-columns:repeat(10,1fr);grid-auto-rows:{ROW_PX}px;gap:10px;padding:16px 24px;max-width:1400px;margin:auto}}
.card{{background:#fff;border:1px solid #e5e7eb;border-radius:8px;display:flex;flex-direction:column;overflow:hidden}}
.card h3{{margin:0;padding:8px 12px;font-size:13px;font-weight:600;border-bottom:1px solid #f0f0f0}}
.card iframe{{flex:1;border:0;width:100%}} .text{{margin:8px 12px;padding-left:18px;font-size:13px;line-height:1.5;overflow:auto}}
.empty{{margin:auto;color:#999;font-size:13px}} .stat{{margin:auto 12px;font-size:26px;font-weight:600}}
</style></head><body>
<header><div><h1>{html.escape(meta["title"])}</h1><p>{html.escape(meta["description"])} · {html.escape(meta["time_range"])}</p></div>{selector}</header>
<div class="grid" id="grid"></div>
<script>
const VIEWS = {json.dumps(views)};
function show(v) {{ document.getElementById("grid").innerHTML = VIEWS[v]; }}
show({json.dumps(labels[0])});
</script></body></html>"""

out = OUTPUT / "dashboard.html"
out.write_text(page)
print(f"Written: {out} ({len(labels)} view(s): {', '.join(labels)})")
if "--no-open" not in sys.argv:
    subprocess.run(["open", str(out)])

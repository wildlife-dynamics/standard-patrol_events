"""Dashboard preview: the interactive view of the standard patrol & events
workflow, built from real data with the same core ecoscope draw_* tasks the
spec wires (pydeck maps, ecoplot charts, draw_table). Each widget is written
as its own HTML file and laid out on the Ecoscope 10-column grid.

The dashboard is for exploring (interactive maps, hover, every row); the Word
report (preview_report.py) is the printable summary of the same outputs.

  M=/Users/zak/Documents/w-dynamics/ecoscope-workflow-task-library-spe/src/ecoscope-workflows-ext-custom/pyproject.toml
  pixi run --manifest-path $M python .scripts/preview_dashboard.py costaecuador
Writes .scripts/output/dashboard_<conn>/index.html
"""

import html
import sys
from pathlib import Path

from _data import OUT, SINCE, UNTIL, build
from _figures import figures, run
from ecoscope.platform.tasks.results import draw_table

CONN = sys.argv[1] if len(sys.argv) > 1 else "costaecuador"
TEAM_GROUPS = {"costaecuador": ["PONGALILLO", "BELLAVISTA", "COSTA RICA", "EL CONCHAL", "PUERTO ROMA"]}
DIR = OUT / f"dashboard_{CONN}"

b = build(CONN, grouper="team", team_groups=TEAM_GROUPS.get(CONN), language="es")
k = b["kpis"]
f = figures(b, DIR, static=False)


def table(name, df):
    (DIR / f"{name}.html").write_text(run(draw_table, dataframe=df))
    return f"{name}.html"


w = {
    "tracks": Path(f["tracks_map"]).name, "time_density": Path(f["time_density_map"]).name,
    "event_density": Path(f["event_density_map"]).name, "events_bar": Path(f["events_bar"]).name,
    "monthly": Path(f["monthly"]).name, "effort": table("effort", b["effort"]),
    "event_summary": table("event_summary", b["events_by_type"]),
    "event_records": table("event_records", b["event_records"]),
}

# ── layout: (title, widget, x, y, w, h) on the 10-col grid; KPIs are single values
kpis = [("Patrullajes", f'{k["patrols"]:,}'), ("Distancia", f'{k["km"]:,.0f} km'),
        ("Horas", f'{k["hours"]:,.0f} h'), ("Días de patrullaje", f'{k["patrol_days"]}'),
        ("Eventos", f'{k["events"]:,}'), ("Resueltos", f'{k["resolved"]} / {k["events"]}')]
cells = [
    ("Recorridos y eventos", w["tracks"], 0, 2, 6, 11), ("Esfuerzo de patrullaje por equipo", w["effort"], 6, 2, 4, 11),
    ("Densidad de tiempo de patrullaje", w["time_density"], 0, 13, 5, 9), ("Densidad de eventos", w["event_density"], 5, 13, 5, 9),
    ("Eventos por tipo", w["events_bar"], 0, 22, 5, 9), ("Eventos por mes", w["monthly"], 5, 22, 5, 9),
    ("Resumen de eventos", w["event_summary"], 0, 31, 4, 10), ("Registros de eventos", w["event_records"], 4, 31, 6, 10),
]
kpi_html = '<div class="kpis">' + "".join(f'<div class="card kpi"><span>{html.escape(t)}</span><b>{html.escape(v)}</b></div>'
                                         for t, v in kpis) + "</div>"
cell_html = "".join(f'<div class="card" style="grid-column:{x + 1}/span {wd};grid-row:{y + 1}/span {h}">'
                    f'<h3>{html.escape(t)}</h3><iframe src="{src}"></iframe></div>'
                    for t, src, x, y, wd, h in cells)
page = f"""<!doctype html><html lang="es"><head><meta charset="utf-8"><title>Patrullajes y eventos — {CONN}</title>
<style>
body{{font-family:Inter,Helvetica,Arial,sans-serif;margin:0;background:#f3f4f6;color:#1f2937}}
header{{background:#fff;border-bottom:1px solid #e5e7eb;padding:14px 24px}}
header h1{{margin:0;font-size:20px}} header p{{margin:4px 0 0;color:#6b7280;font-size:13px}}
.grid{{display:grid;grid-template-columns:repeat(10,1fr);grid-auto-rows:40px;gap:10px;padding:16px 24px;max-width:1440px;margin:auto}}
.card{{background:#fff;border:1px solid #e5e7eb;border-radius:8px;display:flex;flex-direction:column;overflow:hidden}}
.card h3{{margin:0;padding:8px 12px;font-size:13px;font-weight:600;border-bottom:1px solid #f0f0f0}}
.card iframe{{flex:1;border:0;width:100%}}
.kpis{{grid-column:1/-1;grid-row:1/span 2;display:grid;grid-template-columns:repeat(6,1fr);gap:10px}} .kpi{{justify-content:center;padding:0 14px}} .kpi span{{font-size:12px;color:#6b7280}} .kpi b{{font-size:24px;font-variant-numeric:tabular-nums}}
</style></head><body>
<header><h1>Patrullajes y eventos</h1><p>{html.escape(b["server"])} · {SINCE[:10]} → {UNTIL[:10]} · agrupado por equipo</p></header>
<div class="grid">{kpi_html}{cell_html}</div></body></html>"""
(DIR / "index.html").write_text(page)
print(f"wrote {DIR / 'index.html'}")

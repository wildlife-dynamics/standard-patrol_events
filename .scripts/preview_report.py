"""Report preview: renders the redesigned Jinja template (build_report_template.py)
with real data through ext-custom create_docx, exactly as the workflow will, then
converts it to PDF with Word for page-by-page review.

  pixi run --manifest-path $M python .scripts/preview_report.py costaecuador
Writes .scripts/output/report_<conn>/report.docx (+ report.pdf)
"""

import datetime as dt
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd
from _data import OUT, build
from _figures import figures, run
from ecoscope_workflows_ext_custom.tasks.io import download_event_attachments, sanitize_attachments
from ecoscope_workflows_ext_custom.tasks.results import (
    ImageContextItem, ImageListContextItem, TableContextItem, TableListContextItem, TemplateContext,
    TextContextItem, build_image_records, create_docx,
)

CONN = sys.argv[1] if len(sys.argv) > 1 else "costaecuador"
TEAM_GROUPS = {"costaecuador": ["PONGALILLO", "BELLAVISTA", "COSTA RICA", "EL CONCHAL", "PUERTO ROMA"]}
MAX_IMAGES, DETAIL_ROWS = 6, 40
DIR = OUT / f"report_{CONN}"
# The data package lives in a wd-partner-tasks checkout next to this repo (or $PARTNER_TASKS).
_W = Path(subprocess.check_output(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"], text=True).strip()).parents[1]
PARTNER_PKG = Path(os.environ.get("PARTNER_TASKS", _W / "wd-partner-tasks-standard-patrol-events")) / "src/ecoscope-workflows-ext-standard-patrol-events"
TEMPLATE = PARTNER_PKG / "ecoscope_workflows_ext_standard_patrol_events/data/standard_patrol_events.docx"

# headings/captions per language — becomes part of get_report_labels in the real workflow
L = {
    "L_area": "Área", "L_period": "Periodo", "L_generated_by": "Generado por", "L_date_generated": "Fecha de generación",
    "L_patrols": "Patrullajes", "L_distance": "km recorridos", "L_hours": "Horas de patrullaje",
    "L_patrol_days": "Días con patrullaje", "L_events": "Eventos registrados",
    "L_personnel": "Personal", "L_patrol_effort": "Esfuerzo de patrullaje",
    "L_effort_intro": "Patrullajes, distancia y horas por equipo en el periodo.",
    "L_maps": "Mapas", "L_fig_tracks": "Figura 1. Recorridos de patrullaje y eventos registrados.",
    "L_fig_time_density": "Figura 2. Densidad de tiempo de patrullaje (% del tiempo por celda).",
    "L_fig_event_density": "Figura 3. Densidad de eventos por celda de 2 km.",
    "L_event_summary": "Resumen de eventos", "L_fig_events_bar": "Figura 4. Eventos por tipo.",
    "L_category_priority": "Eventos por categoría y prioridad", "L_event_details": "Detalle de eventos",
    "L_images": "Imágenes", "L_conclusions": "Conclusiones",
    "L_footer": "Este reporte fue generado por Ecoscope con datos de EarthRanger",
}
MONTHS = "ene feb mar abr may jun jul ago sep oct nov dic".split()


def fmt(d):
    return f"{d.day:02d} {MONTHS[d.month - 1]} {d.year}"


b = build(CONN, grouper="team", team_groups=TEAM_GROUPS.get(CONN), language="es")
k = b["kpis"]
fig = figures(b, DIR / "figures", static=True)

# images: download only the first events that have photos (the cap), never the whole period
ev = b["events"]
with_files = ev[ev["files"].map(lambda f: bool(f) if f is not None else False)].sort_values("time").head(MAX_IMAGES)
paths = run(download_event_attachments, client=CONN, event_gdf=with_files, output_dir=str(DIR))
paths = run(sanitize_attachments, paths=paths, output_dir=str(DIR))
images = run(build_image_records, events=ev[ev.geometry.notna()],  # shortcut: A5 crashes on null geometry (plan fix)
             attachment_paths=paths, output_dir=str(DIR),
             max_images=MAX_IMAGES, labels=b["labels"])

details = b["event_records"].head(DETAIL_ROWS)
items = [TextContextItem(key=key, value=val) for key, val in {
    **L, "title": "Reporte de patrullajes y eventos", "subtitle": "Costa Ecuador · Golfo de Guayaquil",
    "area": "Golfo de Guayaquil (todo el sitio)",
    "period": f"{fmt(dt.date(2026, 8, 1))} – {fmt(dt.date(2026, 10, 31))}",
    "generated_by": b["user"] or "-", "date_generated": fmt(dt.date.today()),
    "n_patrols": f'{k["patrols"]:,}', "total_km": f'{k["km"]:,.0f}', "total_hours": f'{k["hours"]:,.0f}',
    "patrol_days": str(k["patrol_days"]), "n_events": f'{k["events"]:,}',
    "no_data": b["labels"]["no_data"],
    "detail_intro": f"Primeros {len(details)} de {k['events']} eventos, en orden cronológico. "
                    "La lista completa está en el panel (dashboard).",
    "show_headline_stats": "true", "show_personnel": "false", "show_time_density": "true",
    "show_event_density": "true", "show_events_chart": "true", "show_category_priority": "false",
    "show_per_type": "false", "show_images": "true", "images_manual": "false", "show_conclusions": "true",
}.items()]
items += [
    ImageContextItem(key=key, value=fig[key], width_inches=6.6)
    for key in ("tracks_map", "time_density_map", "event_density_map")
] + [ImageContextItem(key="events_bar", value=fig["events_bar"], width_inches=6.6)]
items += [
    TableContextItem(key="effort", value=b["effort"]),
    TableContextItem(key="events_by_type", value=b["events_by_type"]),
    TableContextItem(key="category_priority", value=b["category_priority"]),
    TableContextItem(key="event_details", value=details),
    TableContextItem(key="personnel", value=pd.DataFrame()),
    TableListContextItem(key="event_detail_tables", value=b["event_tables"]),
    ImageListContextItem(key="images", value=images, width_inches=3.4),
    ImageListContextItem(key="logos", value=pd.DataFrame(columns=["caption", "image_path"]), width_inches=1.4),
]
docx = run(create_docx, template_path=str(TEMPLATE), context=TemplateContext(items=items), output_dir=str(DIR),
           filename_prefix="report")
print("wrote", docx)


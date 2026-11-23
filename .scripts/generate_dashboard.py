"""
Standard Patrol & Events - spike dashboard (one partner, one period).

Renders every MRD block from real EarthRanger data into one HTML page, so the
report's shape can be judged before the workflow (spec.yaml) is built:
  header/meta, headline stats, patrol effort x3 groupers (type | leader/team |
  individual patrol), tracks+events map, time-density map, event summary
  (by type, category x priority, bar, monthly stacked, density map), event
  details in both modes (generic | per-type grouped by category), images,
  conclusions, footer.

Run with the APN env:
  cd /Users/zak/Documents/w-dynamics/APN-patrol_event/ecoscope-workflows-patrol-event-workflow
  .pixi/envs/default/bin/python -I <this repo>/.scripts/generate_dashboard.py <conn> [since] [until]
Output: .scripts/output/dashboard_<conn>.html
"""

import base64
import datetime as dt
import html
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
import pandas as pd  # noqa: E402
import plotly.express as px  # noqa: E402
import plotly.graph_objects as go  # noqa: E402
from ecoscope.platform.connections import EarthRangerConnection  # noqa: E402
from ecoscope.platform.tasks.io import process_events_details  # noqa: E402
from ecoscope.base import TrajSegFilter  # noqa: E402
from ecoscope.relocations import Relocations  # noqa: E402
from ecoscope.trajectory import Trajectory  # noqa: E402

CONN = sys.argv[1] if len(sys.argv) > 1 else "costaecuador"
SINCE = sys.argv[2] if len(sys.argv) > 2 else "2026-08-01T00:00:00Z"
UNTIL = sys.argv[3] if len(sys.argv) > 3 else "2026-11-01T00:00:00Z"
MAX_IMAGES = 12  # shortcut: first N image attachments only; MRD open question on a cap
MAX_GAP_SECS = 3600  # track segments longer than this are gaps, not patrolling
GRID_DEG = 0.01  # ~1 km cells for the time-density map
OUT = Path(__file__).parent / "output"

er = EarthRangerConnection.from_named_connection(CONN).get_client()
print(f"Connected to {er.server}", flush=True)
try:
    me = er.get_me()
    generated_by = f'{me.get("first_name", "")} {me.get("last_name", "")}'.strip() or me.get("username")
except Exception:
    generated_by = "-"

# ---------------------------------------------------------------- lookups (live, never hardcoded)
et = er.get_event_types()
et_disp = dict(zip(et["value"], et["display"]))
et_cat = {v: c.get("display", "-") if isinstance(c, dict) else (c or "-") for v, c in zip(et["value"], et["category"])}
pt = er.get_patrol_types()
pt_disp = dict(zip(pt["value"], pt["display"]))

# team = leader's subject group(s). shortcut: drops only the catch-all "Subjects" group;
# the partner template should list which groups count as teams.
member_of = {}
for g in er._get("subjectgroups/", params={"flat": "true", "include_hidden": "true"}):
    if g["name"] != "Subjects":
        for sub in g.get("subjects", []):
            member_of.setdefault(sub["id"], []).append(g["name"])

# ---------------------------------------------------------------- patrols
patrols = er.get_patrols(since=SINCE, until=UNTIL, status=["done"])
rows = []
for _, p in patrols.iterrows():
    seg = (p["patrol_segments"] or [{}])[0]
    tr = seg.get("time_range") or {}
    start, end = pd.to_datetime(tr.get("start_time"), utc=True), pd.to_datetime(tr.get("end_time"), utc=True)
    rows.append({
        "patrol_id": p["id"], "serial": p["serial_number"], "title": p["title"],
        "patrol_type": pt_disp.get(seg.get("patrol_type"), seg.get("patrol_type") or "-"),
        "leader": (seg.get("leader") or {}).get("name", "-"),
        # multi-group members get one joined label so totals aren't double-counted
        "team": " + ".join(sorted(member_of.get((seg.get("leader") or {}).get("id"), []))) or (seg.get("leader") or {}).get("name", "-"),
        "start": start, "end": end,
        "n_events": sum(len(s.get("events") or []) for s in p["patrol_segments"] or []),
    })
pdf = pd.DataFrame(rows)
print(f"patrols: {len(pdf)}", flush=True)

# ---------------------------------------------------------------- tracks -> trajectory (one bulk call)
tracks = None
pdf["distance_km"] = pdf["hours"] = 0.0
if len(patrols):
    obs = er.get_patrol_observations(patrols_df=patrols, include_patrol_details=True)
    relocs = obs if isinstance(obs, Relocations) else Relocations.from_gdf(getattr(obs, "gdf", obs))
    if len(relocs.gdf) > 1:
        traj = Trajectory.from_relocations(relocs)
        # drop segments spanning a >1 h gap between fixes (device off / patrol left open)
        traj.apply_traj_filter(TrajSegFilter(max_time_secs=MAX_GAP_SECS), inplace=True)
        traj.remove_filtered(inplace=True)
        tracks = traj.gdf
        pid_col = "extra__patrol_id" if "extra__patrol_id" in tracks else "patrol_id"
        dist = tracks.groupby(pid_col)["dist_meters"].sum() / 1000
        pdf["distance_km"] = pdf["patrol_id"].map(dist).fillna(0.0)
        # track time, not segment start/end: patrols left open for days would otherwise inflate hours
        hrs = tracks.groupby(pid_col)["timespan_seconds"].sum() / 3600
        pdf["hours"] = pdf["patrol_id"].map(hrs).fillna(0.0)
        tracks = tracks.merge(pdf[["patrol_id", "patrol_type", "leader", "serial"]], left_on=pid_col, right_on="patrol_id")
print(f"track segments: {0 if tracks is None else len(tracks)}", flush=True)

# ---------------------------------------------------------------- events (all in period, with details + files)
ev = er.get_events(since=SINCE, until=UNTIL, include_details=True, include_files=True)
if len(ev):
    ev = ev.reset_index(drop=True)
    ev["type"] = ev["event_type"].map(et_disp).fillna(ev["event_type"])
    ev["category"] = ev["event_type"].map(et_cat).fillna("-")
    ev["time"] = pd.to_datetime(ev["time"], utc=True)
    ev["lon"], ev["lat"] = ev.geometry.x, ev.geometry.y
    ev["on_patrol"] = ev["patrol_segments"].map(lambda x: x is not None and len(x) > 0)
    try:
        details = process_events_details(df=ev[["event_type", "event_details"]].copy(), client=er)["event_details"]
    except Exception as e:  # titles/enum resolution is nice-to-have; fall back to raw keys
        print(f"process_events_details failed ({e}); using raw keys")
        details = ev["event_details"]
    ev["details"] = details.map(lambda d: {k: v for k, v in (d or {}).items() if v not in (None, "", [], {})})
print(f"events: {len(ev)}", flush=True)

# ---------------------------------------------------------------- html helpers
FIG_JS = {"first": True}


def fig_html(fig, h=420):
    fig.update_layout(height=h, margin=dict(l=10, r=10, t=40, b=10), template="plotly_white")
    out = fig.to_html(full_html=False, include_plotlyjs="cdn" if FIG_JS["first"] else False)
    FIG_JS["first"] = False
    return out


def table(df, totals=None):
    if df is None or not len(df):
        return '<p class="empty">No data in this period.</p>'
    df = df.copy()
    if totals is not None:
        df = pd.concat([df, pd.DataFrame([totals])], ignore_index=True)
    return df.to_html(index=False, escape=True, classes="t", float_format=lambda x: f"{x:,.1f}", na_rep="")


def section(n, title, body, note=""):
    note = f'<p class="note">{note}</p>' if note else ""
    return f'<section><h2><span>{n}</span>{html.escape(title)}</h2>{note}{body}</section>'


def fmt_details(d, limit=None):
    items = list(d.items())[:limit]
    return "; ".join(f"{k}: {v if not isinstance(v, list) else ', '.join(map(str, v))}" for k, v in items)


# ---------------------------------------------------------------- blocks
S = []
period = f"{SINCE[:10]} → {UNTIL[:10]}"
meta = pd.DataFrame([
    {"Field": "Region / area", "Value": er.server},
    {"Field": "Generated by", "Value": generated_by},
    {"Field": "Period", "Value": period},
    {"Field": "Date generated", "Value": dt.date.today().isoformat()},
])
S.append(section(2, "Report summary", table(meta)))

S.append(section(3, "Personnel", '<p class="empty">Source TBD — patrol metadata changing soon. '
                 f'Closest today: segment leader ({pdf["leader"].nunique() if len(pdf) else 0} distinct).</p>'))

cards = [("Patrols", f'{len(pdf):,}'), ("Total distance", f'{pdf["distance_km"].sum():,.0f} km' if len(pdf) else "0 km"),
         ("Total hours", f'{pdf["hours"].sum():,.0f} h' if len(pdf) else "0 h"), ("Events reported", f"{len(ev):,}")]
S.append(section(4, "Headline stats", '<div class="cards">' + "".join(
    f'<div class="card"><div class="v">{v}</div><div class="l">{k}</div></div>' for k, v in cards) + "</div>"))

if len(pdf):
    agg = dict(patrols=("patrol_id", "count"), distance_km=("distance_km", "sum"), hours=("hours", "sum"))
    by_type = pdf.groupby("patrol_type").agg(**agg).reset_index().sort_values("patrols", ascending=False)
    by_team = pdf.groupby("leader").agg(**agg).reset_index().sort_values("patrols", ascending=False)
    by_group = pdf.groupby("team").agg(**agg, leaders=("leader", "nunique")).reset_index().sort_values("patrols", ascending=False)
    indiv = pdf.sort_values("start")[["start", "end", "serial", "patrol_type", "distance_km", "hours", "n_events"]].copy()
    indiv["start"], indiv["end"] = indiv["start"].dt.strftime("%Y-%m-%d %H:%M"), indiv["end"].dt.strftime("%Y-%m-%d %H:%M")
    tot = lambda d, k: {k: "Total", "patrols": d["patrols"].sum(), "distance_km": d["distance_km"].sum(), "hours": d["hours"].sum()}  # noqa: E731
    tabs = [("By patrol type", table(by_type, tot(by_type, "patrol_type"))),
            ("By team (subject group)", table(by_group, {**tot(by_group, "team"), "leaders": pdf["leader"].nunique()})),
            ("By leader", table(by_team, tot(by_team, "leader"))),
            ("By individual patrol", table(indiv, {"start": "Total", "distance_km": indiv["distance_km"].sum(),
                                                    "hours": indiv["hours"].sum(), "n_events": indiv["n_events"].sum()}))]
    body = '<div class="tabs">' + "".join(f'<button onclick="tab(this,{i})"{" class=on" if i == 0 else ""}>{t}</button>' for i, (t, _) in enumerate(tabs)) + "</div>"
    body += "".join(f'<div class="pane"{"" if i == 0 else " hidden"}>{b}</div>' for i, (_, b) in enumerate(tabs))
    S.append(section(5, "Patrol effort", body, "Grouper is a workflow parameter — all shown. Team = the leader's ER subject group(s), "
                     "excluding the catch-all 'Subjects' group (falls back to leader name). Hours and distance both come from the GPS track (patrols with no track show 0)."))
else:
    S.append(section(5, "Patrol effort", table(None)))

# maps
if tracks is not None or len(ev):
    fig = go.Figure()
    if tracks is not None:
        colors = px.colors.qualitative.Bold
        for i, (ptype, g) in enumerate(tracks.groupby("patrol_type")):
            lats, lons = [], []
            for geom in g.geometry:
                xs, ys = geom.xy
                lons += list(xs) + [None]
                lats += list(ys) + [None]
            fig.add_trace(go.Scattermap(lat=lats, lon=lons, mode="lines", name=f"Patrol: {ptype}",
                                        line=dict(width=2, color=colors[i % len(colors)])))
    if len(ev):
        for etype, g in ev.groupby("type"):
            fig.add_trace(go.Scattermap(lat=g["lat"], lon=g["lon"], mode="markers", name=f"Event: {etype}",
                                        marker=dict(size=8), text=g["serial_number"].astype(str), hovertemplate="%{text}"))
    centre = ev if len(ev) else tracks.geometry.centroid.to_frame().assign(lat=lambda d: d.geometry.y, lon=lambda d: d.geometry.x)
    fig.update_layout(map=dict(style="open-street-map", zoom=8, center=dict(lat=centre["lat"].median(), lon=centre["lon"].median())))
    body = fig_html(fig, 560)

    if tracks is not None:
        t = tracks.copy()
        t["cy"], t["cx"] = (t.geometry.centroid.y / GRID_DEG).round() * GRID_DEG, (t.geometry.centroid.x / GRID_DEG).round() * GRID_DEG
        g = t.groupby(["cy", "cx"])["timespan_seconds"].sum().reset_index()
        g["pct_time"] = 100 * g["timespan_seconds"] / g["timespan_seconds"].sum()
        dfig = px.density_map(g, lat="cy", lon="cx", z="pct_time", radius=14, zoom=8, map_style="open-street-map",
                              title="Patrol time density (% time by ~1 km cell)")
        body += fig_html(dfig, 480)
    S.append(section(6, "Maps", body, "Tracks coloured by patrol type, events by event type. "
                     "Time density here is a quick grid sum; the workflow would use ecoscope's ETD/grid task."))

if len(ev):
    by_type = ev.groupby(["category", "type"]).agg(count=("serial_number", "count"), resolved=("state", lambda s: (s == "resolved").sum())).reset_index().sort_values("count", ascending=False)
    cat_pri = pd.crosstab(ev["category"], ev["priority_label"], margins=True, margins_name="Total").reset_index()
    body = "<h3>Events by type</h3>" + table(by_type, {"category": "Total", "count": by_type["count"].sum(), "resolved": by_type["resolved"].sum()})
    body += "<h3>Events by category × priority</h3>" + table(cat_pri)
    body += fig_html(px.bar(by_type.head(20).sort_values("count"), x="count", y="type", orientation="h", color="category", title="Events by type (top 20)"), 520)
    monthly = ev.assign(month=ev["time"].dt.strftime("%Y-%m")).groupby(["month", "type"]).size().reset_index(name="count")
    body += fig_html(px.bar(monthly, x="month", y="count", color="type", title="Events by month, by type"), 420)
    body += fig_html(px.density_map(ev, lat="lat", lon="lon", radius=12, zoom=8, map_style="open-street-map", title="Event density"), 460)
    S.append(section(7, "Event summary", body, f'Validated (state = resolved): {(ev["state"] == "resolved").sum()} of {len(ev)}. '
                     f'Linked to a patrol: {ev["on_patrol"].sum()} of {len(ev)}.'))

    gen = ev.sort_values("time")[["serial_number", "type", "time", "lat", "lon", "details"]].copy()
    gen["time"] = gen["time"].dt.strftime("%Y-%m-%d %H:%M")
    gen["coords"] = gen["lat"].round(5).astype(str) + ", " + gen["lon"].round(5).astype(str)
    gen["details"] = gen["details"].map(fmt_details)
    generic = table(gen[["serial_number", "type", "time", "coords", "details"]])

    per_type = ""
    for cat, cg in ev.groupby("category"):
        per_type += f"<h3>{html.escape(str(cat))}</h3>"
        for etype, g in cg.groupby("type"):
            # shortcut: top-3 most-filled fields per type stand in for the partner template's chosen fields
            fields = pd.Series([k for d in g["details"] for k in d]).value_counts().head(3).index.tolist()
            t = g.sort_values("time")[["serial_number", "time", "lat", "lon"]].copy()
            t["time"] = t["time"].dt.strftime("%Y-%m-%d %H:%M")
            t["coords"] = t.pop("lat").round(5).astype(str) + ", " + t.pop("lon").round(5).astype(str)
            for f in fields:
                t[f] = g["details"].map(lambda d, f=f: d.get(f, ""))
            per_type += f"<h4>{html.escape(etype)} ({len(g)})</h4>" + table(t)
    body = '<div class="tabs"><button class="on" onclick="tab(this,0)">Per event type</button><button onclick="tab(this,1)">Generic table</button></div>'
    body += f'<div class="pane">{per_type}</div><div class="pane" hidden>{generic}</div>'
    S.append(section(8, "Event details", body, "Display mode is a workflow parameter — both shown. "
                     "Per-type columns are auto-picked (3 most-filled fields); the real template would fix them per partner."))

    imgs, n_files = [], int(ev["files"].map(lambda f: len(f or [])).sum()) if "files" in ev else 0
    for _, r in ev[ev.get("files", pd.Series(dtype=object)).map(bool)].iterrows() if n_files else []:
        for f in r["files"]:
            url = (f.get("images") or {}).get("thumbnail") or f.get("url")
            if not url or not str(f.get("file_type", "image")).startswith("image") or len(imgs) >= MAX_IMAGES:
                continue
            try:
                b = er.get_file(url).content
                imgs.append((r, base64.b64encode(b).decode()))
            except Exception as e:
                print(f"  image fetch failed: {e}")
    rows_html = "".join(
        f'<tr><td>#{r["serial_number"]}<br>{html.escape(r["type"])}<br>{r["lat"]:.5f}, {r["lon"]:.5f}<br>{r["time"]:%Y-%m-%d %H:%M}</td>'
        f'<td><img src="data:image/jpeg;base64,{b}"></td></tr>' for r, b in imgs)
    S.append(section(9, "Images", f'<table class="t img"><tr><th>Details</th><th>Image</th></tr>{rows_html}</table>' if imgs else table(None),
                     f"{n_files} attachments on {ev['files'].map(bool).sum() if n_files else 0} events; showing first {len(imgs)} (auto-populated)."))

S.append(section(10, "Conclusions", '<div class="box" contenteditable>Technician to complete…</div>'))

page = f"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Patrol & Events — {CONN}</title><style>
:root{{--bg:#f6f5f1;--fg:#1d2321;--mute:#6b736f;--line:#dcd9d0;--card:#fff;--acc:#2f6b4f}}
@media (prefers-color-scheme:dark){{:root{{--bg:#151816;--fg:#e8ebe9;--mute:#9aa39e;--line:#2c322f;--card:#1d211f;--acc:#7cc39d}}}}
body{{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,-apple-system,Segoe UI,sans-serif}}
main{{max-width:1200px;margin:auto;padding:24px 16px 64px}}
header{{border-bottom:3px solid var(--acc);padding-bottom:12px;margin-bottom:8px}}
header h1{{margin:0;font-size:26px}} header p{{margin:4px 0 0;color:var(--mute)}}
section{{margin-top:36px}} h2{{font-size:19px;display:flex;gap:10px;align-items:center}}
h2 span{{background:var(--acc);color:var(--bg);border-radius:4px;font-size:12px;padding:2px 7px}}
h3{{font-size:15px;margin:22px 0 6px}} h4{{font-size:14px;margin:16px 0 4px;color:var(--mute)}}
.note{{color:var(--mute);font-size:13px;margin-top:-6px}} .empty{{color:var(--mute);font-style:italic}}
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:16px}}
.card .v{{font-size:28px;font-weight:650;font-variant-numeric:tabular-nums}} .card .l{{color:var(--mute);font-size:13px}}
.t{{border-collapse:collapse;width:100%;background:var(--card);font-size:13px;display:block;overflow-x:auto}}
.t th,.t td{{border-bottom:1px solid var(--line);padding:6px 10px;text-align:left;vertical-align:top}}
.t th{{background:var(--bg)}} .t tr:last-child td{{font-weight:600}} .img img{{max-width:320px;border-radius:4px}}
.tabs{{display:flex;gap:6px;margin-bottom:8px;flex-wrap:wrap}}
.tabs button{{border:1px solid var(--line);background:var(--card);color:var(--fg);border-radius:6px;padding:6px 12px;cursor:pointer}}
.tabs button.on{{background:var(--acc);color:var(--bg);border-color:var(--acc)}}
.box{{min-height:120px;border:1px dashed var(--line);border-radius:8px;padding:12px;background:var(--card);color:var(--mute)}}
footer{{margin-top:48px;color:var(--mute);font-size:13px;border-top:1px solid var(--line);padding-top:12px}}
</style></head><body><main>
<header><h1>Patrol &amp; Events Report — {html.escape(CONN)}</h1><p>{period} · spike preview of the Standard Patrol &amp; Events MRD blocks · logos / title come from the partner template</p></header>
{''.join(S)}
<footer>This report was generated by Ecoscope using EarthRanger data.</footer>
</main><script>function tab(b,i){{const s=b.closest('section');s.querySelectorAll('.tabs button').forEach((x,j)=>x.classList.toggle('on',j==i));s.querySelectorAll('.pane').forEach((p,j)=>p.hidden=j!=i)}}</script></body></html>"""

OUT.mkdir(exist_ok=True)
out = OUT / f"dashboard_{CONN}.html"
out.write_text(page)
print(f"wrote {out}")

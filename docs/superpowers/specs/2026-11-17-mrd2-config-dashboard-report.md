# MRD v2: configuration, dashboard and report

**Date:** 2026-11-17 · **Source:** *Standard Patrol & Events MRD-2* · **Supersedes:** the partner-profile parts of `2026-11-16-standard-patrol-events-design.md` (§5.2, §5.3)

## 1. What changed in MRD-2

| Topic | Design so far (v1) | MRD-2 | Impact |
|---|---|---|---|
| Output | Word report only | **Dashboard and** Word report | The spec gets a `gather_dashboard` with widgets *and* `create_docx`, both fed by the same outputs (§3) |
| Partner differences | A partner profile YAML picked from a dropdown | **Every difference is a run-time parameter.** Labels, logos and wording live in the template | Drop the profiles. The data package keeps only templates (§2.3) |
| Event types | A fixed list per template | **Chosen by the user at run time** | Core `event_types` dropdown |
| Event fields shown | Per type, in the profile | **Typed as free text for now** (a dropdown comes later) | A text list param |
| Validated only | on/off plus states | **Event state: all / resolved only / active only** | `filter_validated` becomes a 3-way choice |
| Event grouping | Always by type | **By event type or by event category** | One param drives tables, charts and map colour |
| Retrieval | `event_scope` area / patrol | Same, with the **default to confirm** | Keep it; default "patrols + all events in period" (spike: only 3–9% of events are linked at ICF, El Palmar, Iguazú) |
| Effort grouper | type / team / individual | Same **+ vehicle** (optional) | Vehicle is a later block; it depends on the patrol schema (§5) |
| Logos | Inside the template | **Logos as links** | Logo URL params; the template inserts the images (§4) |
| Reuse | Our own effort table | **Reuse the Patrol Effort / Event Analysis catalogue outputs** | Use their tasks and widgets; don't fork them |
| Personnel | The new-model leg members | **Built on the new patrol attributes** feature | Unchanged (APN only for now) |
| New outputs | — | Area covered km² (Galápagos), events by category × priority (Honduras), events by reporting group (Ecuador), per-type tables (Honduras, Q4) | km² is cheap (track buffer area). Reporting group stays out until ER has a field |
| Scope | LATAM partners | Same, **and it must work for any site** | No LATAM-only code paths. English is the default language |

## 2. Configuration (the rjsf form)

### 2.1 Principles
- **One form section per decision a technician makes.** Nothing internal leaks into the form. The current compiled form shows about 100 untitled fields (`block_*`, `show_*`, `skip_*`, `default`/`raise_on_missing`) because profile plumbing goes through `get_collection_item`. Parameters remove all of that.
- **Reuse existing annotations,** so the dropdowns come for free and stay consistent with other workflows: ER connection, `TimeRange`, `PatrolTypesAnnotation`, `EventTypesAnnotation`, base maps.
- **Advanced** (`ecoscope:advanced`) holds the knobs most sites never touch: gap limit, cell sizes, colour palettes.
- **Optional blocks are switches,** each one form field. An off block becomes a `SkipSentinel`, so its widget and its report section disappear.

### 2.2 Form sections

| # | Section (form title) | Fields | Type / source | Default |
|---|---|---|---|---|
| 1 | Workflow Details | name, description | core `set_workflow_details` | — |
| 2 | Data Source | EarthRanger connection | core `set_er_connection` | — |
| 3 | Time Range | since, until, timezone | core `set_time_range` (month / two months / quarter / custom) | last full month |
| 4 | Spatial Scope | level (`site / national / region / protected_area`), unit | `get_area_scope` (spatial feature groups `report:<level>`) | `site` |
| 5 | Patrols | patrol types (multi-select), team (subject group, optional), single patrol serial (optional) | core patrol types dropdown + text | all |
| 6 | Patrol Effort | grouper (`Patrol type / Team / Individual patrol`); team groups (advanced) | enum with `oneOf` titles | Patrol type |
| 7 | Events | retrieval (`Patrols + all events in period / Patrols + linked events only`); event types (multi-select); state (`All / Resolved only / Active only`); grouping (`Event type / Event category`) | core `event_types` dropdown + enums | all events, all types, All, Event type |
| 8 | Event Details | mode (`General table / One table per event type`); fields shown (free text, one line per field) | enum + string list | General table |
| 9 | Images | mode (`From attachments / Leave blank`); max images | enum + int | From attachments, 50 |
| 10 | Report Blocks | personnel, headline stats, time density map, event density map, events chart, monthly chart, category × priority, area covered, conclusions | booleans | per MRD core/optional split: core on, optional off |
| 11 | Report Template | language (`English / Español / Português`); title; subtitle; logo URLs (list); header fields (area name, authority…); footer text | enum + strings | English, "Patrol & Events Report" |
| 12 | Map Style (advanced) | base maps; track colour by (type/team); time-density cell size; track gap limit (default 3600 s) | core `set_base_maps` + existing colour-map params | — |

Example `param.yaml` (Costa Ecuador, Aug–Oct 2026):

```yaml
workflow_details: {name: "Costa Ecuador · Aug–Oct 2026", description: ""}
er_client: {data_source: {name: costaecuador}}
time_range: {since: "2026-08-01T00:00:00", until: "2026-11-01T00:00:00", timezone: {label: "UTC-05:00", tzCode: America/Guayaquil}}
spatial_scope: {level: site, unit: null}
patrols: {patrol_types: [], team: null, patrol_serial: null}
patrol_effort: {grouper: team, team_groups: [PONGALILLO, BELLAVISTA, COSTA RICA, EL CONCHAL, PUERTO ROMA]}
events: {retrieval: all_in_period, event_types: [], state: all, grouping: event_type}
event_details: {mode: general, fields: []}
images: {mode: attachments, max_images: 50}
report_blocks: {personnel: false, headline_stats: true, time_density: true, event_density: true, events_chart: true, monthly_chart: false, category_priority: false, area_covered: false, conclusions: true}
report_template: {language: es, title: "Reporte de patrullajes y eventos", subtitle: "Costa Ecuador", logos: ["https://…/maate.png", "https://…/earthranger.png"], area_name: "Golfo de Guayaquil", footer: null}
```

### 2.3 What happens to the data package
- **Keep it, but for templates only:** `standard_patrol_events_{en,es,pt}.docx` plus `load_report_template(language)`.
- **Remove** the partner profiles, `load_partner_profile` and `resolve_report_options`. The B1 profile YAMLs become `param.yaml` presets and `test-cases.yaml` cases, which is where per-site settings belong.
- A partner that needs its own layout gets its own template file, which adds a value to the template dropdown. That is the only per-partner artefact left.

## 3. Dashboard vs report

| | Dashboard (ecoscope-web) | Word report (.docx) |
|---|---|---|
| Purpose | Explore: where effort went, where events cluster, data QA | Deliver: the monthly/quarterly document sent to the authority |
| Maps | Interactive pydeck (zoom, hover, legend) | Static PNG of the same map (`html_to_png`), one per page width |
| Tables | Full, scrollable (every event row) | Summaries. Event details are capped or per type. Long tables are paginated |
| Grouping | Grouper views (switch patrol type / team in the dashboard filter) | Fixed sections, in the order the template defines |
| Text | Titles only | Header, metadata, intro paragraphs, conclusions box, footer, logos |
| Built from | `create_*_widget_single_view` → `gather_dashboard`, laid out by `layout.json` | `create_docx(TemplateContext)` |

**Both are fed by the same task outputs.** The effort table, maps, charts and event tables are computed once. The dashboard wraps them in widgets and the report wraps them in context items. Nothing is computed twice.

Dashboard layout (10-col grid, previewed in `.scripts/preview_dashboard.py`):
```
[Patrols][Distance][Hours][Patrol days][Events][Resolved]          ← single values (Patrol Effort / Event Analysis)
[ Tracks + events map (6)              ][ Patrol effort table (4) ]
[ Patrol time density (5)    ][ Event density (5)                 ]
[ Events by type/category (5)][ Events by month (5)               ]
[ Event summary table (4) ][ Event records table (6)              ]
```

## 4. Report template (Jinja / docxtpl)
- **Cover block:** logo row (from URLs, max 4), title, subtitle, then a 2-column metadata table: Area · Period · Generated by · Date generated.
- **Headline stats:** a 1×5 table of figures with small captions underneath (Patrols · km · hours · patrol days · events).
- **Sections** with numbered headings (1 Patrol effort, 2 Maps, 3 Event summary, 4 Event details, 5 Images, 6 Conclusions). An off block drops its whole section and the numbering closes up.
- **Tables:** a clean grid style (header row shaded, thin borders, right-aligned numbers, 1 decimal place, totals row in bold).
- **Maps:** full text width with a figure caption ("Figure 1 – Patrol tracks and events").
- **Images:** a 2-column grid of photo plus caption (#serial · type · date · coords). In blank mode, the same grid with empty cells.
- **Conclusions:** a bordered empty box.
- **Footer:** "This report was generated by Ecoscope using EarthRanger data", plus page numbers.
- **All headings and captions come from the language labels** (en/es/pt), so there are no mixed-language headings.

## 5. Impact on the plan

| Task | Status | Change |
|---|---|---|
| A0–A7 (ext-custom) | done | `filter_validated` gains a `state` mode (`all/resolved/active`). The event tables and charts take a `group_by` (type/category). Add an `area_covered_km2` single value |
| B1 data package | done | Shrink to templates only (§2.3) |
| B2 base template | done | Redesign per §4, in three languages |
| B3 spec | partial | Rewrite against the §2.2 form. Add dashboard widgets + `gather_dashboard` + `layout.json`. About 46 `get_collection_item` calls go away |
| B4 partner templates | — | Becomes "language templates + logo URLs". Partner-specific templates only on request |
| B5 | — | Unchanged |
| Vehicle grouper | new, later | Needs the patrol-schema fields (MRD §Data needs). Optional block after v1 |

## 6. Open questions (from MRD-2, still open)
1. Retrieval default: "patrols + all events in period" is recommended, based on the linkage numbers.
2. Vehicle block: in v1 or later?
3. Image cap: user-set max (proposed default 50).
4. Image captions "headers" (Andres): which details, where.
5. Logos as links: yes, docxtpl can insert an `InlineImage` from a downloaded URL. But ecoscope-web forbids runtime downloads, so this needs confirming with the platform team. The fallback is packaged logos.
6. Area km² and reporting group: proposed km² optional, reporting group out until ER has a field.

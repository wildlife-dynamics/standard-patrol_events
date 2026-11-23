# Standard Patrol & Events Report — Design

**Date:** 2026-11-16 · **Source requirements:** *Standard Patrol & Events MRD* (PRD) · **Spike:** `.scripts/` in this repo

## 1. Intent

Today every partner gets its own patrol report: its own workflow repo, its own task package, and its own copy of the code that builds the report data, adds the map, captions the photos and renders the docx. APN, Belize, ICMBio, WildAid, ICF and Lion Guardians all repeat that pattern, with Spanish/Portuguese labels and partner field keys hardcoded in Python.

The MRD asks for **one reusable workflow** that produces a patrol and events report for any partner. The report has a fixed set of blocks: metadata, personnel, headline stats, patrol effort, maps, event summary, event details, images, conclusions and footer. Partners differ only in:
- how patrol effort is grouped
- how event details are shown
- which header fields, logos and blocks appear

The aim is that adding a partner means writing a **profile and a template**, not code.

Primary users are LatAm partners: APN (Los Alerces, El Palmar, Iguazú, Los Glaciares), Costa Ecuador, Galápagos, ICF Honduras, PARNA Iguaçu and MMARN.

## 2. Goals, non-goals, anti-goals

**Goals**
- A single Ecoscope workflow (`spec.yaml` in this repo) that renders every MRD block into a Word document from a template.
- Partner differences are expressed as configuration (a *profile*) plus a per-partner `.docx` template, shipped in a small data-only package built from this repo.
- It works on every LatAm site whether or not the site has ER's new patrol model (`patrol_schemas`), and uses the new model's data when it is there.
- New generic tasks live in the shared library, not in a partner package.
- It can be published to ecoscope-web: no runtime file downloads, and the template ships with the workflow.

**Non-goals**
- Migrating existing partner workflows (APN-patrol_event, latam-patrol_summary, …) onto this one. They can switch later.
- The MRD's "by vehicle" effort table (fuel, origin and destination). On ER this data only exists where the new patrol model's segment or patrol-type forms capture it. It is a later block.
- "Events by reporting group (gender)" (Ecuador). The only existing implementation guesses gender from reporter names. It is out until ER has a real field for it.
- A live dashboard. The deliverable is the docx. The spike HTML exists only to judge the report's shape.

**Anti-goals (a technically working report that would still be a failure)**
- Hours or distance inflated by patrols left open. The spike saw 3,168 h for 2 APN patrols before gap filtering.
- An event-details or images block that is mostly empty because events weren't attached to patrols (only 3–9% are on ICF, El Palmar and Iguazú).
- Partner field keys or labels hardcoded in task code.
- A report that crashes because one optional input is empty. Blocks skip themselves instead.

## 3. Constraints and facts established by the spike

Measured on the live accounts, Aug–Oct 2026 (`.scripts/output/partners.json`):

| Partner | Patrols | Events | Events on a patrol | Events with images | Resolved | New patrol model |
|---|---|---|---|---|---|---|
| apn (Los Alerces) | 101 | 541 | 91% | 74% | 82 | on, no teams defined |
| apnelpalmar | 52 | 1016 | 3% | 6% | 394 | on |
| apniguazu | 56 | 999 | 9% | 79% | 634 | on |
| apnlosglaciares | 4 | 192 | 78% | 2% | 192 | on |
| costaecuador | 215 | 339 | 45% | 67% | 17 | off |
| galapagos | 195 | 28 | 100% | 29% | 0 | off |
| icf | 15 | 284 | 5% | 75% | 33 | off |
| parnaiguacu | 152 | 891 | 27% | 68% | 792 | off |
| mmarn | 6 | 3 | 33% | 33% | 3 | off |
| mep (test site) | — | — | — | — | — | on, 5 teams defined |

ER/DAS facts the design relies on (from the `das` repo):
- **Team.**
  - On sites with the new patrol model, each patrol *leg* has `team` (a team from the site's patrol configuration), `members` (people), `assets` (vehicles and boats), `segment_details` (the site-wide segment form) and `type_details` (the patrol-type form), plus `is_pause`. Members and assets come back as bare ids. Names come from `GET activity/patrols/config/default/resolved/`.
  - When the model is off, these keys are absent.
  - Without the new model, the best team source is the leader's **subject group**. People can be in several groups, and a catch-all "Subjects" group exists. At Costa Ecuador and Galápagos all leaders are shared device logins, so grouping by leader name is meaningless there.
- **Validated.** ER has no validated state. Event states are `new`, `active`, `resolved` and `review`.
- **Priority** is 0/100/200/300, labelled Gray/Green/Amber/Red. Costa Ecuador and Galápagos log everything as Gray.
- **Event-to-patrol links.** On new-model sites ER infers links: an event created by the leader or a member inside a leg's time is linked to that leg. Open legs count for at most 48 h. Elsewhere, links exist only when the client attached the event.
- **Tracks.** ER has no patrol-track endpoint. Tracks are the leader's fixes inside the leg's time range, so a forgotten open patrol collects idle fixes. The spike fixed this with `TrajSegFilter(max_time_secs=3600)`. After that, Costa Ecuador's longest patrol was 10 h (median 3.1 h), and devices that report less often than the gap limit get 0 km and 0 h.
- **Event schemas.** v2 `activity/eventtypes/<t>/schema` returns 404 for version-1 event types. Fall back to v1. Some APN fields hold values that ER no longer accepts as choices, and `process_events_details` retries 6× on them, which is slow.
- **Areas.** Spatial features have no parent/child relationship. The national → region → protected area hierarchy has to be a convention (a feature group per level).
- **Publishing.** Templates and other files must ship with the workflow (no runtime downloads). Never hand-edit compiled output, and always `recompile` (`publish-workflow-gcp.md`).
- **Environment.** Build against the APN env's stack: ecoscope-platform 2.26, ext-custom ≥ 0.1.5 for GCS template support, docxtpl.

## 4. Approaches considered

| | Approach | Trade-off |
|---|---|---|
| **A (chosen)** | One workflow repo. The new generic tasks go into the shared `ecoscope-workflows-ext-custom` library (`ecoscope-workflow-task-library`). Partners differ by profile and template. | No new partner package, and other workflows can reuse the tasks. Releases are tied to the shared library's cycle. |
| B | The same workflow, with the new tasks in a new `ext-standard` package. | Can be released independently, but it adds another package and more chances of duplicate task names (the compiler `_1` aliasing seen in CI). |
| C | Extend `APN-patrol_event`. | It's the newest code, but full of APN-only assumptions (`numero_patrulla`, `info_inicial_patrulla`, Spanish strings in code). |

The user approved A on 2026-11-16.

## 5. Design

### 5.1 Data flow

```
set_er_connection ─ get_user_me / get_report_generated_by
time_range, area scope, patrol-type filter, patrol id (optional)
        │
        ├─ patrols:  set_patrols_and_patrol_events_params → get_patrols_from_combined_params
        │            → get_patrol_observations_from_patrols_df_and_combined_params
        │            → process_relocations → relocations_to_trajectory(TrajectorySegmentFilter(max_time_secs = profile.max_gap_secs))
        │            → resolve_patrol_team (NEW) → patrol_effort_table (NEW, grouper = profile/param)
        │
        ├─ events:   get_events(include_details, include_files)  [scope = all-in-area | patrol-linked]
        │            → filter_validated (NEW, states = profile.validated_states)
        │            → process_events_details → event category display (apn get_event_categories / wd add_event_category_display)
        │            → event summary tables + charts; event_detail_tables (NEW)
        │
        ├─ maps:     tracks + events (draw_map → html_to_png); time density (create_meshgrid + calculate_linear_time_density)
        ├─ images:   xc download_event_attachments → sanitize_attachments → build_image_records (NEW, cap = profile.max_images)
        │            (not ext-wd's photo tasks: that would make this workflow depend on another partner package)
        └─ report:   create_docx(template = profile.template, TemplateContext[...]) → .docx
```

Every block is one or more `TemplateContext` items. A block that is turned off, or has no data, produces a `SkipSentinel` that `create_docx` drops. The template's Jinja `{% if %}` hides the heading.

### 5.2 Workflow parameters (form)
These are the MRD parameters as they appear in the workflow form:
- Date range: month, two months, quarter or custom.
- Area scope: the level, then the unit (see 5.5).
- Patrol type filter.
- Single patrol by serial number. When it is set, the report switches to single-patrol mode: one map of that patrol, and the effort table shows only that patrol.
- Effort grouper: `patrol_type | team | individual_patrol`.
- Validated events only: on/off.
- Event detail mode: `per_type | generic`.
- Images: auto / leave blank.
- Partner: a dropdown that loads the partner's profile and template (§5.3). The fields above default to the profile's values.

### 5.3 Partner profile
A profile is the set of values that differ by partner and are fixed by the template rather than chosen at run time.

**Where profiles live (decided 2026-11-16): a small data package built from this repo.** The package is `ecoscope-workflows-ext-standard-patrol-events` and contains only `profiles/<partner>.yaml` and `templates/<partner>.docx`, with **no partner logic**.
- It ships two tasks:
  - `load_partner_profile(partner) -> PartnerProfile`
  - `load_partner_template(partner) -> path` (read via `importlib.resources`, the Lion Guardians `load_*_file` pattern)
- The form has a **Partner** dropdown, and the profile fills the other task inputs.
- The run-time form fields in §5.2 (grouper, validated-only, detail mode, images) default to the profile's value. When a user sets one, it overrides the profile for that run.
- Adding a partner means adding a profile YAML and a template, then releasing this package. ext-custom (the generic tasks) is not touched.
- `param.yaml` presets and `test-cases.yaml` cases then just name the partner.

Profile keys:

| Key | Meaning | Example |
|---|---|---|
| `event_types` | Fixed list of event types in the report (MRD: set per template) | ICF threat + bio-monitoring types |
| `event_scope` | `area` = all events in area and period; `patrol` = only patrol-linked events | `area` for icf / apnelpalmar / apniguazu; `patrol` for galapagos |
| `validated_states` | States that count as validated | `["resolved"]` (ICF) |
| `team_source` | `auto` = new-model team, then subject group, then leader | `auto` |
| `team_groups` | Subject groups that count as teams (no other group is used) | APN: `GUARDAPARQUES ZONA SUR/NORTE/CENTRO, OPERACIONES, SINEP` |
| `max_gap_secs` | Gap limit for the track filter | 3600 by default; larger for sparse devices |
| `detail_fields` | Per event type, the 2–3 fields for per-type tables | ICF hunting: species, method, quantity |
| `max_images` | Image cap per report | 50 (MRD open question; see §7) |
| `language` | `es` / `pt` / `en` for generated labels and dates | `es` |
| `template` | Packaged `.docx` for this partner (logos, title, header fields, which blocks show) | `templates/icf.docx` in the data package |
| `grouper`, `validated_only`, `detail_mode`, `images` | Defaults for the run-time form fields | ICF: `patrol_type`, `true`, `per_type`, `blank` |
| `blocks` | Which optional blocks are on (personnel, headline stats, time density, category × priority, events bar, monthly stacked, conclusions) | follows the MRD partner matrix |

The MRD partner matrix maps onto these profiles:
- Honduras (icf): grouped by patrol type, per-type tables, images left blank for manual insertion, validated only, category × priority.
- Ecuador (costaecuador): grouped by team, time density, events bar.
- Galápagos: grouped by individual patrol, generic event details, personnel, headline stats.
- Patagonia (apnlosglaciares / apn): individual patrol, personnel grouped by role.
- Iguaçu (parnaiguacu): individual patrol, generic event details plus camera traps, monthly stacked chart.

### 5.4 New tasks (in ext-custom)
1. **`resolve_patrol_team(patrols_df, client, team_groups) -> df`.** Adds `team` and `personnel` columns per patrol.
   - Order: the new-model leg `team` label, then the leader's subject groups ∩ `team_groups` (joined with " + " so totals aren't counted twice), then the leader name.
   - `personnel` = the resolved names of leg `members`, with role where the site's form provides it. Empty when the model is off.
2. **`patrol_effort_table(traj_df, patrols_df, grouper, labels) -> df`.** One task for the three groupers, with a totals row.
   - Columns per the MRD: by type (patrols, km, h); by team (patrols, km, h, participants); by individual patrol (start, end, serial, type, km, h, number of events).
   - Built on `summarize_df`.
3. **`filter_validated(events_df, enabled, states) -> df`.**
4. **`event_detail_tables(events_df, mode, detail_fields, labels) -> TableContextItem | grouped list`.**
   - `generic`: one row per event, with all populated fields as "Label: value" lines, reusing wd's `format_event_details` logic.
   - `per_type`: one table per type under category subheadings, with `detail_fields[type]` columns. When a type is missing from the profile, it falls back to the 3 most-filled fields.
5. **`select_area_scope(client, level, unit) -> geometry`.** Resolves the chosen area from spatial-feature groups named by convention (§5.5) and masks patrols and events to it (`mask_aoi`).

6. **`build_image_records(events_df, attachment_paths, output_dir, max_images, labels) -> df[caption, image_path]`.**
7. **`create_docx` gains two generic context items:**
   - `TableListContextItem`: a list of `{heading, title, table}` for the per-type tables under category subheadings.
   - `ImageListContextItem`: rows of caption plus image path, rendered as `InlineImage`.
   The existing grouped items need groupers that are shared across the whole render call, which doesn't fit per-type tables or an image annex.

Each task gets a unit test, written first. Deduplicate against existing names before adding: `apply_qualitative_color_map`, `get_spatial_features` and others already exist in several packages.

### 5.5 Area hierarchy convention
ER has no hierarchy, so a site sets one up as spatial-feature groups named `report:national`, `report:region`, `report:protected_area` (a feature type per level also works).
- The form offers the levels that exist on the site.
- The grouper under the chosen level is the next level down.
- Protected area has no lower grouper.

Sites without the groups get "whole site" only. Galápagos (islands) and ICF (protected areas) already use subject groups for places, which is a hint about what to seed.

### 5.6 Report rendering
- `create_docx` from ext-custom, which supports `TextContextItem`, `ImageContextItem` (HTML→PNG), `TableContextItem` and grouped sections.
- **One base template** `templates/standard_patrol_events.docx` in the data package holds every block, each wrapped in `{% if block %}`. Each partner template is a copy with its own logos, title, header fields and labels.
- Templates are loaded from the data package by `load_partner_template`, never downloaded at runtime.
- Labels generated by code (column headers, captions, dates) come from a `language` labels table modelled on wd photo-records' `LABELS`, not from process-wide `set_locale`.
- Footer: "This report was generated by Ecoscope using EarthRanger data", with the Ecoscope logo.

### 5.7 Repo layout (this repo)
Modelled on `lion-guardians`, which keeps its data package and workflows in one repo:
- `workflows/standard_patrol_events/{spec.yaml, param.yaml, layout.json, test-cases.yaml}` (a param preset and a test case per partner, plus `mep` for the new model)
- `publish/build.sh` + `publish/recipes/release/*.yaml`
- `pixi.toml`, `Makefile` (`build` makes the data package into the local channel, as the APN Makefile does for its ext library), `dev/recompile.sh`
- `src/ecoscope-workflows-ext-standard-patrol-events/` — the data package (`profiles/*.yaml`, `templates/*.docx`, the two loader tasks and their tests)
- `.scripts/` (spike and checks)

The compiled package is `ecoscope-workflows-standard-patrol-events-workflow/`.

### 5.8 Calls made during review (builder's call, marked so they can be checked)
- **Camera traps (Iguaçu).** These are the site's camera-trap event types (`armadilhas_fotogrficas`, `retirada_armadilhas_fotogrficas`). They render as an extra per-type table next to the generic table, configured through `detail_fields`, with no separate data source.
- **Single-patrol events.** On new-model sites the events are the ones ER links to the patrol. Elsewhere they are patrol-linked events plus events reported by the patrol's leader inside the patrol's time window. That avoids an almost-empty block on sites where only 3–9% of events are linked.
- **Area scope selects, it doesn't clip.**
  - Patrols whose track intersects the area are included whole.
  - Events are included by point-in-polygon.
  - This matches the MRD's wording ("selects which patrols and events are included") and keeps per-patrol km and h stable.
- **Area level is a fixed list** (`site | national | region | protected_area`). A level whose `report:*` group is missing on the site falls back to the whole site, with a warning in the report metadata. ecoscope-web dropdowns can't be filled from ER at runtime.
- **Delivery is two-phase.**
  - During development the new tasks build into the local conda channel (the `APN-patrol_event` Makefile `build` pattern).
  - Before publishing, an ext-custom release must exist and be pinned. Publishing forbids `file://`.

## 6. Decided vs left to the builder

**Decided:** approach A; profiles and templates live in this repo's data package and are picked with a Partner dropdown, with form fields overriding; reusing the tasks named in 5.1; the profile keys; the team resolution order; the gap-filter approach; event scope as a profile key; `create_docx` and packaged templates; labels by language table; test cases per partner, including `mep`.

**Left to the builder:**
- Exact task signatures and module placement within ext-custom.
- Chart styling.
- Map colours (reuse `apply_qualitative_color_map`).
- Grid cell size for time density.
- How `blocks` is expressed in the form (one boolean per block, or a multi-select).
- Default image cap value.
- Whether personnel roles come from `segment_details` or a member subject attribute (whatever the site form provides).

## 7. Open questions (need an answer from the partner or ER, not the builder)
1. **Image cap.** The MRD asks whether to auto-populate by default and how to cap. The spike saw 497–856 attachments per quarter on several sites.
2. **APN teams.** Will APN define teams in its patrol configuration (matching its GUARDAPARQUES zones)? Until it does, team falls back to subject groups.
3. **New patrol model on non-APN sites.** When will ER enable it on costaecuador, galapagos, icf and parnaiguacu? Personnel stays empty there until then.
4. **Area hierarchy.** Will the partners or ER create the `report:*` feature groups?
5. **Personnel source.** The MRD notes "patrol metadata changing soon". Confirm that the new model's leg `members` (plus roles) is that change.

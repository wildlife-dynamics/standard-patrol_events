# Standard Patrol & Events Workflow — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** One Ecoscope workflow that renders the MRD's patrol & events report to .docx for any LatAm partner. Partners differ by a profile and a template shipped in a small data package.

**Architecture:**
- Generic tasks (team resolution, effort table, validated filter, event-detail tables, area scope, image records, labels, two new `create_docx` context items) are added to the shared `ecoscope-workflows-ext-custom` library.
- This repo holds a data-only package `ecoscope-workflows-ext-standard-patrol-events` (profiles YAML, .docx templates, loader tasks) and one workflow under `workflows/standard_patrol_events/`, wired from core and ext-custom tasks.
- The repo layout copies `lion-guardians` (package + publish recipes + workflows in one repo).

**Tech Stack:** Python 3.12, ecoscope-platform ≥2.18.4,<3 (2.26 in practice), wt-registry / wt-compiler, pandas / geopandas, docxtpl, pydantic, pytest, pixi, rattler-build.

**Spec:** `docs/superpowers/specs/2026-11-16-standard-patrol-events-design.md` (read it first; this plan argues from it).

## Global Constraints

- Two repos:
  - **Part A** = `/Users/zak/Documents/w-dynamics/ecoscope-workflow-task-library` (ext-custom), on a new branch `zak/standard-patrol-events-tasks`.
  - **Part B** = this repo.
- ext-custom requires `ecoscope-platform = ">=2.18.4,<3.0.0"`. Do not raise it.
- Tasks follow the ext-custom style: `@register()` from `wt_registry`, `Annotated[..., Field(description=...)]` parameters, `AnyDataFrame` from `ecoscope.platform.annotations`. Export each task from its subpackage `__init__.py` and `__all__`.
- Before naming a task, check that the name doesn't already exist in core, ext-custom, ext-apn or ext-wd. Duplicates trigger the compiler's `_1` aliasing.
- No partner field keys, partner names or language strings in task code. Labels come from `get_report_labels(language)`.
- Every task that can receive an empty input accepts `SkipSentinel | None` and returns an empty result or a `SkipSentinel`. It must never raise because a block has no data.
- Templates are read from the installed data package. No runtime downloads, no `file://` or `*` requirements in anything published.
- Workflow compile uses `wt-compiler = "==0.10.2"`. Always `recompile` (`--update`), never `compile`, after the first scaffold. Never hand-edit the generated `ecoscope-workflows-standard-patrol-events-workflow/`.
- Track gap default: `max_gap_secs = 3600`.
- Validated defaults to `["resolved"]`.
- Team resolution order: new-model leg `team` label → leader's subject groups ∩ `team_groups`, joined with `" + "` in sorted order → leader name → `"-"`.
- Commit messages end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. **A site without the new patrol model.** The segment keys `team`, `members` and `segment_details` are absent and `GET activity/patrols/config/default/` returns 404. Team falls back to subject group, then leader. Personnel is empty and nothing raises. Pinned in Task A1.
2. **A patrol with no track, or a device that reports less often than the gap limit.** The patrol still appears in the effort table with 0 km and 0 h and counts in the patrol total. It isn't silently dropped. Pinned in Task A2.
3. **A period with no patrols, or no events.** The report still renders, the affected blocks show the template's "no data" text, and the run doesn't fail. Pinned in Task B3.
4. **An event type with no v2 schema, or a profile that names no detail fields for a type.** Raw field keys are used, the top-3 most-filled fields are picked, and nothing raises. Pinned in Task A4.
5. **Attachments that aren't images (PDF, audio), and more photos than the cap.** Non-images are dropped, the cap is applied in event-time order, and captions match the right event. Pinned in Task A5.

---

## Part A — ext-custom (shared library)

Paths below are relative to `src/ecoscope-workflows-ext-custom/` in the task-library repo.

Run the tests with:
```bash
pixi run --manifest-path src/ecoscope-workflows-ext-custom/pyproject.toml pytest src/ecoscope-workflows-ext-custom/tests/tasks/<file> -vv
```

### Task A0: Branch and report labels

**Files:**
- Create: `ecoscope_workflows_ext_custom/tasks/localization/_report_labels.py`
- Modify: `ecoscope_workflows_ext_custom/tasks/localization/__init__.py`
- Test: `tests/tasks/test_report_labels.py`

**Interfaces:**
- Produces:
  - `ReportLanguage = Literal["en", "es", "pt"]`
  - `get_report_labels(language: ReportLanguage = "en") -> dict[str, str]`

  The keys are exactly: `patrol_type, team, leader, patrols, distance_km, hours, participants, personnel, start, end, serial, n_events, total, event_id, event_type, category, priority, time, coords, details, count, resolved, no_data`.

- [ ] **Step 1:** `git checkout -b zak/standard-patrol-events-tasks` in the task-library repo.
- [ ] **Step 2: Write the failing test**
```python
def test_labels_same_keys_every_language():
    en = get_report_labels("en")
    assert set(get_report_labels("es")) == set(en) == set(get_report_labels("pt"))

def test_labels_spanish_values():
    es = get_report_labels("es")
    assert es["distance_km"] == "Distancia (km)" and es["total"] == "Total" and es["patrol_type"] == "Tipo de patrullaje"
```
- [ ] **Step 3:** Run the test. Expected: FAIL (import error).
- [ ] **Step 4:** Implement `get_report_labels` as a module-level `dict[str, dict[str, str]]` lookup that returns a copy.
- [ ] **Step 5:** Run the test. Expected: PASS.
- [ ] **Step 6:** Commit: `feat: add get_report_labels (en/es/pt) for report column labels`.

### Task A1: Patrol team and personnel

**Files:**
- Create: `ecoscope_workflows_ext_custom/tasks/io/_patrol_team.py` (IO)
- Create: `ecoscope_workflows_ext_custom/tasks/transformation/_patrol_team.py` (pure)
- Test: `tests/tasks/test_patrol_team.py`

**Interfaces:**
- Produces (IO): `get_patrol_team_sources(client: EarthRangerClient) -> dict`.
  - It returns `{"subject_groups": list[dict], "teams": dict[str, str], "subjects": dict[str, str]}`.
  - `subject_groups` comes from `client._get("subjectgroups/", params={"flat": "true", "include_hidden": "true"})`.
  - `teams` maps team id to display, from `activity/patrols/config/default/`.
  - `subjects` maps subject id to name, from `activity/patrols/config/default/resolved/` (members and assets).
  - On a 404 from either config route, `teams` and `subjects` are `{}`.
- Produces (pure): `resolve_patrol_team(patrols_df: AnyDataFrame, sources: dict, team_groups: list[str]) -> AnyDataFrame`.
  - One row per patrol, with columns `patrol_id, patrol_serial_number, patrol_type, leader, team, personnel, start, end, n_events`.
  - `patrol_type` is the raw value of the first segment.
  - `personnel` is a `", "`-joined string of member names (empty string if none).
  - `n_events` is the count of events embedded across segments.

- [ ] **Step 1: Write the failing tests.** Fixture patrols are built as dicts in the ER `patrol_segments` shape (copy from the spike probe output in the spec §3).
```python
def test_new_model_team_wins():          # segment has "team": "t1"; sources.teams = {"t1": "Alpha"} -> team == "Alpha"
def test_subject_group_fallback_joined(): # leader in groups ZONA SUR + ZONA CENTRO, both in team_groups -> "ZONA CENTRO + ZONA SUR"
def test_groups_outside_team_groups_ignored(): # leader only in "Subjects" -> team == leader name
def test_no_leader_gives_dash():          # segment leader None -> leader == "-", team == "-"
def test_keys_absent_site_does_not_raise(): # no team/members keys, sources.teams == {} -> personnel == ""
def test_personnel_names_from_members():  # members ["s1","s2"], sources.subjects {"s1":"Ana","s2":"Luis"} -> "Ana, Luis"
```
- [ ] **Step 2:** Run the tests. Expected: FAIL.
- [ ] **Step 3:** Implement both tasks. `get_patrol_team_sources` catches the client's not-found error (`ERClientNotFound` from `ecoscope.io.earthranger`) only, and lets everything else raise.
- [ ] **Step 4:** Run the tests. Expected: PASS.
- [ ] **Step 5:** Commit: `feat: resolve patrol team (new-model team, subject group, leader) and personnel`.

### Task A2: Patrol effort table

**Files:**
- Create: `ecoscope_workflows_ext_custom/tasks/analysis/_patrol_effort.py`
- Test: `tests/tasks/test_patrol_effort.py`

**Interfaces:**
- Consumes:
  - the output of `resolve_patrol_team` (A1)
  - a trajectory GeoDataFrame from core `relocations_to_trajectory`, with columns `extra__patrol_id, dist_meters, timespan_seconds`
  - `get_report_labels` (A0)
- Produces: `patrol_effort_table(trajectory: AnyDataFrame | SkipSentinel, patrols: AnyDataFrame, grouper: Literal["patrol_type","team","individual_patrol"], labels: dict[str,str], patrol_type_display: dict[str,str] | None = None) -> AnyDataFrame`.
  - Columns are already labelled, and the last row is the totals row.
  - `patrol_type`: `[patrol_type, patrols, distance_km, hours]`
  - `team`: `[team, patrols, distance_km, hours, participants]`, where participants is the distinct count of leaders plus member names
  - `individual_patrol`: `[start, end, serial, patrol_type, distance_km, hours, n_events]`, sorted by start
  - km and h are rounded to 1 decimal.

- [ ] **Step 1: Write the failing tests**
```python
def test_patrol_without_track_kept_with_zero():   # 3 patrols, trajectory only for 2 -> patrols total 3, missing one has 0.0 km / 0.0 h
def test_totals_row_sums():                       # last row label == labels["total"], distance == sum of rows
def test_grouper_team_columns():                  # columns == [labels[k] for k in ("team","patrols","distance_km","hours","participants")]
def test_individual_sorted_by_start():
def test_trajectory_skipped_gives_zeros():        # trajectory=SkipSentinel() -> all distances 0.0, no raise
```
- [ ] **Step 2:** Run the tests. Expected: FAIL.
- [ ] **Step 3:** Implement. Aggregate the trajectory by `extra__patrol_id`, left-join onto `patrols`, `fillna(0)`, group, then append the totals row.
- [ ] **Step 4:** Run the tests. Expected: PASS.
- [ ] **Step 5:** Commit: `feat: add patrol_effort_table with three groupers and totals row`.

### Task A3: Validated filter and area scope

**Files:**
- Create: `ecoscope_workflows_ext_custom/tasks/transformation/_event_filters.py`
- Create: `ecoscope_workflows_ext_custom/tasks/spatial_ops/_area_scope.py`
- Test: `tests/tasks/test_event_filters.py`, `tests/tasks/test_area_scope.py`

**Interfaces:**
- Produces:
  - `filter_validated(events: AnyDataFrame, enabled: bool, states: list[str] = ["resolved"]) -> AnyDataFrame`
  - `AreaLevel = Literal["site","national","region","protected_area"]`
  - `get_area_scope(client: EarthRangerClient, level: AreaLevel, unit: str | None) -> AnyGeoDataFrame | SkipSentinel`. It reads the feature group named `report:<level>` and returns the single feature whose `name == unit`. It returns a `SkipSentinel` for `site`, or when the group or unit is missing (log a warning).
  - `select_in_area(gdf: AnyGeoDataFrame, area: AnyGeoDataFrame | SkipSentinel, id_column: str | None = None) -> AnyGeoDataFrame`. With `id_column`, it keeps **every** row of any id that has at least one intersecting row (whole patrols). Without it, it keeps rows that intersect (events). A `SkipSentinel` area returns `gdf` unchanged.

- [ ] **Step 1: Write the failing tests**
```python
def test_validated_off_keeps_all():
def test_validated_on_keeps_states():            # states ["resolved","review"] keeps both
def test_whole_patrol_kept_when_partly_inside(): # patrol with 2 segments, 1 inside polygon -> both kept
def test_events_point_in_polygon():
def test_skip_area_returns_input():
```
- [ ] **Step 2:** Run the tests. Expected: FAIL.
- [ ] **Step 3:** Implement. `get_area_scope` uses the existing ext-custom `get_spatial_features` source types where possible (`io/_spatial_features.py`), not a new HTTP path.
- [ ] **Step 4:** Run the tests. Expected: PASS.
- [ ] **Step 5:** Commit: `feat: add filter_validated and area-scope selection`.

### Task A4: Event detail tables

**Files:**
- Create: `ecoscope_workflows_ext_custom/tasks/transformation/_event_details_tables.py`
- Test: `tests/tasks/test_event_details_tables.py`

**Interfaces:**
- Consumes: events after core `process_events_details`, with columns `serial_number, time, geometry, event_type_display, event_category_display, event_details`, and labels (A0).
- Produces:
  - `event_detail_table(events, labels) -> AnyDataFrame` (generic mode). Columns: `[event_id, event_type, time, coords, details]`. `details` holds `"Key: value"` lines joined by `"\n"`, empty values dropped, lists joined with `", "`. `coords` is `"lat, lon"` to 5 decimals.
  - `event_detail_table_list(events, detail_fields: dict[str, list[str]], labels, fallback_n: int = 3) -> list[dict]` (per-type mode). It returns `[{"heading": category, "title": f"{type} ({n})", "table": DataFrame}]`, ordered by category, then type. Columns are `[event_id, time, coords, *fields]`.
  - The fields for a type come from `detail_fields[event_type value or display]`. If the type isn't listed, the `fallback_n` most-filled keys are used.
  - `events_by_type_table(events, labels) -> AnyDataFrame`. Columns: `[category, event_type, count, resolved]`, sorted by count descending, with a totals row.
  - `category_priority_table(events, labels) -> AnyDataFrame`. Rows are categories, columns are the `priority_label` values present, plus a `total` column and a totals row.

- [ ] **Step 1: Write the failing tests**
```python
def test_generic_details_lines_skip_empty():
def test_per_type_uses_profile_fields():
def test_per_type_fallback_top_filled():         # type absent from detail_fields -> 3 most frequent keys
def test_missing_field_value_blank():            # field named in profile but absent on an event -> ""
def test_empty_events_returns_empty():           # empty df -> [] and empty generic table with labelled columns
def test_events_by_type_counts_and_resolved():   # 3 events of type A (1 resolved) -> count 3, resolved 1; totals row last
def test_category_priority_crosstab():           # columns only for priority labels present, totals row and column
```
- [ ] **Step 2:** Run the tests. Expected: FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run the tests. Expected: PASS.
- [ ] **Step 5:** Commit: `feat: add generic and per-type event detail tables`.

### Task A5: Image records

**Files:**
- Create: `ecoscope_workflows_ext_custom/tasks/results/_image_records.py`
- Test: `tests/tasks/test_image_records.py` (use small PNG/JPEG fixtures written in the test with PIL)

**Interfaces:**
- Consumes: relative paths from the existing `download_event_attachments` (`attachments/<event_id>/<file>`) after `sanitize_attachments`.
- Produces: `build_image_records(events: AnyDataFrame | SkipSentinel, attachment_paths: list[str] | SkipSentinel, output_dir: str, max_images: int, labels: dict[str,str]) -> AnyDataFrame` with columns `caption, image_path`.
  - Caption is `f"#{serial} · {type} · {lat:.5f}, {lon:.5f} · {time:%Y-%m-%d %H:%M}"`.
  - Rows are ordered by event time, and the cap is applied after ordering.
  - Extensions other than `.jpg/.jpeg/.png/.gif/.webp` are dropped.
- Also fix the double `client._get(url)` in `io/_earthranger.py:75-76` (download once). Pin the fix with a test that mocks the client and asserts one call per file.

- [ ] **Step 1: Write the failing tests**
```python
def test_non_images_dropped():
def test_cap_applied_in_time_order():           # 5 images, max_images=2 -> the 2 earliest events
def test_caption_matches_event():
def test_skip_inputs_return_empty():
def test_download_event_attachments_fetches_once():
```
- [ ] **Step 2:** Run the tests. Expected: FAIL.
- [ ] **Step 3:** Implement and fix the double GET.
- [ ] **Step 4:** Run the tests. Expected: PASS.
- [ ] **Step 5:** Commit: `feat: add build_image_records; download each attachment once`.

### Task A6: Two new `create_docx` context items

**Files:**
- Modify: `ecoscope_workflows_ext_custom/tasks/results/_create_docx.py`. Add the classes beside `TableContextItem` (around line 93) and extend `ContextItem`. Rendering goes where items are processed (around line 799).
- Test: `tests/tasks/test_create_docx.py` (extend). Build the template in the test with python-docx, as the existing tests do.

**Interfaces:**
- Consumes: the A4 list and the A5 DataFrame.
- Produces:
  - `TableListContextItem(item_type: Literal["table_list"], key: str, value: list[dict] | SkipSentinel)`. Each entry renders to `{"heading", "title", "col_labels", "tbl_contents"}` using the existing `_dataframe_to_docxtpl_context`.
  - `ImageListContextItem(item_type: Literal["image_list"], key: str, value: AnyDataFrame | SkipSentinel, width_inches: float = 4.0)`. Each row renders to `{"caption", "image": InlineImage}`. Images go through the same path resolver as `ImageContextItem` (GCS-safe).

- [ ] **Step 1: Write the failing tests**
```python
def test_table_list_renders_each_table():     # 2 entries -> both titles and a cell value appear in output docx text
def test_image_list_renders_inline_images():  # 2 rows -> output docx has 2 inline shapes and both captions
def test_list_items_skip_sentinel_dropped():  # SkipSentinel -> key in skipped keys, render succeeds
```
- [ ] **Step 2:** Run the tests. Expected: FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run the whole `create_docx` suite (`tests/tasks/test_create_docx.py tests/tasks/test_docx_gcs.py`). Expected: PASS, with no regressions.
- [ ] **Step 5:** Commit: `feat(create_docx): add table_list and image_list context items`.

### Task A7: Library check and local build

- [ ] **Step 1:** `pixi run pytest` and `pixi run mypy` at the task-library root. Expected: all pass.
- [ ] **Step 2:** `pixi run build-release`. Expected: the ext-custom package lands in `/tmp/ecoscope-workflows-custom/release/artifacts`.
- [ ] **Step 3:** Open a PR on the task-library repo. The release tag is cut by the library maintainer. **Publishing Part B waits on that release** (spec §5.8). Development continues against the local channel.

---

## Part B — this repo

### Task B1: Repo scaffold and data package

**Files** (copy the structure from `/Users/zak/Documents/w-dynamics/lion-guardians`, renaming `lion-guardians` / `lion_guardians` to `standard-patrol-events` / `standard_patrol_events`):
- Create: `pixi.toml`
  - Local channel `file:///tmp/ecoscope-workflows-custom/release/artifacts/` first.
  - `wt-compiler = "==0.10.2"`.
  - The `compile` feature depends on `ecoscope-workflows-ext-standard-patrol-events = "*"` and `ecoscope-workflows-ext-custom = "*"` locally. Pin both before publishing.
- Create: `publish/build.sh`, `publish/recipes/release/ecoscope-workflows-ext-standard-patrol-events.yaml`. Run requirements: `wt-registry`, `wt-task`, `ecoscope-platform >=2.18.4,<3.0.0`, `ecoscope-workflows-ext-custom`, `pyyaml`, `pydantic`.
- Create: `dev/recompile.sh`, `dev/pytest-task.sh`, `Makefile` (`build`, `compile`, `recompile`, `run PARTNER=<name>`), and extend `.gitignore` with `/tmp`-style outputs and the generated workflow's `.pixi`.
- Create: `src/ecoscope-workflows-ext-standard-patrol-events/pyproject.toml`. Copy the LG one, and make sure `data/*.yaml` and `data/*.docx` are included in the wheel.
- Create: `src/.../ecoscope_workflows_ext_standard_patrol_events/{__init__.py,_version.py,tasks/__init__.py,tasks/_profiles.py,data/}`
- Test: `src/.../tests/test_profiles.py`

**Interfaces:**
- Produces:
  - `Partner = Literal["apn", "costaecuador", "galapagos", "icf", "parnaiguacu", "mep"]`
  - `PartnerProfile` (pydantic) with the spec §5.3 keys: `event_types: list[str]`, `event_scope: Literal["area","patrol"]`, `validated_states: list[str]`, `team_groups: list[str]`, `max_gap_secs: int = 3600`, `detail_fields: dict[str, list[str]]`, `max_images: int`, `language: Literal["en","es","pt"]`, `template: str`, `blocks: dict[str, bool]`, `grouper`, `validated_only: bool`, `detail_mode: Literal["per_type","generic"]`, `images: Literal["auto","blank"]`.
  - `load_partner_profile(partner: Partner) -> dict`. It validates through `PartnerProfile` and returns `model_dump()`, so spec steps can read keys with ext-custom `get_collection_item`.
  - `load_partner_template(partner: Partner) -> str`. It returns the absolute path of the partner's `template` file, using LG's `importlib.resources` `as_file` pattern.
  - `resolve_report_options(profile: dict, grouper: str | None = None, validated_only: bool | None = None, detail_mode: str | None = None, images: str | None = None) -> dict`. It returns the profile with the non-`None` overrides applied.
  - The `blocks` keys are exactly: `personnel, headline_stats, time_density, events_by_type, category_priority, events_bar, monthly_stacked, conclusions`.

- [ ] **Step 1: Write the failing tests**
```python
@pytest.mark.parametrize("partner", get_args(Partner))
def test_every_partner_profile_loads(partner):          # validates, template file exists
def test_override_beats_profile():                       # icf grouper patrol_type, override "team" -> "team"
def test_none_override_keeps_profile():
def test_unknown_partner_raises():
```
- [ ] **Step 2:** Run `pixi run --manifest-path src/ecoscope-workflows-ext-standard-patrol-events/pyproject.toml pytest src/ecoscope-workflows-ext-standard-patrol-events/tests -vv`. Expected: FAIL.
- [ ] **Step 3:** Implement the loaders. Write the six profiles in `data/<partner>.yaml` with values from the MRD partner matrix and spec §5.3:
  - **icf:** `patrol_type`, validated_only, `["resolved"]`, `per_type`, images `blank`, blocks category_priority + conclusions.
  - **costaecuador:** `team`, `team_groups` = its community groups (PONGALILLO, BELLAVISTA, COSTA RICA, EL CONCHAL, PUERTO ROMA), time_density + events_bar + conclusions.
  - **galapagos:** `individual_patrol`, `generic`, personnel + headline_stats + time_density + events_bar + conclusions, event_scope `patrol`.
  - **apn:** `individual_patrol`, personnel, team_groups = the GUARDAPARQUES zone groups + SINEP.
  - **parnaiguacu:** `individual_patrol`, `generic`, `detail_fields` for `armadilhas_fotogrficas`, personnel + headline_stats + time_density + events_bar + monthly_stacked.
  - **mep:** a copy of apn (it exists to exercise the new patrol model).

  Every profile points `template` at `standard_patrol_events.docx` until Task B4.
- [ ] **Step 4:** Run the tests. Expected: PASS (the template file is created in B2, so mark `test_every_partner_profile_loads` xfail until B2 lands, then remove the xfail in B2).
- [ ] **Step 5:** `make build`. Expected: the package lands in the local channel.
- [ ] **Step 6:** Commit: `feat: data package with partner profiles and loader tasks`.

### Task B2: Base report template

**Files:**
- Create: `.scripts/build_base_template.py`. It builds `data/standard_patrol_events.docx` with python-docx, modelled on `belize-patrol_report/.scripts/build_report_template.py`.
- Create: `src/.../data/standard_patrol_events.docx` (generated, committed)
- Test: `src/.../tests/test_template.py`

**Interfaces:**
- Consumes: the A6 context items and the B1 `blocks` keys.
- Produces the template variables later tasks fill:
  - text: `title, subtitle, area, generated_by, date_generated`
  - timerange: `period`
  - stat text: `n_patrols, total_km, total_hours, n_events`
  - tables (direct pattern): `effort, events_by_type, category_priority, personnel`
  - images: `tracks_map, time_density_map, events_bar, monthly_stacked, event_density_map`
  - generic details as table `event_details`
  - table_list: `event_detail_tables`
  - image_list: `images`
  - text: `detail_intro`
  - block flags: `show_<block>` for each `blocks` key, plus `show_images_manual`
  - the fixed conclusions heading and footer text from the spec §5.6

  Each block is wrapped in `{% if show_<block> %}`. Each data block also uses `{% if <key> %} … {% else %}{{ no_data }}{% endif %}`.

- [ ] **Step 1: Write the failing test.** Render the template with ext-custom `create_docx` using a minimal fixture context (two-row DataFrames, a 10×10 PNG, one table_list entry, one image_list row) and `show_*` all true. Assert that every heading and the footer text appear in the output docx text. Then render again with `show_time_density=False` and an empty `effort`, and assert that the time-density heading is gone and the `no_data` text appears.
- [ ] **Step 2:** Run the test. Expected: FAIL (no template).
- [ ] **Step 3:** Write `build_base_template.py`, run it, and commit the .docx. Remove the B1 xfail.
- [ ] **Step 4:** Run the data package tests. Expected: PASS.
- [ ] **Step 5:** Commit: `feat: base standard patrol & events report template`.

### Task B3: Workflow spec

**Files:**
- Create: `workflows/standard_patrol_events/spec.yaml`, `param.yaml`, `layout.json` (`[]`), `test-cases.yaml`
- Generated (do not edit): `workflows/standard_patrol_events/ecoscope-workflows-standard-patrol-events-workflow/`

**Interfaces:** wiring only. Every task comes from Part A, B1 or core. Follow the data flow in spec §5.1 exactly. Notes per section:
- **Header:** `set_er_connection`, `get_user_me` (generated_by), `set_time_range`, `get_timezone_from_time_range`, the `partner` dropdown, then `load_partner_profile`, then `resolve_report_options` (the form's grouper / validated_only / detail_mode / images, all optional, default `null`), then `load_partner_template`, then `get_report_labels(language)`.
- **Patrols:** reuse APN `spec.yaml:536-646` (combined params, then patrols, then observations, then `process_relocations` with `relocs_columns` including `patrol_id, patrol_type__display, patrol_serial_number`). `relocations_to_trajectory` takes a `TrajectorySegmentFilter` whose `max_time_secs` is read from the profile. Then `get_patrol_team_sources`, then `resolve_patrol_team`, then `get_area_scope` / `select_in_area(id_column="extra__patrol_id")`, then `patrol_effort_table`.
- **Events:** `get_events(include_details=True, include_display_values=True)` restricted to profile `event_types`, then `select_in_area`, then `filter_validated`, then core `process_events_details`, then category display (ext-apn `get_event_categories` + `map_event_category_display` are available; if adding ext-apn is unwanted, add the category join to A4's input prep instead and note it). When `event_scope == "patrol"`, use `unpack_events_from_patrols_df_and_combined_params` instead (spec §5.8 single-patrol rule).
- **Maps:** tracks + events go through `create_path_layer` / `create_scatterplot_layer` / `view_state_from_layers` / `draw_map`, then `persist_text`. Time density: `create_meshgrid` + `calculate_linear_time_density`, then a polygon layer, then `draw_map`. Charts: core bar chart tasks, persisted HTML. `create_docx` converts the HTML to PNG.
- **Headline stats:** core `dataframe_column_nunique` (patrols), `dataframe_column_sum` (km and h, from the effort input), and the event count, formatted into text items.
- **Personnel:** ext-custom `select_columns` on the `resolve_patrol_team` output (`patrol_serial_number, team, personnel`), dropping rows with empty personnel.
- **Event summary:** `events_by_type_table`, `category_priority_table` (A4).
- **Event density map:** `create_meshgrid` + core `calculate_feature_density` over the events, then a polygon layer, then `draw_map` (the ops-dashboard wiring).
- **Images:** `download_event_attachments(skip_download = images == "blank")`, then `sanitize_attachments`, then `build_image_records`.
- **Render:** `create_docx(template_path=load_partner_template, context=TemplateContext[...])`. A disabled block passes a `SkipSentinel` value and `show_<block>=False`.
- `task-instance-defaults` uses `skipif: any_is_empty_df / any_dependency_skipped`, and `create_docx` uses `skipif: never` (upgrade guide).
- `test-cases.yaml` has one case per partner in `Partner`, with period `2026-08-01`–`2026-11-01`.

- [ ] **Step 1:** Write `spec.yaml` and the `costaecuador` test case. `make compile` once, then `make recompile`. Expected: the compiler succeeds and `graph.png` is produced.
- [ ] **Step 2:** Run the generated mock-IO tests (`pixi run --manifest-path workflows/standard_patrol_events/ecoscope-workflows-standard-patrol-events-workflow/pixi.toml pytest`). Expected: PASS for the costaecuador case.
- [ ] **Step 3: Review Focus 3.** Add a test case `empty_period` (a period with no data on costaecuador, e.g. 2020-01-01..2020-01-02) and re-run. Expected: the run succeeds, and the output .docx contains the `no_data` label in the effort and event blocks.
- [ ] **Step 4:** Real run: `make run PARTNER=costaecuador`. Expected:
  - a .docx in the results folder
  - the effort totals match the spike (215 patrols, 3,434 km, 636 h)
  - the team table lists PONGALILLO / BELLAVISTA / …
- [ ] **Step 5:** Add the remaining partner cases (`apn, galapagos, icf, parnaiguacu, mep`), then recompile and re-run the mock tests. Expected: PASS. Real-run `mep`, and expect the effort team column to show the configured team names (new-model path).
- [ ] **Step 6:** Commit: `feat: standard patrol & events workflow spec with per-partner test cases`.

### Task B4: Partner templates

**Files:**
- Create: `src/.../data/{icf,costaecuador,galapagos,apn,parnaiguacu}.docx`. These are copies of the base template with partner logos, title, subtitle and header fields from the MRD §1. Use placeholder logos where the partner hasn't supplied one, and list them in the PR.
- Modify: each `data/<partner>.yaml` so `template` points at its own file.
- Test: extend `test_template.py`. Parametrize the B2 render test over every partner template and assert that the partner title appears.

- [ ] **Step 1:** Write the failing parametrized test. Expected: FAIL.
- [ ] **Step 2:** Create the templates (extend `build_base_template.py` with a per-partner header section rather than hand-editing five files).
- [ ] **Step 3:** Run the tests. Expected: PASS.
- [ ] **Step 4:** `make build && make recompile`, then real-run icf and apn. Expected:
  - the ICF report has per-type tables, blank image rows, a category × priority table, and validated-only counts (33 resolved for Aug–Oct)
  - the APN report has an individual-patrol table and a personnel block (empty until APN fills leg members; note that in the PR)
- [ ] **Step 5:** Commit: `feat: partner report templates`.

### Task B5: Comparison and publish readiness

- [ ] **Step 1:** Generate the APN report for the same period with `APN-patrol_event` and compare with ours. Distance and hours will differ by design (gap filter). The event counts per type must match for patrol-linked events. Record the differences in `docs/superpowers/specs/…-design.md` §3 as a short table.
- [ ] **Step 2:** Work through the ecoscope-web form checklist in `/Users/zak/Documents/w-dynamics/publish-workflow-gcp.md:51-117`:
  - dropdowns use `ecoscope:transform`
  - no file inputs
  - no runtime downloads
  - `metadata:` block in spec
  - `recompile --variant=gcp`

  Expected: the checklist passes. Pin `ecoscope-workflows-ext-custom` to the released version from A7, and the data package to its first tag.
- [ ] **Step 3:** Update `README.md` with how to add a partner (profile YAML + template + `make build`), and commit: `docs: how to add a partner; publish readiness`.

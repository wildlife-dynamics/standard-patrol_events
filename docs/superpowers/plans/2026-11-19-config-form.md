# Config Form Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the compiled config form of `standard_patrol_events` match the approved form mock, section by section, and make the workflow honour every new setting (Patrol Filter, Leader and Area effort groupings, Event State list, per-type event tables, attachments, report text).

**Architecture:** Each form section is one spec step. New sections are small *settings tasks* in the data package that return a dict; downstream steps read single values with core `get_collection_item`. Form wording, hidden labels, advanced flags, ER dropdowns and the rules *inside* a section come from `rjsf-overrides`. Rules on the form root wait for a wt-compiler change (Task 12); until then every section is visible.

**Tech Stack:** wt-compiler 0.11.2 spec (`--from-env --with-caching`), ecoscope-platform ≥2.37 core tasks, ext-custom tasks (pydantic, pandas, geopandas), RJSF.

**Spec:** `docs/superpowers/specs/2026-11-19-config-form-design.md` · **Form source of truth:** `docs/superpowers/specs/2026-11-19-config-form-checkbox.rjsf.json`

## Global Constraints

- Every title, description and default is copied **verbatim** from design §2 / the mock. Do not reword.
- Section keys in the compiled form are spec step ids. Two mock keys collide with existing step ids and are renamed: mock `patrols` → step **`patrol_filter`**, mock `events` → step **`event_scope`**. Every other mock key is the step id.
- Unlabelled single fields: title `" "` (never `""`) plus uiSchema `"ui:options": {"label": false}`.
- `ecoscope:advanced` only on a section's base fields, never inside `if`/`then`/`else`.
- Every settings-task parameter has a default (the form only sends the chosen option's fields).
- New patrol schema only; no old-model fallbacks.
- Labels in `en`, `es`, `pt` for every new report string.
- ext-custom: full test suite and `mypy` clean after each task. Data package: its test suite green.
- Dev loop: `make dev` to recompile, `make run-dev PARTNER=<case>`; delete the case's output folder before each run.
- Commit each task in the repo it touches; never push.
- ext-custom is an editable install shared with worktree `custom-theme-82ce48`, whose spec still uses `filter_event_state(state=…)`. Task 5 changes that signature; note it in the commit message.

## Review Focus

1. **Old saved configs / param files** (keys `patrol_serial`, `teams`, `leader_group`, `effort_grouper`, `effort_metrics`, `state_events.state`, `detail_mode`, `images_options`, `labels`, `report_title`, `area_scope`) must fail validation with a clear "extra field" error, not run with defaults. → Task 11 test `test_old_param_keys_rejected`.
2. **Stale hidden values:** Team ticked while an old `team_leader_group` is still filled must ignore the group. → Task 1 test `test_unticked_follow_up_fields_ignored`.
3. **Several patrol filters in one params file** (the form prevents it, a hand-written file does not): Single Patrol wins, then Team, then Team Leader. → Task 1 test `test_precedence_single_then_team_then_leader`.
4. **Area grouping with a map layer no track crosses:** the table shows one "Outside areas" row and the Total, no crash. → Task 3 test `test_area_none_row_is_outside_areas` and Task 11 run.
5. **Per-type tables naming a field the event type doesn't have:** the run stops with the valid field names for that type. → Task 7 test `test_unknown_field_lists_valid_fields`.

---

### Task 1: Patrol Filter settings task

**Files:**
- Create: `src/ecoscope-workflows-ext-standard-patrol-events/ecoscope_workflows_ext_standard_patrol_events/tasks/_settings.py`
- Modify: `…/tasks/__init__.py` (export)
- Test: `src/ecoscope-workflows-ext-standard-patrol-events/tests/test_settings.py`

**Interfaces:**
- Produces: `set_patrol_filter(team: bool = False, teams: list[str] = [], team_leader: bool = False, team_leader_group: str = "", single_patrol: bool = False, patrol_id: str = "") -> dict[str, str | list[str]]` returning keys `patrol_serial: str`, `teams: list[str]`, `leader_group: str` (empty = no filter).
- Produces: `effective_patrol_types(patrol_types: list[str] = [], patrol_serial: str = "") -> list[str]` — `[]` when a patrol serial is set (the Patrol Type section is hidden for a single patrol and a stale type must not exclude the patrol), else `patrol_types`. Test `test_patrol_types_ignored_for_single_patrol`.

- [ ] **Step 1: Write the failing tests**

```python
def test_default_is_no_filter():
    assert set_patrol_filter() == {"patrol_serial": "", "teams": [], "leader_group": ""}

def test_each_option():
    assert set_patrol_filter(single_patrol=True, patrol_id=" 70 ")["patrol_serial"] == "70"
    assert set_patrol_filter(team=True, teams=["Alpha"])["teams"] == ["Alpha"]
    assert set_patrol_filter(team_leader=True, team_leader_group="Rangers")["leader_group"] == "Rangers"

def test_unticked_follow_up_fields_ignored():
    out = set_patrol_filter(team=True, teams=["Alpha"], team_leader_group="Rangers", patrol_id="70")
    assert out == {"patrol_serial": "", "teams": ["Alpha"], "leader_group": ""}

def test_precedence_single_then_team_then_leader():
    out = set_patrol_filter(single_patrol=True, patrol_id="70", team=True, teams=["A"], team_leader=True, team_leader_group="R")
    assert out == {"patrol_serial": "70", "teams": [], "leader_group": ""}
    assert set_patrol_filter(team=True, teams=["A"], team_leader=True, team_leader_group="R")["leader_group"] == ""
```

- [ ] **Step 2: Run** `.pixi/envs/dev/bin/python -m pytest -q src/ecoscope-workflows-ext-standard-patrol-events/tests/test_settings.py` — Expected: FAIL (import error).
- [ ] **Step 3: Implement** `set_patrol_filter` (`@register()`), strip the patrol id, apply the precedence above.
- [ ] **Step 4: Run** the same command — Expected: PASS.
- [ ] **Step 5: Commit** `feat(settings): Patrol Filter settings task`.

### Task 2: Patrol Effort settings task

**Files:** Modify `…/tasks/_settings.py`, `…/tasks/__init__.py`; Test `tests/test_settings.py`

**Interfaces:**
- Produces: `set_patrol_effort(group_by: Literal["patrol_type", "team", "leader", "patrol", "area"] = "patrol_type", map_layer: str = "", columns: list[Literal["patrol_count", "total_distance", "total_duration", "patrol_days", "leg_count", "member_days", "area_covered_merged"]] = ["patrol_count", "total_distance", "total_duration"]) -> dict` with keys `grouper: str`, `map_layer: str`, `metrics: list[dict]`.
- `grouper` mapping: `patrol_type`→`"patrol_type"`, `team`→`"patrol_team_name"`, `leader`→`"patrol_subject"`, `patrol`→`"patrol_serial_number"`, `area`→`f"SpatialGrouper_{map_layer}"` (core `SpatialGrouper.index_name`).
- `metrics`: core `set_patrol_summary_metrics` items in `columns` order; `total_distance` gets `"unit": "km"`, `total_duration` gets `"unit": "h"`, the rest `{"metric": name}`.
- Produces: `effort_grouper_for(grouper: str, patrol_serial: str = "") -> str` — `"patrol_serial_number"` when a patrol serial is set (design §7: a single patrol keeps a one-row effort table grouped by individual patrol), else `grouper`. Test `test_single_patrol_groups_by_patrol`.

- [ ] **Step 1: Failing tests**

```python
def test_effort_defaults():
    out = set_patrol_effort()
    assert out["grouper"] == "patrol_type" and out["map_layer"] == ""
    assert out["metrics"] == [{"metric": "patrol_count"}, {"metric": "total_distance", "unit": "km"}, {"metric": "total_duration", "unit": "h"}]

def test_effort_groupers():
    assert set_patrol_effort(group_by="leader")["grouper"] == "patrol_subject"
    assert set_patrol_effort(group_by="area", map_layer="Sectors")["grouper"] == "SpatialGrouper_Sectors"

def test_area_needs_a_map_layer():
    with pytest.raises(ValueError, match="Map Layer"):
        set_patrol_effort(group_by="area")

def test_map_layer_ignored_unless_area():
    assert set_patrol_effort(group_by="team", map_layer="Sectors")["map_layer"] == ""
```

- [ ] **Step 2–4:** run (FAIL), implement, run (PASS) with the Task 1 command.
- [ ] **Step 5: Commit** `feat(settings): Patrol Effort settings task`.

### Task 3: Leader and Area rows in the effort table (ext-custom)

**Files:**
- Modify: `ecoscope_workflows_ext_custom/tasks/analysis/_effort_format.py`, `ecoscope_workflows_ext_custom/tasks/localization/_report_labels.py`
- Test: `tests/tasks/test_effort_format.py`, label tests

**Interfaces:**
- Consumes: `grouper` strings from Task 2.
- Produces: `format_effort_table(..., grouper: str, ...)` (was a `Literal`) accepting `patrol_type`, `patrol_team_name`, `patrol_subject`, `patrol_serial_number` and any `SpatialGrouper_<name>`; anything else → `ValueError`. New labels `leader` (en "Leader", es "Líder", pt "Líder"), `area` (en "Area", es "Área", pt "Área"), `outside_areas` (en "Outside areas", es "Fuera de las áreas", pt "Fora das áreas").

- [ ] **Step 1: Failing tests** — `test_leader_rows_use_leader_header` (grouper `patrol_subject` → first column header `L["leader"]`, a `None` leader shown as `L["no_team"]`); `test_area_rows_use_area_header` (grouper `SpatialGrouper_Sectors` → header `L["area"]`); `test_area_none_row_is_outside_areas` (a `"None"` group → row label `L["outside_areas"]`, Total row unchanged); `test_unknown_grouper_rejected`.
- [ ] **Step 2–4:** run `.pixi/envs/default/bin/python -m pytest -q tests` in ext-custom (FAIL → implement → PASS), then `mypy ecoscope_workflows_ext_custom` clean.
- [ ] **Step 5: Commit** (ext-custom) `feat: effort table rows by leader and by area`.

### Task 4: Area grouping helpers (ext-custom)

**Files:** Create `ecoscope_workflows_ext_custom/tasks/transformation/_area_groupers.py`; export; Test `tests/tasks/test_area_groupers.py`

**Interfaces:**
- Produces: `area_groupers(map_layer: str = "") -> list[SpatialGrouper]` (`[]` when empty, else `[SpatialGrouper(spatial_index_name=map_layer)]`) and `area_regions(client: EarthRangerClient, map_layer: str = "") -> list` (`[]` when empty, else the result of core `load_spatial_features_group` for that name, wrapped in a list).
- Consumed by Task 11: core `resolve_spatial_feature_groups_for_spatial_groupers(groupers, spatial_feature_groups)`, `add_spatial_index(gdf, groupers)` on `effort_tracks`, `apportion_legs_by_spatial_index(legs, indexed_traj, groupers)` on `effort_legs`. With `[]` groupers all three pass data through unchanged.

- [ ] **Step 1: Failing tests** — `test_no_layer_no_groupers` (`area_groupers("") == []`), `test_layer_gives_spatial_grouper` (`index_name == "SpatialGrouper_Sectors"`), `test_area_regions_empty_without_layer` (fake client never called).
- [ ] **Step 2–4:** FAIL → implement → PASS; mypy clean.
- [ ] **Step 5: Commit** (ext-custom) `feat: area grouper helpers for patrol effort`.

### Task 5: Event State as a list (ext-custom)

**Files:** Modify `ecoscope_workflows_ext_custom/tasks/transformation/_event_filters.py`; Test `tests/tasks/test_event_filters.py`

**Interfaces:**
- Produces: `filter_event_state(events, states: list[Literal["new", "active", "resolved", "review"]] = []) -> AnyDataFrame | SkipSentinel`; empty = all states. The old `state` parameter is removed.

- [ ] **Step 1: Failing tests** — replace the old state tests: `test_empty_keeps_all`, `test_states_filter` (`["resolved"]` keeps only resolved; `["new", "active"]` keeps both), `test_skip_and_none_pass_through` kept.
- [ ] **Step 2–4:** FAIL → implement → PASS; mypy clean.
- [ ] **Step 5: Commit** (ext-custom) `feat!: filter_event_state takes a list of states (custom-theme-82ce48 spec still passes state=)`.

### Task 6: Event scope, report text, attachments and report sections settings

**Files:** Modify `…/tasks/_settings.py`, `…/tasks/_report.py`, `…/tasks/__init__.py`; Test `tests/test_settings.py`, `tests/test_report.py`

**Interfaces:**
- Produces:
  - `set_event_scope(linked_only: bool = False) -> str` → `"linked_only"` or `"all_in_period"` (value for `filter_linked_events.retrieval`).
  - `effective_event_types(event_types: list[str] = [], retrieval: str = "all_in_period", patrol_serial: str = "") -> list[str]` → `[]` when `retrieval == "linked_only"` or a patrol serial is set (Event Type is hidden then), else `event_types`. Test `test_event_types_ignored_when_linked_or_single`.
  - `set_report_text(language: Literal["en", "es", "pt"] = "en", title: str = "Patrol & Events Report", subtitle: str = "", details_intro: str = "") -> dict[str, str]` with the same keys.
  - `set_images_options(skip_download: bool = False, max_images: int = 50) -> dict` → `{"list_only": skip_download, "max_images": max_images}` (replaces the `mode` parameter).
  - `set_report_blocks(headline_stats=True, personnel=False, time_density=True, event_density=True, events_chart=True, monthly_chart=False, category_priority=False, conclusions=True)` — titles exactly as design §2 row 15; the `images` parameter is removed and the result always carries `"show_images": "true"` (photos are switched off by Skip Photo Attachments, which keeps captions).

- [ ] **Step 1: Failing tests** — `test_event_scope`, `test_report_text_defaults`, `test_images_options_skip` (`skip_download=True` → `list_only is True`), `test_report_blocks_defaults` (8 switches + `show_images == "true"`, MRD core/optional split), update `test_template.py` for the 8 switches.
- [ ] **Step 2–4:** FAIL → implement → PASS (data package suite).
- [ ] **Step 5: Commit** `feat(settings): event scope, report text, attachments and sections`.

### Task 7: Per-type event tables settings + unknown-field error

**Files:** Modify `…/tasks/_settings.py` (data package); `ecoscope_workflows_ext_custom/tasks/transformation/_event_details_tables.py` (ext-custom); Tests in both

**Interfaces:**
- Produces (data package): `EventTypeFields(BaseModel)` with `event_type: str`, `fields: list[str] = []`; `set_event_details(all_details: bool = True, tables: list[EventTypeFields] = []) -> dict` → `{"mode": "general" | "per_type", "detail_fields": {event_type: fields}}` (`mode` is `"general"` when `all_details`, else `"per_type"`; rows without fields are kept so the type still gets its first 3).
- Changes (ext-custom): `event_detail_table_list` raises `ValueError(f"Unknown field(s) {bad} for {type}. Fields: {', '.join(valid)}")` when a listed field is not a detail key of any event of that type.

- [ ] **Step 1: Failing tests** — `test_event_details_default_general`, `test_event_details_per_type_mapping`; ext-custom `test_unknown_field_lists_valid_fields`.
- [ ] **Step 2–4:** FAIL → implement → PASS in both repos; mypy clean.
- [ ] **Step 5: Commit** both repos `feat: per-type event detail tables from the form`.

### Task 8: Remove Spatial Scope

**Files:** Modify `workflows/standard_patrol_events/spec.yaml`, `test-cases.yaml`, `param.yaml`

- [ ] **Step 1:** Delete steps `area_scope` and `area`; `trajectory` becomes the `patrol_trajectory` output (drop its `select_in_area`); delete `events_in_area` and point `state_events.events` at `retrieved_events`. Remove `area_scope` from every test case and `param.yaml`.
- [ ] **Step 2:** `make dev` — Expected: exit 0; `grep -c area_scope …/rjsf.json` → 0.
- [ ] **Step 3:** `make run-dev PARTNER=apncentral` — Expected: `result.json` error `None`, headline 5 patrols.
- [ ] **Step 4: Commit** `refactor(spec): drop Spatial Scope (area is a grouping now)`.

### Task 9: Wire the new sections in the spec

**Files:** Modify `workflows/standard_patrol_events/spec.yaml`, `test-cases.yaml`, `param.yaml`

**Interfaces:** consumes Tasks 1–7.

- [ ] **Step 1: Patrol Filter and Patrol Type.** Replace form steps `patrol_serial`, `teams`, `leader_group` with step `patrol_filter: set_patrol_filter` (name "Patrol Filter") and three `get_collection_item` steps (`patrol_serial`, `teams`, `leader_group_name`) feeding the existing `report_range`, `filter_patrols_by_serial`, `filter_by_teams`, `get_leader_group_ids(group=…)`, `filter_linked_events(patrol_serial=…)`. Add form step `patrol_type: set_optional_string_list` (name "Patrol Type") → `effective_patrol_types` → `patrol_params.patrol_types` (no longer a form field of `patrol_params`).
- [ ] **Step 2: Patrol Effort.** Replace form steps `effort_grouper` and `effort_metrics` with `patrol_effort: set_patrol_effort` (name "Patrol Effort"); `effort_metrics` keeps `set_patrol_summary_metrics` with `metrics` from the dict; `summarize_df`/`format_effort_table` take the grouper from `effort_grouper_for(grouper, patrol_serial)`. Add the area chain: `area_groupers` → `area_regions` → `resolve_spatial_feature_groups_for_spatial_groupers` → `add_spatial_index` on `effort_tracks` → `apportion_legs_by_spatial_index` on `effort_legs` (`drop_unplaced: false`); summaries read the indexed frames.
- [ ] **Step 3: Events.** Form step `event_scope: set_event_scope` (name "Events") feeds `retrieved_events.retrieval`; rename form step `event_types` → `event_type` (name "Event Type") and feed `get_events` / `add_missing_linked_events` through `effective_event_types`; `state_events` becomes form section "Event State" (`states`); `event_grouping`, `tracks_color_by` (renamed step `patrol_grouping`, name "Patrol Grouping") keep their tasks.
- [ ] **Step 4: Event details, attachments, report.** `event_details_settings: set_event_details` (name "Event Details") feeds `detail_mode` and `event_detail_tables.detail_fields` via `get_collection_item`, removing the old `detail_mode` / `event_detail_tables` form fields; rename `images_options` → `download_attachments` (name "Download Event Attachments"); `report: set_report_text` (name "Report") feeds `labels` (language), title, subtitle and details intro via `get_collection_item`; `report_blocks` named "Report Sections"; `template_path` fixed in a partial (no form).
- [ ] **Step 5: Migrate test cases and `param.yaml`** to the new keys (e.g. `apncentral_patrol70`: `patrol_filter: {single_patrol: true, patrol_id: "70"}`; `mep_team`: `patrol_filter: {team: true, teams: [Hurricane Ridge District]}`).
- [ ] **Step 6:** `make dev` (exit 0) and `make run-dev PARTNER=apncentral` (error `None`).
- [ ] **Step 7: Commit** `feat(spec): config sections per the approved form`.

### Task 10: rjsf-overrides to match the mock

**Files:** Modify `workflows/standard_patrol_events/spec.yaml` (`rjsf-overrides`); Create `workflows/standard_patrol_events/tests/test_form.py` (or the repo's existing workflow test folder)

- [ ] **Step 1: Failing test** `test_compiled_form_matches_mock`: load the compiled `rjsf.json` and the mock (with `patrols`→`patrol_filter`, `events`→`event_scope`); for every section in the mock's `ui:order`, assert equal `title`, `description`, and, per field, `title`, `description`, `default`, `ecoscope:advanced`, `ecoscope:transform`, the in-section `if`/`then`/`else`/`allOf`, and the section's `uiSchema`. Ignore the mock's **root** `if`/`else` (Task 12).
- [ ] **Step 2:** run it — Expected: FAIL listing mismatches.
- [ ] **Step 3: Write the overrides.** Per section, override the whole `<step>.properties` object where fields move into rules (`patrol_filter`, `patrol_effort`, `event_details_settings`) and add the section's `if`/`then`/`else`/`allOf` from the mock; set root `uiSchema.ui:order` to the mock's order (with renamed keys) and per-section uiSchema (hidden labels, textarea, row labels).
- [ ] **Step 4:** `make dev`; run the test — Expected: PASS.
- [ ] **Step 5: Commit** `feat(form): rjsf overrides match the approved form`.

### Task 11: End-to-end runs and old-key check

**Files:** Modify `test-cases.yaml` (add `mep_area`, `apn_leader`); Test `tests/test_form.py`

- [ ] **Step 1: Failing test** `test_old_param_keys_rejected`: validating a params dict containing `patrol_serial: {var: "70"}` against the compiled form raises an "Additional properties" error.
- [ ] **Step 2:** implement nothing new if it already passes (the form has `additionalProperties: false`); otherwise fix the overrides. Run — Expected: PASS.
- [ ] **Step 3: Runs** (delete each output folder first), all with `result.json` error `None`:
  - `apncentral` — 5 patrols, 11 legs.
  - `apncentral_patrol70` — period 11 nov 2026, 2 legs.
  - `belize` — headline unchanged from the last baseline.
  - `mep_team` — 15 patrols.
  - `mep_area` — `patrol_effort: {group_by: area, map_layer: <a mep layer the tracks cross>}`: effort rows per area plus "Outside areas", Total equals the ungrouped Total.
  - `apn_leader` — `patrol_filter: {team_leader: true, team_leader_group: "GUARDAPARQUES ZONA NORTE"}` on Los Alerces, Aug–Oct 2026: fewer patrols than the unfiltered run.
- [ ] **Step 4:** Validate one report with the OOXML validator and open it in Word.
- [ ] **Step 5: Commit** `test: config form cases (area, leader, single patrol)`.

### Task 12: wt-compiler root-rules proposal

**Files:** Create `docs/superpowers/specs/2026-11-19-wt-compiler-root-rules.md`

- [ ] **Step 1:** Write the proposal: let `ReactJSONSchemaFormOverrides` accept root keys `if`, `then`, `else` (and pass them through `ReactJSONSchemaFormConfiguration`), with a doctest; include the exact nested root rule this workflow needs (mock root `if`/`else` with `patrols`→`patrol_filter`, `events`→`event_scope`) and why sibling rules / root `allOf` don't work in RJSF.
- [ ] **Step 2:** Add the rule to the spec as a commented-out `rjsf-overrides` block with a `# needs wt-compiler >= <release>` note.
- [ ] **Step 3: Commit** `docs: wt-compiler root rules proposal`. Do not open issues or PRs in other repositories without the user's go-ahead.

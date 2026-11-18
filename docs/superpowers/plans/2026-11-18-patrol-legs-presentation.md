# Patrol Legs Presentation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show patrol legs as the unit in the report table, the tracks map and the effort table.

**Architecture:** Core already stamps every GPS point with its leg id (`patrol_segment_id`) and the leg's own type. Keep the leg id through the track pipeline and make one track per leg; the legs table gains per-leg km/hours from those tracks and a merged patrol cell in the Word template; the effort table gains a "transport" grouping computed from the per-leg tracks.

**Tech Stack:** ext-custom tasks (Python, pandas), docxtpl template built by `.scripts/build_base_template.py`, wt spec; dev loop `make dev` / `make run-dev`.

**Spec:** `docs/superpowers/specs/2026-11-18-patrol-legs-presentation-design.md`

## Global Constraints

- Labels follow the report language (en/es/pt): leg = Leg / Tramo / Trecho; legs = legs / tramos / trechos; transport = Transport / Medio / Meio; no transport = No type / Sin tipo / Sem tipo.
- Headline counts stay per patrol (patrols, total km, total hours, patrol days).
- A single-leg patrol must read like a plain patrol list (one row, Tramo 1).
- Legs in start-time order; pause legs excluded.
- Dashboard table: one row per leg (no merged cells).
- ext-custom repo: `/Users/zak/Documents/w-dynamics/ecoscope-workflow-task-library-spe/src/ecoscope-workflows-ext-custom` (tests: `pixi run -e default pytest -q tests`; types: `pixi run -e default mypy ecoscope_workflows_ext_custom`).

## Review Focus

- A leg that recorded no GPS points: table shows "—" for km and hours, not 0 and not a crash (Task 3 test).
- A patrol whose legs have no type: "Sin tipo" in the table and the map legend, never "-" or "NaN" (Tasks 3, 6).
- Sites still on one leg per patrol (Belize): unchanged effort totals and a plain table (Task 6 check).
- Track points with no leg id (column absent): tracks fall back to one per patrol, not dropped (Task 2 test).
- Two consecutive patrols with identical patrol-cell text must not merge across patrols: the cell text includes the patrol number, which is unique (Task 3 test).

---

### Task 1: Labels for legs

**Files:**
- Modify: `ecoscope_workflows_ext_custom/tasks/localization/_report_labels.py`
- Test: `tests/tasks/test_report_labels.py`

**Interfaces:**
- Produces: label keys `leg`, `legs`, `transport`, `no_type` in all three languages.

- [ ] **Step 1: Failing test** `test_leg_labels`: for `en`, `es`, `pt`, assert `(L["leg"], L["legs"], L["transport"], L["no_type"])` equals `("Leg","legs","Transport","No type")`, `("Tramo","tramos","Medio","Sin tipo")`, `("Trecho","trechos","Meio","Sem tipo")`.
- [ ] **Step 2: Run** `pixi run -e default pytest -q tests/tasks/test_report_labels.py` → FAIL (KeyError).
- [ ] **Step 3: Add the four keys** to each language block next to `members`.
- [ ] **Step 4: Run** the test → PASS; full suite green.
- [ ] **Step 5: Commit** `feat(labels): leg, legs, transport, no_type`.

### Task 2: One track per leg

**Files:**
- Modify: `ecoscope_workflows_ext_custom/tasks/transformation/_short_tracks.py`, `transformation/__init__.py`
- Test: `tests/tasks/test_apn_fixes.py`

**Interfaces:**
- Produces: `tracks_per_leg(relocations: AnyDataFrame, leg_column: str = "patrol_segment_id", group_column: str = "groupby_col") -> AnyDataFrame` — copies `leg_column` into `group_column` where it is set; returns the input unchanged when `leg_column` is absent.

- [ ] **Step 1: Failing tests** `test_tracks_per_leg_groups_by_leg` (two legs of one patrol → two distinct `groupby_col` values equal to the leg ids) and `test_tracks_per_leg_without_leg_column_unchanged` (frame returned with `groupby_col` untouched).
- [ ] **Step 2: Run** → FAIL (ImportError).
- [ ] **Step 3: Implement** in `_short_tracks.py`; rows with a null leg id keep their patrol `groupby_col`; export it.
- [ ] **Step 4: Run** → PASS; mypy clean.
- [ ] **Step 5: Commit** `feat: tracks_per_leg — one track per patrol leg`.

### Task 3: Legs table — merged patrol cell, per-leg km/hours

**Files:**
- Modify: `ecoscope_workflows_ext_custom/tasks/transformation/_patrol_legs.py`
- Test: `tests/tasks/test_patrol_legs.py`

**Interfaces:**
- Consumes: Task 1 labels.
- Produces: `patrol_legs_table(..., trajectory: AnyDataFrame | SkipSentinel | None = None, ...)` returning columns `[L["patrol"], L["leg"], L["transport"], L["start_end"], L["distance_km"], L["hours"], L["leader"], L["members"], L["details"]]`. Patrol cell text: `"#<serial>\n<YYYY-MM-DD of first leg start, report tz> · <n> <L['leg'] lower if n == 1 else L['legs']>"`, identical on every row of that patrol (Task 5 merges equal consecutive cells). km/hours: sum of `dist_meters`/1000 and `timespan_seconds`/3600 over trajectory rows whose `extra__patrol_segment_id` equals the leg id, rounded to 1 decimal; `"—"` when the leg has no rows. Transport: `patrol_type_display` value, else `L["no_type"]`.

- [ ] **Step 1: Update and add tests**: column list as above; `#70 · 1/2` labels removed (patrol cell `"#70\n2026-11-11 · 2 tramos"` with `es` labels); km/hours from a 2-row trajectory fixture for leg `s1` (`0.1`, `0.0`) and `"—"` for leg `s2`; untyped leg shows `"Sin tipo"`; single-leg patrol cell ends `"· 1 tramo"`; two patrols never share a cell value.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement**; keep start-time sort and pause exclusion.
- [ ] **Step 4: Run** → PASS; full suite + mypy green.
- [ ] **Step 5: Commit** `feat(patrol_legs_table): patrol cell, Tramo, Medio, per-leg km/hours`.

### Task 4: Effort by transport

**Files:**
- Modify: `ecoscope_workflows_ext_custom/tasks/analysis/_patrol_effort.py`
- Test: `tests/tasks/test_patrol_effort.py`

**Interfaces:**
- Consumes: Task 1 labels.
- Produces: `grouper` accepts `"transport"`: rows grouped by trajectory `extra__patrol_type__display` (null → `L["no_type"]`), columns `[L["transport"], L["patrols"], L["distance_km"], L["hours"]]` where patrols = distinct `extra__patrol_id`, plus the existing totals row (totals: patrols = distinct patrols overall, not the column sum).

- [ ] **Step 1: Failing test** `test_effort_by_transport`: one patrol with a foot leg (2 km, 1 h) and a truck leg (10 km, 0.5 h) → rows Pedestre (1, 2.0, 1.0), Camioneta (1, 10.0, 0.5), total (1, 12.0, 1.5).
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** the branch.
- [ ] **Step 4: Run** → PASS; suite + mypy green.
- [ ] **Step 5: Commit** `feat(patrol_effort_table): transport grouping from per-leg tracks`.

### Task 5: Template — merged patrol cell

**Files:**
- Modify: `.scripts/build_base_template.py` (personnel section), regenerate `src/ecoscope-workflows-ext-standard-patrol-events/ecoscope_workflows_ext_standard_patrol_events/data/standard_patrol_events.docx`
- Test: `src/ecoscope-workflows-ext-standard-patrol-events/tests/test_template.py`

**Interfaces:**
- Consumes: Task 3's 9 columns (by position).

- [ ] **Step 1: Failing test** `test_personnel_patrol_cell_merges`: render with a 3-row personnel table where rows 1–2 share column-0 text; assert the rendered table XML has `w:vMerge` on the second row's first cell and the patrol text appears once.
- [ ] **Step 2: Run** (`cd src/ecoscope-workflows-ext-standard-patrol-events && PYTHONPATH=. pixi run --manifest-path <ext-custom>/pyproject.toml pytest -q -p no:cacheprovider tests`) → FAIL.
- [ ] **Step 3: Implement**: personnel uses `fixed_table` with widths (cm) `[2.2, 1.0, 1.9, 2.3, 1.0, 1.0, 1.8, 2.4, 3.4]`; column 0 cell text `{% vm %}{{ item.cols[0] }}`; rebuild the docx.
- [ ] **Step 4: Run** → PASS (all template tests).
- [ ] **Step 5: Commit** `feat(template): legs table with merged patrol cell`.

### Task 6: Spec wiring and live check

**Files:**
- Modify: `workflows/standard_patrol_events/spec.yaml`

**Interfaces:**
- Consumes: Tasks 2–4 task names; `get_collection_item` (already used in the spec) to read `no_type` from `labels`.

- [ ] **Step 1: Wire**: add `patrol_segment_id` and `patrol_subject` to `patrol_relocations.relocs_columns`; insert `tracks_per_leg` between `patrol_relocations` and `patrol_tracks`; `tracks_typed.value` = labels' `no_type`; `tracks_layer.tooltip_columns: [extra__patrol_serial_number, extra__patrol_type__display, extra__patrol_subject]`; `personnel.trajectory: ${{ workflow.trajectory.return }}`; add `transport` to the effort grouper's form options (title "Transport (per leg)").
- [ ] **Step 2: Compile**: `make dev` → "Compiled workflow" with no task errors.
- [ ] **Step 3: Live check APN-central** (`make run-dev PARTNER=apncentral PARAMS=/tmp/standard_patrol_events/apncentral_params.yaml`): no error; legs table shows #68 once over 3 rows; map legend has no "-"/"NaN".
- [ ] **Step 4: Live check Belize** (one week: `make run-dev PARTNER=belize_week PARAMS=/tmp/standard_patrol_events/belize_week/params.yaml`): no error; headline equals the pre-change baseline (4 patrols, 225 km, 15 h, 482 events) within ±1% on km and hours.
- [ ] **Step 5: Commit** spec only (`make recompile` before committing the compiled package).

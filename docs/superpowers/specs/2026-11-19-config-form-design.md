# Config form redesign — Standard Patrol & Events

**Date:** 2026-11-19 · **Status:** draft for approval · **Source of truth for the form:** [`2026-11-19-config-form-checkbox.rjsf.json`](2026-11-19-config-form-checkbox.rjsf.json) (hand-written mock, rendered and checked in RJSF; being tested in ecoscope-web)

## 1. Why

The compiled form had grown from the pipeline outwards: internal steps leaked onto the page (`legs_teamed`, `legs_led`, filter overrides), optional fields were marked required, Spatial Scope was a filter where the MRD asks for a grouper, and one "Patrols" choice crammed every patrol setting into a single box. The user (the person at the site who runs the report each month or quarter) could not tell what to fill in.

**Goal:** one short section per decision the user makes, in the order they make them, showing only what applies to their choices.

**Non-goals:** new report outputs; changing how the workflow computes anything except the new groupings in §4; ecoscope-web changes (listed in §6 as requests).

**Anti-goals:** a form that is technically complete but needs a manual to fill in; fields the user must leave alone; options that silently do nothing in the chosen mode.

## 2. The form, top to bottom

Wording is the agreed text. "Blank label" means the field's own label is hidden (single-field sections: the section title says it, and ecoscope-web adds no asterisk). "Hidden when …" is a show/hide rule (§3).

| # | Section | Fields (default) | Description / notes |
|---|---|---|---|
| 1 | **Data Source** | ER connection | core field, unchanged |
| 2 | **Time Range** | since, until, timezone | core field, must stay top-level (ecoscope-web only attaches its date picker to top-level since/until sections) |
| 3 | **Base Maps** | core base-map list | core field, unchanged; placed third as in other workflows |
| 4 | **Patrol Filter** | ☐ Team · ☐ Team Leader · ☐ Single Patrol (all unticked) | "Optional: limit the patrols to one team, team leader or patrol. Leave unticked to include all patrols." Ticking one hides the other two. Team → team names (typed list, "Team names as set in EarthRanger's patrol configuration."). Team Leader → subject group (ER dropdown, "Patrols led by someone in this subject group."). Single Patrol → Patrol ID ("The patrol to analyze, matched against its serial number (the ID shown in EarthRanger)."). Labels of the follow-up fields are blank. |
| 5 | **Patrol Type** | patrol types (empty = all) | "Choose the patrol types to include. Leave it empty to include all of them." ER dropdown, blank label. Hidden when Single Patrol. |
| 6 | **Patrol Effort** | Group By (Patrol Type); Columns (Patrols, Distance (km), Hours) | "Choose how the patrol effort table is grouped and which columns it shows." Group By: Patrol Type · Team · Leader · Individual Patrol · Area (Map Layer). Area → **Map Layer** (ER spatial-feature-group dropdown, "Spatial feature group whose areas (e.g. regions, sectors) become the rows of the table."). Columns: Patrols, Distance (km), Hours, Days With Patrols, Legs, Person-Days, Area Covered (km²); field description "Columns of the patrol effort table." Hidden when Single Patrol. |
| 7 | **Patrol Grouping** | Patrol Type | "Choose how patrol tracks are coloured on the map. Tracks without a team use their leader's name." Options Patrol Type · Team. Blank label. Shown in every mode. |
| 8 | **Events** | ☐ Only events linked to the patrols | "Choose which events to include." Unticked = all events in the time range. Hidden when Single Patrol (a single patrol always uses its linked events). |
| 9 | **Event Type** | event types (empty = all) | "Choose the event types to include. Leave it empty to include all of them." ER dropdown, blank label. Hidden when Single Patrol **or** "Only events linked to the patrols" is ticked. |
| 10 | **Event State** | none (= all states) | Core field and text as in eden/rubeho: "Choose to analyze events with a certain state. If left empty, events of all states will be analyzed". Options New · Active · Resolved · Review. Blank label. |
| 11 | **Event Grouping** | Event Type | "Choose how events are grouped in the tables, charts and map colours." Options Event Type · Event Category. Blank label. |
| 12 | **Event Details** | ☑ Show all fields | Checkbox description: "When ticked, every event is shown with all its details. Untick to choose the fields for each event type." Unticked → repeating rows of **Event Type** (ER dropdown) + **Fields** (typed list, "Field names as on the event form, one per line."), row list description "Add an event type and choose the fields to show for it. Event types you don't add show their first 3 fields." |
| 13 | **Download Event Attachments** | ☐ Skip Photo Attachments; Maximum Images 50 (advanced) | Checkbox: "Event photos are included in the report. Tick to leave them out." Maximum Images: "Used when photos are included." Title and checkbox name match ICMBio/Belize. No "attachments subdirectory" field. |
| 14 | **Report** | Language (English), Title ("Patrol & Events Report"), Subtitle (""), Event Details Introduction ("", "Text shown above the event details.") | "Language and titles of the Word report." Language: English · Español · Português. |
| 15 | **Report Sections** | Headline Figures ☑, Personnel ☐, Patrol Time Density Map ☑, Event Density Map ☑, Events Chart ☑, Events by Month ☐, Events by Category and Priority ☐, Conclusions Box ☑ | "Choose the optional sections to include." MRD core/optional split. |

**Removed from the form:** Spatial Scope (replaced by the Area grouping), the incident storyboard switch, Event Details mode list (now a checkbox), team/leader filter as its own section, the internal `legs_teamed` / `legs_led` / filter-override / event-detail-field settings, the attachments subdirectory, the report template path (one template, set in the spec).

## 3. Show/hide rules

| When | Hidden | Where the rule lives |
|---|---|---|
| Team, Team Leader or Single Patrol ticked | the other two checkboxes | inside Patrol Filter |
| each of those ticked | its own follow-up field shown | inside Patrol Filter |
| Single Patrol ticked | Patrol Type, Patrol Effort, Events, Event Type | form root |
| Only events linked to the patrols ticked | Event Type | form root (nested inside the Single Patrol rule) |
| Group By = Area | Map Layer shown | inside Patrol Effort |
| Show all fields unticked | per-type rows shown | inside Event Details |

Rules on the form root must be **nested**: `if (Single Patrol) … else { …, if (linked only) … else { Event Type } }`. Two sibling root rules, or rules inside a root `allOf`, were ignored by RJSF in testing.

## 4. Workflow changes this needs

- **Settings tasks** that read the new sections and hand the workflow what it uses today (patrol serial, team names, leader group, patrol types, effort grouper and metrics, linked-only, event types, states, grouping, detail tables, image options, report labels and blocks). Defaults on every parameter, because the form only sends the fields of the chosen options.
- **Patrol Filter:** at most one of team / team leader / single patrol; existing tasks `filter_by_teams`, `filter_by_leaders` (by subject id, people only, patrol member groups), `report_time_range` + `filter_patrols_by_serial`.
- **Patrol Effort groupings:** add **Leader** (leg leader name) and **Area** (MRD "patrol effort by management area"). **Area uses ecoscope core's spatial grouping as is (decided):** `SpatialGrouper` over the chosen spatial feature group, resolved with `resolve_spatial_feature_groups_for_spatial_groupers`; `add_spatial_index` classifies the track by area at the boundaries (`Trajectory.apply_spatial_classification`), so distance follows the track; `apportion_legs_by_spatial_index` copies each leg once per area it touched and scales its hours and person-days by that area's share of the track. Effort outside every area goes to core's "None" group, shown in the report as "Outside areas" (localized label). A patrol that touched several areas counts in each, so area rows can add up to more patrols than the Total row; the Total row stays core's ungrouped summary.
- **Event Details per-type tables:** typed field names per event type; types not listed get their first 3 fields. Unknown field names stop the run with the list of valid fields for that type.
- **Event State:** back as a filter (all states when empty).
- **Patrol Grouping:** existing `team_or_leader` + track colour step.
- **Drop:** `get_area_scope` / Spatial Scope wiring; incident storyboard leftovers.

## 5. Approaches considered

| Approach | Trade-off | Decision |
|---|---|---|
| One "Patrols" choice holding every patrol setting | everything hides together, but one crammed box | rejected by the user ("terrible", "chunked") |
| Separate sections, nothing hides | simplest, compiler-ready, but irrelevant sections stay visible for a single patrol | fallback only |
| **Separate sections + form-level show/hide** | matches how the user thinks; needs compiler support (below) | **chosen** |
| Two catalogue workflows (period / single patrol) | simplest forms, double maintenance; MRD describes one workflow | rejected |
| Radio buttons / dropdowns for modes | standard controls, but the user preferred checkboxes | checkboxes chosen; mutually exclusive ones hide each other |

**How the compiled form gets the root rules — decided: wt-compiler change.**
1. **wt-compiler change (chosen):** let `rjsf-overrides` set root-level keys (`if` / `then` / `else`, nested as in §3). Clean; needs the owners' review and a release. *Until it is released* the workflow ships with every section visible (the "nothing hides" fallback): Patrol Type, Patrol Effort, Events and Event Type stay on screen for Single Patrol and are ignored by the workflow in that mode. When the release lands, the root rules go into `rjsf-overrides`; nothing else changes.
2. ~~Post-compile patch in the Makefile~~: rejected; every `make recompile` would have to re-apply it and the next maintainer would not expect it.
Rules *inside* a section already compile today: override the section's whole `properties` object (overrides replace values, they cannot delete keys) and add its `if`/`then`/`else`.

## 6. Constraints found in ecoscope-web / ecoscope-server

- **Asterisks:** ecoscope-web's `FieldTemplate` shows `*` on any field with `oneOf`/`anyOf`, required or not (`required || schema.anyOf || schema.oneOf`). Hide the label (`"ui:options": {"label": false}`) on unlabelled choice fields; labelled ones (Group By, Language) keep it. *Request:* show `*` only when required.
- **Advanced:** ecoscope-web only folds a section's **base** fields marked `ecoscope:advanced`; fields inside an `if`/`then`/`else` branch are never folded.
- **Blank labels:** a field title of `""` makes RJSF show the key name; use `" "` (as core's groupers do).
- **Dropdown lookups** (`EarthRangerEnumResolver`) exist for patrol types, event types, subject groups, spatial feature groups and event-type number/choice fields. None exists for patrol teams, single subjects, or "all fields of an event type" (`event_type_schema_properties` returns the event type itself, works for one event type per form, and only for types with a number field). *Requests:* `patrol_team`, `subject` (people), and an all-fields lookup that follows a per-row `depends_on`.
- **Time Range** must stay a top-level section for the date picker.

## 7. Calls made while writing this up (check these)

- **Single Patrol keeps the Patrol Effort table**, as the report does today: one row for that patrol, grouped by individual patrol with the default columns, followed by its legs table. The Patrol Effort *section* is hidden because there is nothing to choose.
- **Hidden fields keep their old values** (RJSF keeps them), so settings tasks only read a follow-up field when its checkbox or option is chosen (e.g. team names only when Team is ticked).
- **Single Patrol always means linked events only**, whatever the Events checkbox was.
- **Legs without a leader** get the existing "no team"-style label when grouped by Leader.

## 8. Left to the builder

Field keys in the compiled form, the exact settings-task signatures, how `rjsf-overrides` are written per section, test cases (`apncentral`, `apncentral_patrol70`, `belize`, `mep_team`, Los Alerces), and the error wording for invalid team names, leader groups, patrol IDs and field names (follow the existing "… Teams in the period: …" style).

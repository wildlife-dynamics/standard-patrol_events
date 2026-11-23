# wt-compiler proposal: root-level `if` / `then` / `else` and `remove` in `rjsf-overrides`

Status: draft for the wt-compiler maintainers (written against wt-compiler 0.11.2). Nothing has been opened upstream.

## Problem

`standard_patrol_events` has a form where ticking **Single Patrol** must hide four whole sections (Patrol Type,
Patrol Effort, Events, Event Type), and ticking **Only events linked to the patrols** must hide Event Type.
Sections only exist at the form root, so the show/hide rule has to live at the form root too.

`rjsf-overrides` cannot do this today, for two reasons:

1. `ReactJSONSchemaFormOverrides` has only `properties`, `$defs` and `uiSchema`, and
   `ReactJSONSchemaFormConfiguration` has no `if` / `then` / `else`, so a root rule cannot be emitted.
2. Overrides only set values at dotted paths (`_apply_dict_overrides`); they cannot delete a key. The four
   sections are generated into root `properties` from the workflow's tasks, and a section that is also in a rule
   branch would show on screen all the time. They must be removed from root `properties`.

(A root override such as `properties: {patrol_type: {...}}` replaces that one value; it does not drop the key.)

## Why the rule is nested

Tested in RJSF during design (design doc §3): two sibling rules at the root, or rules inside a root `allOf`, are
ignored by RJSF. A single root `if` whose `else` contains the second `if` / `else` works. So the compiler only
needs to pass `if` / `then` / `else` through untouched; the author nests them.

## Proposed change

In `wt_compiler/jsonschema.py`:

- `ReactJSONSchemaFormConfiguration` and `ReactJSONSchemaFormOverrides` get optional `if_`, `then_`, `else_`
  (aliases `if`, `then`, `else`; `dict[str, Any] | None`, default `None`; `populate_by_name=True`).
  `compiler.py` already serialises with `by_alias=True, exclude_none=True`, so unset rules add nothing to
  `rjsf.json`.
- `ReactJSONSchemaFormOverrides` gets `remove: list[str] = []`, dotted paths deleted from `properties` before the
  overrides are applied (`ui:order` is left alone: RJSF takes the names from the rule branches).
- `apply_overrides` passes the three rule fields and the removals through. Overrides replace, never merge, a root
  rule (same semantics as every other override value).

No change to `params.json` (flat schema), the DAG, or the CLI.

### Doctest (in `ReactJSONSchemaFormOverrides.apply_overrides`)

```python
>>> initial = ReactJSONSchemaFormConfiguration(
...     title="Test",
...     properties={"mode": {"type": "object"}, "extra": {"type": "object"}},
...     uiSchema={},
... )
>>> overrides = ReactJSONSchemaFormOverrides(
...     remove=["extra"],
...     **{
...         "if": {"properties": {"mode": {"const": True}}, "required": ["mode"]},
...         "else": {"properties": {"extra": {"type": "object"}}},
...     },
... )
>>> rjsf = overrides.apply_overrides(initial).model_dump(by_alias=True, exclude_none=True)
>>> sorted(rjsf["properties"])
['mode']
>>> rjsf["if"]
{'properties': {'mode': {'const': True}}, 'required': ['mode']}
>>> rjsf["else"]
{'properties': {'extra': {'type': 'object'}}}
>>> "then" in rjsf
False
```

(A throwaway subclass of 0.11.2 with this behaviour was run locally and produces exactly this output shape.)

## The rule this workflow needs

Keys are the real step ids of the compiled form (`patrol_filter`, `event_scope`; the mock's `patrols` / `events`
renamed). The branch contents are copied from the compiled `rjsf.json`, so titles, descriptions, enum resolvers and
the Patrol Effort `if` / `then` (Map Layer) stay as generated. There is no `then`: for a Single Patrol the form
shows nothing extra.

```yaml
rjsf-overrides:
  remove:
  - patrol_type
  - patrol_effort
  - event_scope
  - event_type
  if:
    properties:
      patrol_filter:
        properties:
          single_patrol:
            const: true
        required:
        - single_patrol
    required:
    - patrol_filter
  else:
    properties:
      patrol_type:
        additionalProperties: false
        properties:
          vars:
            title: ' '
            type: array
            uniqueItems: true
            default: []
            description: Choose the patrol types to include. Leave it empty to include all of them.
            items:
              type: string
            ecoscope:transform:
            - transformer: EarthRangerEnumResolver
              transformer_kws:
                type: patrol_type
                depends_on: properties.er_client.properties.data_source.properties.name
        type: object
        required: []
        title: Patrol Type
      patrol_effort:
        additionalProperties: true
        properties:
          group_by:
            title: Group By
            type: string
            default: patrol_type
            oneOf:
            - const: patrol_type
              title: Patrol Type
            - const: team
              title: Team
            - const: leader
              title: Leader
            - const: patrol
              title: Individual Patrol
            - const: area
              title: Area (Map Layer)
          columns:
            title: Columns
            type: array
            uniqueItems: true
            description: Columns of the patrol effort table.
            default:
            - patrol_count
            - total_distance
            - total_duration
            items:
              type: string
              oneOf:
              - const: patrol_count
                title: Patrols
              - const: total_distance
                title: Distance (km)
              - const: total_duration
                title: Hours
              - const: patrol_days
                title: Days With Patrols
              - const: leg_count
                title: Legs
              - const: member_days
                title: Person-Days
              - const: area_covered_merged
                title: "Area Covered (km\xB2)"
        type: object
        required: []
        title: Patrol Effort
        description: Choose how the patrol effort table is grouped and which columns it shows.
        if:
          properties:
            group_by:
              const: area
          required:
          - group_by
        then:
          properties:
            map_layer:
              title: Map Layer
              type: string
              description: Spatial feature group whose areas (e.g. regions, sectors) become the rows of the table.
              ecoscope:transform:
              - transformer: EarthRangerEnumResolver
                transformer_kws:
                  type: spatial_feature_group
                  depends_on: properties.er_client.properties.data_source.properties.name
          required:
          - map_layer
      event_scope:
        additionalProperties: false
        properties:
          linked_only:
            default: false
            title: Only events linked to the patrols
            type: boolean
        type: object
        required: []
        title: Events
        description: Choose which events to include.
    if:
      properties:
        event_scope:
          properties:
            linked_only:
              const: true
          required:
          - linked_only
      required:
      - event_scope
    else:
      properties:
        event_type:
          additionalProperties: false
          properties:
            vars:
              title: ' '
              type: array
              uniqueItems: true
              default: []
              items:
                type: string
              description: Choose the event types to include. Leave it empty to include all of them.
              ecoscope:transform:
              - transformer: EarthRangerEnumResolver
                transformer_kws:
                  type: event_type
                  depends_on: properties.er_client.properties.data_source.properties.name
          type: object
          required: []
          title: Event Type
```

Behaviour:

| Form state | Sections shown from the rule |
|---|---|
| Single Patrol ticked | none (Patrol Type, Patrol Effort, Events, Event Type hidden) |
| Single Patrol not ticked | Patrol Type, Patrol Effort, Events |
| ... and Only events linked ticked | Event Type hidden |
| ... and Only events linked not ticked | Event Type shown |

## Until it is released

The workflow ships with every section visible (design §5 fallback); the settings tasks ignore the hidden sections in
Single Patrol mode. The rule sits commented out in `workflows/standard_patrol_events/spec.yaml` under
`rjsf-overrides`, marked `# needs wt-compiler >= <release with root rules>`. When the release lands: uncomment it,
bump the wt-compiler pin, run `make dev`, and check `tests/test_form.py` against the mock.

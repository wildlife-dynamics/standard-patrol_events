"""The compiled config form (rjsf.json, from spec.yaml's rjsf-overrides) matches the approved mock."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MOCK = ROOT / "docs/superpowers/specs/2026-11-19-config-form-checkbox.rjsf.json"
COMPILED = (
    ROOT / "workflows/standard_patrol_events/ecoscope-workflows-standard-patrol-events-workflow"
    "/ecoscope_workflows_standard_patrol_events_workflow/rjsf.json"
)

# mock section -> step id
SECTIONS = {
    "patrols": "patrol_filter",
    "events": "event_scope",
    "event_state": "state_events",
    "event_details": "event_details_settings",
    "report": "report_text",
    "report_sections": "report_blocks",
}
# (mock section, mock field) -> param name of the generic core task
FIELDS = {
    ("patrol_type", "patrol_types"): "vars",
    ("event_type", "event_types"): "vars",
    ("patrol_grouping", "tracks_color_by"): "var",
    ("event_grouping", "group_by"): "var",
    ("event_state", "event_states"): "states",
}
# option values the workflow reads as column names; the mock uses short names
CONSTS = {
    ("patrol_grouping", "tracks_color_by"): {"team": "patrol_team_name"},
    ("event_grouping", "group_by"): {"event_type": "event_type_display", "event_category": "event_category_display"},
}
FIELD_KEYS = ("title", "description", "default", "ecoscope:advanced", "ecoscope:transform", "oneOf", "items")
RULE_KEYS = ("if", "then", "else", "allOf")


def _mock_sections(mock):
    # sections shown only for all patrols / not linked sit under the root else (Task 12 adds that rule)
    sections, node = {}, mock
    while node:
        sections.update(node.get("properties", {}))
        node = node.get("else")
    return sections


def _expected_field(section, name, field):
    consts = CONSTS.get((section, name))
    if not consts:
        return field
    field = json.loads(json.dumps(field))
    field["default"] = consts.get(field["default"], field["default"])
    for option in field["oneOf"]:
        option["const"] = consts.get(option["const"], option["const"])
    return field


def _mismatches():
    mock, compiled = json.loads(MOCK.read_text()), json.loads(COMPILED.read_text())
    sections, out = _mock_sections(mock), []

    # workflow_details (name/description, not in the mock) stays first
    order = ["workflow_details"] + [SECTIONS.get(k, k) for k in mock["uiSchema"]["ui:order"]]
    if compiled["uiSchema"].get("ui:order") != order:
        out.append(f"ui:order: {compiled['uiSchema'].get('ui:order')} != {order}")
    extra = set(compiled["properties"]) - {SECTIONS.get(k, k) for k in sections} - {"workflow_details"}
    if extra:
        out.append(f"sections not in the mock: {sorted(extra)}")

    for key in mock["uiSchema"]["ui:order"]:
        if key == "*":
            continue
        step, want = SECTIONS.get(key, key), sections[key]
        got = compiled["properties"].get(step)
        if got is None:
            out.append(f"{step}: missing")
            continue
        for k in ("title", "description", *RULE_KEYS):
            if got.get(k) != want.get(k):
                out.append(f"{step}.{k}: {got.get(k)!r} != {want.get(k)!r}")
        names = {FIELDS.get((key, f), f): f for f in want["properties"]}
        if set(got["properties"]) != set(names):
            out.append(f"{step}.properties: {sorted(got['properties'])} != {sorted(names)}")
        for name, mock_name in names.items():
            exp = _expected_field(key, mock_name, want["properties"][mock_name])
            field = got["properties"].get(name, {})
            for k in FIELD_KEYS:
                got_v, want_v = field.get(k), exp.get(k)
                if k == "ecoscope:advanced":  # an override can't delete the key, only set it false
                    got_v, want_v = bool(got_v), bool(want_v)
                if got_v != want_v:
                    out.append(f"{step}.{name}.{k}: {field.get(k)!r} != {exp.get(k)!r}")
        ui = compiled["uiSchema"].get(step, {})
        for k, v in mock["uiSchema"].get(key, {}).items():
            k = FIELDS.get((key, k), k)
            if ui.get(k) != v:
                out.append(f"uiSchema.{step}.{k}: {ui.get(k)!r} != {v!r}")
    return out


def test_compiled_form_matches_mock():
    mismatches = _mismatches()
    assert not mismatches, "\n".join(mismatches)


def test_old_param_keys_rejected():
    import jsonschema
    import pytest

    form = json.loads(COMPILED.read_text())
    schema = {k: form[k] for k in ("properties", "$defs", "additionalProperties") if k in form}
    with pytest.raises(jsonschema.ValidationError, match="Additional properties"):
        jsonschema.validate({"patrol_serial": {"var": "70"}}, schema)

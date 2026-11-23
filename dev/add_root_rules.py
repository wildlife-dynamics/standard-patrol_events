"""Adds the form-root show/hide rules to the compiled rjsf.json (run after every compile).

shortcut: wt-compiler can't emit root if/then/else yet (docs/superpowers/specs/2026-11-19-wt-compiler-root-rules.md);
delete this script and its Makefile/recompile.sh calls once it can, and move the rules into spec.yaml's rjsf-overrides.
Single Patrol hides Patrol Type, Patrol Effort, Events and Event Type; "Only events linked to the patrols" hides
Event Type. Nested on purpose: RJSF ignores sibling root rules and rules inside a root allOf.
"""

import json
import sys


def _ticked(section: str, field: str) -> dict:
    return {"properties": {section: {"properties": {field: {"const": True}}, "required": [field]}}, "required": [section]}


def add_root_rules(form: dict) -> dict:
    props = form["properties"]
    if "if" in form:  # already applied
        return form
    shown = {k: props.pop(k) for k in ("patrol_type", "patrol_effort", "event_scope")}
    event_type = props.pop("event_type")
    form["if"] = _ticked("patrol_filter", "single_patrol")
    form["else"] = {
        "properties": shown,
        "if": _ticked("event_scope", "linked_only"),
        "else": {"properties": {"event_type": event_type}},
    }
    return form


if __name__ == "__main__":
    path = sys.argv[1]
    with open(path) as f:
        form = json.load(f)
    with open(path, "w") as f:
        json.dump(add_root_rules(form), f, indent=2)
        f.write("\n")

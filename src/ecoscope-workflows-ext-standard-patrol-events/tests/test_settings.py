from typing import get_args

import pytest

from ecoscope_workflows_ext_standard_patrol_events.tasks._report import _BLOCKS
from ecoscope_workflows_ext_standard_patrol_events.tasks import (
    effective_event_types,
    effective_map_layer,
    effective_patrol_types,
    EventTypeFields,
    effort_grouper_for,
    pick_setting,
    set_event_details,
    set_event_scope,
    set_patrol_effort,
    set_patrol_filter,
    set_report_text,
)


def test_default_is_no_filter():
    assert set_patrol_filter() == {"patrol_serial": "", "teams": [], "leaders": []}


def test_each_option():
    assert set_patrol_filter(single_patrol=True, patrol_id=" 70 ")["patrol_serial"] == "70"
    assert set_patrol_filter(team=True, teams=["Alpha"])["teams"] == ["Alpha"]
    assert set_patrol_filter(team_leader=True, leaders=["Ana"])["leaders"] == ["Ana"]


def test_unticked_follow_up_fields_ignored():
    out = set_patrol_filter(team=True, teams=["Alpha"], leaders=["Ana"], patrol_id="70")
    assert out == {"patrol_serial": "", "teams": ["Alpha"], "leaders": []}


def test_precedence_single_then_team_then_leader():
    out = set_patrol_filter(
        single_patrol=True, patrol_id="70", team=True, teams=["A"], team_leader=True, leaders=["R"]
    )
    assert out == {"patrol_serial": "70", "teams": [], "leaders": []}
    assert set_patrol_filter(team=True, teams=["A"], team_leader=True, leaders=["R"])["leaders"] == []


def test_patrol_types_ignored_for_single_patrol():
    assert effective_patrol_types(["Foot"], "70") == []
    assert effective_patrol_types(["Foot"], "") == ["Foot"]


def test_single_patrol_needs_an_id():
    for blank in ("", "  "):
        with pytest.raises(ValueError, match="Patrol ID is required for a single patrol."):
            set_patrol_filter(single_patrol=True, patrol_id=blank)


def test_effort_defaults():
    out = set_patrol_effort()
    assert out["grouper"] == "patrol_type" and out["map_layer"] == ""
    assert out["metrics"] == [
        {"metric": "patrol_count"},
        {"metric": "total_distance", "unit": "km"},
        {"metric": "total_duration", "unit": "h"},
    ]


def test_effort_groupers():
    assert set_patrol_effort(group_by="leader")["grouper"] == "patrol_subject"
    assert set_patrol_effort(group_by="area", map_layer="Sectors")["grouper"] == "SpatialGrouper_Sectors"


def test_area_needs_a_map_layer():
    with pytest.raises(ValueError, match="Map Layer"):
        set_patrol_effort(group_by="area")


def test_map_layer_ignored_unless_area():
    assert set_patrol_effort(group_by="team", map_layer="Sectors")["map_layer"] == ""


def test_single_patrol_groups_by_patrol():
    assert effort_grouper_for("patrol_type", "70") == "patrol_serial_number"
    assert effort_grouper_for("patrol_type") == "patrol_type"


def test_event_scope():
    assert set_event_scope() == "all_in_period"
    assert set_event_scope(linked_only=True) == "linked_only"


def test_event_types_ignored_when_linked_or_single():
    assert effective_event_types(["a"], "all_in_period", "") == ["a"]
    assert effective_event_types(["a"], "linked_only", "") == []
    assert effective_event_types(["a"], "all_in_period", "70") == []


def test_report_text_defaults():
    assert set_report_text() == {
        "language": "en",
        "title": "Patrol & Events Report",
        "subtitle": "",
        "details_intro": "",
        "sections": list(get_args(_BLOCKS)),
    }


def test_event_details_default_general():
    assert set_event_details() == {"mode": "general", "detail_fields": {}}


def test_event_details_per_type_mapping():
    out = set_event_details(
        all_details=False,
        tables=[EventTypeFields(event_type="a", fields=["X", "K"]), EventTypeFields(event_type="b")],
    )
    assert out == {"mode": "per_type", "detail_fields": {"a": ["X", "K"], "b": []}}


def test_map_layer_ignored_for_single_patrol():
    assert effective_map_layer("Sectors", "70") == ""
    assert effective_map_layer("Sectors", "") == "Sectors"


def test_pick_setting_is_json_cacheable():
    from wt_task.cache._spec import resolve_task

    assert pick_setting({"a": [1]}, "a") == [1]
    with pytest.raises(KeyError):
        pick_setting({}, "a")
    for f in (pick_setting, set_patrol_effort, set_event_details):
        assert resolve_task(getattr(f, "func", f)).root_codec == "json/v1"


def test_grouping_label_follows_the_chosen_grouping():
    from ecoscope_workflows_ext_standard_patrol_events.tasks import grouping_label

    labels = {"patrol_type": "Tipo de patrullaje", "team": "Equipo", "event_type": "Tipo de evento", "category": "Categoría"}
    assert grouping_label("patrol_type", labels) == "Tipo de patrullaje"
    assert grouping_label("patrol_team_name", labels) == "Equipo"
    assert grouping_label("event_category_display", labels) == "Categoría"
    assert grouping_label("other", labels) == "other"


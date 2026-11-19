from ecoscope_workflows_ext_standard_patrol_events.tasks import effective_patrol_types, set_patrol_filter


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
    out = set_patrol_filter(
        single_patrol=True, patrol_id="70", team=True, teams=["A"], team_leader=True, team_leader_group="R"
    )
    assert out == {"patrol_serial": "70", "teams": [], "leader_group": ""}
    assert set_patrol_filter(team=True, teams=["A"], team_leader=True, team_leader_group="R")["leader_group"] == ""


def test_patrol_types_ignored_for_single_patrol():
    assert effective_patrol_types(["Foot"], "70") == []
    assert effective_patrol_types(["Foot"], "") == ["Foot"]

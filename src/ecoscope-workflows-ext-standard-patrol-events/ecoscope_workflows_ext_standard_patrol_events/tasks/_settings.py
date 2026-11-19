from typing import Annotated

from pydantic import Field
from wt_registry import register


@register()
def set_patrol_filter(
    team: Annotated[bool, Field(title="Team")] = False,
    teams: Annotated[
        list[str], Field(title=" ", description="Team names as set in EarthRanger's patrol configuration.")
    ] = [],  # noqa: B006
    team_leader: Annotated[bool, Field(title="Team Leader")] = False,
    team_leader_group: Annotated[
        str, Field(title=" ", description="Patrols led by someone in this subject group.")
    ] = "",
    single_patrol: Annotated[bool, Field(title="Single Patrol")] = False,
    patrol_id: Annotated[
        str,
        Field(
            title="Patrol ID",
            description="The patrol to analyze, matched against its serial number (the ID shown in EarthRanger).",
        ),
    ] = "",
) -> Annotated[
    dict[str, str | list[str]], Field(description="patrol_serial, teams, leader_group (empty = no filter).")
]:
    """Patrol Filter section. One filter applies: single patrol, else teams, else team leader group."""
    out: dict[str, str | list[str]] = {"patrol_serial": "", "teams": [], "leader_group": ""}
    if single_patrol:
        if not patrol_id.strip():
            raise ValueError("Patrol ID is required for a single patrol.")
        out["patrol_serial"] = patrol_id.strip()
    elif team:
        out["teams"] = list(teams)
    elif team_leader:
        out["leader_group"] = team_leader_group.strip()
    return out


@register()
def effective_patrol_types(
    patrol_types: Annotated[list[str], Field(title="Patrol types")] = [],  # noqa: B006
    patrol_serial: Annotated[str, Field(title="Patrol serial")] = "",
) -> Annotated[
    list[str], Field(description="[] for a single patrol (a stale type must not exclude it), else patrol_types.")
]:
    """Patrol types to filter on."""
    return [] if patrol_serial else list(patrol_types)

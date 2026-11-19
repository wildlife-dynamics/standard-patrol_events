from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field
from wt_contracts import CodecRef
from wt_registry import register

# Plain-JSON returns: lets the wt step cache store them (an untyped return blocks every step downstream).
_JSON = CodecRef("wt_task.cache:JSON")


@register()
def pick_setting(
    collection: Annotated[dict[str, Any], Field(title="Settings")],
    key: Annotated[str, Field(title="Key")],
) -> Annotated[Any, _JSON]:
    """One value of a settings dict (cacheable, unlike core's untyped get_collection_item)."""
    return collection[key]


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


_GROUPERS = {
    "patrol_type": "patrol_type",
    "team": "patrol_team_name",
    "leader": "patrol_subject",
    "patrol": "patrol_serial_number",
}
_UNITS = {"total_distance": "km", "total_duration": "h"}


@register()
def set_patrol_effort(
    group_by: Annotated[
        Literal["patrol_type", "team", "leader", "patrol", "area"], Field(title="Group By")
    ] = "patrol_type",
    map_layer: Annotated[
        str,
        Field(
            title="Map Layer",
            description="Spatial feature group whose areas (e.g. regions, sectors) become the rows of the table.",
        ),
    ] = "",
    columns: Annotated[
        list[
            Literal[
                "patrol_count",
                "total_distance",
                "total_duration",
                "patrol_days",
                "leg_count",
                "member_days",
                "area_covered_merged",
            ]
        ],
        Field(title="Columns", description="Columns of the patrol effort table."),
    ] = ["patrol_count", "total_distance", "total_duration"],  # noqa: B006
) -> Annotated[dict, _JSON, Field(description="grouper, map_layer (empty unless grouping by area), metrics.")]:
    """Patrol Effort section."""
    if group_by == "area":
        if not map_layer.strip():
            raise ValueError("Choose a Map Layer to group patrol effort by area.")
        map_layer = map_layer.strip()
        grouper = f"SpatialGrouper_{map_layer}"
    else:
        map_layer, grouper = "", _GROUPERS[group_by]
    metrics = [{"metric": c, **({"unit": _UNITS[c]} if c in _UNITS else {})} for c in columns]
    return {"grouper": grouper, "map_layer": map_layer, "metrics": metrics}


@register()
def effort_grouper_for(
    grouper: Annotated[str, Field(title="Grouper")],
    patrol_serial: Annotated[str, Field(title="Patrol serial")] = "",
) -> Annotated[str, Field(description="Individual patrol for a single patrol, else grouper.")]:
    """Effort table grouper: a single patrol keeps a one-row table grouped by patrol."""
    return "patrol_serial_number" if patrol_serial else grouper


@register()
def effective_map_layer(
    map_layer: Annotated[str, Field(title="Map layer")] = "",
    patrol_serial: Annotated[str, Field(title="Patrol serial")] = "",
) -> Annotated[str, Field(description="'' for a single patrol (no area apportioning), else map_layer.")]:
    """Map layer for the area grouping."""
    return "" if patrol_serial else map_layer


@register()
def set_event_scope(
    linked_only: Annotated[bool, Field(title="Only events linked to the patrols")] = False,
) -> Annotated[str, Field(description="Value for filter_linked_events.retrieval.")]:
    """Event Scope section."""
    return "linked_only" if linked_only else "all_in_period"


@register()
def effective_event_types(
    event_types: Annotated[list[str], Field(title="Event types")] = [],  # noqa: B006
    retrieval: Annotated[str, Field(title="Retrieval")] = "all_in_period",
    patrol_serial: Annotated[str, Field(title="Patrol serial")] = "",
) -> Annotated[list[str], Field(description="[] when events are linked-only or one patrol, else event_types.")]:
    """Event types to filter on (Event Type is hidden in those two cases)."""
    return [] if retrieval == "linked_only" or patrol_serial else list(event_types)


@register()
def set_report_text(
    language: Annotated[Literal["en", "es", "pt"], Field(title="Language")] = "en",
    title: Annotated[str, Field(title="Title")] = "Patrol & Events Report",
    subtitle: Annotated[str, Field(title="Subtitle")] = "",
    details_intro: Annotated[
        str, Field(title="Event Details Introduction", description="Text shown above the event details.")
    ] = "",
) -> Annotated[dict[str, str], Field(description="language, title, subtitle, details_intro.")]:
    """Report Text section."""
    return {"language": language, "title": title, "subtitle": subtitle, "details_intro": details_intro}


class EventTypeFields(BaseModel):
    event_type: Annotated[str, Field(title="Event Type")]
    fields: Annotated[
        list[str], Field(title="Fields", description="Field names as on the event form, one per line.")
    ] = []  # noqa: B006


@register()
def set_event_details(
    all_details: Annotated[
        bool,
        Field(
            title="Show all fields",
            description=(
                "When ticked, every event is shown with all its details. "
                "Untick to choose the fields for each event type."
            ),
        ),
    ] = True,
    tables: Annotated[
        list[EventTypeFields],
        Field(
            title=" ",
            description=(
                "Add an event type and choose the fields to show for it. "
                "Event types you don't add show their first 3 fields."
            ),
        ),
    ] = [],  # noqa: B006
) -> Annotated[
    dict, _JSON, Field(description="mode ('general' | 'per_type') and detail_fields {event_type: fields}.")
]:
    """Event Details section."""
    return {
        "mode": "general" if all_details else "per_type",
        "detail_fields": {t.event_type: list(t.fields) for t in tables},
    }

"""Shared data for the dashboard and report previews.

Fetches one partner/period from EarthRanger once and caches it, then builds the
report-ready tables with the same core + ext-custom tasks the workflow uses.
Run the previews in the ext-custom env (it has ecoscope + the Part A tasks):

  M=/Users/zak/Documents/w-dynamics/ecoscope-workflow-task-library-spe/src/ecoscope-workflows-ext-custom/pyproject.toml
  pixi run --manifest-path $M python .scripts/preview_dashboard.py costaecuador
"""

import pickle
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
import pandas as pd  # noqa: E402

OUT = Path(__file__).parent / "output"
SINCE, UNTIL = "2026-08-01T00:00:00Z", "2026-11-01T00:00:00Z"
MAX_GAP_SECS = 3600


def _fetch(conn: str) -> dict:
    from ecoscope.base import RelocsCoordinateFilter, TrajSegFilter
    from ecoscope.platform.connections import EarthRangerConnection
    from ecoscope.platform.tasks.io import process_events_details
    from ecoscope.relocations import Relocations
    from ecoscope.trajectory import Trajectory
    from ecoscope_workflows_ext_custom.tasks.io import get_event_type_lookup, get_patrol_team_sources

    er = EarthRangerConnection.from_named_connection(conn).get_client()
    print(f"fetching {conn} from {er.server}", flush=True)
    patrols = er.get_patrols(since=SINCE, until=UNTIL, status=["done"])
    obs = er.get_patrol_observations(patrols_df=patrols, include_patrol_details=True)
    relocs = obs if isinstance(obs, Relocations) else Relocations.from_gdf(getattr(obs, "gdf", obs))
    # same junk-fix filter the workflow uses (null-island / placeholder coords)
    relocs.apply_reloc_filter(RelocsCoordinateFilter(filter_point_coords=[[180, 90], [0, 0], [1, 1]]), inplace=True)
    relocs.remove_filtered(inplace=True)
    traj = Trajectory.from_relocations(relocs)
    traj.apply_traj_filter(TrajSegFilter(max_time_secs=MAX_GAP_SECS, max_speed_kmhr=500), inplace=True)
    traj.remove_filtered(inplace=True)
    events = er.get_events(since=SINCE, until=UNTIL, include_details=True, include_files=True)
    try:
        events = process_events_details(df=events, client=er)
    except Exception as e:  # labels are nice-to-have; raw keys still render
        print(f"process_events_details failed: {e}")
    pt = er.get_patrol_types()
    me = er._get("user/me")
    return {
        "server": er.server,
        "user": f'{me.get("first_name", "")} {me.get("last_name", "")}'.strip(),
        "patrols": patrols,
        "trajectory": traj.gdf,
        "events": events,
        "event_types": get_event_type_lookup(er),
        "patrol_types": dict(zip(pt["value"], pt["display"])),
        "team_sources": get_patrol_team_sources(er),
    }


def load(conn: str, refresh: bool = False) -> dict:
    cache = OUT / "cache" / f"{conn}.pkl"
    if refresh or not cache.exists():
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_bytes(pickle.dumps(_fetch(conn)))
    return pickle.loads(cache.read_bytes())


def build(conn: str, grouper: str = "team", team_groups: list[str] | None = None,
          language: str = "es", refresh: bool = False) -> dict:
    """Everything both previews need, as plain DataFrames/values."""
    from ecoscope_workflows_ext_custom.tasks.analysis import patrol_effort_table
    from ecoscope_workflows_ext_custom.tasks.localization import get_report_labels
    from ecoscope_workflows_ext_custom.tasks.transformation import (
        add_event_display_columns, category_priority_table, event_detail_table,
        event_detail_table_list, events_by_type_table, resolve_patrol_team,
    )

    d = load(conn, refresh)
    labels = get_report_labels(language)
    patrols = resolve_patrol_team(d["patrols"], d["team_sources"], team_groups or [])
    traj = d["trajectory"]
    pid = "extra__patrol_id" if "extra__patrol_id" in traj else "patrol_id"
    traj = traj.merge(patrols[["patrol_id", "patrol_type", "team"]], left_on=pid, right_on="patrol_id", how="left")
    traj["patrol_type_display"] = traj["patrol_type"].map(d["patrol_types"]).fillna(traj["patrol_type"])
    events = add_event_display_columns(d["events"], d["event_types"])
    # placeholder (0,0) locations are device defaults, not real positions — keep the event, drop its point
    g = events.geometry
    events.loc[(g.x.abs() < 1e-6) & (g.y.abs() < 1e-6), "geometry"] = None
    effort = patrol_effort_table(traj, patrols, grouper, labels, d["patrol_types"])
    per_patrol = traj.groupby(pid).agg(km=("dist_meters", "sum"), s=("timespan_seconds", "sum"))
    starts = pd.to_datetime(patrols["start"], utc=True)
    return {
        **d, "labels": labels, "language": language, "patrols_resolved": patrols, "trajectory": traj,
        "events": events, "effort": effort,
        "events_by_type": events_by_type_table(events, labels),
        "category_priority": category_priority_table(events, labels),
        "event_records": event_detail_table(events, labels),
        "event_tables": event_detail_table_list(events, {}, labels),
        "kpis": {
            "patrols": len(patrols),
            "km": per_patrol["km"].sum() / 1000,
            "hours": per_patrol["s"].sum() / 3600,
            "patrol_days": starts.dt.date.nunique(),
            "events": len(events),
            "resolved": int((events["state"] == "resolved").sum()) if len(events) else 0,
        },
    }


if __name__ == "__main__":
    b = build(sys.argv[1] if len(sys.argv) > 1 else "costaecuador", refresh="--refresh" in sys.argv)
    print(b["kpis"])
    print(b["effort"].to_string())

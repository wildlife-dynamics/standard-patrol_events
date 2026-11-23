"""
Standard Patrol & Events - what can each LatAm partner's EarthRanger actually support?

For every MRD block, checks the real data on each partner instance over one window:
  - patrol effort groupers (MRD open question): patrol_type, leader (team/subject), patrol serial
  - tracks available for distance/hours (sampled patrols)
  - events: volume, linked-to-patrol share, state (validated = resolved), category, priority
  - event details populated, attachments (images block)

Writes .scripts/output/partners.json and prints a matrix.

Run with the APN env (recently updated ecoscope):
  cd /Users/zak/Documents/w-dynamics/APN-patrol_event/ecoscope-workflows-patrol-event-workflow
  .pixi/envs/default/bin/python -I <this repo>/.scripts/explore_partners.py [since] [until] [conn ...]
"""

import json
import sys
import warnings
from collections import Counter
from pathlib import Path

warnings.filterwarnings("ignore")
from ecoscope.platform.connections import EarthRangerConnection  # noqa: E402

SINCE = sys.argv[1] if len(sys.argv) > 1 else "2026-08-01T00:00:00Z"
UNTIL = sys.argv[2] if len(sys.argv) > 2 else "2026-11-01T00:00:00Z"
PARTNERS = sys.argv[3:] or [
    "apn", "apncentral", "apnelpalmar", "apniguazu", "apnlosglaciares",
    "costaecuador", "galapagos", "icf", "parnaiguacu", "mmarn",
]
TRACK_SAMPLE = 10
OUT = Path(__file__).parent / "output"


def pct(n, d):
    return round(100 * n / d) if d else 0


def explore(name):
    er = EarthRangerConnection.from_named_connection(name).get_client()
    r = {"server": er.server}

    pt = er.get_patrol_types()
    r["patrol_types"] = int(pt["is_active"].sum())
    et = er.get_event_types()
    r["event_types"] = int(et["is_active"].sum())
    r["event_categories"] = sorted({c["display"] for c in et["category"] if isinstance(c, dict)})

    patrols = er.get_patrols(since=SINCE, until=UNTIL, status=["done"])
    r["patrols"] = len(patrols)
    segs = [s for ss in patrols.get("patrol_segments", []) for s in ss]
    r["segments"] = len(segs)
    leaders = [s["leader"] for s in segs if s.get("leader")]
    r["grouper_patrol_type_pct"] = pct(sum(bool(s.get("patrol_type")) for s in segs), len(segs))
    r["grouper_leader_pct"] = pct(len(leaders), len(segs))
    r["leader_subject_types"] = dict(Counter(f'{l.get("subject_type")}/{l.get("subject_subtype")}' for l in leaders))
    r["distinct_leaders"] = len({l["id"] for l in leaders})
    r["patrol_types_used"] = dict(Counter(s.get("patrol_type") for s in segs).most_common(8))
    r["patrol_has_title_pct"] = pct(patrols["title"].notna().sum() if len(patrols) else 0, len(patrols))
    r["patrol_events_linked"] = sum(len(s.get("events") or []) for s in segs)

    # tracks: sample a few patrols, does every patrol have observations?
    if len(patrols):
        obs = er.get_patrol_observations(patrols_df=patrols.head(TRACK_SAMPLE), include_patrol_details=True)
        gdf = getattr(obs, "gdf", obs)
        r["track_sample_patrols_with_obs"] = f'{gdf["patrol_id"].nunique() if len(gdf) else 0}/{min(TRACK_SAMPLE, len(patrols))}'

    ev = er.get_events(since=SINCE, until=UNTIL, include_details=True, include_files=True)
    r["events"] = len(ev)
    if len(ev):
        r["events_on_patrol_pct"] = pct(ev["patrol_segments"].map(lambda x: bool(len(x) if x is not None else 0)).sum(), len(ev))
        r["event_states"] = dict(Counter(ev["state"]))
        r["event_categories_used"] = dict(Counter(ev["event_category"]).most_common(10))
        r["event_priorities"] = dict(Counter(ev["priority_label"]))
        r["event_details_populated_pct"] = pct(ev["event_details"].map(bool).sum(), len(ev))
        files = ev["files"] if "files" in ev else []
        r["events_with_files_pct"] = pct(sum(bool(f) for f in files), len(ev))
        r["images_total"] = sum(len(f or []) for f in files)
        r["top_event_types"] = dict(Counter(ev["event_type"]).most_common(8))
    return r


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    results = {}
    for p in PARTNERS:
        print(f"... {p}", flush=True)
        try:
            results[p] = explore(p)
        except Exception as e:  # one broken account must not stop the sweep
            results[p] = {"error": f"{type(e).__name__}: {e}"[:300]}
    (OUT / "partners.json").write_text(json.dumps({"since": SINCE, "until": UNTIL, "partners": results}, indent=2, default=str))

    cols = ["patrols", "segments", "grouper_patrol_type_pct", "grouper_leader_pct", "distinct_leaders",
            "track_sample_patrols_with_obs", "events", "events_on_patrol_pct", "event_details_populated_pct",
            "events_with_files_pct", "images_total"]
    print(f"\nWindow {SINCE} -> {UNTIL}\n" + "partner".ljust(16) + " ".join(c[:10].rjust(10) for c in cols))
    for p, r in results.items():
        print(p.ljust(16) + (r["error"][:120] if "error" in r else " ".join(str(r.get(c, "-")).rjust(10) for c in cols)))
    print(f"\nFull detail: {OUT / 'partners.json'}")

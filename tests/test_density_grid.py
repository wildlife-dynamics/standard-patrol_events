"""Density grids must stay small for any site extent, and fine enough to read. A fixed 2 km
cell made APN (stray 0,0 points) build 10M cells and mep (US..Kenya) 33M cells; core's
auto-scale over a country-wide site (APN Central) made ~113 km cells. Both maps now use one
cell size taken from the typical patrol, with cells only where the data is.
Runs only where the task package is installed (importorskip)."""

import re
from pathlib import Path

import pytest

pytest.importorskip("ecoscope_workflows_ext_standard_patrol_events")

import geopandas as gpd  # noqa: E402
from ecoscope_workflows_ext_standard_patrol_events.tasks.analysis import (  # noqa: E402
    cells_covering,
    density_cell_size,
)
from shapely.geometry import LineString, Point  # noqa: E402

SPEC = Path(__file__).parents[1] / "spec.yaml"


def test_both_density_maps_share_one_cell_size():
    spec = SPEC.read_text()
    assert len(re.findall(r"task: cells_covering", spec)) == 2
    assert len(re.findall(r"cell_size_m: \$\{\{ workflow\.grid_size\.return \}\}", spec)) == 4  # 2 grids, 2 legends
    assert "create_meshgrid" not in spec  # never core's auto-scale over the whole extent


@pytest.mark.parametrize("extra", [
    [],                                      # one park (APN)
    [(-65.20, -22.90), (-65.16, -22.86)],    # plus a park 2,200 km away (APN Central)
    [(0.0, 0.0), (0.001, 0.001)],            # plus a stray 0,0 track
])  # fmt: skip
def test_grid_is_fine_and_bounded_for_any_extent(extra):
    lines = [[(-71.80, -42.80), (-71.75, -42.76)]] + ([extra] if extra else [])
    tracks = gpd.GeoDataFrame(
        {"extra__patrol_id": [f"p{i}" for i in range(len(lines))]},
        geometry=[LineString(pts) for pts in lines],
        crs=4326,
    )
    size = density_cell_size(tracks)
    cells = cells_covering(tracks, size)
    assert size <= 500 and 10 < len(cells) < 50_000
    events = gpd.GeoDataFrame(geometry=[Point(p) for p in lines[0] + extra], crs=4326)
    assert len(cells_covering(events, size)) <= len(lines[0] + extra)

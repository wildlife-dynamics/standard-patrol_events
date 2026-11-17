"""Density grids must stay small for any site extent. A fixed 2 km cell made
APN (stray 0,0 points) build 10M cells and mep (US..Kenya) 33M cells: hours of CPU.
Runs only in the ext-custom env (importorskip), like test_template."""

import re
from pathlib import Path

import pytest

pytest.importorskip("ecoscope")

import geopandas as gpd  # noqa: E402
from ecoscope.platform.tasks.analysis import create_meshgrid  # noqa: E402
from wt_task import task  # noqa: E402
from shapely.geometry import Point  # noqa: E402

SPEC = Path(__file__).parents[3] / "workflows/standard_patrol_events/spec.yaml"


def test_spec_meshgrids_auto_scale():
    sizes = re.findall(r"auto_scale_or_custom_cell_size: (.*)", SPEC.read_text())
    assert len(sizes) == 2 and all("Auto-scale" in s for s in sizes), sizes


@pytest.mark.parametrize("points", [
    [(-71.9, -43.1), (-71.5, -42.6)],  # one park (APN)
    [(-124.7, 48.1), (57.5, -4.1)],    # worldwide dev site (mep)
    [(-71.9, -43.1), (0.0, 0.0)],      # park plus a stray 0,0 point
])
def test_auto_scale_grid_is_bounded(points):
    aoi = gpd.GeoDataFrame(geometry=[Point(p) for p in points], crs=4326)
    grid = task(create_meshgrid).validate().call(aoi=aoi, auto_scale_or_custom_cell_size={"auto_scale_or_custom": "Auto-scale"})
    assert 100 < len(grid) < 50_000

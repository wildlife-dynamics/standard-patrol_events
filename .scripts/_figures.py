"""Maps and charts shared by the dashboard and report previews, drawn with the
core ecoscope tasks the spec wires. static=False → interactive (dashboard),
static=True → print-ready (report; create_docx screenshots the HTML)."""

from pathlib import Path

import pandas as pd
from ecoscope.platform.tasks.analysis import calculate_feature_density, calculate_linear_time_density, create_meshgrid
from ecoscope.platform.tasks.results import (
    create_path_layer, create_polygon_layer_pydeck, create_scatterplot_layer, draw_bar_chart,
    draw_map, draw_time_series_bar_chart, set_base_maps, view_state_from_layers,
)
from ecoscope.platform.tasks.transformation import apply_classification, apply_color_map
from wt_task import task


def run(fn, **kw):
    """Call a task the way the workflow runtime does (pydantic-validated args)."""
    return task(fn).validate().call(**kw)


def figures(b: dict, outdir: Path, static: bool, group_by: str = "event_type_display") -> dict[str, str]:
    outdir.mkdir(parents=True, exist_ok=True)
    tiles = run(set_base_maps)

    def save(name, content):
        path = outdir / f"{name}.html"
        path.write_text(content)
        return str(path)

    def a_map(name, layers):
        return save(name, run(draw_map, geo_layers=layers, tile_layers=tiles, static=static, title=None,
                              legend_style={"placement": "bottom-right"},
                              view_state=run(view_state_from_layers, layers=layers)))

    def density(name, gdf, col, legend_title):
        gdf = run(apply_color_map, df=gdf.to_crs(4326), input_column_name=col, colormap="RdYlGn_r",
                  output_column_name="fill")
        layer = run(create_polygon_layer_pydeck, geodataframe=gdf, layer_style={"get_fill_color": "fill", "opacity": 0.6},
                    legend={"title": legend_title, "label_column": col, "color_column": "fill"})
        return a_map(name, [layer])

    traj = b["trajectory"].dropna(subset=["geometry"])
    ev = b["events"]
    pts = ev[["serial_number", group_by, "geometry"]].dropna(subset=["geometry"])
    pts = run(apply_color_map, df=pts, input_column_name=group_by, colormap="tab20", output_column_name="c")
    tr = run(apply_color_map, df=traj[["patrol_type_display", "geometry"]], input_column_name="patrol_type_display",
             colormap="tab10", output_column_name="c")
    tracks = run(create_path_layer, geodataframe=tr, layer_style={"get_color": "c", "get_width": 2},
                 legend={"label_column": "patrol_type_display", "color_column": "c"})
    points = run(create_scatterplot_layer, geodataframe=pts, layer_style={"get_fill_color": "c", "get_radius": 5},
                 legend={"label_column": group_by, "color_column": "c"},
                 tooltip_columns=["serial_number", group_by])
    out = {"tracks_map": a_map("tracks_map", [tracks, points])}

    grid = run(create_meshgrid, aoi=traj.to_crs(3857), intersecting_only=False)
    td = run(calculate_linear_time_density, trajectory_gdf=traj.to_crs(3857), meshgrid=grid).dropna(subset=["percentile"])
    out["time_density_map"] = density("time_density_map", td, "percentile", "% time")
    egrid = run(create_meshgrid, aoi=pts.to_crs(3857), intersecting_only=False,
                auto_scale_or_custom_cell_size={"auto_scale_or_custom": "Customize", "grid_cell_size": 2000})
    ed = run(calculate_feature_density, geodataframe=pts.to_crs(3857), meshgrid=egrid, geometry_type="point")
    ed = ed[ed["density"] > 0].sort_values("density")
    # ordered classes, as ops-dashboard does (raw counts as categories give a scrambled legend)
    ed = run(apply_classification, df=ed, input_column_name="density", output_column_name="density_bins",
             classification_options={"scheme": "equal_interval", "k": 5},
             label_options={"label_ranges": True, "label_decimals": 0})
    out["event_density_map"] = density("event_density_map", ed, "density_bins", "Events")

    out["events_bar"] = save("events_bar", run(
        draw_bar_chart, dataframe=ev[["serial_number", group_by]], category=group_by,
        bar_chart_configs=[{"column": "serial_number", "agg_func": "count", "label": b["labels"]["count"]}]))
    out["monthly"] = save("monthly", run(
        draw_time_series_bar_chart,
        dataframe=ev[["time", "serial_number", group_by]].assign(time=pd.to_datetime(ev["time"])),
        x_axis="time", y_axis="serial_number", category=group_by, agg_function="count", time_interval="month"))
    return out

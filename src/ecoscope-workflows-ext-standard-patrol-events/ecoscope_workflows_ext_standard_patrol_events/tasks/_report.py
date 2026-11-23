from importlib.resources import as_file, files
from pathlib import Path
from typing import Annotated, Literal, get_args

from ecoscope.platform.annotations import AdvancedField
from pydantic import Field
from wt_registry import register

# Templates shipped in data/. Language is not a template choice: every heading comes from
# get_report_labels(language). A partner that needs its own layout adds a file here.
ReportTemplate = Literal["standard"]
_FILES = {"standard": "standard_patrol_events.docx"}


@register()
def load_report_template(
    template: Annotated[
        ReportTemplate, Field(title="Report template", description="Report layout.")
    ] = "standard",
) -> Annotated[str, Field(description="Local path to the packaged .docx template.")]:
    """Return the local path of a template shipped with this package (no runtime download)."""
    resource = files("ecoscope_workflows_ext_standard_patrol_events") / "data" / _FILES[template]
    with as_file(resource) as path:
        local = Path(path)
    if not local.is_file():
        raise FileNotFoundError(f"Packaged template is missing: {local}")
    return str(local.resolve())


_BLOCKS = Literal[
    "headline_stats",
    "personnel",
    "time_density",
    "event_density",
    "events_chart",
    "monthly_chart",
    "category_priority",
    "conclusions",
]


DEFAULT_BLOCKS = get_args(_BLOCKS)


@register()
def set_report_blocks(
    sections: Annotated[list[_BLOCKS], Field(title="Report Sections")] = list(DEFAULT_BLOCKS),
) -> Annotated[dict[str, str], Field(description="show_<block> template switches as 'true'/'false'.")]:
    """Optional report blocks, as template switches (docx context values are strings)."""
    switches = {f"show_{b}": str(b in sections).lower() for b in get_args(_BLOCKS)}
    # Photos are switched off by Leave Out Event Photos (captions stay), not here.
    return {**switches, "show_images": "true"}


@register()
def set_images_options(
    skip_download: Annotated[
        bool,
        Field(
            title="Leave Out Event Photos",
            description="Event photos are included in the report. Tick to leave them out.",
        ),
    ] = False,
    max_images: Annotated[
        int, AdvancedField(default=50, title="Maximum Images", description="Used when photos are included.", ge=0)
    ] = 50,
) -> Annotated[dict[str, bool | int], Field(description="list_only (no download) and max_images for the image tasks.")]:
    """Images block options; skipping lists the photos (captions) without downloading them."""
    return {"list_only": skip_download, "max_images": max_images}

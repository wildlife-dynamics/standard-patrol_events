from importlib.resources import as_file, files
from pathlib import Path
from typing import Annotated, Literal

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


@register()
def set_report_blocks(
    headline_stats: Annotated[bool, Field(title="Headline Figures")] = True,
    personnel: Annotated[bool, Field(title="Personnel")] = False,
    time_density: Annotated[bool, Field(title="Patrol Time Density Map")] = True,
    event_density: Annotated[bool, Field(title="Event Density Map")] = True,
    events_chart: Annotated[bool, Field(title="Events Chart")] = True,
    monthly_chart: Annotated[bool, Field(title="Events by Month")] = False,
    category_priority: Annotated[bool, Field(title="Events by Category and Priority")] = False,
    conclusions: Annotated[bool, Field(title="Conclusions Box")] = True,
) -> Annotated[dict[str, str], Field(description="show_<block> template switches as 'true'/'false'.")]:
    """Optional report blocks, as template switches (docx context values are strings)."""
    switches = {f"show_{k}": str(v).lower() for k, v in locals().items()}
    # Photos are switched off by Skip Photo Attachments (captions stay), not here.
    return {**switches, "show_images": "true"}


@register()
def set_images_options(
    skip_download: Annotated[
        bool,
        Field(
            title="Skip Photo Attachments",
            description="Event photos are included in the report. Tick to leave them out.",
        ),
    ] = False,
    max_images: Annotated[
        int, AdvancedField(default=50, title="Maximum Images", description="Used when photos are included.", ge=0)
    ] = 50,
) -> Annotated[dict[str, bool | int], Field(description="list_only (no download) and max_images for the image tasks.")]:
    """Images block options; skipping lists the photos (captions) without downloading them."""
    return {"list_only": skip_download, "max_images": max_images}

from importlib.resources import as_file, files
from pathlib import Path
from typing import Annotated, Literal

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
    personnel: Annotated[bool, Field(title="Personnel", description="Patrol personnel (sites with patrol attributes).")] = False,
    headline_stats: Annotated[bool, Field(title="Headline stats")] = True,
    time_density: Annotated[bool, Field(title="Patrol time density map")] = True,
    event_density: Annotated[bool, Field(title="Event density map")] = True,
    events_chart: Annotated[bool, Field(title="Events chart")] = True,
    monthly_chart: Annotated[bool, Field(title="Events by month chart")] = False,
    category_priority: Annotated[bool, Field(title="Events by category and priority")] = False,
    incidents: Annotated[bool, Field(title="Incident storyboard", description="Incidents (collection events) in the period with their events.")] = False,
    images: Annotated[bool, Field(title="Images")] = True,
    conclusions: Annotated[bool, Field(title="Conclusions box")] = True,
) -> Annotated[dict[str, str], Field(description="show_<block> template switches as 'true'/'false'.")]:
    """Optional report blocks, as template switches (docx context values are strings)."""
    return {f"show_{k}": str(v).lower() for k, v in locals().items()}


@register()
def set_images_options(
    mode: Annotated[
        Literal["attachments", "blank"],
        Field(title="Images", description="Fill from event attachments, or leave the photo cells blank to add by hand."),
    ] = "attachments",
    max_images: Annotated[int, Field(title="Maximum number of images", ge=0)] = 50,
) -> Annotated[dict[str, bool | int], Field(description="list_only (no download) and max_images for the image tasks.")]:
    """Images block options; 'blank' lists the photos (captions) without downloading them."""
    return {"list_only": mode == "blank", "max_images": max_images}

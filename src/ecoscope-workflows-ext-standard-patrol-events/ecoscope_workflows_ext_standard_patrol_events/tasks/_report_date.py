from datetime import datetime, timedelta, timezone
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field
from wt_registry import register


class _Timezone(BaseModel):
    # Reads core's TimezoneInfo by attribute, so this package needs no ecoscope import.
    model_config = ConfigDict(from_attributes=True)

    utc_offset: str  # e.g. "-05:00"


@register()
def get_report_date(
    timezone_info: Annotated[_Timezone, Field(description="The report timezone (get_timezone_from_time_range).")],
) -> Annotated[str, Field(description="Today's date in that timezone, as YYYY-MM-DD.")]:
    """Return the date the report is generated, in the report's timezone."""
    tz = _Timezone.model_validate(timezone_info, from_attributes=True)
    sign = -1 if tz.utc_offset.startswith("-") else 1
    hours, minutes = map(int, tz.utc_offset.lstrip("+-").split(":"))
    offset = timezone(sign * timedelta(hours=hours, minutes=minutes))
    return datetime.now(offset).strftime("%Y-%m-%d")

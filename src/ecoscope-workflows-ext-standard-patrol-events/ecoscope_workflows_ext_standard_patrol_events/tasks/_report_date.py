from datetime import date, datetime, timedelta, timezone
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field
from wt_registry import register

_Labels = Annotated[dict[str, str], Field(description="Report labels (get_report_labels); months_short is used.")]


class _Timezone(BaseModel):
    # Reads core's TimezoneInfo by attribute, so this package needs no ecoscope import.
    model_config = ConfigDict(from_attributes=True)

    utc_offset: str  # e.g. "-05:00"


class _TimeRange(BaseModel):
    # Reads core's TimeRange by attribute (since/until as entered in the form).
    model_config = ConfigDict(from_attributes=True)

    since: datetime
    until: datetime


def _day(d: date, labels: dict[str, str]) -> str:
    """'06 nov 2026': month names from the report language, not the system locale (which a
    workflow container may not have)."""
    return f"{d.day:02d} {labels['months_short'].split(',')[d.month - 1]} {d.year}"


@register()
def get_report_date(
    timezone_info: Annotated[_Timezone, Field(description="The report timezone (get_timezone_from_time_range).")],
    labels: _Labels,
) -> Annotated[str, Field(description="Today's date in that timezone, e.g. '18 nov 2026'.")]:
    """Return the date the report is generated, in the report's timezone."""
    tz = _Timezone.model_validate(timezone_info, from_attributes=True)
    sign = -1 if tz.utc_offset.startswith("-") else 1
    hours, minutes = map(int, tz.utc_offset.lstrip("+-").split(":"))
    offset = timezone(sign * timedelta(hours=hours, minutes=minutes))
    return _day(datetime.now(offset).date(), labels)


@register()
def get_report_period(
    time_range: Annotated[_TimeRange, Field(description="The report period (set_time_range).")],
    labels: _Labels,
) -> Annotated[str, Field(description="The period, e.g. '01 ene 2026 – 18 nov 2026'.")]:
    """Return the report period as entered, in the same day format as the report date."""
    tr = _TimeRange.model_validate(time_range, from_attributes=True)
    return f"{_day(tr.since.date(), labels)} – {_day(tr.until.date(), labels)}"

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from ecoscope_workflows_ext_standard_patrol_events.tasks import get_report_date


def test_report_date_is_today_in_the_given_offset():
    # +14:00 and -12:00 are a day apart for most of the day, so the offset must be applied.
    for offset, hours in (("+14:00", 14), ("-12:00", -12)):
        tz = timezone(timedelta(hours=hours))
        before = datetime.now(tz).strftime("%Y-%m-%d")
        got = get_report_date(SimpleNamespace(utc_offset=offset))
        after = datetime.now(tz).strftime("%Y-%m-%d")
        assert got in (before, after)

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from ecoscope_workflows_ext_standard_patrol_events.tasks import get_report_date


def test_report_date_is_today_in_the_given_offset():
    # +14:00 and -12:00 are a day apart for most of the day, so the offset must be applied.
    for offset, hours in (("+14:00", 14), ("-12:00", -12)):
        tz = timezone(timedelta(hours=hours))
        before = datetime.now(tz).strftime("%d %m %Y")
        got = get_report_date(SimpleNamespace(utc_offset=offset), {"months_short": ",".join(f"{m:02d}" for m in range(1, 13))})
        after = datetime.now(tz).strftime("%d %m %Y")
        assert got in (before, after)


ES = {"months_short": "ene,feb,mar,abr,may,jun,jul,ago,sep,oct,nov,dic"}


def test_report_date_short_month_in_report_language():
    got = get_report_date(SimpleNamespace(utc_offset="+00:00"), ES)
    day, month, year = got.split(" ")
    assert len(day) == 2 and month in ES["months_short"].split(",") and len(year) == 4


def test_period_as_entered_short_months():
    from ecoscope_workflows_ext_standard_patrol_events.tasks import get_report_period

    tr = SimpleNamespace(since=datetime(2026, 1, 1), until=datetime(2026, 11, 18))
    assert get_report_period(tr, ES) == "01 ene 2026 – 18 nov 2026"

from typing import get_args

import pytest

from ecoscope_workflows_ext_standard_patrol_events.tasks import (
    load_partner_profile,
    load_partner_template,
    resolve_report_options,
)
from ecoscope_workflows_ext_standard_patrol_events.tasks._profiles import BLOCK_KEYS, Partner


@pytest.mark.parametrize("partner", get_args(Partner))
def test_every_partner_profile_validates(partner):
    profile = load_partner_profile(partner)
    assert set(profile["blocks"]) == set(BLOCK_KEYS)
    assert profile["max_gap_secs"] == 3600


@pytest.mark.xfail(strict=False, reason="template added in B2")
@pytest.mark.parametrize("partner", get_args(Partner))
def test_every_partner_profile_loads(partner):
    load_partner_profile(partner)
    assert load_partner_template(partner).endswith("standard_patrol_events.docx")


def test_override_beats_profile():
    profile = load_partner_profile("icf")
    assert profile["grouper"] == "patrol_type"
    assert resolve_report_options(profile, grouper="team")["grouper"] == "team"


def test_none_override_keeps_profile():
    profile = load_partner_profile("icf")
    assert resolve_report_options(profile) == profile


def test_unknown_partner_raises():
    with pytest.raises(ValueError):
        load_partner_profile("nope")

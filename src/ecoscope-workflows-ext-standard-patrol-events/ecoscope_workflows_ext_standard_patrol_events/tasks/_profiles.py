from importlib.resources import as_file, files
from pathlib import Path
from typing import Annotated, Literal, get_args

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator
from wt_registry import register

Partner = Literal["apn", "costaecuador", "galapagos", "icf", "parnaiguacu", "mep"]

BLOCK_KEYS = (
    "personnel",
    "headline_stats",
    "time_density",
    "events_by_type",
    "category_priority",
    "events_bar",
    "monthly_stacked",
    "conclusions",
)


class PartnerProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_types: list[str]  # [] = all event types
    event_scope: Literal["area", "patrol"]
    validated_states: list[str]
    team_groups: list[str]
    max_gap_secs: int = 3600
    detail_fields: dict[str, list[str]]
    max_images: int
    language: Literal["en", "es", "pt"]
    template: str
    blocks: dict[str, bool]
    grouper: Literal["patrol_type", "team", "individual_patrol"]
    validated_only: bool
    detail_mode: Literal["per_type", "generic"]
    images: Literal["auto", "blank"]

    @field_validator("blocks")
    @classmethod
    def _block_keys(cls, v: dict[str, bool]) -> dict[str, bool]:
        if set(v) != set(BLOCK_KEYS):
            raise ValueError(f"blocks keys must be exactly {BLOCK_KEYS}, got {tuple(v)}")
        return v


def _data_file(name: str) -> Path:
    # Installed packages are plain folders, so as_file yields the real file path.
    with as_file(files("ecoscope_workflows_ext_standard_patrol_events") / "data" / name) as path:
        return Path(path).resolve()


@register()
def load_partner_profile(
    partner: Annotated[Partner, Field(description="The partner whose report profile to load.")],
) -> Annotated[dict, Field(description="The validated partner profile.")]:
    """Load and validate a partner's report profile shipped with this package."""
    if partner not in get_args(Partner):
        raise ValueError(f"Unknown partner {partner!r}. Available: {', '.join(get_args(Partner))}")
    return PartnerProfile(**yaml.safe_load(_data_file(f"{partner}.yaml").read_text())).model_dump()


@register()
def load_partner_template(
    partner: Annotated[Partner, Field(description="The partner whose Word template to load.")],
) -> Annotated[str, Field(description="Local path to the partner's Word template.")]:
    """Return the local path of the partner's packaged Word template."""
    local = _data_file(load_partner_profile(partner)["template"])
    if not local.is_file():
        raise FileNotFoundError(f"Packaged template is missing: {local}")
    return str(local)


@register()
def resolve_report_options(
    profile: Annotated[dict, Field(description="A partner profile.")],
    grouper: Annotated[str | None, Field(description="Override the profile grouper.")] = None,
    validated_only: Annotated[bool | None, Field(description="Override validated-only.")] = None,
    detail_mode: Annotated[str | None, Field(description="Override the detail mode.")] = None,
    images: Annotated[str | None, Field(description="Override the images mode.")] = None,
) -> Annotated[dict, Field(description="The profile with run-time overrides applied.")]:
    """Apply the non-None run-time form values on top of the profile."""
    overrides = dict(grouper=grouper, validated_only=validated_only, detail_mode=detail_mode, images=images)
    return {**profile, **{k: v for k, v in overrides.items() if v is not None}}

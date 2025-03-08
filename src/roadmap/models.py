import typing as t

from datetime import date
from enum import StrEnum

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field


class Meta(BaseModel):
    count: int
    total: int | None = None


class LifecycleType(StrEnum):
    mainline = "mainline"
    eus = "EUS"
    els = "ELS"
    e4s = "E4S"
    aus = "AUS"


class SupportStatus(StrEnum):
    supported = "Supported"
    six_months = "Support ends within 6 months"
    retired = "Retired"
    not_installed = "Not installed"
    upcoming = "Upcoming"


class HostCount(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    major: int
    minor: int | None = None
    lifecycle: LifecycleType


class System(BaseModel):
    name: str
    major: int
    minor: int | None = None
    release_date: date | t.Literal["Unknown"] | None
    retirement_date: date | t.Literal["Unknown"] | None
    support_status: SupportStatus = SupportStatus.supported
    count: int = 0
    lifecycle_type: LifecycleType


class Lifecycle(BaseModel):
    name: str
    start: date
    end: date


class RHELLifecycle(Lifecycle):
    name: str = "RHEL"
    major: int
    minor: int | None = None
    end_e4s: date | None = None
    end_els: date | None = None
    end_eus: date | None = None
    end_aus: date | None = None


class ReleaseModel(BaseModel):
    major: int = Field(gt=8, le=10, description="Major version number, e.g., 7 in version 7.0")
    minor: int = Field(ge=0, le=100, description="Minor version number, e.g., 0 in version 7.0")


class TaggedParagraph(BaseModel):
    title: str = Field(description="The paragraph title")
    text: str = Field(description="The paragraph text")
    tag: str = Field(description="The paragraph htmltag")

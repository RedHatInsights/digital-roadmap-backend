import typing as t

from datetime import date
from datetime import timedelta
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import model_validator


class Meta(BaseModel):
    count: int
    total: int | None = None


class LifecycleType(StrEnum):
    mainline = "mainline"
    eus = "EUS"
    els = "ELS"
    e4s = "E4S"


class SupportStatus(StrEnum):
    supported = "Supported"
    near_retirement = "Near retirement"
    retired = "Retired"
    not_installed = "Not installed"
    upcoming = "Upcoming release"
    unknown = "Unknown"


class HostCount(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    major: int
    minor: int | None = None
    lifecycle: LifecycleType


class Lifecycle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    start_date: date
    end_date: date
    support_status: SupportStatus = SupportStatus.unknown

    @model_validator(mode="after")
    def update_support_status(self):
        """Validator for setting support status.
        Expected types/values of start_date and end_date are:
            - str(Unknown)
            - None
            - date(YYYY-MM-DD)
        """
        today = date.today()
        self.support_status = _calculate_support_status(
            start_date=self.start_date,
            end_date=self.end_date,
            current_date=today,
            months=3,
        )

        return self


class System(Lifecycle):
    name: str
    display_name: str = ""
    major: int
    minor: int | None = None
    start_date: date | t.Literal["Unknown"] | None
    end_date: date | t.Literal["Unknown"] | None
    count: int = 0
    lifecycle_type: LifecycleType
    related: bool = False
    systems: set[UUID] = set()

    @model_validator(mode="after")
    def set_display_name(self):
        if not self.display_name:
            self.display_name = _get_rhel_display_name(self.name, self.major, self.minor)

        return self


class RHELLifecycle(Lifecycle):
    name: str = "RHEL"
    display_name: str = ""
    major: int
    minor: int | None = None
    end_date_e4s: date | None = None
    end_date_els: date | None = None
    end_date_eus: date | None = None

    @model_validator(mode="after")
    def set_display_name(self):
        if not self.display_name:
            self.display_name = _get_rhel_display_name(self.name, self.major, self.minor)

        return self


class ReleaseModel(BaseModel):
    major: int = Field(gt=8, le=10, description="Major version number, e.g., 7 in version 7.0")
    minor: int = Field(ge=0, le=100, description="Minor version number, e.g., 0 in version 7.0")


class TaggedParagraph(BaseModel):
    title: str = Field(description="The paragraph title")
    text: str = Field(description="The paragraph text")
    tag: str = Field(description="The paragraph htmltag")


def _calculate_support_status(
    start_date: date | None,
    end_date: date | None,
    current_date: date,
    months: int,
) -> SupportStatus:
    support_status = SupportStatus.unknown

    if start_date not in (None, SupportStatus.unknown):
        if start_date > current_date:
            return SupportStatus.upcoming

    if end_date not in (None, SupportStatus.unknown):
        if end_date < current_date:
            return SupportStatus.retired

        expiration_date = end_date - timedelta(days=30 * months)
        if expiration_date <= current_date:
            return SupportStatus.near_retirement

        return SupportStatus.supported

    return support_status


def _get_rhel_display_name(name: str, major: int, minor: int | None):
    display_name = f"{name} {major}"
    if minor is not None:
        display_name += f".{minor}"

    return display_name

import typing as t

from datetime import date
from datetime import timedelta
from enum import StrEnum

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
    six_months = "Support ends within 6 months"
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


class System(BaseModel):
    name: str
    major: int
    minor: int | None = None
    release_date: date | t.Literal["Unknown"] | None
    retirement_date: date | t.Literal["Unknown"] | None
    support_status: SupportStatus = SupportStatus.unknown
    count: int = 0
    lifecycle_type: LifecycleType

    @model_validator(mode="after")
    def update_support_status(self):
        """Validator for setting support status.
        Expected types/values of start_date and end_date are:
            - str(Unknown)
            - None
            - date(YYYY-MM-DD)
        """
        today = date.today()

        if self.release_date != "Unknown" and self.release_date is not None:
            if self.release_date > today:
                self.support_status = SupportStatus.upcoming
                return self

        if self.retirement_date != "Unknown" and self.retirement_date is not None:
            if self.retirement_date < today:
                self.support_status = SupportStatus.retired
                return self

            six_months_date = self.retirement_date - timedelta(days=180)
            if six_months_date <= today:
                self.support_status = SupportStatus.six_months
            else:
                self.support_status = SupportStatus.supported

        else:
            self.support_status = SupportStatus.unknown
            return self

        return self


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


class ReleaseModel(BaseModel):
    major: int = Field(gt=8, le=10, description="Major version number, e.g., 7 in version 7.0")
    minor: int = Field(ge=0, le=100, description="Minor version number, e.g., 0 in version 7.0")


class TaggedParagraph(BaseModel):
    title: str = Field(description="The paragraph title")
    text: str = Field(description="The paragraph text")
    tag: str = Field(description="The paragraph htmltag")

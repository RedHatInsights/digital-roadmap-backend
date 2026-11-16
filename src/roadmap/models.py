import typing as t

from datetime import date
from datetime import timedelta
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import model_validator


class SupportStatus(StrEnum):
    supported = "Supported"
    near_retirement = "Near retirement"
    retired = "Retired"
    not_installed = "Not installed"
    upcoming = "Upcoming release"
    unknown = "Unknown"


def _get_system_uuids(data) -> set[UUID]:
    """
    Populate systems field using data in systems_detail.id field.

    Note: this can be removed once the systems field is deprecated.
    """
    if systems_detail := data.get("systems_detail") or data.get("potentiallyAffectedSystemsDetail"):
        return {system.id for system in systems_detail}
    return set()


def _calculate_support_status(
    start_date: date | t.Literal[SupportStatus.unknown] | None,
    end_date: date | t.Literal[SupportStatus.unknown] | None,
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


class Meta(BaseModel):
    count: int
    total: int | None = None


class LifecycleType(StrEnum):
    mainline = "mainline"
    eus = "EUS"
    els = "ELS"
    e4s = "E4S"


class HostCount(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    major: int
    minor: int | None = None
    lifecycle: LifecycleType


class SystemInfo(BaseModel, frozen=True):
    """Information about relevant system."""

    model_config = ConfigDict(frozen=True)

    id: UUID
    display_name: str
    os_major: int
    os_minor: int | None


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


class System(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    display_name: str = ""
    major: int
    minor: int | None = None
    start_date: date | t.Literal[SupportStatus.unknown] | None
    end_date: date | t.Literal[SupportStatus.unknown] | None
    support_status: SupportStatus = SupportStatus.unknown
    count: int = 0
    lifecycle_type: LifecycleType
    related: bool = False
    systems_detail: set[SystemInfo]
    systems: set[UUID] = Field(default_factory=_get_system_uuids)

    @model_validator(mode="after")
    def set_display_name(self):
        if not self.display_name:
            base = _get_rhel_display_name(self.name, self.major, self.minor)
            suffix = {
                LifecycleType.eus: " EUS",
                LifecycleType.els: " ELS",
                LifecycleType.e4s: " for SAP",
            }.get(self.lifecycle_type, "")
            self.display_name = f"{base}{suffix}"

        return self

    @model_validator(mode="after")
    def update_support_status(self):
        today = date.today()
        self.support_status = _calculate_support_status(
            start_date=self.start_date,
            end_date=self.end_date,
            current_date=today,
            months=3,
        )

        # If no systems are using this system release, mark as not installed
        if self.count == 0:
            self.support_status = SupportStatus.not_installed
            return self

        return self


class RHELLifecycle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = "RHEL"
    start_date: date
    end_date: date
    support_status: SupportStatus = SupportStatus.unknown
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

    @model_validator(mode="after")
    def update_support_status(self):
        today = date.today()
        self.support_status = _calculate_support_status(
            start_date=self.start_date,
            end_date=self.end_date,
            current_date=today,
            months=3,
        )

        return self


class PaginatedSystemsResponse(BaseModel):
    """Paginated response for v2 systems endpoints with offset/limit metadata."""

    meta: Meta
    data: list[SystemInfo]


#: Largest host_ids list a single request may carry.
#:
#: The console UI already splits its reads into batches before posting them:
#: 5000 ids for the RHEL endpoint and 1000 for upcoming and app streams (see
#: BATCH_SIZE in the frontend's relevant*Loader.ts). This cap sits at twice the
#: largest of those, so every batch the UI sends today passes with headroom
#: while a request is still bounded.
#:
#: Without a bound, one request could carry an arbitrarily long list. Each id
#: becomes a parsed UUID and an element of a bound Postgres array, so the
#: memory cost is set by the caller rather than by the service, on pods limited
#: to a few GiB.
MAX_HOST_IDS = 10_000


class HostIdsRequest(BaseModel):
    """Host ids to read. The caller must be permitted to see them."""

    host_ids: list[UUID] = Field(
        max_length=MAX_HOST_IDS,
        description=(
            f"Host UUIDs to include, at most {MAX_HOST_IDS} per request. "
            "An empty list is accepted and matches no hosts. Split larger "
            "reads into several requests."
        ),
    )


class ReleaseModel(BaseModel):
    major: int = Field(gt=8, le=10, description="Major version number, e.g., 7 in version 7.0")
    minor: int = Field(ge=0, le=100, description="Minor version number, e.g., 0 in version 7.0")


class TaggedParagraph(BaseModel):
    title: str = Field(description="The paragraph title")
    text: str = Field(description="The paragraph text")
    tag: str = Field(description="The paragraph htmltag")

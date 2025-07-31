import string
import typing as t

from datetime import date
from enum import StrEnum

from pydantic import AfterValidator
from pydantic import AliasChoices
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator
from pydantic import model_validator

from roadmap.common import ensure_date
from roadmap.data.systems import OS_LIFECYCLE_DATES
from roadmap.models import _calculate_support_status
from roadmap.models import SupportStatus


Date = t.Annotated[str | date, AfterValidator(ensure_date)]
_DISPLAY_NAME_SPECIAL_CASES = {
    ".net": ".NET",
    "apache httpd": "Apache HTTPD",
    "bind": "BIND",
    "freeradius": "FreeRADIUS",
    "gcc-toolset": "GCC Toolset",
    "idm": "IDM",
    "jboss mod_cluster for apache": "JBoss mod_cluster for Apache",
    "llvm": "LLVM",
    "mariadb": "MariaDB",
    "mod_auth_openidc for apache": "Mod Auth OpenIDC for Apache",
    "mysql": "MySQL",
    "nginx": "NGINX",
    "node.js": "Node.js",
    "nodejs": "Node.js",
    "openjdk": "OpenJDK",
    "osinfo-db": "OSInfo DB",
    "php": "PHP",
    "postgresql": "PostgreSQL",
    "rhn-tools": "RHN Tools",
    "swig": "SWIG",
}


class AppStreamImplementation(StrEnum):
    module = "dnf_module"
    package = "package"
    scl = "scl"
    stream = "stream"


class AppStreamType(StrEnum):
    stream = "Application Stream"
    full = "Full Life Application Stream"
    rolling = "Rolling Application Stream"
    dependent = "Dependent Application Stream"


class AppStream(BaseModel):
    model_config = ConfigDict(frozen=True)

    display_name: str = ""
    start_date: Date | None = None
    end_date: Date | None = Field(validation_alias=AliasChoices("end_date", "enddate"), default=None)
    os_major: int | None = None
    os_minor: int | None = None
    application_stream_name: str = ""
    application_stream_type: AppStreamType | None
    support_status: SupportStatus = SupportStatus.unknown


class AppStreamEntity(BaseModel):
    """An application stream module or package."""

    name: str = Field(min_length=1)
    display_name: str = ""
    application_stream_name: str = ""
    application_stream_type: AppStreamType | None = None
    stream: str
    start_date: Date | None = None
    end_date: Date | None = Field(validation_alias=AliasChoices("end_date", "enddate"), default=None)
    impl: AppStreamImplementation
    initial_product_version: str | None = None
    support_status: SupportStatus = SupportStatus.unknown
    os_major: int | None = None
    os_minor: int | None = None
    lifecycle: int | None = None
    rolling: bool = False

    @field_validator("initial_product_version")
    @classmethod
    def validate_version(cls, value):
        if value is not None:
            return ".".join(value.split(".")[:2])

    @model_validator(mode="after")
    def set_start_date(self):
        """If no start_date is supplied, get it from the OS lifecycle date"""
        if self.start_date is None:
            try:
                self.start_date = OS_LIFECYCLE_DATES[self.initial_product_version].start_date  # pyright: ignore [reportArgumentType]
            except KeyError:
                return self

        return self

    @model_validator(mode="after")
    def set_rolling(self):
        if self.application_stream_type in [AppStreamType.rolling, AppStreamType.dependent]:
            self.rolling = True

        return self

    @model_validator(mode="after")
    def set_os_version(self):
        if self.initial_product_version is not None:
            self.os_major = int(self.initial_product_version.split(".")[0])
            try:
                self.os_minor = int(self.initial_product_version.split(".")[1])
            except IndexError:
                self.os_minor = None

        return self

    @model_validator(mode="after")
    def set_display_name(self):
        """Create a normalized name field for presentation"""

        display_name = self.name
        if self.application_stream_name and self.application_stream_name != "Unknown":
            display_name = self.application_stream_name

        # Ensure the version number is in the display name
        if display_name[-1] not in (string.digits):
            version = ".".join(self.stream.split(".")[:2])

            # Avoid putting a duplicate string at the end
            if version and display_name[-len(version) :].lower() != version:
                display_name = f"{display_name.rstrip()} {version}"

        # Correct capitalization
        display_name_lower = display_name.casefold()
        for name, cased_name in _DISPLAY_NAME_SPECIAL_CASES.items():
            if name in display_name_lower:
                display_name = display_name_lower.replace(name, cased_name)
                break
        else:
            display_name = display_name.title()

        self.display_name = display_name.replace("-", " ").replace("Rhel", "RHEL")

        return self

    @model_validator(mode="after")
    def update_support_status(self):
        """Validator for setting status."""
        today = date.today()
        self.support_status = _calculate_support_status(
            start_date=self.start_date,  # pyright: ignore [reportArgumentType]
            end_date=self.end_date,  # pyright: ignore [reportArgumentType]
            current_date=today,  # pyright: ignore [reportArgumentType]
            months=6,
        )

        return self

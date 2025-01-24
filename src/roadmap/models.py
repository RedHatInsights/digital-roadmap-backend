from datetime import date
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class AppStreamType(StrEnum):
    module = "module"
    package = "package"
    scl = "scl"


class ReleaseModel(BaseModel):
    major: int = Field(description="Major version number, e.g., 7 in version 7.0")
    minor: int = Field(description="Minor version number, e.g., 0 in version 7.0")


class TaggedParagraph(BaseModel):
    tag: str = Field(description="The paragraph htmltag")
    text: str = Field(description="The paragraph text")
    title: str = Field(description="The paragraph title")


class AppStream(BaseModel):
    arch: str
    context: str
    description: str
    end_date: date | str
    name: str
    profiles: dict[str, list[str]]
    start_date: date | str
    stream: str
    version: str

    @field_validator("start_date", "end_date")
    def dates(cls, value):
        if isinstance(value, date):
            return value.strftime("%Y%m%d")

        return value


class Module(BaseModel):
    module_name: str
    rhel_major_version: int | str
    streams: list[AppStream]
    type: AppStreamType

    @field_validator("rhel_major_version")
    def version(cls, value):
        return str(value)


class AppStreamResponse(BaseModel):
    data: list[Module]

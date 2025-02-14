import typing as t

from datetime import date

from pydantic import BaseModel
from pydantic import Field


class System(BaseModel):
    name: str
    major: int
    minor: int | None = None
    release: str
    release_date: date | t.Literal["Unknown"]
    retirement_date: date | t.Literal["Unknown"]
    count: int = 0
    lifecycle_type: str


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

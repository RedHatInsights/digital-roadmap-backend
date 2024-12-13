from pydantic import BaseModel, Field


class ReleaseModel(BaseModel):
    major: int = Field(..., description="Major version number, e.g., 7 in version 7.0")
    minor: int = Field(..., description="Minor version number, e.g., 0 in version 7.0")


class TaggedParagraph(BaseModel):
    title: str = Field(..., description="The paragraph title")
    text: str = Field(..., description="The paragraph text")
    tag: str = Field(..., description="The paragraph htmltag")

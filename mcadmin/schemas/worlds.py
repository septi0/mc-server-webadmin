import re
from pydantic import BaseModel, Field, field_validator

server_version_pattern = r"^(?:\d+\.\d+(?:\.\d+)?(?:-(?:pre|rc)\d+)?|\d{2}w\d{2}[a-z])$"


class CreateWorldSchema(BaseModel):
    name: str = Field(title="World Name", max_length=30)
    server_version: str = Field(title="Server Version")

    @field_validator("server_version")
    @classmethod
    def check_version(cls, v):
        if not re.match(server_version_pattern, v):
            raise ValueError("Version must have the format '1.2.3' or '24w05a'")
        return v


class UpdateWorldSchema(BaseModel):
    id: str = Field(title="World ID")
    server_version: str = Field(title="Server Version")

    @field_validator("server_version")
    @classmethod
    def check_version(cls, v):
        if not re.match(server_version_pattern, v):
            raise ValueError("Version must have the format '1.2.3' or '24w05a'")
        return v

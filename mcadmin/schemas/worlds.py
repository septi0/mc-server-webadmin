import re
from pydantic import BaseModel, Field, field_validator
from aiohttp import web
from typing import Any, Optional

server_version_pattern = r"^(?:\d+\.\d+(?:\.\d+)?(?:-(?:pre|rc)\d+)?|\d{2}w\d{2}[a-z])$"
zip_signatures = [b'PK\x03\x04', b'PK\x05\x06', b'PK\x07\x08']


class CreateWorldSchema(BaseModel):
    name: str = Field(title="World Name", max_length=30)
    server_version: str = Field(title="Server Version")
    world_archive: Optional[Any] = None

    @field_validator("server_version")
    @classmethod
    def check_version(cls, v):
        if not re.match(server_version_pattern, v):
            raise ValueError("Version must have the format '1.2.3' or '24w05a'")
        return v

    @field_validator("world_archive")
    @classmethod
    def check_world_archive(cls, v):
        if not v:
            return v
        
        if not isinstance(v, web.FileField):
            raise ValueError("World archive must be a file")
        elif not v.filename.endswith(".zip"):
            raise ValueError("World archive must be a .zip file")
        elif not any(v.file.read(len(sig)) == sig for sig in zip_signatures):
            raise ValueError("World archive is not a valid zip file")
        v.file.seek(0)
        
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


class AddWorldDatapackSchema(BaseModel):
    datapack_archive: Any

    @field_validator("datapack_archive")
    @classmethod
    def check_datapack_archive(cls, v):
        if not isinstance(v, web.FileField):
            raise ValueError("Datapack archive must be a file")
        elif not v.filename.endswith(".zip"):
            raise ValueError("Datapack archive must be a .zip file")
        elif not any(v.file.read(len(sig)) == sig for sig in zip_signatures):
            raise ValueError("Datapack archive is not a valid zip file")
        v.file.seek(0)

        return v

class AddWorldModSchema(BaseModel):
    mod_jar: Any

    @field_validator("mod_jar")
    @classmethod
    def check_mod_jar(cls, v):
        if not isinstance(v, web.FileField):
            raise ValueError("Mod jar must be a file")
        elif not v.filename.endswith(".jar"):
            raise ValueError("Mod jar must be a .jar file")

        return v

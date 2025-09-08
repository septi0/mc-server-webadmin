from pydantic import BaseModel, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class McServerConfigSchema(BaseSettings):
    java_bin: str = Field(default="java")
    java_min_memory: str = Field(default="1024M")
    java_max_memory: str = Field(default="1024M")
    server_additional_args: list[str] = Field(default=[])
    server_ip: str = Field(default="0.0.0.0")
    server_port: int = Field(default=25565)
    rcon_port: int = Field(default=25575)
    display_ip: Optional[str] = None
    display_host: Optional[str] = None
    display_port: Optional[int] = Field(default=None, ge=0, le=65535)

    model_config = SettingsConfigDict(env_prefix="MCADMIN_")

    @model_validator(mode="after")
    def check_ip_or_host_exclusive(self):
        if self.display_ip and self.display_host:
            raise ValueError("Cannot set both display_ip and display_host")
        return self


class WebServerConfigSchema(BaseSettings):
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)

    model_config = SettingsConfigDict(env_prefix="MCADMIN_WEB_")


class ConfigSchema(BaseModel):
    mc_server: McServerConfigSchema = Field(default_factory=McServerConfigSchema)
    web_server: WebServerConfigSchema = Field(default_factory=WebServerConfigSchema)

from pydantic import BaseModel, Field, model_validator, IPvAnyAddress
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
from ipaddress import ip_address


class McServerConfigSchema(BaseSettings):
    java_bin: Optional[str] = None
    java_min_memory: str = Field(default="1024M", min_length=1)
    java_max_memory: str = Field(default="1024M", min_length=1)
    server_additional_args: Optional[list[str]] = None
    server_ip: IPvAnyAddress = ip_address("0.0.0.0")
    server_port: int = Field(default=25565, ge=0, le=65535)
    rcon_port: int = Field(default=25575, ge=0, le=65535)
    display_ip: Optional[IPvAnyAddress] = None
    display_host: Optional[str] = None
    display_port: Optional[int] = Field(default=None, ge=0, le=65535)

    model_config = SettingsConfigDict(env_prefix="MCADMIN_")

    @model_validator(mode="after")
    def check_ip_or_host_exclusive(self):
        if self.display_ip and self.display_host:
            raise ValueError("Cannot set both display_ip and display_host")
        return self


class WebServerConfigSchema(BaseSettings):
    ip: IPvAnyAddress = ip_address("0.0.0.0")
    port: int = Field(default=8000, ge=0, le=65535)

    model_config = SettingsConfigDict(env_prefix="MCADMIN_WEB_")


class ConfigSchema(BaseModel):
    mc_server: McServerConfigSchema = Field(default_factory=McServerConfigSchema)
    web_server: WebServerConfigSchema = Field(default_factory=WebServerConfigSchema)

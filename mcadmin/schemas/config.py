from pydantic import BaseModel, Field, model_validator, IPvAnyAddress, IPvAnyNetwork
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
from ipaddress import ip_address


class McServerConfigSchema(BaseSettings):
    java_bin: Optional[str] = None
    java_min_memory: str = Field(default="1024M", min_length=1)
    java_max_memory: str = Field(default="1024M", min_length=1)
    server_additional_args: Optional[list[str]] = []
    server_ip: IPvAnyAddress = ip_address("0.0.0.0")
    server_port: int = Field(default=25565, ge=0, le=65535)
    rcon_port: int = Field(default=25575, ge=0, le=65535)
    display_ip: Optional[IPvAnyAddress | None] = None
    display_host: Optional[str | None] = None
    display_port: Optional[int | None] = Field(default=None, ge=0, le=65535)

    model_config = SettingsConfigDict(env_prefix="MCADMIN_")

    @model_validator(mode="before")
    def parse_additional_args(cls, values):
        additional_args = values.get("server_additional_args")
        if isinstance(additional_args, str):
            values["server_additional_args"] = [arg.strip() for arg in additional_args.split(",") if arg.strip()]
        return values


class WebServerConfigSchema(BaseSettings):
    ip: IPvAnyAddress = ip_address("0.0.0.0")
    port: int = Field(default=8000, ge=0, le=65535)
    trusted_proxies: Optional[list[IPvAnyAddress | IPvAnyNetwork]] = []

    model_config = SettingsConfigDict(env_prefix="MCADMIN_WEB_")

    @model_validator(mode="before")
    def parse_trusted_proxies(cls, values):
        trusted_proxies = values.get("trusted_proxies")
        if isinstance(trusted_proxies, str):
            values["trusted_proxies"] = [ip.strip() for ip in trusted_proxies.split(",") if ip.strip()]
        return values


class ConfigSchema(BaseModel):
    mc_server: McServerConfigSchema = Field(default_factory=McServerConfigSchema)
    web_server: WebServerConfigSchema = Field(default_factory=WebServerConfigSchema)

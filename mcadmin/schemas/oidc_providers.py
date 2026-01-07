import json
from pydantic import BaseModel, Field, model_validator, field_validator
from typing import Optional

class OIDCProviderConfig(BaseModel):
    issuer_url: str = Field(title="Issuer URL", min_length=5, max_length=300)
    client_id: str = Field(title="Client ID", min_length=2, max_length=200)
    client_secret: str = Field(title="Client Secret", min_length=2, max_length=200)
    scope: str = Field(title="Scope", max_length=500)

    @field_validator("scope")
    def validate_scope(cls, v):
        if "openid" not in v:
            raise ValueError("Scope must contain 'openid'")
        return v

class CreateOIDCProviderSchema(BaseModel):
    name: str = Field(title="Name", min_length=2, max_length=100)
    default: bool = Field(title="Default", default=False)
    allow_registration: bool = Field(title="Auto Register", default=False)
    auto_launch: bool = Field(title="Auto Launch", default=False)
    user_claim: Optional[str] = Field(title="User Claim", max_length=100, default=None)
    config: OIDCProviderConfig = Field(title="Config")

    @model_validator(mode="before")
    def parse_config(cls, values):
        config = values.get("config", "{}")

        if isinstance(config, str):
            values["config"] = json.loads(config)

        return values

class UpdateOIDCProviderSchema(BaseModel):
    default: bool = Field(title="Default", default=False)
    allow_registration: bool = Field(title="Auto Register", default=False)
    auto_launch: bool = Field(title="Auto Launch", default=False)
    user_claim: Optional[str] = Field(title="User Claim", max_length=100, default=None)
    config: OIDCProviderConfig = Field(title="Config")

    @model_validator(mode="before")
    def parse_config(cls, values):
        config = values.get("config", "{}")

        if isinstance(config, str):
            values["config"] = json.loads(config)

        return values

import json
from pydantic import BaseModel, model_validator, field_validator, Field
from typing import Literal, List

class UpdateAuthMethodsSchema(BaseModel):
    auth_methods: List[Literal["local", "oidc"]] = Field(title="Authentication Methods")

    @model_validator(mode="before")
    def parse_auth_methods(cls, values):
        auth_methods = values.get("auth_methods", "[]")

        if isinstance(auth_methods, str):
            values["auth_methods"] = json.loads(auth_methods)

        return values

    @field_validator("auth_methods")
    @classmethod
    def at_least_one(cls, v):
        if not v:
            raise ValueError("At least one auth method is required")
        return v

from pydantic import BaseModel, Field, model_validator
from typing import Optional, Literal


class UpdatePasswordSchema(BaseModel):
    current_password: str = Field(title="Current Password")
    new_password: str = Field(title="New Password", min_length=6, max_length=100)
    new_password_confirm: str = Field(title="Confirm New Password")

    @model_validator(mode="after")
    def check_new_passwords_match(self):
        if self.new_password != self.new_password_confirm:
            raise ValueError("New passwords do not match")
        return self

class CreateUserSchema(BaseModel):
    username: str = Field(title="Username", min_length=3, max_length=100)
    password: str = Field(title="Password", min_length=6, max_length=100)
    role: Literal["user", "admin"] = Field(title="Role", default="user")


class CreatePasswordlessUserSchema(BaseModel):
    username: str = Field(title="Username", min_length=3, max_length=100)
    role: Literal["user", "admin"] = Field(title="Role", default="user")


class UpdateUserSchema(BaseModel):
    password: Optional[str] = Field(default=None, title="Password", min_length=6, max_length=100)
    role: Literal["user", "admin"] = Field(title="Role", default="user")

class AuthSchema(BaseModel):
    username: str = Field(title="Username", min_length=3, max_length=100)
    password: str = Field(title="Password", min_length=6, max_length=100)

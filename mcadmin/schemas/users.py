from pydantic import BaseModel, Field, model_validator
from typing import Optional


class UpdatePasswordSchema(BaseModel):
    current_password: str = Field(title="Current Password")
    new_password: str = Field(title="New Password", min_length=6)
    new_password_confirm: str = Field(title="Confirm New Password")

    @model_validator(mode="after")
    def check_new_passwords_match(self):
        if self.new_password != self.new_password_confirm:
            raise ValueError("New passwords do not match")
        return self

class CreateUserSchema(BaseModel):
    username: str = Field(title="Username", min_length=3, max_length=100)
    password: str = Field(title="Password", min_length=6)
    role: str = Field(title="Role", default="user")

class UpdateUserSchema(BaseModel):
    id: str = Field(title="User ID")
    password: Optional[str] = Field(default=None, title="Password", min_length=6)
    role: str = Field(title="Role", default="user")
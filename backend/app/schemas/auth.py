"""Pydantic schemas for auth."""
from pydantic import BaseModel, EmailStr, field_validator


class LoginRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.lower().strip()


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    role: str
    is_active: bool

    model_config = {"from_attributes": True}


class MeResponse(UserResponse):
    team_memberships: list[dict] = []

    model_config = {"from_attributes": True}

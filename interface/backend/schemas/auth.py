from typing import Literal

from pydantic import BaseModel, Field, field_validator


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=256)
    remember: bool = False

    @field_validator("email")
    @classmethod
    def valid_email(cls, value: str) -> str:
        value = value.strip().lower()
        if "@" not in value or not value.split("@", 1)[1]:
            raise ValueError("Email không hợp lệ")
        return value


class UserOut(BaseModel):
    id: int
    email: str
    name: str
    role: Literal["doctor", "pharmacist"]

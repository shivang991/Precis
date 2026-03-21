import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr


class UserBase(BaseModel):
    email: EmailStr
    name: str
    avatar_url: str | None = None
    default_theme: str = "default"
    include_headings_in_summary: bool = True


class UserRead(UserBase):
    id: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class UserUpdateSettings(BaseModel):
    default_theme: str | None = None
    include_headings_in_summary: bool | None = None

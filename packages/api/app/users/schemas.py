import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr


class UserBase(BaseModel):
    email: EmailStr
    name: str
    avatar_url: str | None = None


class UserRead(UserBase):
    id: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class UserUpdateSettings(BaseModel):
    pass


class TokenExchangeRequest(BaseModel):
    code: str
    redirect_uri: str | None = None


class GoogleAuthUrl(BaseModel):
    url: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

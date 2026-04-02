"""
Google OAuth 2.0 flow + JWT issuance.
"""

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.shared.config import get_settings
from app.users.models import User
from app.shared.security import create_access_token

settings = get_settings()

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


def get_google_auth_url(state: str, redirect_uri: str | None = None) -> str:
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": redirect_uri or settings.google_redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "state": state,
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return f"https://accounts.google.com/o/oauth2/v2/auth?{query}"


async def exchange_code_for_user_info(code: str, redirect_uri: str | None = None) -> dict:
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(GOOGLE_TOKEN_URL, data={
            "code": code,
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "redirect_uri": redirect_uri or settings.google_redirect_uri,
            "grant_type": "authorization_code",
        })
        token_resp.raise_for_status()
        access_token = token_resp.json()["access_token"]

        user_resp = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        user_resp.raise_for_status()
        return user_resp.json()


async def get_or_create_user(db: AsyncSession, google_info: dict) -> User:
    google_id = google_info["sub"]
    result = await db.execute(select(User).where(User.google_id == google_id))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            google_id=google_id,
            email=google_info["email"],
            name=google_info.get("name", ""),
            avatar_url=google_info.get("picture"),
        )
        db.add(user)
        await db.flush()

    return user


async def login_with_google(db: AsyncSession, code: str, redirect_uri: str | None = None) -> str:
    """Full OAuth flow — returns a signed JWT for the user."""
    google_info = await exchange_code_for_user_info(code, redirect_uri)
    user = await get_or_create_user(db, google_info)
    return create_access_token(user.id)

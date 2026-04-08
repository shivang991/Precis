"""
Google OAuth 2.0 flow + JWT issuance + user operations.
"""

import secrets

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.shared.config import get_settings
from app.shared.security import create_access_token
from app.users.models import User
from app.users.schemas import UserUpdateSettings, GoogleAuthUrl, TokenResponse
from app.users.errors import GoogleAuthError

settings = get_settings()

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


class UserService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def get_google_auth_url(self, redirect_uri: str | None = None) -> GoogleAuthUrl:
        state = secrets.token_urlsafe(16)
        params = {
            "client_id": settings.google_client_id,
            "redirect_uri": redirect_uri or settings.google_redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "access_type": "offline",
            "state": state,
        }
        query = "&".join(f"{k}={v}" for k, v in params.items())
        return GoogleAuthUrl(url=f"https://accounts.google.com/o/oauth2/v2/auth?{query}")

    async def login_with_google(self, code: str, redirect_uri: str | None = None) -> TokenResponse:
        """Full OAuth flow — returns a signed JWT for the user."""
        try:
            google_info = await self._exchange_code_for_user_info(code, redirect_uri)
        except Exception:
            raise GoogleAuthError()
        user = await self._get_or_create_user(google_info)
        return TokenResponse(access_token=create_access_token(user.id))

    async def update_settings(self, user: User, body: UserUpdateSettings) -> User:
        for field, value in body.model_dump(exclude_none=True).items():
            setattr(user, field, value)
        await self.db.flush()
        return user

    # ── Private helpers ──────────────────────────────────────────────────────

    async def _exchange_code_for_user_info(self, code: str, redirect_uri: str | None = None) -> dict:
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

    async def _get_or_create_user(self, google_info: dict) -> User:
        google_id = google_info["sub"]
        result = await self.db.execute(select(User).where(User.google_id == google_id))
        user = result.scalar_one_or_none()

        if user is None:
            user = User(
                google_id=google_id,
                email=google_info["email"],
                name=google_info.get("name", ""),
                avatar_url=google_info.get("picture"),
            )
            self.db.add(user)
            await self.db.flush()

        return user

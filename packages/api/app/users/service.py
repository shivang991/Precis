"""
Google OAuth 2.0 flow + JWT issuance + user operations.
"""

import base64
import json
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

import httpx
from fastapi.responses import RedirectResponse
from jose import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared import get_logger, get_settings

from .errors import GoogleAuthError
from .models import User
from .schemas import GoogleAuthUrl, TokenResponse, UserUpdateSettings

settings = get_settings()
logger = get_logger()

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


class UserService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def get_google_auth_url(self, redirect_uri: str | None = None) -> GoogleAuthUrl:
        csrf = secrets.token_urlsafe(16)

        # When a mobile redirect URI is provided (e.g. precis://auth), encode
        # it into the OAuth state so the callback can redirect there after
        # exchanging the code.  Google's redirect_uri is always the backend
        # callback. Custom schemes aren't accepted by web-type OAuth clients.
        if redirect_uri:
            state_payload = json.dumps({"s": csrf, "r": redirect_uri})
            encoded = base64.urlsafe_b64encode(state_payload.encode())
            state = encoded.decode().rstrip("=")
        else:
            state = csrf

        params = {
            "client_id": settings.google_client_id,
            "redirect_uri": settings.google_redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "access_type": "offline",
            "state": state,
        }
        query = urlencode(params)
        return GoogleAuthUrl(
            url=f"https://accounts.google.com/o/oauth2/v2/auth?{query}"
        )

    async def login_with_google(
        self, code: str, redirect_uri: str | None = None
    ) -> TokenResponse:
        """Full OAuth flow — returns a signed JWT for the user."""
        try:
            google_info = await self._exchange_code_for_user_info(code, redirect_uri)
        except Exception as exc:
            logger.exception("google_oauth_exchange_failed")
            raise GoogleAuthError() from exc
        user = await self._get_or_create_user(google_info)
        return TokenResponse(access_token=self._create_access_token(user.id))

    async def handle_google_callback(
        self,
        code: str,
        state: str,
        redirect_uri: str | None = None,
    ) -> TokenResponse | RedirectResponse:
        """Exchange a Google auth code and return a token or mobile redirect."""
        result = await self.login_with_google(code, redirect_uri)

        _, mobile_redirect = self._parse_oauth_state(state)
        if mobile_redirect:
            target = f"{mobile_redirect}?{urlencode({
                'access_token': result.access_token,
            })}"
            return RedirectResponse(url=target)

        return result

    async def update_settings(self, user: User, body: UserUpdateSettings) -> User:
        for field, value in body.model_dump(exclude_none=True).items():
            setattr(user, field, value)
        await self.db.flush()
        return user

    # ── Private helpers ──────────────────────────────────────────────────────

    def _parse_oauth_state(self, state: str) -> tuple[str, str | None]:
        """Extract (csrf_token, mobile_redirect | None) from state."""
        try:
            padded = state + "=" * (-len(state) % 4)
            data = json.loads(base64.urlsafe_b64decode(padded))
            return data["s"], data.get("r")
        except Exception:
            return state, None

    def _create_access_token(self, user_id: uuid.UUID) -> str:
        expire = datetime.now(UTC) + timedelta(
            minutes=settings.jwt_access_token_expire_minutes
        )
        payload = {"sub": str(user_id), "exp": expire}
        return jwt.encode(
            payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
        )

    async def _exchange_code_for_user_info(
        self, code: str, redirect_uri: str | None = None
    ) -> dict:
        async with httpx.AsyncClient() as client:
            token_resp = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret,
                    "redirect_uri": redirect_uri or settings.google_redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
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

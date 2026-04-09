from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.database import get_db
from app.shared.dependencies import get_current_user
from app.users.models import User
from app.users.schemas import UserRead, UserUpdateSettings, TokenExchangeRequest, GoogleAuthUrl, TokenResponse
from app.users.service import UserService

auth_router = APIRouter(prefix="/auth", tags=["auth"])
users_router = APIRouter(prefix="/users", tags=["users"])


def _get_service(db: AsyncSession = Depends(get_db)) -> UserService:
    return UserService(db)


# ── Auth routes ───────────────────────────────────────────────────────────────


@auth_router.get("/login", response_model=GoogleAuthUrl)
async def google_login(
    redirect_uri: str | None = Query(
        default=None,
        description="Override redirect URI — pass the mobile deep link (e.g. precis://auth) for app-based OAuth.",
    ),
    svc: UserService = Depends(_get_service),
):
    """Return the Google OAuth redirect URL for the client to navigate to."""
    return svc.get_google_auth_url(redirect_uri)


@auth_router.get("/callback", response_model=TokenResponse)
async def google_callback(
    code: str = Query(...),
    redirect_uri: str | None = Query(default=None),
    svc: UserService = Depends(_get_service),
):
    """Exchange Google auth code for a Precis JWT (web callback)."""
    return await svc.login_with_google(code, redirect_uri)


@auth_router.post("/token", response_model=TokenResponse)
async def exchange_token(
    body: TokenExchangeRequest,
    svc: UserService = Depends(_get_service),
):
    """
    Exchange a Google OAuth code for a Precis JWT (mobile / POST flow).

    The mobile app uses expo-auth-session which captures the code via deep link,
    then POSTs it here with the same redirect_uri it passed to /login.
    """
    return await svc.login_with_google(body.code, body.redirect_uri)


@auth_router.get("/me", response_model=UserRead)
async def me(current_user: User = Depends(get_current_user)):
    return current_user


# ── Users routes ──────────────────────────────────────────────────────────────


@users_router.get("/me", response_model=UserRead)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@users_router.patch("/me/settings", response_model=UserRead)
async def update_general_settings(
    body: UserUpdateSettings,
    current_user: User = Depends(get_current_user),
    svc: UserService = Depends(_get_service),
):
    """Update user-level general settings."""
    return await svc.update_settings(current_user, body)

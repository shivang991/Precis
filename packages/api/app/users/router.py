from fastapi import APIRouter, Depends, Query

from app.shared import get_current_user
from .models import User
from .schemas import (
    UserRead,
    UserUpdateSettings,
    TokenExchangeRequest,
    GoogleAuthUrl,
    TokenResponse,
)
from .user_service import UserService

auth_router = APIRouter(prefix="/auth", tags=["auth"])
users_router = APIRouter(prefix="/users", tags=["users"])


# ── Auth routes ───────────────────────────────────────────────────────────────


@auth_router.get("/login", response_model=GoogleAuthUrl)
async def google_login(
    redirect_uri: str | None = Query(
        default=None,
        description="Override redirect URI — pass the mobile deep link (e.g. precis://auth) for app-based OAuth.",
    ),
    svc: UserService = Depends(UserService),
):
    """Return the Google OAuth redirect URL for the client to navigate to."""
    return svc.get_google_auth_url(redirect_uri)


@auth_router.get("/callback", response_model=TokenResponse)
async def google_callback(
    code: str = Query(...),
    redirect_uri: str | None = Query(default=None),
    svc: UserService = Depends(UserService),
):
    """Exchange Google auth code for a Precis JWT (web callback)."""
    return await svc.login_with_google(code, redirect_uri)


@auth_router.post("/token", response_model=TokenResponse)
async def exchange_token(
    body: TokenExchangeRequest,
    svc: UserService = Depends(UserService),
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
    svc: UserService = Depends(UserService),
):
    """Update user-level general settings."""
    return await svc.update_settings(current_user, body)

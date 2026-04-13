from fastapi import APIRouter, Depends, Query

from .dependencies import get_current_user, get_user_service
from .models import User
from .schemas import (
    GoogleAuthUrl,
    TokenExchangeRequest,
    TokenResponse,
    UserRead,
    UserUpdateSettings,
)
from .service import UserService

auth_router = APIRouter(prefix="/auth", tags=["auth"])
users_router = APIRouter(prefix="/users", tags=["users"])


# ── Auth routes ───────────────────────────────────────────────────────────────


@auth_router.get("/login", response_model=GoogleAuthUrl, operation_id="get_login_url")
async def google_login(
    redirect_uri: str | None = Query(
        default=None,
        description=(
            "Override redirect URI — pass the mobile deep link"
            " (e.g. precis://auth) for app-based OAuth."
        ),
    ),
    svc: UserService = Depends(get_user_service),
):
    """Return the Google OAuth redirect URL for the client to navigate to."""
    return svc.get_google_auth_url(redirect_uri)


@auth_router.get(
    "/callback", response_model=TokenResponse, operation_id="google_callback"
)
async def google_callback(
    code: str = Query(...),
    state: str = Query(default=""),
    redirect_uri: str | None = Query(default=None),
    svc: UserService = Depends(get_user_service),
):
    """Exchange Google auth code for a Precis JWT (web callback).

    When the OAuth state contains an encoded mobile redirect URI the
    response is a 302 redirect to ``<redirect>?access_token=<jwt>``
    so the mobile app receives the token via its deep-link handler.
    """
    return await svc.handle_google_callback(code, state, redirect_uri)


@auth_router.post("/token", response_model=TokenResponse, operation_id="exchange_token")
async def exchange_token(
    body: TokenExchangeRequest,
    svc: UserService = Depends(get_user_service),
):
    """
    Exchange a Google OAuth code for a Precis JWT (mobile / POST flow).

    The mobile app uses expo-auth-session which captures the code via deep link,
    then POSTs it here with the same redirect_uri it passed to /login.
    """
    return await svc.login_with_google(body.code, body.redirect_uri)


@auth_router.get("/me", response_model=UserRead, operation_id="get_auth_me")
async def me(current_user: User = Depends(get_current_user)):
    return current_user


# ── Users routes ──────────────────────────────────────────────────────────────


@users_router.get("/me", response_model=UserRead, operation_id="get_profile")
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@users_router.patch(
    "/me/settings", response_model=UserRead, operation_id="update_settings"
)
async def update_general_settings(
    body: UserUpdateSettings,
    current_user: User = Depends(get_current_user),
    svc: UserService = Depends(get_user_service),
):
    """Update user-level general settings."""
    return await svc.update_settings(current_user, body)

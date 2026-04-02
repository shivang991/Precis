import secrets
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.database import get_db
from app.shared.dependencies import get_current_user
from app.users.models import User
from app.users.schemas import UserRead, UserUpdateSettings
from app.users.services import get_google_auth_url, login_with_google

auth_router = APIRouter(prefix="/auth", tags=["auth"])
users_router = APIRouter(prefix="/users", tags=["users"])


# ── Auth routes ───────────────────────────────────────────────────────────────

class TokenExchangeRequest(BaseModel):
    code: str
    redirect_uri: str | None = None


@auth_router.get("/login")
async def google_login(
    redirect_uri: str | None = Query(
        default=None,
        description="Override redirect URI — pass the mobile deep link (e.g. precis://auth) for app-based OAuth.",
    )
):
    """Return the Google OAuth redirect URL for the client to navigate to."""
    state = secrets.token_urlsafe(16)
    return {"url": get_google_auth_url(state, redirect_uri)}


@auth_router.get("/callback")
async def google_callback(
    code: str = Query(...),
    redirect_uri: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Exchange Google auth code for a Precis JWT (web callback)."""
    try:
        token = await login_with_google(db, code, redirect_uri)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return {"access_token": token, "token_type": "bearer"}


@auth_router.post("/token")
async def exchange_token(
    body: TokenExchangeRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Exchange a Google OAuth code for a Precis JWT (mobile / POST flow).

    The mobile app uses expo-auth-session which captures the code via deep link,
    then POSTs it here with the same redirect_uri it passed to /login.
    """
    try:
        token = await login_with_google(db, body.code, body.redirect_uri)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return {"access_token": token, "token_type": "bearer"}


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
    db: AsyncSession = Depends(get_db),
):
    """Update user-level general settings (theme, heading preference)."""
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(current_user, field, value)
    await db.flush()
    return current_user

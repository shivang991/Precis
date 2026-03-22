import secrets
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.auth_service import get_google_auth_url, login_with_google
from app.core.dependencies import get_current_user
from app.schemas.user import UserRead
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])


class TokenExchangeRequest(BaseModel):
    code: str
    redirect_uri: str | None = None


@router.get("/login")
async def google_login(
    redirect_uri: str | None = Query(
        default=None,
        description="Override redirect URI — pass the mobile deep link (e.g. precis://auth) for app-based OAuth.",
    )
):
    """Return the Google OAuth redirect URL for the client to navigate to."""
    state = secrets.token_urlsafe(16)
    return {"url": get_google_auth_url(state, redirect_uri)}


@router.get("/callback")
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


@router.post("/token")
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


@router.get("/me", response_model=UserRead)
async def me(current_user: User = Depends(get_current_user)):
    return current_user

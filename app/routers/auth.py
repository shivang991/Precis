import secrets
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.auth_service import get_google_auth_url, login_with_google
from app.core.dependencies import get_current_user
from app.schemas.user import UserRead
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/login")
async def google_login():
    """Return the Google OAuth redirect URL for the client to navigate to."""
    state = secrets.token_urlsafe(16)
    return {"url": get_google_auth_url(state)}


@router.get("/callback")
async def google_callback(
    code: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Exchange Google auth code for a Precis JWT."""
    try:
        token = await login_with_google(db, code)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me", response_model=UserRead)
async def me(current_user: User = Depends(get_current_user)):
    return current_user

import uuid
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from app.shared.config import get_settings

settings = get_settings()


def create_access_token(user_id: uuid.UUID) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.jwt_access_token_expire_minutes
    )
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> uuid.UUID:
    """Raises JWTError if invalid or expired."""
    payload = jwt.decode(
        token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
    )
    user_id: str = payload.get("sub")
    if user_id is None:
        raise JWTError("Missing subject claim")
    return uuid.UUID(user_id)

import uuid
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from app.shared.config import get_settings


class AuthService:
    def __init__(self) -> None:
        settings = get_settings()
        self._secret_key = settings.jwt_secret_key
        self._algorithm = settings.jwt_algorithm
        self._expire_minutes = settings.jwt_access_token_expire_minutes

    def create_access_token(self, user_id: uuid.UUID) -> str:
        expire = datetime.now(timezone.utc) + timedelta(minutes=self._expire_minutes)
        payload = {"sub": str(user_id), "exp": expire}
        return jwt.encode(payload, self._secret_key, algorithm=self._algorithm)

    def decode_access_token(self, token: str) -> uuid.UUID:
        """Raises JWTError if invalid or expired."""
        payload = jwt.decode(token, self._secret_key, algorithms=[self._algorithm])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise JWTError("Missing subject claim")
        return uuid.UUID(user_id)

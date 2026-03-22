"""Unit tests for app/core/security.py — JWT round-trip, no DB required."""

import uuid
import time
import pytest
from jose import JWTError
from app.core.security import create_access_token, decode_access_token


def test_create_and_decode_roundtrip():
    user_id = uuid.uuid4()
    token = create_access_token(user_id)
    decoded = decode_access_token(token)
    assert decoded == user_id


def test_create_returns_string():
    token = create_access_token(uuid.uuid4())
    assert isinstance(token, str) and len(token) > 0


def test_decode_invalid_token_raises():
    with pytest.raises(JWTError):
        decode_access_token("not.a.valid.token")


def test_decode_tampered_token_raises():
    token = create_access_token(uuid.uuid4())
    tampered = token[:-4] + "xxxx"
    with pytest.raises(JWTError):
        decode_access_token(tampered)

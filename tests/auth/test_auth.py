from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.auth import require_user

def make_request() -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/test",
            "headers": [],
        }
    )

def test_require_user_returns_clerk_user_id(monkeypatch):
    fake_auth_state = SimpleNamespace(
        is_signed_in=True,
        payload={
            "sub": "user_test_123",
        },
    )

    monkeypatch.setattr(
        "app.auth.authenticate_request",
        lambda *args, **kwargs: fake_auth_state,
    )

    user_id = require_user(make_request())

    assert user_id == "user_test_123"

def test_require_user_rejects_unsigned_user(monkeypatch):
    fake_auth_state = SimpleNamespace(
        is_signed_in=False,
        payload={},
    )

    monkeypatch.setattr(
        "app.auth.authenticate_request",
        lambda *args, **kwargs: fake_auth_state,
    )

    with pytest.raises(HTTPException) as error:
        require_user(make_request())

    assert error.value.status_code == 401
    assert error.value.detail == "Unauthorized"

def test_require_user_rejects_token_without_user_id(
    monkeypatch,
):
    fake_auth_state = SimpleNamespace(
        is_signed_in=True,
        payload={},
    )

    monkeypatch.setattr(
        "app.auth.authenticate_request",
        lambda *args, **kwargs: fake_auth_state,
    )

    with pytest.raises(HTTPException) as error:
        require_user(make_request())

    assert error.value.status_code == 401
    assert error.value.detail == "Invalid authentication token"
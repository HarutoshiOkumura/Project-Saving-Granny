"""The shared app token the capture page (and later the dashboard) sends. Not a Supabase key."""

import secrets
from typing import Annotated

from fastapi import Header, HTTPException, status

from app.config import get_settings


def require_app_token(authorization: Annotated[str | None, Header()] = None) -> None:
    """`Authorization: Bearer <APP_TOKEN>`. Without APP_TOKEN set, every request is refused."""
    token = get_settings().app_token
    if token is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "APP_TOKEN is not set")
    expected = f"Bearer {token.get_secret_value()}".encode()
    if authorization is None or not secrets.compare_digest(authorization.encode(), expected):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "bad or missing token", {"WWW-Authenticate": "Bearer"}
        )

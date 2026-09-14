from fastapi import HTTPException, Request, status
from clerk_backend_api import (
    authenticate_request,
    AuthenticateRequestOptions,
)

from app.config import settings

def require_user(request: Request) -> str:
    auth_state = authenticate_request(
        request,
        AuthenticateRequestOptions(
            secret_key=settings.clerk_secret_key,
            jwt_key=settings.clerk_jwt_key,
            authorized_parties=settings.authorized_parties,
            accepts_token=["session_token"],
        ),
    )

    if not auth_state.is_signed_in:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
        )

    return auth_state.payload["sub"]
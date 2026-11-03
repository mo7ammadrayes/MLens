import logging
import uuid
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from backend.auth.supabase_jwt import AuthConfigurationError, verify_access_token
from backend.database.session import get_db
from backend.features.user.model import User
from backend.features.user.service import (
    AccountLinkError,
    get_or_create_auth_user,
)

logger = logging.getLogger(__name__)

# auto_error=False so a missing header returns 401 rather than 403.
bearer_scheme = HTTPBearer(
    auto_error=False,
    description="Supabase Auth access token",
)


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=401,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise _unauthorized("Not authenticated")

    try:
        claims = verify_access_token(credentials.credentials)
    except AuthConfigurationError as error:
        logger.error("Auth is misconfigured: %s", error)
        raise HTTPException(500, "Authentication is not configured") from error
    except jwt.PyJWKClientConnectionError as error:
        logger.exception("Could not fetch Supabase signing keys")
        raise HTTPException(
            503,
            "Could not verify the session; try again shortly",
        ) from error
    except jwt.ExpiredSignatureError as error:
        raise _unauthorized("Session expired; sign in again") from error
    except jwt.InvalidTokenError as error:
        raise _unauthorized("Invalid session token") from error

    if claims.get("role") != "authenticated":
        raise _unauthorized("Invalid session token")

    try:
        auth_id = uuid.UUID(claims["sub"])
    except (KeyError, ValueError) as error:
        raise _unauthorized("Invalid session token") from error

    metadata = claims.get("user_metadata") or {}

    try:
        return get_or_create_auth_user(
            db,
            auth_id=auth_id,
            email=claims.get("email"),
            name=metadata.get("name") or metadata.get("full_name"),
            email_verified=metadata.get("email_verified") is True,
        )
    except AccountLinkError as error:
        raise HTTPException(409, str(error)) from error


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_optional_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
    db: Session = Depends(get_db),
) -> User | None:
    """For public pages: the signed-in user, or None for anonymous visitors.

    An invalid or expired token is treated as anonymous rather than an error.
    """
    if credentials is None:
        return None
    try:
        return get_current_user(credentials, db)
    except HTTPException as error:
        if error.status_code in (401, 409):
            return None
        raise


OptionalUser = Annotated[User | None, Depends(get_optional_user)]

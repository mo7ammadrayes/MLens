"""Verification of Supabase Auth access tokens.

Supabase signs session JWTs either with asymmetric signing keys (ES256/RS256,
published at /auth/v1/.well-known/jwks.json) or, on older projects, with the
legacy shared HS256 JWT secret. Both are supported.
"""
import os
from functools import lru_cache
from pathlib import Path

import jwt
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

ASYMMETRIC_ALGORITHMS = ("ES256", "RS256", "EdDSA")


class AuthConfigurationError(RuntimeError):
    pass


def _supabase_url() -> str:
    url = os.getenv("SUPABASE_URL")
    if not url:
        raise AuthConfigurationError("SUPABASE_URL is not configured")
    return url.rstrip("/")


@lru_cache(maxsize=1)
def _jwks_client() -> jwt.PyJWKClient:
    headers = {}
    publishable_key = os.getenv("SUPABASE_PUBLISHABLE_KEY")
    if publishable_key:
        headers["apikey"] = publishable_key

    return jwt.PyJWKClient(
        f"{_supabase_url()}/auth/v1/.well-known/jwks.json",
        cache_keys=True,
        lifespan=600,
        headers=headers,
    )


def verify_access_token(token: str) -> dict:
    """Return the verified claims or raise jwt.InvalidTokenError."""
    header = jwt.get_unverified_header(token)
    algorithm = header.get("alg")

    if algorithm == "HS256":
        secret = os.getenv("SUPABASE_JWT_SECRET")
        if not secret:
            raise AuthConfigurationError(
                "This project signs tokens with the legacy JWT secret; "
                "set SUPABASE_JWT_SECRET"
            )
        key = secret
    elif algorithm in ASYMMETRIC_ALGORITHMS:
        key = _jwks_client().get_signing_key_from_jwt(token).key
    else:
        raise jwt.InvalidAlgorithmError(f"Unsupported token algorithm: {algorithm}")

    return jwt.decode(
        token,
        key,
        algorithms=[algorithm],
        audience="authenticated",
        issuer=f"{_supabase_url()}/auth/v1",
        leeway=30,
        options={"require": ["exp", "sub", "aud", "iss"]},
    )

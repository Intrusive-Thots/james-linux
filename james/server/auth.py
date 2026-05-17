"""
JAMES Authentication.

JWT-based token auth with bcrypt-hashed API key verification.
"""

import time
import hmac
import hashlib
import base64
import json
import logging
from typing import Optional

import bcrypt
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from james.server.config import ServerConfig

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)


def hash_api_key(api_key: str) -> str:
    """Hash an API key using bcrypt."""
    return bcrypt.hashpw(api_key.encode(), bcrypt.gensalt()).decode()


def verify_api_key(api_key: str, hashed: str) -> bool:
    """Verify an API key against its bcrypt hash."""
    try:
        return bcrypt.checkpw(api_key.encode(), hashed.encode())
    except Exception:
        return False


# ── Simple JWT (no external jose dependency) ────────────────────


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(s: str) -> bytes:
    padding = 4 - len(s) % 4
    s += "=" * padding
    return base64.urlsafe_b64decode(s)


def create_jwt(payload: dict, secret: str, expire_minutes: int = 1440) -> str:
    """Create a simple HMAC-SHA256 JWT."""
    header = {"alg": "HS256", "typ": "JWT"}
    payload = dict(payload)
    payload["exp"] = int(time.time()) + (expire_minutes * 60)
    payload["iat"] = int(time.time())

    header_b64 = _b64url_encode(json.dumps(header).encode())
    payload_b64 = _b64url_encode(json.dumps(payload).encode())
    message = f"{header_b64}.{payload_b64}"

    signature = hmac.new(
        secret.encode(), message.encode(), hashlib.sha256
    ).digest()
    sig_b64 = _b64url_encode(signature)

    return f"{message}.{sig_b64}"


def decode_jwt(token: str, secret: str) -> Optional[dict]:
    """Decode and verify a JWT. Returns payload or None."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None

        message = f"{parts[0]}.{parts[1]}"
        expected_sig = hmac.new(
            secret.encode(), message.encode(), hashlib.sha256
        ).digest()
        actual_sig = _b64url_decode(parts[2])

        if not hmac.compare_digest(expected_sig, actual_sig):
            return None

        payload = json.loads(_b64url_decode(parts[1]))

        # check expiry
        if payload.get("exp", 0) < time.time():
            return None

        return payload
    except Exception:
        return None


# ── FastAPI dependency ──────────────────────────────────────────


class AuthManager:
    """FastAPI-compatible auth dependency."""

    def __init__(self, config: ServerConfig):
        self.config = config

    async def __call__(
        self,
        request: Request,
        credentials: HTTPAuthorizationCredentials = Depends(security),
    ) -> dict:
        # skip auth if no API key configured
        if not self.config.api_key:
            return {"sub": "anonymous"}

        if credentials is None:
            raise HTTPException(
                status_code=401, detail="Missing authorization token"
            )

        payload = decode_jwt(credentials.credentials, self.config.jwt_secret)
        if payload is None:
            raise HTTPException(
                status_code=401, detail="Invalid or expired token"
            )

        return payload

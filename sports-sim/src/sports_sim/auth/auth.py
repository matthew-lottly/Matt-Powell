from __future__ import annotations

import os
import time
import json
import hmac
import hashlib
from base64 import urlsafe_b64encode, urlsafe_b64decode
from typing import Dict, Any

from fastapi import HTTPException, Header
from fastapi import Depends

# Simple in-memory user store for demo purposes
USERS = {
    "admin": {"password": "adminpass", "role": "admin"},
    "user": {"password": "userpass", "role": "user"},
    "editor": {"password": "editorpass", "role": "editor"},
}


def _secret() -> str:
    return os.getenv("SPORTS_SIM_AUTH_SECRET", "dev-secret")


def _now() -> int:
    return int(time.time())


def _b64encode(data: bytes) -> str:
    return urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64decode(s: str) -> bytes:
    # pad
    padding = "=" * (-len(s) % 4)
    return urlsafe_b64decode((s + padding).encode("ascii"))


def create_token(username: str, role: str, expires: int = 3600) -> str:
    payload = {"username": username, "role": role, "exp": _now() + expires}
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    sig = hmac.new(_secret().encode("utf-8"), raw, hashlib.sha256).digest()
    return f"{_b64encode(raw)}.{_b64encode(sig)}"


def verify_token(token: str) -> Dict[str, Any]:
    try:
        p, s = token.split(".")
        raw = _b64decode(p)
        sig = _b64decode(s)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token format")
    expected = hmac.new(_secret().encode("utf-8"), raw, hashlib.sha256).digest()
    if not hmac.compare_digest(expected, sig):
        raise HTTPException(status_code=401, detail="Invalid token signature")
    payload = json.loads(raw.decode("utf-8"))
    if payload.get("exp", 0) < _now():
        raise HTTPException(status_code=401, detail="Token expired")
    return payload


async def get_current_user(authorization: str | None = Header(None)) -> dict:
    """FastAPI dependency to return current user dict. If auth is disabled by env var,
    returns a guest user dict."""
    enabled = os.getenv("SPORTS_SIM_AUTH_ENABLED", "0") == "1"
    if not enabled:
        return {"username": "anonymous", "role": "guest"}
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid Authorization header")
    token = authorization.split(" ", 1)[1]
    payload = verify_token(token)
    return {"username": payload.get("username"), "role": payload.get("role")}


def authenticate(username: str, password: str) -> dict | None:
    u = USERS.get(username)
    if not u:
        return None
    if u["password"] != password:
        return None
    return {"username": username, "role": u["role"]}


def role_required(*roles: str):
    """Return a FastAPI dependency that enforces the current user's role is in `roles`."""
    async def _dep(current_user: dict = Depends(get_current_user)):
        # If auth is globally disabled, allow through (maintain previous behavior)
        enabled = os.getenv("SPORTS_SIM_AUTH_ENABLED", "0") == "1"
        if not enabled:
            return current_user
        if current_user is None:
            raise HTTPException(status_code=401, detail="Unauthorized")
        if current_user.get("role") not in roles:
            raise HTTPException(status_code=403, detail="Forbidden")
        return current_user

    return _dep

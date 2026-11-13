"""
NayBinho NAS — JWT Authentication Middleware.

Public routes (no token required):
  POST /api/auth/login
  GET  /api/health
  GET  /api/docs
  GET  /api/redoc
  GET  /api/openapi.json
"""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from jose import JWTError, jwt
from loguru import logger

from config import settings

PUBLIC_PATHS: set[str] = {
    "/api/auth/login",
    "/api/auth/logout",
    "/api/health",
    "/api/docs",
    "/api/redoc",
    "/api/openapi.json",
}

PUBLIC_PREFIXES: tuple[str, ...] = (
    "/api/docs",
    "/api/redoc",
    "/api/openapi.json",
)


def _is_public(path: str) -> bool:
    if path in PUBLIC_PATHS:
        return True
    return any(path.startswith(p) for p in PUBLIC_PREFIXES)


def decode_token(token: str) -> dict:
    """Decode and validate a JWT token. Raises JWTError on failure."""
    return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        if _is_public(path):
            return await call_next(request)

        # Extract Bearer token
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing or invalid Authorization header"},
            )

        token = auth_header.removeprefix("Bearer ").strip()
        try:
            payload = decode_token(token)
            # Attach user info to request state for downstream use
            request.state.user = payload
            request.state.username = payload.get("sub", "unknown")
            request.state.role = payload.get("role", "user")
        except JWTError as exc:
            logger.warning(f"JWT validation failed for {path}: {exc}")
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or expired token"},
            )

        return await call_next(request)

"""
NayBinho NAS — FastAPI main application entry point.
"""
from __future__ import annotations

import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from config import settings
from middleware.auth import AuthMiddleware
from routers import system, storage, docker_manager, apps_store, network, users


# ── Lifespan ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"🚀 {settings.app_name} v{settings.app_version} starting up…")
    # Ensure default admin user exists
    from services.user_service import ensure_default_admin
    await ensure_default_admin()
    yield
    logger.info("🛑 Shutting down NayBinho NAS backend.")


# ── Application factory ───────────────────────────────────────────────────────

def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="REST API for NayBinho NAS management interface",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    # ── CORS ─────────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Custom JWT auth middleware ────────────────────────────────────────────
    app.add_middleware(AuthMiddleware)

    # ── Routers ──────────────────────────────────────────────────────────────
    PREFIX = settings.api_prefix

    app.include_router(users.router,          prefix=PREFIX)
    app.include_router(system.router,         prefix=PREFIX)
    app.include_router(storage.router,        prefix=PREFIX)
    app.include_router(docker_manager.router, prefix=PREFIX)
    app.include_router(apps_store.router,     prefix=PREFIX)
    app.include_router(network.router,        prefix=PREFIX)

    # ── Global exception handler ──────────────────────────────────────────────
    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        logger.exception(f"Unhandled error on {request.url}: {exc}")
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "error": str(exc)},
        )

    # ── Health check ─────────────────────────────────────────────────────────
    @app.get("/api/health", tags=["health"])
    async def health():
        return {"status": "ok", "version": settings.app_version}

    return app


app = create_app()


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        workers=settings.workers,
        log_level="info",
    )

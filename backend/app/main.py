"""
main.py
-------
FastAPI application factory.

- Registers middleware (CORS, request size limit)
- Mounts routers
- Manages application lifespan (start/stop cleanup scheduler)
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.cleanup import CleanupScheduler
from app.core.config import settings
from app.routers import jobs

_scheduler = CleanupScheduler(
    interval_seconds=settings.cleanup_interval_seconds,
    ttl_minutes=settings.job_ttl_minutes,
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Start background scheduler on startup; stop it on shutdown."""
    _scheduler.start()
    yield
    _scheduler.stop()


def create_app() -> FastAPI:
    app = FastAPI(
        title="PDF Password Protector API",
        description="Stateless bulk PDF encryption service. No database — all state is ephemeral.",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # ── CORS ────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routers ─────────────────────────────────────────────────────────
    app.include_router(jobs.router)

    # ── Health check ────────────────────────────────────────────────────
    @app.get("/health", tags=["meta"])
    async def health() -> dict:
        return {"status": "ok", "service": "pdf-protector-api"}

    return app


app = create_app()

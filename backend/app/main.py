from pathlib import Path
from uuid import uuid4

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError
from sqlalchemy.exc import OperationalError
from starlette.exceptions import HTTPException as StarletteHTTPException

import app.modules  # noqa: F401
from app.api.platform.router import platform_router
from app.api.v1.router import api_router
from app.core.config import settings
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.modules.platform.services.bootstrap import (
    bootstrap_platform,
    seed_platform_billing_dev,
    seed_platform_dev,
)
from app.seed import bootstrap_production, seed_if_empty
from app.shared.errors import AppError, app_error_handler, http_error_handler, problem_body


logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    application = FastAPI(title=settings.app_name, version="0.1.0")
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origin_list or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Security middleware - Plan 06 implementation
    @application.middleware("http")
    async def security_middleware(request: Request, call_next):
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Cache-Control"] = "no-store, max-age=0"
        response.headers["Pragma"] = "no-cache"
        
        # Content Security Policy
        response.headers["Content-Security-Policy"] = "default-src 'self';"

        return response

    application.add_exception_handler(AppError, app_error_handler)
    application.add_exception_handler(StarletteHTTPException, http_error_handler)

    @application.exception_handler(RequestValidationError)
    async def request_validation_handler(request: Request, exc: RequestValidationError):
        from fastapi.responses import JSONResponse

        return JSONResponse(
            status_code=422,
            content=problem_body(
                request,
                422,
                "VALIDATION_ERROR",
                "Validation error",
                "The request failed validation.",
            ),
            media_type="application/problem+json",
        )

    @application.exception_handler(ValidationError)
    async def pydantic_validation_handler(request: Request, exc: ValidationError):
        from fastapi.responses import JSONResponse

        return JSONResponse(
            status_code=422,
            content=problem_body(
                request,
                422,
                "VALIDATION_ERROR",
                "Validation error",
                "The request failed validation.",
            ),
            media_type="application/problem+json",
        )

    @application.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        request.state.request_id = request.headers.get("X-Request-ID", str(uuid4()))
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    @application.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @application.get("/ready")
    def ready() -> dict:
        return {"status": "ready"}

    application.include_router(api_router, prefix="/api/v1")
    application.include_router(platform_router, prefix="/api/platform")
    return application


app = create_app()


@app.on_event("startup")
def on_startup() -> None:
    if settings.app_env == "production":
        # Platform realm is required in production. Fails fast on missing or
        # unsafe values; never invents a domain (PA-ADR-011).
        settings.validate_platform_config()
        # In production, schema shape is owned by Alembic, not create_all.
        # Fail fast when the deployed database is missing migrations instead of
        # silently mutating it, and warn when it has drifted from the models.
        from alembic.config import Config
        from alembic.script import ScriptDirectory
        from sqlalchemy import text

        from app.db.session import SessionLocal as _SessionLocal
        from app.db.session import engine as _engine

        alembic_root = Path(__file__).resolve().parents[1] / "alembic.ini"
        script = ScriptDirectory.from_config(Config(str(alembic_root)))
        head = script.get_current_head()
        db_check = SessionLocal()
        try:
            try:
                stamp = db_check.execute(
                    text("SELECT version_num FROM alembic_version")
                ).scalar_one_or_none()
            except OperationalError as exc:
                raise RuntimeError(
                    "Database is not migrated (alembic_version not found). "
                    "Run: alembic upgrade head"
                ) from exc
            if stamp != head:
                raise RuntimeError(
                    f"Database migration {stamp!r} is not head {head!r}. Run: alembic upgrade head"
                )
        finally:
            db_check.close()
        # Verify the connection the server will actually use, then bootstrap
        # the structural minimum (never demo data — see app/seed.py).
        _ = _engine  # fail fast early if engine cannot even be constructed
        db = _SessionLocal()
        try:
            bootstrap_platform(db, settings)
            from app.modules.platform.services.settings import ensure_defaults

            ensure_defaults(db)
            bootstrap_production(db, settings)
        finally:
            db.close()
    else:
        # Development and tests keep the fast create_all bootstrap.
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        try:
            seed_if_empty(db)
            seed_platform_dev(db, settings)
            seed_platform_billing_dev(db)
        finally:
            db.close()

    # Optional in-process FCM outbox worker (dev convenience).
    # Set FCM_WORKER_ENABLED=true to run the worker as a background daemon
    # thread inside the API process. For production, run the standalone
    # script (backend/run_fcm_worker.py) as a separate process instead.
    if settings.fcm_worker_enabled:
        from app.workers.fcm_outbox import FCMOutboxWorker
        import threading

        worker = FCMOutboxWorker()
        thread = threading.Thread(target=worker.run, daemon=True, name="fcm-outbox-worker")
        thread.start()
        logger.info("FCM outbox worker started in-process (dev mode)")

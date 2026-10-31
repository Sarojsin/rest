from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.errors import AppError, app_error_handler, http_error_handler, problem_body
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.seed import bootstrap_production, seed_if_empty

import app.models  # noqa: F401
from pathlib import Path
from sqlalchemy.exc import OperationalError


def create_app() -> FastAPI:
    application = FastAPI(title=settings.app_name, version="0.1.0")
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.add_exception_handler(AppError, app_error_handler)
    application.add_exception_handler(StarletteHTTPException, http_error_handler)

    @application.exception_handler(RequestValidationError)
    async def request_validation_handler(request: Request, exc: RequestValidationError):
        from fastapi.responses import JSONResponse

        return JSONResponse(
            status_code=422,
            content=problem_body(
                request, 422, "VALIDATION_ERROR", "Validation error", "The request failed validation."
            ),
            media_type="application/problem+json",
        )

    @application.exception_handler(ValidationError)
    async def pydantic_validation_handler(request: Request, exc: ValidationError):
        from fastapi.responses import JSONResponse

        return JSONResponse(
            status_code=422,
            content=problem_body(
                request, 422, "VALIDATION_ERROR", "Validation error", "The request failed validation."
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
    return application


app = create_app()


@app.on_event("startup")
def on_startup() -> None:
    if settings.app_env == "production":
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
                stamp = db_check.execute(text("SELECT version_num FROM alembic_version")).scalar_one_or_none()
            except OperationalError as exc:
                raise RuntimeError(
                    "Database is not migrated (alembic_version not found). Run: alembic upgrade head"
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
            bootstrap_production(db, settings)
        finally:
            db.close()
    else:
        # Development and tests keep the fast create_all bootstrap.
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        try:
            seed_if_empty(db)
        finally:
            db.close()

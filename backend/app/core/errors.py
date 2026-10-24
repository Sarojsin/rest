from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppError(Exception):
    def __init__(
        self,
        status: int,
        code: str,
        title: str,
        detail: str,
        extra: dict[str, Any] | None = None,
    ) -> None:
        self.status = status
        self.code = code
        self.title = title
        self.detail = detail
        self.extra = extra or {}


def problem_body(request: Request, status: int, code: str, title: str, detail: str) -> dict:
    request_id = getattr(request.state, "request_id", None)
    return {
        "type": f"https://api.restaurant.invalid/problems/{code.lower().replace('_', '-')}",
        "title": title,
        "status": status,
        "code": code,
        "detail": detail,
        "request_id": request_id,
    }


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status,
        content=problem_body(request, exc.status, exc.code, exc.title, exc.detail),
        media_type="application/problem+json",
    )


async def http_error_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    title = "Request failed"
    code = "HTTP_ERROR"
    if exc.status_code == 401:
        title, code = "Unauthorized", "UNAUTHORIZED"
    elif exc.status_code == 403:
        title, code = "Forbidden", "FORBIDDEN"
    elif exc.status_code == 404:
        title, code = "Not found", "NOT_FOUND"
    elif exc.status_code == 409:
        title, code = "Conflict", "CONFLICT"
    return JSONResponse(
        status_code=exc.status_code,
        content=problem_body(request, exc.status_code, code, title, str(exc.detail)),
        media_type="application/problem+json",
    )


async def validation_error_handler(request: Request, exc: ValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content=problem_body(
            request,
            422,
            "VALIDATION_ERROR",
            "Validation error",
            "The request body failed validation.",
        ),
        media_type="application/problem+json",
    )

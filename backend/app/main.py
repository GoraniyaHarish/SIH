"""FastAPI application factory: middleware, CORS, security headers, error handling."""
from __future__ import annotations

import time
import uuid

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.routers import admin, assessment, auth, dashboard, documents, framework, learning, quiz
from app.core.config import settings
from app.core.logging import configure_logging, get_logger, log_event

log = get_logger("http")

MAX_BODY_BYTES = 21 * 1024 * 1024  # uploads cap at 20 MB, plus multipart overhead


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Defence in depth for the browser: no sniffing, no framing, strict referrer and CSP."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
        response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        response.headers.setdefault("Cross-Origin-Resource-Policy", "same-origin")
        if request.url.path.startswith(settings.api_prefix):
            response.headers.setdefault("Cache-Control", "no-store")
            response.headers.setdefault(
                "Content-Security-Policy",
                "default-src 'none'; frame-ancestors 'none'; base-uri 'none'",
            )
        if settings.is_production:
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )
        return response


class BodySizeMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        length = request.headers.get("content-length")
        if length and length.isdigit() and int(length) > MAX_BODY_BYTES:
            return JSONResponse(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                content={"detail": "Request body too large"},
            )
        return await call_next(request)


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:16]
        started = time.perf_counter()
        response = await call_next(request)
        elapsed = int((time.perf_counter() - started) * 1000)
        response.headers["X-Request-ID"] = request_id
        response.headers["Server-Timing"] = f"app;dur={elapsed}"
        log_event(
            log, 20 if response.status_code < 400 else 30, "request",
            request_id=request_id, method=request.method, path=request.url.path,
            status=response.status_code, duration_ms=elapsed,
        )
        return response


def create_app() -> FastAPI:
    configure_logging()

    app = FastAPI(
        title="PRAMANA API",
        description=(
            "Competency intelligence and grounded learning platform for India's Official "
            "Statistical System (SIH 26101, MoSPI)."
        ),
        version=dashboard.VERSION,
        docs_url=f"{settings.api_prefix}/docs",
        redoc_url=None,
        openapi_url=f"{settings.api_prefix}/openapi.json",
    )

    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(BodySizeMiddleware)
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
        max_age=600,
    )

    for module in (auth, framework, assessment, learning, documents, quiz, dashboard, admin):
        app.include_router(module.router, prefix=settings.api_prefix)

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        # Field-level messages only: never echo the submitted value, which may be sensitive.
        errors = [
            {
                "field": ".".join(str(p) for p in err["loc"][1:]),
                "message": err["msg"],
                "type": err["type"],
            }
            for err in exc.errors()
        ]
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": "Validation failed", "errors": errors},
        )

    @app.exception_handler(Exception)
    async def unhandled(request: Request, exc: Exception):
        # Log the class only; no stack traces, paths or SQL reach the client.
        log.exception("unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={"detail": "An internal error occurred. Reference the request id when reporting."},
        )

    @app.get("/", include_in_schema=False)
    def root() -> dict:
        return {"service": "PRAMANA API", "version": dashboard.VERSION,
                "docs": f"{settings.api_prefix}/docs"}

    @app.on_event("startup")
    def _startup() -> None:
        warnings = __import__("app.core.deps", fromlist=["ensure_env_sane"]).ensure_env_sane()
        log_event(log, 20, "startup", env=settings.env, warnings=warnings,
                  ai_configured=settings.ai_configured)
        if settings.process_inline_worker:
            from app.worker import start_worker_thread

            start_worker_thread()

    return app


app = create_app()

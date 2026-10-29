import logging
from urllib.parse import urlparse
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from . import auth, catalog, inventory, reports, room_import
from .config import settings
from .db import Session

app = FastAPI(title="PrintTrack API", version="1.0.0", docs_url=None, redoc_url=None)
for router in (
    auth.router,
    catalog.router,
    inventory.router,
    reports.router,
    room_import.router,
):
    app.include_router(router)


@app.middleware("http")
async def browser_security(request: Request, call_next):
    origin = request.headers.get("origin")
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        # Same-origin only, including login; do not enable permissive CORS.
        if (
            origin and urlparse(origin).netloc != request.headers.get("host")
        ) or request.headers.get("sec-fetch-site") == "cross-site":
            return JSONResponse({"detail": "FORBIDDEN"}, status_code=403)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cache-Control"] = "no-store"
    return response


@app.exception_handler(RequestValidationError)
async def invalid_input(request, exc):
    # Never echo submitted passwords or other rejected values.
    return JSONResponse({"detail": "INVALID_INPUT"}, status_code=422)


@app.exception_handler(IntegrityError)
async def conflict(request, exc):
    return JSONResponse({"detail": "CONFLICT"}, status_code=409)


@app.exception_handler(SQLAlchemyError)
async def database_error(request, exc):
    logging.getLogger("printtrack").error(
        "Database operation failed (%s)", type(exc).__name__
    )
    return JSONResponse({"detail": "DATABASE_ERROR"}, status_code=503)


@app.get("/api/health")
def health():
    with Session() as db:
        db.execute(text("SELECT 1"))
    return {"status": "ok", "demo": settings.demo_mode}

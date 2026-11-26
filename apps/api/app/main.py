from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from .config import settings
from .core import AppError
from .db import Base, SessionLocal, engine
from .ratelimit import limiter
from .routers import common, hiring, manage, work


@asynccontextmanager
async def lifespan(_: FastAPI):
    from . import models  # noqa: F401
    if settings.database_url.startswith("sqlite"):
        Base.metadata.create_all(engine)  # 운영(MySQL)은 alembic upgrade head로 생성
    if settings.seed_on_empty:
        from .models import User
        with SessionLocal() as db:
            empty = db.query(User).count() == 0
        if empty:
            from .seed import reset_and_seed
            reset_and_seed()
    yield


app = FastAPI(title="my-vdream API", version="1.0.0", docs_url="/api/docs", openapi_url="/api/openapi.json", lifespan=lifespan)

app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limited(_: Request, e: RateLimitExceeded):
    return JSONResponse({"error": {"code": "RATE_LIMITED", "message": "요청이 너무 많습니다. 잠시 후 다시 시도해 주세요."}}, status_code=429)


app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins.split(","), allow_methods=["*"], allow_headers=["*"])


@app.exception_handler(AppError)
async def app_error(_: Request, e: AppError):
    return JSONResponse({"error": {"code": e.code, "message": e.message}}, status_code=e.status)


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, e: RequestValidationError):
    return JSONResponse({"error": {"code": "VALIDATION_ERROR", "message": "입력값을 확인해 주세요.", "details": e.errors()[:5]}}, status_code=422)


for r in (common.router, hiring.router, work.router, manage.router):
    app.include_router(r, prefix="/api/v1")


@app.get("/api/health")
def health():
    with engine.connect() as c:
        c.exec_driver_sql("SELECT 1")
    return {"status": "ok"}



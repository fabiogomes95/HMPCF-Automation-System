from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import router as v1_router
from app.core.config import settings
from app.core.exceptions import (
    BusinessRuleError,
    ConflictError,
    HMPCFError,
    NotFoundError,
    ValidationError,
)
from app.database.session import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    version="2.0.0",
    description="Plataforma hospitalar HMPCF — backend modular PostgreSQL",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(v1_router, prefix="/api/v1")


# ── Exception handlers ────────────────────────────────────────────────────────

@app.exception_handler(NotFoundError)
async def _not_found(request, exc: NotFoundError):
    return JSONResponse(status_code=404, content={"error": exc.code, "message": exc.message})


@app.exception_handler(ConflictError)
async def _conflict(request, exc: ConflictError):
    return JSONResponse(status_code=409, content={"error": exc.code, "message": exc.message})


@app.exception_handler(BusinessRuleError)
async def _business_rule(request, exc: BusinessRuleError):
    return JSONResponse(status_code=422, content={"error": exc.code, "message": exc.message})


@app.exception_handler(ValidationError)
async def _validation(request, exc: ValidationError):
    return JSONResponse(status_code=422, content={"error": exc.code, "message": exc.message})


@app.exception_handler(HMPCFError)
async def _hmpcf_generic(request, exc: HMPCFError):
    return JSONResponse(status_code=500, content={"error": exc.code, "message": exc.message})


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health", tags=["infra"])
async def health():
    return {"status": "ok", "app": settings.APP_NAME, "env": settings.ENVIRONMENT}

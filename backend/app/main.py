from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import router as v1_router
from app.core.config import settings
from app.core.exceptions import (
    BusinessRuleError,
    ConflictError,
    ForbiddenError,
    HMPCFError,
    NotFoundError,
    UnauthorizedError,
    ValidationError,
)
from app.database.session import engine

DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    version="2.0.0",
    description="Plataforma hospitalar HMPCF — backend modular PostgreSQL",
    lifespan=lifespan,
    # Oculta documentação em produção
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None if settings.is_production else "/redoc",
    openapi_url=None if settings.is_production else "/openapi.json",
)

# GZip comprime respostas JSON e arquivos de texto >= 1 KB
app.add_middleware(GZipMiddleware, minimum_size=1000)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(v1_router, prefix="/api/v1")


# ── Exception handlers ────────────────────────────────────────────────────────

@app.exception_handler(UnauthorizedError)
async def _unauthorized(request, exc: UnauthorizedError):
    return JSONResponse(status_code=401, content={"error": exc.code, "message": exc.message})


@app.exception_handler(ForbiddenError)
async def _forbidden(request, exc: ForbiddenError):
    return JSONResponse(status_code=403, content={"error": exc.code, "message": exc.message})


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


@app.exception_handler(RequestValidationError)
async def _pydantic_validation(request: Request, exc: RequestValidationError):
    """Converte erros de validação Pydantic em mensagem legível."""
    erros = exc.errors()
    if erros:
        primeiro = erros[0]
        campo = " → ".join(str(p) for p in primeiro.get("loc", []) if p != "body")
        msg = primeiro.get("msg", "Dados inválidos")
        msg = msg.removeprefix("Value error, ")
        detail = f"{msg} (campo: {campo})" if campo else msg
    else:
        detail = "Dados inválidos"
    return JSONResponse(status_code=422, content={"detail": detail})


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health", tags=["infra"])
async def health():
    return {"status": "ok", "app": settings.APP_NAME, "env": settings.ENVIRONMENT}


# ── Frontend estático (produção) ──────────────────────────────────────────────
# Montado APÓS as rotas de API para não conflitar.
# Só ativa se o build Vite existir (frontend/dist/).

if DIST.exists():
    # /assets/ → bundles JS/CSS com hash (cache longo)
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="static-assets")

    # /img/ → imagens públicas copiadas do public/
    if (DIST / "img").exists():
        app.mount("/img", StaticFiles(directory=DIST / "img"), name="static-img")

    _NO_CACHE = {"Cache-Control": "no-cache, no-store, must-revalidate", "Pragma": "no-cache"}

    @app.get("/", include_in_schema=False)
    async def serve_index():
        return FileResponse(DIST / "index.html", headers=_NO_CACHE)

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        """Serve arquivos estáticos existentes ou index.html para rotas React."""
        p = DIST / full_path
        if p.is_file():
            return FileResponse(p)
        return FileResponse(DIST / "index.html", headers=_NO_CACHE)

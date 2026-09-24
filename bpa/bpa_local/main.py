"""App FastAPI do BPA local (porta 8503, só 127.0.0.1)."""
import json
from contextlib import asynccontextmanager
from datetime import date

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from bpa_local import config, postgres
from bpa_local.api.rotas import router
from bpa_local.cache import cache
from bpa_local.services import backup_lotes, migracao_auto


@asynccontextmanager
async def lifespan(app: FastAPI):
    cache.carregar_tudo()
    migracao_auto.executar_se_preciso()  # 1ª abertura do dia: migra em segundo plano
    backup_lotes.iniciar()               # lotes de digitação -> servidor (e dali pro Google Drive)
    yield


app = FastAPI(
    title="BPA local HMPCF",
    lifespan=lifespan,
    docs_url=None, redoc_url=None, openapi_url=None,
)


# ── Quem pode chamar ──────────────────────────────────────────────────────────
@app.middleware("http")
async def origem_autorizada(request: Request, call_next):
    """Aceita só o sistema do hospital e a própria página local; responde o
    preflight do navegador e devolve os cabeçalhos de CORS / Private Network
    Access que o Chrome exige pra uma página da rede chamar o próprio PC."""
    origem = (request.headers.get("origin") or "").rstrip("/")
    do_sistema = origem in config.ORIGENS_SISTEMA
    if origem and not do_sistema and origem not in config.ORIGENS_LOCAIS:
        return JSONResponse({"ok": False, "erro": "Origem não autorizada"}, status_code=403)

    resp = Response(status_code=204) if request.method == "OPTIONS" else await call_next(request)
    if do_sistema:
        resp.headers["Access-Control-Allow-Origin"] = origem
        resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
        resp.headers["Access-Control-Allow-Private-Network"] = "true"
        resp.headers["Access-Control-Max-Age"] = "600"
        resp.headers["Vary"] = "Origin"
    return resp


app.include_router(router)


# ── Estado (pra aba BPA do sistema saber se o BPA local está vivo) ────────────
@app.get("/api/status")
def status():
    # A aba BPA consulta isto ao abrir e a cada 30 s -- também é o gatilho da
    # migração automática quando o BPA ficou ligado de um dia pro outro.
    migracao_auto.executar_se_preciso()
    return {
        "ok": not cache.erro,
        "pacientes": len(cache.pacientes),
        "profissionais": len(cache.profissionais),
        "erro_firebird": cache.erro,
        "migracao_auto": migracao_auto.estado(),
        "modo_teste": bool(config.POSTGRES_FALSO),  # pacientes falsos no lugar do Postgres
        "backup_lotes": backup_lotes.estado(),
    }


# ── Telas novas servidas pelo próprio BPA (sem o servidor do hospital) ────────
# Mesmas telas da aba BPA do sistema, montadas em bpa/ui/ por "npm run build:bpa".
# Modo offline: se a rede do hospital cair, o faturamento continua por aqui.
_UI = config.BASE / "ui"
if (_UI / "assets").exists():
    app.mount("/ui/assets", StaticFiles(directory=_UI / "assets"), name="ui-assets")


@app.get("/ui", include_in_schema=False)
def ui_sem_barra():
    return RedirectResponse("/ui/")


@app.get("/ui/", include_in_schema=False)
def ui():
    return FileResponse(_UI / "bpa-local.html", headers={"Cache-Control": "no-cache"})


# ── Página atual (Bootstrap) — sai quando a aba BPA do sistema estiver pronta ─
if config.ASSETS.exists():
    app.mount("/assets", StaticFiles(directory=config.ASSETS), name="assets")

_templates = Jinja2Templates(directory=str(config.TEMPLATES))


@app.get("/", include_in_schema=False)
def index(request: Request):
    competencias = postgres.competencias_disponiveis() or [{
        "value": date.today().strftime("%Y%m"),
        "label": postgres.nome_mes(date.today().month, date.today().year),
    }]
    return _templates.TemplateResponse(request, "index.html", {
        "total": len(cache.pacientes),
        "erro_firebird": cache.erro,
        "profissionais_json": json.dumps(cache.profissionais, ensure_ascii=False),
        "competencias": competencias,
        "mes_atual": competencias[0]["value"],
    })

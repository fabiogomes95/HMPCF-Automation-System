import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import init_db
from database_pg import close_pool
from routes import pacientes, atendimentos, terminal
from routes import pacientes_pg

app = FastAPI(title="HMPCF API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# v1 — legado SQLite (intocado)
app.include_router(pacientes.router,    prefix="/api/v1/pacientes",    tags=["pacientes-sqlite"])
app.include_router(atendimentos.router, prefix="/api/v1/atendimentos", tags=["atendimentos"])
app.include_router(terminal.router,     prefix="/api/v1/terminal",     tags=["terminal"])

# v2 — novo PostgreSQL
app.include_router(pacientes_pg.router, prefix="/api/v2/pacientes", tags=["pacientes-pg"])


@app.on_event("startup")
def startup():
    init_db()


@app.on_event("shutdown")
def shutdown():
    close_pool()


@app.get("/api/v1/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)

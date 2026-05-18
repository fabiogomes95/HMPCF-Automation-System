"""
SESSION.PY — Gerenciamento de conexão com o banco de dados.

CONCEITOS IMPORTANTES:

  1. ENGINE — O "motor" que conecta Python ao banco de dados.
     Uma engine por aplicação. Criamos uma única vez.

  2. SESSION — O "carteiro" que leva e traz dados.
     Cada requisição web cria uma sessão e fecha ao final.
     Isso é chamado de "request-scoped session".

  3. SESSIONMAKER — A "fábrica de carteiros".
     Em vez de criar session direto, usamos SessionLocal().

FLUXO TÍPICO:
  1. Requisição chega no endpoint
  2. endpoint chama get_session()
  3. get_session() cria uma nova sessão
  4. endpoint faz consultas/inserções com a sessão
  5. Ao final, get_session() fecha a sessão automaticamente
  6. Isso funciona graças ao Generator (yield) do Python

  Código no endpoint:
    @router.get("/pacientes")
    def listar(session: Session = Depends(get_session)):
        return session.query(Paciente).all()
    # Quando a função termina, o Depends fecha a sessão

Nota técnica: O parâmetro check_same_thread=False é específico
para SQLite. Permite que o FastAPI (async) acesse o SQLite
de várias threads. Não é necessário para PostgreSQL.
"""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

# Cria o diretório de dados se não existir (onde fica o SQLite)
DATA_DIR: Path = settings.DATA_DIR
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ── ENGINE (motor do banco) ─────────────────────────────────
engine = create_engine(
    settings.DATABASE_URL,
    # SQLite não suporta acesso de múltiplas threads por padrão
    # check_same_thread=False permite acesso async
    connect_args={"check_same_thread": False}
    if "sqlite" in settings.DATABASE_URL
    else {},
    echo=settings.DEBUG,  # Mostra SQL no terminal se DEBUG=true
    pool_pre_ping=True,   # Verifica se conexão está viva antes de usar
)

# ── SESSIONMAKER (fábrica de sessões) ────────────────────────
# autocommit=False → controle manual de transações
# autoflush=False  → performance, flush explícito quando necessário
SessionLocal: sessionmaker[Session] = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)


# ── DEPENDÊNCIA FastAPI ──────────────────────────────────────
# Usada como: session: Session = Depends(get_session)
def get_session() -> Generator[Session, None, None]:
    """
    Gera uma sessão e garante fechamento ao final.

    O bloco try/finally é crucial:
      Se algo der errado (exception), a sessão ainda será fechada.
      Isso evita "vazamento de conexões" (connection leak).
    """
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

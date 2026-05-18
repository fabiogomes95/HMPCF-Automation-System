"""
BASE.PY — Clase base para todos os modelos do banco de dados.

CONCEITO: Declarative Base
  No SQLAlchemy, cada tabela do banco é representada por uma
  classe Python. Todas as classes herdam de "Base".

  Exemplo de modelo:
    class Paciente(Base):
        __tablename__ = "pacientes"
        nome: str
        cpf: str

  Isso cria automaticamente a tabela "pacientes" no banco.

O QUE ESTA BASE OFERECE:
  ✅ id (int, autoincremento, chave primária)
  ✅ created_at (datetime, preenchido automaticamente na criação)
  ✅ updated_at (datetime, atualizado automaticamente em alterações)
  ✅ dict() (método para converter objeto em dicionário)

Isso significa que todo modelo que herdar de Base já vem
com esses campos prontos — sem precisar redefinir em cada um.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """
    Base — Classe abstrata que serve de fundação para todos os modelos.

    abstract = True significa que o SQLAlchemy NÃO vai criar
    uma tabela chamada "Base". Apenas as classes filhas viram tabelas.
    """

    __abstract__ = True

    # ── Colunas padrão para TODAS as tabelas ────────────────
    # mapped_column(primary_key=True) = chave primária autoincremento
    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # Datetime com fuso horário, preenchido automaticamente
    # server_default=func.now() = o banco que preenche (mais preciso)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )

    # onupdate = atualiza toda vez que a linha é modificada
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )

    # ── Método utilitário ───────────────────────────────────
    def dict(self) -> dict[str, Any]:
        """
        Converte o objeto SQLAlchemy em dicionário Python.

        Útil para retornar JSON na API, já que o FastAPI
        entende dicionários nativamente.

        Uso:
            paciente = session.query(Paciente).first()
            return paciente.dict()
            # {"id": 1, "nome": "João", "created_at": "2026-...", ...}
        """
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

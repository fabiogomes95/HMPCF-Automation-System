from datetime import date, datetime, time
from typing import Optional

from sqlalchemy import Date, DateTime, Index, Integer, String, Time, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class AtendimentoPlanilha(Base):
    """Entradas das planilhas manuais da recepção (ago/2021 em diante — antes do
    sistema). Só consulta: alimentada por `scripts/importar_planilhas_recepcao.py`,
    que apaga e recarrega tudo a cada importação; nunca editada pelo sistema.

    Serve pra aba Entradas (achar em que dias o paciente veio e localizar o
    boletim impresso). Nada aqui se mistura com `recepcao_atendimentos`.
    """

    __tablename__ = "atendimentos_planilha"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    data: Mapped[date] = mapped_column(Date, nullable=False)          # dia em que chegou (calendário)
    hora: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    nome: Mapped[str] = mapped_column(String(150), nullable=False)
    nome_busca: Mapped[str] = mapped_column(String(150), nullable=False)  # sem acento, maiúsculo
    cpf: Mapped[Optional[str]] = mapped_column(String(11), nullable=True)
    cns: Mapped[Optional[str]] = mapped_column(String(15), nullable=True)
    nascimento: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    arquivo: Mapped[str] = mapped_column(String(150), nullable=False)
    aba: Mapped[str] = mapped_column(String(60), nullable=False)
    linha: Mapped[int] = mapped_column(Integer, nullable=False)
    importado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("idx_atp_cpf", "cpf"),
        Index("idx_atp_nome_busca", "nome_busca"),
        Index("idx_atp_data", "data"),
    )

from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class LogAuditoria(Base):
    """
    Registro de escrita (criar/atualizar/remover) em pacientes/atendimentos.
    Só metadados — nunca CPF/CNS/endereço/dado de saúde em si (mesmo
    cuidado já adotado pros logs de aplicação, ver docs/HISTORICO.md).

    `usuario_username` é denormalizado de propósito: sobrevive a
    desativação/exclusão da conta que fez a ação (por isso `usuario_id`
    é SET NULL, não CASCADE — apagar uma conta não pode apagar o
    histórico dela).
    """

    __tablename__ = "logs_auditoria"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    usuario_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
    )
    usuario_username: Mapped[str] = mapped_column(String(50), nullable=False)

    acao:    Mapped[str] = mapped_column(String(20), nullable=False)  # criar | atualizar | remover
    recurso: Mapped[str] = mapped_column(String(30), nullable=False)  # paciente | atendimento
    recurso_id: Mapped[int] = mapped_column(Integer, nullable=False)

    campos_alterados: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)

    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("idx_logs_auditoria_recurso", "recurso", "recurso_id"),
        Index("idx_logs_auditoria_criado_em", "criado_em"),
    )

    def __repr__(self) -> str:
        return (
            f"<LogAuditoria id={self.id} {self.acao} {self.recurso}#{self.recurso_id} "
            f"por={self.usuario_username!r}>"
        )

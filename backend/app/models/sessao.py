from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.usuario import Usuario


class Sessao(Base):
    """
    Sessão de login ativa. O cookie do navegador guarda só o token bruto;
    aqui fica o hash SHA-256 dele — nunca o token em texto puro (uma
    leitura do banco não é suficiente pra forjar um cookie válido).
    """

    __tablename__ = "sessoes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    usuario_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("usuarios.id", ondelete="CASCADE"),
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)

    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expira_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ip_criacao: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)

    usuario: Mapped["Usuario"] = relationship("Usuario", lazy="joined")

    __table_args__ = (
        Index("idx_sessoes_expira_em", "expira_em"),
    )

    def __repr__(self) -> str:
        return f"<Sessao id={self.id} usuario_id={self.usuario_id} expira_em={self.expira_em}>"

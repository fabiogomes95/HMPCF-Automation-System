import enum
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Index, SmallInteger, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.paciente import Paciente


class ClassificacaoRisco(str, enum.Enum):
    VERMELHO = "VERMELHO"
    LARANJA  = "LARANJA"
    AMARELO  = "AMARELO"
    VERDE    = "VERDE"
    AZUL     = "AZUL"


class RecepcaoAtendimento(Base):
    """
    Ficha de atendimento registrada manualmente pela recepção.
    Armazena, organiza e permite consulta — sem automação clínica.
    """

    __tablename__ = "recepcao_atendimentos"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    paciente_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("pacientes.id", ondelete="RESTRICT"),
        nullable=False,
    )

    data_atendimento: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    classificacao_risco: Mapped[Optional[str]] = mapped_column(
        Enum(ClassificacaoRisco, name="classificacao_risco_enum", create_type=True),
        nullable=True,
    )

    registro:             Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    procedencia:          Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    observacoes:          Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    historia_clinica:     Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    hipotese_diagnostica: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # ── Relacionamento ─────────────────────────────────────────────────────────
    paciente: Mapped["Paciente"] = relationship(
        "Paciente",
        back_populates="atendimentos",
        lazy="noload",   # carregado explicitamente com selectinload quando necessário
    )

    __table_args__ = (
        Index("idx_rec_paciente_id",        "paciente_id"),
        Index("idx_rec_data_atendimento",   "data_atendimento"),
    )

    def __repr__(self) -> str:
        return (
            f"<RecepcaoAtendimento id={self.id} "
            f"paciente_id={self.paciente_id} "
            f"risco={self.classificacao_risco}>"
        )

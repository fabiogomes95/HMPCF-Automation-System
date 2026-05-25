from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.recepcao_atendimento import RecepcaoAtendimento


class Paciente(Base):
    __tablename__ = "pacientes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Padrão CADCNS / BPA-SUS
    cns:          Mapped[Optional[str]] = mapped_column(String(15), nullable=True, unique=True)
    num_cpf:      Mapped[Optional[str]] = mapped_column(String(11), nullable=True)
    nome:         Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    dtnasc:       Mapped[Optional[str]] = mapped_column(String(8),  nullable=True)
    sexo:         Mapped[Optional[str]] = mapped_column(String(1),  nullable=True)
    raca:         Mapped[Optional[str]] = mapped_column(String(2),  nullable=True)
    maepcn:       Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    logpcn:       Mapped[str]           = mapped_column(String(50), nullable=False, server_default="PRINCIPAL")
    numpcn:       Mapped[str]           = mapped_column(String(5),  nullable=False, server_default="S/N")
    bairro_pcnte: Mapped[str]           = mapped_column(String(50), nullable=False, server_default="CENTRO")
    nmres:        Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    ddtel_pcnte:  Mapped[Optional[str]] = mapped_column(String(2),  nullable=True)
    tel_pcnte:    Mapped[Optional[str]] = mapped_column(String(9),  nullable=True)
    ibge:         Mapped[Optional[str]] = mapped_column(String(6),  nullable=True)
    ceppcn:       Mapped[Optional[str]] = mapped_column(String(8),  nullable=True)
    co_lograd:    Mapped[Optional[str]] = mapped_column(String(3),  nullable=True)

    # Campos extras HMPCF
    nome_social:   Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    idade:         Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    civil:         Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    ocupacao:      Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    responsavel:   Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    cidade:        Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    estado:        Mapped[Optional[str]] = mapped_column(String(2),  nullable=True)
    nacionalidade: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    migrated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    atendimentos: Mapped[list["RecepcaoAtendimento"]] = relationship(
        "RecepcaoAtendimento",
        back_populates="paciente",
        lazy="noload",
    )

    __table_args__ = (
        Index("idx_pac_cpf",  "num_cpf"),
        Index("idx_pac_cns",  "cns"),
        Index("idx_pac_nome", "nome"),
    )

    def __repr__(self) -> str:
        return f"<Paciente id={self.id} cpf={self.num_cpf} nome={self.nome!r}>"

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, DateTime, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.recepcao_atendimento import RecepcaoAtendimento


class Paciente(Base):
    """
    Tabela pacientes — padrão Firebird/CADCNS com campos extras do HMPCF.

    Os nomes das colunas em maiúsculas seguem o padrão CADCNS/Firebird do legado.
    Os atributos Python usam snake_case via mapeamento explícito.
    """

    __tablename__ = "pacientes"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # ── Padrão CADCNS ─────────────────────────────────────────────────────────
    cns: Mapped[Optional[str]] = mapped_column("CNS", Text, nullable=True)
    num_cpf: Mapped[Optional[str]] = mapped_column("NUM_CPF", String(11), nullable=True)
    nome: Mapped[Optional[str]] = mapped_column("NOME", Text, nullable=True)
    dtnasc: Mapped[Optional[str]] = mapped_column("DTNASC", String(8), nullable=True)
    sexo: Mapped[Optional[str]] = mapped_column("SEXO", String(1), nullable=True)
    raca: Mapped[Optional[str]] = mapped_column("RACA", String(2), nullable=True)
    maepcn: Mapped[Optional[str]] = mapped_column("MAEPCN", Text, nullable=True)
    logpcn: Mapped[str] = mapped_column("LOGPCN", Text, nullable=False, server_default="principal")
    numpcn: Mapped[str] = mapped_column("NUMPCN", Text, nullable=False, server_default="s/n")
    bairro_pcnte: Mapped[str] = mapped_column("BAIRRO_PCNTE", Text, nullable=False, server_default="centro")
    nmres: Mapped[Optional[str]] = mapped_column("NMRES", Text, nullable=True)
    ddtel_pcnte: Mapped[Optional[str]] = mapped_column("DDTEL_PCNTE", String(3), nullable=True)
    tel_pcnte: Mapped[Optional[str]] = mapped_column("TEL_PCNTE", String(12), nullable=True)

    # ── Campos extras HMPCF ───────────────────────────────────────────────────
    nome_social: Mapped[Optional[str]] = mapped_column("nomeSocial", Text, nullable=True)
    idade: Mapped[Optional[str]] = mapped_column("idade", Text, nullable=True)
    civil: Mapped[Optional[str]] = mapped_column("civil", Text, nullable=True)
    ocupacao: Mapped[Optional[str]] = mapped_column("ocupacao", Text, nullable=True)
    responsavel: Mapped[Optional[str]] = mapped_column("responsavel", Text, nullable=True)
    cidade: Mapped[Optional[str]] = mapped_column("cidade", Text, nullable=True)
    estado: Mapped[Optional[str]] = mapped_column("estado", String(2), nullable=True)

    # ── Metadados ─────────────────────────────────────────────────────────────
    migrated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # ── Relacionamentos ────────────────────────────────────────────────────────
    atendimentos: Mapped[list["RecepcaoAtendimento"]] = relationship(
        "RecepcaoAtendimento",
        back_populates="paciente",
        lazy="noload",
    )

    __table_args__ = (
        Index("idx_pac_cpf", "NUM_CPF"),
        Index("idx_pac_cns", "CNS"),
        Index("idx_pac_nome", "NOME"),
    )

    def __repr__(self) -> str:
        return f"<Paciente id={self.id} cpf={self.num_cpf} nome={self.nome!r}>"

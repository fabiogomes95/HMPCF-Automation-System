from sqlalchemy import CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin


class Paciente(Base, TimestampMixin):
    __tablename__ = "pacientes"

    __table_args__ = (
        CheckConstraint("sexo IN ('M','F','I')", name="ck_paciente_sexo"),
    )

    cns: Mapped[str | None] = mapped_column(unique=True)
    num_cpf: Mapped[str | None] = mapped_column(unique=True)

    nome: Mapped[str] = mapped_column(nullable=False)
    nome_social: Mapped[str | None]

    dtnasc: Mapped[str | None]
    sexo: Mapped[str | None]
    raca: Mapped[str | None]
    maepcn: Mapped[str | None]

    logpcn: Mapped[str | None]
    numpcn: Mapped[str | None]
    bairro_pcnte: Mapped[str | None]
    ceppcn: Mapped[str | None]

    cidade: Mapped[str | None]
    estado: Mapped[str | None]
    telefone: Mapped[str | None]

    ibge: Mapped[str] = mapped_column(default="240360")
    co_lograd: Mapped[str] = mapped_column(default="081")

    etnia: Mapped[str | None]
    nacionalidade: Mapped[str | None]
    estado_civil: Mapped[str | None]
    ocupacao: Mapped[str | None]
    responsavel: Mapped[str | None]

    atendimentos: Mapped[list["Atendimento"]] = relationship(
        back_populates="paciente"
    )

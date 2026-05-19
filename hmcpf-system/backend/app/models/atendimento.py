from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin


class Atendimento(Base, TimestampMixin):
    __tablename__ = "atendimentos"

    paciente_id: Mapped[int] = mapped_column(
        ForeignKey("pacientes.id"), nullable=False
    )
    data_atendimento: Mapped[str | None]
    hora_atendimento: Mapped[str | None]
    registro: Mapped[str | None]
    procedencia: Mapped[str | None]
    enviado_nuvem: Mapped[int] = mapped_column(default=0)

    paciente: Mapped["Paciente"] = relationship(back_populates="atendimentos")

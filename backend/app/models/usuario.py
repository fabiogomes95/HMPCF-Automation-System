from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, SmallInteger, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class Usuario(Base):
    """
    Conta de acesso à recepção. V1: login por papel (recepcao/coordenacao/
    bpa), não por pessoa — várias pessoas podem compartilhar o mesmo
    `username`. `password_hash` é sempre bcrypt, nunca texto puro.
    """

    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    username:      Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(60), nullable=False)
    role:          Mapped[str] = mapped_column(String(30), nullable=False)
    ativo:         Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

    tentativas_falhas: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="0")
    bloqueado_ate:     Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_login_at:     Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<Usuario id={self.id} username={self.username!r} role={self.role!r}>"

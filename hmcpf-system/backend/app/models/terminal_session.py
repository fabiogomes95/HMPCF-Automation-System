import uuid
from datetime import datetime

from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin


def _generate_session_id() -> str:
    return uuid.uuid4().hex[:16].upper()


class TerminalSession(Base, TimestampMixin):
    __tablename__ = "terminal_sessions"

    terminal_nome: Mapped[str] = mapped_column(unique=True, nullable=False)
    session_id: Mapped[str] = mapped_column(
        nullable=False, default=_generate_session_id
    )
    ip_address: Mapped[str | None]
    ativo: Mapped[int] = mapped_column(default=1)
    ultima_atividade: Mapped[str | None]

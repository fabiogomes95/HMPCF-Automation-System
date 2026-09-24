from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class BpaLoteBackup(Base):
    """Cópia dos lotes de digitação do BPA (DD-MM-AAAA.txt) de cada notebook.

    Os lotes só existem no notebook do faturamento; o BPA local manda cada
    arquivo pra cá quando muda (usuário `bpa_leitura`, que só pode escrever
    nesta tabela). Como fica no banco, entra no backup diário e vai pro
    Google Drive. Restaurar: bpa/ferramentas/restaurar_lotes.py.
    """

    __tablename__ = "bpa_lotes_backup"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    notebook: Mapped[str] = mapped_column(String(100), nullable=False)   # nome do PC
    arquivo: Mapped[str] = mapped_column(String(100), nullable=False)    # ex.: 22-09-2026.txt
    conteudo: Mapped[str] = mapped_column(Text, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    tamanho: Mapped[int] = mapped_column(Integer, nullable=False)
    modificado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)  # no notebook
    recebido_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (UniqueConstraint("notebook", "arquivo", name="uq_bpa_lote_notebook_arquivo"),)

from datetime import datetime
from typing import Optional

from app.schemas.common import BaseSchema


class LogAuditoriaResponse(BaseSchema):
    """Nunca inclui valor de campo nenhum — só metadados de quem/quando/o quê."""
    usuario_username: str
    acao: str
    recurso: str
    recurso_id: int
    campos_alterados: Optional[list[str]] = None
    criado_em: datetime

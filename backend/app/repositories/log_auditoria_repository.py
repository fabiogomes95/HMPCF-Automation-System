from app.models.log_auditoria import LogAuditoria
from app.repositories.base import BaseRepository


class LogAuditoriaRepository(BaseRepository[LogAuditoria]):
    model = LogAuditoria

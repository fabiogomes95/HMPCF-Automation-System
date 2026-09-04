from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.log_auditoria import LogAuditoria
from app.models.usuario import Usuario


class AuditoriaService:
    """
    Registra escritas (criar/atualizar/remover) em pacientes/atendimentos.
    Só metadados — nunca valor de campo (ver docstring de LogAuditoria).
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def registrar(
        self,
        usuario: Optional[Usuario],
        acao: str,
        recurso: str,
        recurso_id: int,
        campos_alterados: Optional[list[str]] = None,
    ) -> None:
        """Não grava nada se `usuario` for None — permite instanciar os
        services (Paciente/Recepcao) sem usuário em uso direto/testes,
        sem exigir HTTP no meio."""
        if usuario is None:
            return
        log = LogAuditoria(
            usuario_id=usuario.id,
            usuario_username=usuario.username,
            acao=acao,
            recurso=recurso,
            recurso_id=recurso_id,
            campos_alterados=campos_alterados,
        )
        self.session.add(log)
        await self.session.flush()

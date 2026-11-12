from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.log_auditoria import LogAuditoria
from app.models.usuario import Usuario


# Consultas (LGPD: "quem viu os dados desta pessoa?"). Ficam DIAS_CONSULTAS e
# saem sozinhas (apagar_consultas_antigas); escritas ficam pra sempre.
CONSULTAR = "consultar"      # abriu a ficha/histórico do paciente
BUSCAR_DOC = "buscar_doc"    # achou o paciente digitando CPF ou CNS
ACOES_CONSULTA = (CONSULTAR, BUSCAR_DOC)
DIAS_CONSULTAS = 365


class AuditoriaService:
    """
    Registra escritas (criar/atualizar/remover) em pacientes/atendimentos e
    consultas a dados de paciente (ACOES_CONSULTA).
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

    async def registrar_consulta(self, usuario: Optional[Usuario], paciente_id: int, acao: str = CONSULTAR) -> None:
        """Quem viu os dados do paciente -- sempre com recurso 'paciente', pra
        um único filtro achar todos os acessos a ele."""
        await self.registrar(usuario, acao, "paciente", paciente_id)

    async def apagar_consultas_antigas(self, dias: int = DIAS_CONSULTAS) -> int:
        """Apaga registros de CONSULTA com mais de `dias`; escritas não saem."""
        limite = datetime.now(timezone.utc) - timedelta(days=dias)
        result = await self.session.execute(
            delete(LogAuditoria).where(
                LogAuditoria.acao.in_(ACOES_CONSULTA), LogAuditoria.criado_em < limite,
            )
        )
        return result.rowcount or 0

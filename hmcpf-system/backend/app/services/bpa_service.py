"""
BPA_SERVICE.PY — Lógica de negócio do módulo BPA.

RESPONSABILIDADES (futuras):
  - Gerar arquivo BPA (formato SUS)
  - Calcular totais por procedimento
  - Validar dados antes da exportação
  - Integrar com Firebird e SQLite

PADRÃO: Service Layer
  A classe BPAService agrupa todas as operações relacionadas ao BPA.
  Cada método é uma operação de negócio atômica.

  Uso nos endpoints:
    service = BPAService()
    resultado = await service.get_summary()

  Vantagem: se a lógica mudar, mudamos só aqui, não nos endpoints.
"""

from __future__ import annotations


class BPAService:
    """
    Serviço de BPA — lógica de negócio do Boletim de Produção Ambulatorial.

    Por enquanto é um placeholder. Na Fase 2 será preenchido com
    a lógica real de:
      - Consultar procedimentos no banco
      - Agrupar por competência
      - Gerar arquivo no formato do SUS
      - Validar totais
    """

    @staticmethod
    async def get_summary() -> dict[str, str]:
        """
        Retorna um resumo do módulo BPA.

        Atualmente retorna placeholder.
        Futuramente retornará dados consolidados como:
          - Total de procedimentos no período
          - Quantidade por tipo
          - Última competência processada
          - Status do último envio
        """
        return {"message": "BPAService — ainda não implementado"}

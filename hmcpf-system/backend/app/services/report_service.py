"""
REPORT_SERVICE.PY — Lógica de negócio dos relatórios.

RESPONSABILIDADES (futuras):
  - Gerar PDFs com fpdf2
  - Gerar planilhas Excel com openpyxl
  - Gerar gráficos com matplotlib/seaborn
  - Calcular indicadores (médias, totais, comparativos)

PADRÃO: STATIC METHODS
  Métodos estáticos (que não precisam de self) são uma escolha
  intencional aqui: o serviço não mantém estado interno.
  Cada chamada é independente das outras.

  Se no futuro precisar de estado (ex: cache), é só remover o
  @staticmethod e usar self normalmente.
"""

from __future__ import annotations


class ReportService:
    """
    Serviço de Relatórios — geração de relatórios gerenciais.

    Placeholder inicial. Futuramente terá métodos como:
      - gerar_relatorio_mes(mes, ano) → bytes (PDF)
      - gerar_auditoria(inicio, fim) → bytes (PDF)
      - gerar_comparativo(meses) → bytes (Excel)
      - calcular_indicadores(inicio, fim) → dict
    """

    @staticmethod
    async def get_available() -> dict[str, str]:
        """
        Lista os tipos de relatório disponíveis.

        Atualmente retorna placeholder.
        Futuramente retornará algo como:
          {
            "disponiveis": ["mensal", "auditoria", "comparativo"],
            "formatos": ["pdf", "xlsx"]
          }
        """
        return {"message": "ReportService — ainda não implementado"}

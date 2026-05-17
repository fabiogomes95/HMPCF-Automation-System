"""
BASE.PY — Classe abstrata para todas as automações.

CONCEITO: ABSTRACT BASE CLASS (ABC)
  Uma classe abstrata é como um "contrato" ou "template".
  Define O QUE cada automação precisa fazer, mas não COMO.

  Vantagens:
    1. Padronização — todas as automações têm a mesma estrutura
    2. Garantia — se esquecer de implementar execute(), o Python
       dá erro na hora de instanciar (não só em runtime)
    3. Reutilização — métodos comuns ficam aqui na base

EXEMPLO DE USO FUTURO:
    class DigitacaoRPA(BaseAutomation):
        async def execute(self):
            # Lógica específica da digitação
            return {"status": "ok", "registros": 50}

    automation = DigitacaoRPA()
    result = await automation.execute()
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from logging import Logger

# Inicializa o logging (se já foi configurado, não duplica)
from app.core.logging import setup_logging

setup_logging()


class BaseAutomation(ABC):
    """
    BaseAutomation — Classe abstrata para todas as automações.

    Para criar uma nova automação:
      1. Crie um arquivo novo em automations/ (ex: digitacao_rpa.py)
      2. Crie uma classe que herde de BaseAutomation
      3. Implemente o método execute()

    Regras:
      - execute() é obrigatório (abstractmethod)
      - execute() deve retornar um dict com status e resultado
      - self.logger está disponível para logging
    """

    def __init__(self) -> None:
        """
        Inicializa a automação com um logger específico.

        O nome do logger é o nome da classe (ex: "DigitacaoRPA").
        Isso facilita identificar nos logs qual automação está rodando.
        """
        self.logger = Logger(self.__class__.__name__)

    @abstractmethod
    async def execute(self) -> dict:
        """
        Executa a automação.

        Todo método execute() deve retornar um dicionário com:
          - status: "ok" ou "error"
          - mensagem: descrição do resultado
          - dados específicos da automação (ex: registros processados)
        """

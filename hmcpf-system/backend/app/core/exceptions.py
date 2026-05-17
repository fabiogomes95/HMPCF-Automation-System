"""
EXCEPTIONS.PY — Erros personalizados do domínio HMPCF.

POR QUE CRIAR EXCEÇÕES PERSONALIZADAS?
  1. Código mais expressivo: raise NotFoundError() em vez de Exception()
  2. O FastAPI consegue capturar e retornar HTTP status code correto
  3. Facilita manutenção: cada erro tem seu tipo

HIERARQUIA:
  HMPCFError (base) → NotFoundError (404)
                     → ValidationError (422)
                     → DatabaseError (500)
                     → AutomationError (500)
                     → AuthenticationError (401)

Para capturar todas, use: except HMPCFError
Para capturar específico, use: except NotFoundError
"""

from __future__ import annotations


class HMPCFError(Exception):
    """
    Classe BASE para TODOS os erros do sistema HMPCF.

    Toda exception personalizada deve herdar desta classe.
    Isso permite capturar qualquer erro do sistema com um único except.
    """


class NotFoundError(HMPCFError):
    """Recurso não encontrado no banco de dados ou sistema."""


class ValidationError(HMPCFError):
    """
    Dados inválidos ou violação de regra de negócio.

    Exemplos:
      - CPF com formato inválido
      - Data de atendimento no futuro
      - Paciente duplicado
    """


class DatabaseError(HMPCFError):
    """
    Erro de conexão ou consulta no banco de dados.

    Exemplos:
      - SQLite corrompido
      - Timeout de conexão
      - Tabela não encontrada
    """


class AutomationError(HMPCFError):
    """Erro durante execução de automação (RPA, processamento em lote)."""


class AuthenticationError(HMPCFError):
    """Falha de autenticação ou autorização (login inválido, token expirado)."""

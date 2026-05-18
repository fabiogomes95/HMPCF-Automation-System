"""
Compatibilidade temporária — reexporta services do novo layout.

Os endpoints ainda importam `app.modules.recepcao.service`,
portanto este módulo apenas redireciona para os services
organizados em `app.services.recepcao/`.
"""

from app.services.recepcao import *  # noqa: F401, F403

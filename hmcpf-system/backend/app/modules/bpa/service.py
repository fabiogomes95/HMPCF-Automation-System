"""
Compatibilidade temporária — reexporta services do novo layout.
Os endpoints ainda importam `app.modules.bpa.service`,
portanto este módulo apenas redireciona para os services
organizados em `app.services.bpa/`.
"""
from app.services.bpa import *  # noqa: F401, F403

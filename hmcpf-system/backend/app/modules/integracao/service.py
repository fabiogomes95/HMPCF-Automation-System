"""
Compatibilidade temporária — reexporta services do novo layout.
Os endpoints ainda importam `app.modules.integracao.service`,
portanto este módulo apenas redireciona para os services
organizados em `app.services.integracao/`.
"""
from app.services.integracao import *  # noqa: F401, F403

# Compatibilidade para testes que importam helpers privados
from app.services.integracao.utils import (  # noqa: F401
    remove_accents as _remove_accents,
    apenas_numeros as _apenas_numeros,
    valida_cns as _valida_cns,
    dn_iso as _dn_iso,
    parse_endereco as _parse_endereco,
    format_telefone as _format_telefone,
    gerar_linha_bpa as _gerar_linha_bpa,
    salvar_buffer as _salvar_buffer,
)

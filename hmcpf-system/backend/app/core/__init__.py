"""
core/ — Configurações e fundação do sistema.

Tudo que é global e usado por todos os módulos fica aqui:
  - Config (variáveis de ambiente, paths)
  - Logging (arquivo + terminal)
  - Exceptions (erros personalizados do domínio)

Regra: nada em core/ deve importar de api/, services/ ou modules/.
Isso evita dependências circulares.
"""

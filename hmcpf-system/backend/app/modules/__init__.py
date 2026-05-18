"""
modules/ — Domínios de negócio do sistema.

CADA SUBPASTA É UM DOMÍNIO:

  recepcao/   → Cadastro de pacientes, atendimento, triagem
  bpa/        → Boletim de Produção Ambulatorial
  relatorios/ → Relatórios gerenciais e indicadores

DIFERENÇA ENTRE modules/ E services/:
  services/ → Lógica de negócio REUTILIZÁVEL entre módulos
  modules/  → Lógica ESPECÍFICA de cada domínio

  Exemplo:
    - BPAService (em services/) tem a lógica de gerar BPA
    - modules/bpa/ pode ter validações específicas do BPA
      que não fazem sentido em outros contextos

PADRÃO: CADA DOMÍNIO É INDEPENDENTE
  Um módulo pode importar services, mas não deve importar
  outros módulos. Isso evita dependência cruzada.
"""

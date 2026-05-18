"""
PACKAGE: app
=========================
Ponto de entrada do backend HMPCF.

Este diretório é o coração do servidor FastAPI.
Aqui dentro organizamos tudo em módulos especializados:

  api/        → Rotas REST (endpoints que o frontend chama)
  core/       → Configurações, logging, exceções personalizadas
  services/   → Lógica de negócio (regras, cálculos, validações)
  automations/ → Módulos de automação (RPA, processamento em lote)
  modules/    → Domínios do sistema (recepção, BPA, relatórios)
  models/     → Modelos SQLAlchemy (mapeamento do banco de dados)
  database/   → Conexão, sessões, base declarativa
  utils/      → Funções auxiliares reutilizáveis

FLUXO DE UMA REQUISIÇÃO:
  Frontend (React)
       ↓ HTTP
  Router (api/v1/*)
       ↓ chama
  Service (lógica de negócio)
       ↓ consulta
  Model / Database (SQLite)
       ↑ retorna
  Service processa e formata
       ↑ JSON
  Frontend renderiza

Esta separação é chamada de "arquitetura em camadas" (layered architecture)
e é o padrão usado em sistemas enterprise profissionais.
"""

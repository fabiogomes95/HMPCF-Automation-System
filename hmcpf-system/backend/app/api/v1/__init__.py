"""
v1/ — Primeira versão da API REST.

Convenção de nomenclatura:
  - Arquivos no plural: bpa.py, reports.py, pacientes.py
  - Rotas no plural: /api/v1/pacientes, /api/v1/bpa
  - Funções com verbos no infinitivo: listar, criar, atualizar, deletar

Padrão REST:
  GET    /recursos      → Listar
  POST   /recursos      → Criar
  GET    /recursos/{id} → Buscar por ID
  PUT    /recursos/{id} → Atualizar
  DELETE /recursos/{id} → Deletar
"""

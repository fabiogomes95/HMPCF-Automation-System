"""
api/ — Camada de REST API (interface HTTP).

ORGANIZAÇÃO POR VERSÃO:
  Usamos versionamento de API para não quebrar clientes existentes.
  v1/ = primeira versão (estável)
  v2/ = futura versão (quando precisar mudar sem quebrar v1)

PADRÃO: CADA ARQUIVO UM ROUTER
  health.py  → endpoints de healthcheck
  bpa.py     → endpoints do módulo BPA
  reports.py → endpoints de relatórios

  Cada arquivo define um APIRouter separado.
  O main.py importa todos e junta no app FastAPI.

COMO CRIAR UM NOVO ENDPOINT:
  1. Crie o arquivo (ex: pacientes.py)
  2. Defina o router:
       router = APIRouter(prefix="/pacientes", tags=["pacientes"])
  3. Crie as funções com @router.get(), @router.post(), etc.
  4. Importe e inclua no main.py:
       app.include_router(pacientes.router)
"""

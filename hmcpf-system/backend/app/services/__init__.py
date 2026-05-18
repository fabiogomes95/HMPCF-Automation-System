"""
services/ — Camada de lógica de negócio (Business Logic Layer).

POR QUE TER UMA CAMADA DE SERVIÇOS?
  Separa a lógica de negócio dos endpoints HTTP.

  SEM services (ruim):
    @router.get("/bpa")
    def listar():
        # 50 linhas de lógica aqui dentro
        # Difícil testar, difícil reutilizar

  COM services (bom):
    @router.get("/bpa")
    def listar(service: BPAService = Depends()):
        return service.listar()
    # Endpoint enxuto, lógica testável isoladamente

REGRAS:
  - Services NÃO sabem que HTTP existe
  - Services recebem e retornam dicionários/objetos simples
  - Services podem chamar outros services
  - Services podem chamar o banco de dados (models)
"""

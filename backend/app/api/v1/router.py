from fastapi import APIRouter

from app.api.v1.endpoints import pacientes, recepcao, terminal

router = APIRouter()

router.include_router(pacientes.router, prefix="/pacientes", tags=["pacientes"])
router.include_router(recepcao.router,  prefix="/recepcao",  tags=["recepcao"])
router.include_router(terminal.router,  prefix="/terminal",  tags=["terminal"])

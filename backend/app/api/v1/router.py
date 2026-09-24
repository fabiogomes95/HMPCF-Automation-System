from fastapi import APIRouter

from app.api.v1.endpoints import auditoria, auth, entradas, pacientes, recepcao, terminal, ti

router = APIRouter()

router.include_router(auth.router,      prefix="/auth",      tags=["auth"])
router.include_router(pacientes.router, prefix="/pacientes", tags=["pacientes"])
router.include_router(recepcao.router,  prefix="/recepcao",  tags=["recepcao"])
router.include_router(terminal.router,  prefix="/terminal",  tags=["terminal"])
router.include_router(auditoria.router, prefix="/auditoria", tags=["auditoria"])
router.include_router(ti.router,        prefix="/ti",        tags=["ti"])
router.include_router(entradas.router,  prefix="/entradas",  tags=["entradas"])

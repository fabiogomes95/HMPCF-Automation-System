from fastapi import HTTPException, status

from app.repositories.atendimento_repository import AtendimentoRepository
from app.repositories.paciente_repository import PacienteRepository
from app.schemas.atendimento import AtendimentoCreate, AtendimentoUpdate


class AtendimentoService:
    def __init__(
        self,
        repo: AtendimentoRepository,
        paciente_repo: PacienteRepository,
    ):
        self.repo = repo
        self.paciente_repo = paciente_repo

    def listar(self, skip: int = 0, limit: int = 100):
        return self.repo.listar(skip, limit)

    def buscar_por_id(self, id: int):
        atendimento = self.repo.buscar_por_id(id)
        if not atendimento:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Atendimento não encontrado",
            )
        return atendimento

    def listar_por_paciente(
        self, paciente_id: int, skip: int = 0, limit: int = 100
    ):
        paciente = self.paciente_repo.buscar_por_id(paciente_id)
        if not paciente:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Paciente não encontrado",
            )
        return self.repo.listar_por_paciente(paciente_id, skip, limit)

    def criar(self, data: AtendimentoCreate):
        dados = data.model_dump()
        paciente = self.paciente_repo.buscar_por_id(dados["paciente_id"])
        if not paciente:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Paciente não encontrado",
            )
        return self.repo.criar(dados)

    def atualizar(self, id: int, data: AtendimentoUpdate):
        atendimento = self.buscar_por_id(id)
        dados = data.model_dump(exclude_unset=True)
        return self.repo.atualizar(atendimento, dados)

    def deletar(self, id: int):
        atendimento = self.buscar_por_id(id)
        self.repo.deletar(atendimento)

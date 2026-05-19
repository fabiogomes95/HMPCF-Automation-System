from fastapi import HTTPException, status

from app.repositories.paciente_repository import PacienteRepository
from app.schemas.paciente import PacienteCreate, PacienteUpdate


class PacienteService:
    def __init__(self, repo: PacienteRepository):
        self.repo = repo

    def listar(self, skip: int = 0, limit: int = 100):
        return self.repo.listar(skip, limit)

    def buscar_por_documento(self, documento: str):
        paciente = self.repo.buscar_por_documento(documento)
        return paciente

    def buscar_por_id(self, id: int):
        paciente = self.repo.buscar_por_id(id)
        if not paciente:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Paciente não encontrado",
            )
        return paciente

    def criar(self, data: PacienteCreate):
        dados = data.model_dump(exclude_unset=True)

        if dados.get("num_cpf"):
            existente = self.repo.buscar_por_cpf(dados["num_cpf"])
            if existente:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="CPF já cadastrado",
                )

        if dados.get("cns"):
            existente = self.repo.buscar_por_cns(dados["cns"])
            if existente:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="CNS já cadastrado",
                )

        return self.repo.criar(dados)

    def atualizar(self, id: int, data: PacienteUpdate):
        paciente = self.buscar_por_id(id)
        dados = data.model_dump(exclude_unset=True)

        if dados.get("num_cpf"):
            existente = self.repo.buscar_por_cpf(dados["num_cpf"])
            if existente and existente.id != id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="CPF já cadastrado para outro paciente",
                )

        if dados.get("cns"):
            existente = self.repo.buscar_por_cns(dados["cns"])
            if existente and existente.id != id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="CNS já cadastrado para outro paciente",
                )

        return self.repo.atualizar(paciente, dados)

    def deletar(self, id: int):
        paciente = self.buscar_por_id(id)
        self.repo.deletar(paciente)

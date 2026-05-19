import re

from sqlalchemy.orm import Session

from app.models.paciente import Paciente


class PacienteRepository:
    def __init__(self, db: Session):
        self.db = db

    def listar(self, skip: int = 0, limit: int = 100) -> list[Paciente]:
        return self.db.query(Paciente).offset(skip).limit(limit).all()

    def buscar_por_id(self, id: int) -> Paciente | None:
        return self.db.query(Paciente).filter(Paciente.id == id).first()

    def buscar_por_cpf(self, num_cpf: str) -> Paciente | None:
        return self.db.query(Paciente).filter(
            Paciente.num_cpf == num_cpf
        ).first()

    def buscar_por_cns(self, cns: str) -> Paciente | None:
        return self.db.query(Paciente).filter(
            Paciente.cns == cns
        ).first()

    def buscar_por_documento(self, documento: str) -> Paciente | None:
        cleaned = re.sub(r"\D", "", documento)
        paciente = self.buscar_por_cpf(cleaned)
        if paciente:
            return paciente
        return self.buscar_por_cns(cleaned)

    def criar(self, data: dict) -> Paciente:
        paciente = Paciente(**data)
        self.db.add(paciente)
        self.db.commit()
        self.db.refresh(paciente)
        return paciente

    def atualizar(self, paciente: Paciente, data: dict) -> Paciente:
        for key, value in data.items():
            setattr(paciente, key, value)
        self.db.commit()
        self.db.refresh(paciente)
        return paciente

    def deletar(self, paciente: Paciente) -> None:
        self.db.delete(paciente)
        self.db.commit()

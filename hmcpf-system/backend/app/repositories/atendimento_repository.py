from sqlalchemy.orm import Session

from app.models.atendimento import Atendimento


class AtendimentoRepository:
    def __init__(self, db: Session):
        self.db = db

    def listar(self, skip: int = 0, limit: int = 100) -> list[Atendimento]:
        return (
            self.db.query(Atendimento)
            .offset(skip).limit(limit)
            .all()
        )

    def buscar_por_id(self, id: int) -> Atendimento | None:
        return (
            self.db.query(Atendimento)
            .filter(Atendimento.id == id)
            .first()
        )

    def listar_por_paciente(
        self, paciente_id: int, skip: int = 0, limit: int = 100
    ) -> list[Atendimento]:
        return (
            self.db.query(Atendimento)
            .filter(Atendimento.paciente_id == paciente_id)
            .offset(skip).limit(limit)
            .all()
        )

    def criar(self, data: dict) -> Atendimento:
        atendimento = Atendimento(**data)
        self.db.add(atendimento)
        self.db.commit()
        self.db.refresh(atendimento)
        return atendimento

    def atualizar(self, atendimento: Atendimento, data: dict) -> Atendimento:
        for key, value in data.items():
            setattr(atendimento, key, value)
        self.db.commit()
        self.db.refresh(atendimento)
        return atendimento

    def deletar(self, atendimento: Atendimento) -> None:
        self.db.delete(atendimento)
        self.db.commit()

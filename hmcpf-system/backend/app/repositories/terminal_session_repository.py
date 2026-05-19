from sqlalchemy.orm import Session

from app.models.terminal_session import TerminalSession


class TerminalSessionRepository:
    def __init__(self, db: Session):
        self.db = db

    def buscar_por_terminal(
        self, terminal_nome: str
    ) -> TerminalSession | None:
        return (
            self.db.query(TerminalSession)
            .filter(TerminalSession.terminal_nome == terminal_nome)
            .first()
        )

    def criar_ou_atualizar(self, data: dict) -> TerminalSession:
        nome = data["terminal_nome"]
        existente = self.buscar_por_terminal(nome)
        if existente:
            for key, value in data.items():
                setattr(existente, key, value)
            self.db.commit()
            self.db.refresh(existente)
            return existente
        sessao = TerminalSession(**data)
        self.db.add(sessao)
        self.db.commit()
        self.db.refresh(sessao)
        return sessao

    def atualizar_atividade(self, sessao: TerminalSession) -> TerminalSession:
        from datetime import datetime

        sessao.ultima_atividade = datetime.now().isoformat()
        self.db.commit()
        self.db.refresh(sessao)
        return sessao

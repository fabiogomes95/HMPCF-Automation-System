from app.repositories.terminal_session_repository import (
    TerminalSessionRepository,
)
from app.schemas.terminal_session import TerminalSessionCreate


class TerminalSessionService:
    def __init__(self, repo: TerminalSessionRepository):
        self.repo = repo

    def iniciar(
        self, data: TerminalSessionCreate
    ) -> dict:
        dados = data.model_dump(exclude_unset=True)
        sessao = self.repo.criar_ou_atualizar(dados)
        self.repo.atualizar_atividade(sessao)
        return {
            "terminal_nome": sessao.terminal_nome,
            "session_id": sessao.session_id,
            "ativo": bool(sessao.ativo),
        }

    def ping(self, terminal_nome: str) -> dict:
        sessao = self.repo.buscar_por_terminal(terminal_nome)
        if not sessao:
            return {"status": "unknown", "terminal": terminal_nome}
        self.repo.atualizar_atividade(sessao)
        return {
            "status": "ok",
            "terminal": sessao.terminal_nome,
            "ativo": bool(sessao.ativo),
        }

    def buscar(self, terminal_nome: str):
        sessao = self.repo.buscar_por_terminal(terminal_nome)
        return sessao

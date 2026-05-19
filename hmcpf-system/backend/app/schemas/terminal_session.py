from datetime import datetime

from pydantic import BaseModel, field_validator


def _strip_extra(v: str | None) -> str | None:
    if v is None:
        return None
    return " ".join(v.split())


class TerminalSessionCreate(BaseModel):
    terminal_nome: str
    ip_address: str | None = None

    @field_validator("terminal_nome")
    @classmethod
    def normalize(cls, v: str) -> str:
        return _strip_extra(v) or v


class TerminalSessionResponse(BaseModel):
    id: int
    terminal_nome: str
    session_id: str
    ip_address: str | None
    ativo: int
    ultima_atividade: str | None
    created_at: datetime | None
    updated_at: datetime | None

    model_config = {"from_attributes": True}

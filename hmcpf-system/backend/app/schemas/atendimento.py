from datetime import datetime

from pydantic import BaseModel, field_validator


def _strip_extra(v: str | None) -> str | None:
    if v is None:
        return None
    return " ".join(v.split())


class AtendimentoCreate(BaseModel):
    paciente_id: int
    data_atendimento: str | None = None
    hora_atendimento: str | None = None
    registro: str | None = None
    procedencia: str | None = None
    enviado_nuvem: int = 0

    @field_validator("registro", "procedencia")
    @classmethod
    def normalize_text(cls, v: str | None) -> str | None:
        return _strip_extra(v)


class AtendimentoUpdate(BaseModel):
    data_atendimento: str | None = None
    hora_atendimento: str | None = None
    registro: str | None = None
    procedencia: str | None = None
    enviado_nuvem: int | None = None

    @field_validator("registro", "procedencia")
    @classmethod
    def normalize_text(cls, v: str | None) -> str | None:
        return _strip_extra(v)


class AtendimentoResponse(BaseModel):
    id: int
    paciente_id: int
    data_atendimento: str | None
    hora_atendimento: str | None
    registro: str | None
    procedencia: str | None
    enviado_nuvem: int
    created_at: datetime | None
    updated_at: datetime | None

    model_config = {"from_attributes": True}

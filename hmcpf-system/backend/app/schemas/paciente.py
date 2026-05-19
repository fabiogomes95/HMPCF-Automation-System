import re
from datetime import datetime

from pydantic import BaseModel, field_validator


def _only_digits(v: str | None) -> str | None:
    if v is None:
        return None
    return re.sub(r"\D", "", v)


def _strip_extra(v: str | None) -> str | None:
    if v is None:
        return None
    return " ".join(v.split())


class PacienteCreate(BaseModel):
    cns: str | None = None
    num_cpf: str | None = None
    nome: str
    nome_social: str | None = None
    dtnasc: str | None = None
    sexo: str | None = None
    raca: str | None = None
    maepcn: str | None = None
    logpcn: str | None = None
    numpcn: str | None = None
    bairro_pcnte: str | None = None
    ceppcn: str | None = None
    cidade: str | None = None
    estado: str | None = None
    telefone: str | None = None
    ibge: str = "240360"
    co_lograd: str = "081"
    etnia: str | None = None
    nacionalidade: str | None = None
    estado_civil: str | None = None
    ocupacao: str | None = None
    responsavel: str | None = None

    @field_validator("cns", "num_cpf")
    @classmethod
    def digits_only(cls, v: str | None) -> str | None:
        return _only_digits(v)

    @field_validator("sexo")
    @classmethod
    def validate_sexo(cls, v: str | None) -> str | None:
        if v is not None and v.upper() not in ("M", "F", "I"):
            raise ValueError("sexo deve ser M, F ou I")
        return v.upper() if v else v

    @field_validator("nome", "nome_social", "maepcn", "logpcn",
                     "bairro_pcnte", "cidade", "raca", "etnia",
                     "nacionalidade", "ocupacao", "responsavel")
    @classmethod
    def normalize_text(cls, v: str | None) -> str | None:
        return _strip_extra(v)


class PacienteUpdate(BaseModel):
    cns: str | None = None
    num_cpf: str | None = None
    nome: str | None = None
    nome_social: str | None = None
    dtnasc: str | None = None
    sexo: str | None = None
    raca: str | None = None
    maepcn: str | None = None
    logpcn: str | None = None
    numpcn: str | None = None
    bairro_pcnte: str | None = None
    ceppcn: str | None = None
    cidade: str | None = None
    estado: str | None = None
    telefone: str | None = None
    ibge: str | None = None
    co_lograd: str | None = None
    etnia: str | None = None
    nacionalidade: str | None = None
    estado_civil: str | None = None
    ocupacao: str | None = None
    responsavel: str | None = None

    @field_validator("cns", "num_cpf")
    @classmethod
    def digits_only(cls, v: str | None) -> str | None:
        return _only_digits(v)

    @field_validator("sexo")
    @classmethod
    def validate_sexo(cls, v: str | None) -> str | None:
        if v is not None and v.upper() not in ("M", "F", "I"):
            raise ValueError("sexo deve ser M, F ou I")
        return v.upper() if v else v

    @field_validator("nome", "nome_social", "maepcn", "logpcn",
                     "bairro_pcnte", "cidade", "raca", "etnia",
                     "nacionalidade", "ocupacao", "responsavel")
    @classmethod
    def normalize_text(cls, v: str | None) -> str | None:
        return _strip_extra(v)


class PacienteResponse(BaseModel):
    id: int
    cns: str | None
    num_cpf: str | None
    nome: str
    nome_social: str | None
    dtnasc: str | None
    sexo: str | None
    raca: str | None
    maepcn: str | None
    logpcn: str | None
    numpcn: str | None
    bairro_pcnte: str | None
    ceppcn: str | None
    cidade: str | None
    estado: str | None
    telefone: str | None
    ibge: str
    co_lograd: str
    etnia: str | None
    nacionalidade: str | None
    estado_civil: str | None
    ocupacao: str | None
    responsavel: str | None
    created_at: datetime | None
    updated_at: datetime | None

    model_config = {"from_attributes": True}

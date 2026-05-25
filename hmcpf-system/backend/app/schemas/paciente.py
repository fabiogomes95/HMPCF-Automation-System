import re
from datetime import datetime
from typing import Optional
from pydantic import ConfigDict, Field, field_validator, model_validator
from app.schemas.common import BaseSchema


class PacienteCreate(BaseSchema):

    cns:          Optional[str] = None
    num_cpf:      Optional[str] = None
    nome:         Optional[str] = None
    dtnasc:       Optional[str] = None
    sexo:         Optional[str] = None
    raca:         Optional[str] = None
    maepcn:       Optional[str] = None
    logpcn:       str = Field(default="PRINCIPAL")
    numpcn:       str = Field(default="S/N")
    bairro_pcnte: str = Field(default="CENTRO")
    nmres:        Optional[str] = None
    ddtel_pcnte:  Optional[str] = None
    tel_pcnte:    Optional[str] = None
    ibge:         str = Field(default="240360")
    ceppcn:       str = Field(default="59575000")
    co_lograd:    str = Field(default="081")
    nome_social:  Optional[str] = None
    idade:        Optional[str] = None
    civil:        Optional[str] = None
    ocupacao:     Optional[str] = None
    responsavel:  Optional[str] = None
    cidade:       Optional[str] = None
    estado:       Optional[str] = None
    nacionalidade: str = Field(default="010")
    naturalidade: Optional[str] = None

    @field_validator("num_cpf", "cns", mode="before")
    @classmethod
    def _apenas_numeros(cls, v: object) -> Optional[str]:
        if v is None:
            return None
        limpo = re.sub(r"\D", "", str(v))
        return limpo or None

    @field_validator("nome", mode="before")
    @classmethod
    def _upper_nome(cls, v: object) -> Optional[str]:
        if v is None:
            return None
        return str(v).strip().upper() or None

    @field_validator("estado", mode="before")
    @classmethod
    def _upper_estado(cls, v: object) -> Optional[str]:
        if v is None:
            return None
        return str(v).strip().upper()[:2] or None

    @field_validator("sexo", mode="before")
    @classmethod
    def _normalizar_sexo(cls, v: object) -> Optional[str]:
        if v is None:
            return None
        s = str(v).strip().upper()
        return s if s in ("M", "F") else "I"

    @model_validator(mode="after")
    def _requer_identificador(self) -> "PacienteCreate":
        if not self.num_cpf and not self.cns:
            raise ValueError("Informe pelo menos CPF ou CNS")
        return self


class PacienteUpdate(BaseSchema):

    nome:         Optional[str] = None
    dtnasc:       Optional[str] = None
    sexo:         Optional[str] = None
    raca:         Optional[str] = None
    maepcn:       Optional[str] = None
    logpcn:       Optional[str] = None
    numpcn:       Optional[str] = None
    bairro_pcnte: Optional[str] = None
    nmres:        Optional[str] = None
    ddtel_pcnte:  Optional[str] = None
    tel_pcnte:    Optional[str] = None
    ibge:         Optional[str] = None
    ceppcn:       Optional[str] = None
    co_lograd:    Optional[str] = None
    nome_social:  Optional[str] = None
    idade:        Optional[str] = None
    civil:        Optional[str] = None
    ocupacao:     Optional[str] = None
    responsavel:  Optional[str] = None
    cidade:       Optional[str] = None
    estado:       Optional[str] = None
    nacionalidade: Optional[str] = None
    naturalidade: Optional[str] = None

    @field_validator("nome", mode="before")
    @classmethod
    def _upper_nome(cls, v: object) -> Optional[str]:
        if v is None:
            return None
        return str(v).strip().upper() or None

    @field_validator("estado", mode="before")
    @classmethod
    def _upper_estado(cls, v: object) -> Optional[str]:
        if v is None:
            return None
        return str(v).strip().upper()[:2] or None

    @field_validator("sexo", mode="before")
    @classmethod
    def _normalizar_sexo(cls, v: object) -> Optional[str]:
        if v is None:
            return None
        s = str(v).strip().upper()
        return s if s in ("M", "F") else "I"


class PacienteResponse(BaseSchema):

    model_config = ConfigDict(from_attributes=True)

    id:           int
    cns:          Optional[str] = None
    num_cpf:      Optional[str] = None
    nome:         Optional[str] = None
    dtnasc:       Optional[str] = None
    sexo:         Optional[str] = None
    raca:         Optional[str] = None
    maepcn:       Optional[str] = None
    logpcn:       str = "PRINCIPAL"
    numpcn:       str = "S/N"
    bairro_pcnte: str = "CENTRO"
    nmres:        Optional[str] = None
    ddtel_pcnte:  Optional[str] = None
    tel_pcnte:    Optional[str] = None
    ibge:         Optional[str] = None
    ceppcn:       Optional[str] = None
    co_lograd:    Optional[str] = None
    nome_social:  Optional[str] = None
    idade:        Optional[str] = None
    civil:        Optional[str] = None
    ocupacao:     Optional[str] = None
    responsavel:  Optional[str] = None
    cidade:       Optional[str] = None
    estado:       Optional[str] = None
    nacionalidade: str = "010"
    naturalidade: Optional[str] = None
    migrated_at:  Optional[datetime] = None

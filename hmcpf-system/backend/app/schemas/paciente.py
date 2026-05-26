import re
from datetime import date, datetime
from typing import Optional

from pydantic import ConfigDict, Field, field_validator, model_validator

from app.schemas.common import BaseSchema


# ── Funções de validação matemática ───────────────────────────────────────────

def _so_digitos(v: object) -> str:
    return re.sub(r"\D", "", str(v or ""))


def _validar_cpf(cpf: str) -> bool:
    d = _so_digitos(cpf)
    if len(d) != 11:
        return False
    if re.match(r"^(\d)\1{10}$", d):
        return False
    soma = sum(int(d[i]) * (10 - i) for i in range(9))
    resto = soma % 11
    dig1 = 0 if resto < 2 else 11 - resto
    if dig1 != int(d[9]):
        return False
    soma = sum(int(d[i]) * (11 - i) for i in range(10))
    resto = soma % 11
    dig2 = 0 if resto < 2 else 11 - resto
    return dig2 == int(d[10])


def _validar_cns(cns: str) -> bool:
    d = _so_digitos(cns)
    if len(d) != 15:
        return False
    if d[0] not in "12789":
        return False
    soma = sum(int(d[i]) * (15 - i) for i in range(15))
    return soma % 11 == 0


def _validar_dtnasc(dtnasc: str) -> bool:
    """Valida data no formato YYYYMMDD: deve existir, não ser futura, não ultrapassar 130 anos."""
    d = _so_digitos(dtnasc)
    if len(d) != 8:
        return False
    try:
        nasc = date(int(d[:4]), int(d[4:6]), int(d[6:8]))
    except ValueError:
        return False
    hoje = date.today()
    if nasc > hoje:
        return False
    if (hoje - nasc).days > 130 * 365:
        return False
    return True


# ── Schemas ────────────────────────────────────────────────────────────────────

class PacienteCreate(BaseSchema):

    cns:          Optional[str] = None
    num_cpf:      Optional[str] = None
    nome:         Optional[str] = None
    dtnasc:       Optional[str] = None
    sexo:         Optional[str] = None
    raca:         Optional[str] = None
    maepcn:       Optional[str] = None
    logpcn:       Optional[str] = None
    numpcn:       Optional[str] = None
    bairro_pcnte: Optional[str] = None
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
    def _normalizar_documento(cls, v: object) -> Optional[str]:
        if v is None:
            return None
        limpo = _so_digitos(v)
        return limpo or None

    @field_validator("num_cpf", mode="after")
    @classmethod
    def _checar_cpf(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        if not _validar_cpf(v):
            raise ValueError("CPF inválido")
        return v

    @field_validator("cns", mode="after")
    @classmethod
    def _checar_cns(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        if not _validar_cns(v):
            raise ValueError("CNS/SUS inválido")
        return v

    @field_validator("nome", mode="before")
    @classmethod
    def _checar_nome(cls, v: object) -> Optional[str]:
        if v is None:
            return None
        nome = str(v).strip().upper()
        if not nome:
            raise ValueError("Nome é obrigatório")
        if len(nome) < 3:
            raise ValueError("Nome muito curto (mínimo 3 caracteres)")
        return nome

    @field_validator("sexo", mode="before")
    @classmethod
    def _checar_sexo(cls, v: object) -> Optional[str]:
        if v is None:
            return None
        s = str(v).strip().upper()
        if s not in ("M", "F"):
            raise ValueError("Sexo deve ser M ou F")
        return s

    @field_validator("dtnasc", mode="before")
    @classmethod
    def _checar_dtnasc(cls, v: object) -> Optional[str]:
        if v is None:
            return None
        raw = str(v).strip()
        if not raw:
            return None
        if not _validar_dtnasc(raw):
            raise ValueError("Data de nascimento inválida — verifique se a data existe, não é futura e não ultrapassa 130 anos")
        return _so_digitos(raw)

    @field_validator("estado", mode="before")
    @classmethod
    def _upper_estado(cls, v: object) -> Optional[str]:
        if v is None:
            return None
        return str(v).strip().upper()[:2] or None

    @model_validator(mode="after")
    def _requer_campos_obrigatorios(self) -> "PacienteCreate":
        if not self.num_cpf and not self.cns:
            raise ValueError("Informe pelo menos um CPF ou CNS válido")
        if not self.nome:
            raise ValueError("Nome é obrigatório")
        if not self.sexo:
            raise ValueError("Sexo é obrigatório (M ou F)")
        if not self.dtnasc:
            raise ValueError("Data de nascimento é obrigatória")
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
    def _checar_nome(cls, v: object) -> Optional[str]:
        if v is None:
            return None
        nome = str(v).strip().upper()
        if not nome:
            return None
        if len(nome) < 3:
            raise ValueError("Nome muito curto (mínimo 3 caracteres)")
        return nome

    @field_validator("sexo", mode="before")
    @classmethod
    def _checar_sexo(cls, v: object) -> Optional[str]:
        if v is None:
            return None
        s = str(v).strip().upper()
        if s not in ("M", "F"):
            raise ValueError("Sexo deve ser M ou F")
        return s

    @field_validator("dtnasc", mode="before")
    @classmethod
    def _checar_dtnasc(cls, v: object) -> Optional[str]:
        if v is None:
            return None
        raw = str(v).strip()
        if not raw:
            return None
        if not _validar_dtnasc(raw):
            raise ValueError("Data de nascimento inválida — verifique se a data existe e não é futura")
        return _so_digitos(raw)

    @field_validator("estado", mode="before")
    @classmethod
    def _upper_estado(cls, v: object) -> Optional[str]:
        if v is None:
            return None
        return str(v).strip().upper()[:2] or None


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
    logpcn:       Optional[str] = None
    numpcn:       Optional[str] = None
    bairro_pcnte: Optional[str] = None
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

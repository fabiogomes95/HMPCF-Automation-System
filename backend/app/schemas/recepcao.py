from datetime import date, datetime
from typing import Optional
from zoneinfo import ZoneInfo

from pydantic import ConfigDict, Field, field_validator

from app.models.recepcao_atendimento import ClassificacaoRisco
from app.schemas.common import BaseSchema


_FUSO_HOSPITAL = ZoneInfo("America/Sao_Paulo")


def _hora_de_brasilia(v: Optional[datetime]) -> Optional[datetime]:
    """A tela manda "2026-11-11T14:00:00", sem fuso. Sem isto, quem decidia o
    fuso era o timezone do PostgreSQL -- num banco restaurado em UTC as horas
    novas sairiam 3 h erradas. Hora sem fuso é sempre a do hospital."""
    return v.replace(tzinfo=_FUSO_HOSPITAL) if v is not None and v.tzinfo is None else v


class PacienteResumo(BaseSchema):
    """Dados mínimos do paciente embutidos na ficha de atendimento."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: Optional[str] = None
    num_cpf: Optional[str] = None
    cns: Optional[str] = None
    dtnasc: Optional[str] = None
    cidade: Optional[str] = None


class RecepcaoCreate(BaseSchema):
    paciente_id: int = Field(..., description="ID do paciente vinculado")
    data_atendimento: Optional[datetime] = Field(
        default=None,
        description="Data/hora do atendimento (padrão: agora)",
    )
    registro:             Optional[int] = None
    classificacao_risco: Optional[ClassificacaoRisco] = None
    procedencia:          Optional[str] = None
    observacoes:          Optional[str] = None
    historia_clinica:     Optional[str] = None
    hipotese_diagnostica: Optional[str] = None

    @field_validator("data_atendimento")
    @classmethod
    def _fuso(cls, v: Optional[datetime]) -> Optional[datetime]:
        return _hora_de_brasilia(v)


class RecepcaoUpdate(BaseSchema):
    """Todos os campos opcionais — semântica PATCH."""

    # Troca o paciente do atendimento (edição na Recepção quando o CPF digitado
    # era de outro cadastro).
    paciente_id:          Optional[int] = None
    data_atendimento:     Optional[datetime] = None
    registro:             Optional[int] = None
    classificacao_risco:  Optional[ClassificacaoRisco] = None
    procedencia:          Optional[str] = None
    observacoes:          Optional[str] = None
    historia_clinica:     Optional[str] = None
    hipotese_diagnostica: Optional[str] = None

    @field_validator("data_atendimento")
    @classmethod
    def _fuso(cls, v: Optional[datetime]) -> Optional[datetime]:
        return _hora_de_brasilia(v)


class RecepcaoResponse(BaseSchema):
    model_config = ConfigDict(from_attributes=True)

    id: int
    paciente_id: int
    paciente: Optional[PacienteResumo] = None
    data_atendimento: datetime
    registro:             Optional[int] = None
    classificacao_risco: Optional[ClassificacaoRisco] = None
    procedencia:          Optional[str] = None
    observacoes:          Optional[str] = None
    historia_clinica:     Optional[str] = None
    hipotese_diagnostica: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class PacienteAgrupadoResponse(BaseSchema):
    """Paciente único com estatísticas de atendimento para busca agrupada."""
    model_config = ConfigDict(from_attributes=True)

    paciente_id: int
    nome: Optional[str] = None
    num_cpf: Optional[str] = None
    cns: Optional[str] = None
    dtnasc: Optional[str] = None
    total_entradas: int = 0
    ultima_data: Optional[datetime] = None


class PlanilhaAtendimentoResponse(BaseSchema):
    """Uma linha do relatório mensal estilo planilha (ver RecepcaoService.planilha_mensal)."""

    atendimento_id: int
    registro: Optional[int] = None
    data_atendimento: datetime
    nome: Optional[str] = None
    dtnasc: Optional[str] = None
    sexo: Optional[str] = None
    raca: Optional[str] = None
    cidade: Optional[str] = None
    num_cpf: Optional[str] = None
    cns: Optional[str] = None
    procedencia: Optional[str] = None
    endereco: Optional[str] = None
    telefone: Optional[str] = None
    dia_referencia: date
    turno: str


class PlanilhaMensalResponse(BaseSchema):
    ano: int
    mes: int
    total: int
    items: list[PlanilhaAtendimentoResponse]


class RecepcaoListResponse(BaseSchema):
    """Resposta compacta para listagens — sem campos de texto longo."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    paciente_id: int
    paciente: Optional[PacienteResumo] = None
    data_atendimento: datetime
    registro:             Optional[int] = None
    classificacao_risco: Optional[ClassificacaoRisco] = None
    procedencia: Optional[str] = None
    observacoes: Optional[str] = None
    created_at: datetime

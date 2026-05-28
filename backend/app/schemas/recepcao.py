from datetime import datetime
from typing import Optional

from pydantic import ConfigDict, Field

from app.models.recepcao_atendimento import ClassificacaoRisco
from app.schemas.common import BaseSchema


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


class RecepcaoUpdate(BaseSchema):
    """Todos os campos opcionais — semântica PATCH."""

    data_atendimento:     Optional[datetime] = None
    registro:             Optional[int] = None
    classificacao_risco:  Optional[ClassificacaoRisco] = None
    procedencia:          Optional[str] = None
    observacoes:          Optional[str] = None
    historia_clinica:     Optional[str] = None
    hipotese_diagnostica: Optional[str] = None


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

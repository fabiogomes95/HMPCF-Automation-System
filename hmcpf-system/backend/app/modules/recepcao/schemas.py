"""
SCHEMAS.PY — Modelos Pydantic para validação de dados da recepção.

Pydantic vs SQLAlchemy:
  SQLAlchemy models = como os dados são SALVOS no banco
  Pydantic schemas  = como os dados TRAFEGAM na API

  Separar os dois é uma boa prática:
  - O schema da API pode ser diferente do schema do banco
  - Podemos expor campos diferentes do que salvamos
  - Validação acontece antes de chegar no banco

COMO USAR NOS ENDPOINTS:
  @router.post("/pacientes", response_model=PacienteResponse)
  def criar(paciente: PacienteCreate, session=Depends(get_session)):
      db = Paciente(**paciente.model_dump())
      session.add(db)
      session.commit()
      return db
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── PACIENTES ─────────────────────────────────────────────────


class PacienteBase(BaseModel):
    """Campos comuns entre criar, listar e atualizar paciente."""

    cpf: str = Field(..., description="CPF do paciente (chave primária)")
    sus: Optional[str] = None
    nome: Optional[str] = None
    nome_social: Optional[str] = Field(None, alias="nomeSocial")
    naturalidade: Optional[str] = None
    dn: Optional[str] = None
    idade: Optional[str] = None
    sexo: Optional[str] = None
    civil: Optional[str] = None
    raca: Optional[str] = None
    ocupacao: Optional[str] = None
    mae: Optional[str] = None
    responsavel: Optional[str] = None
    tel: Optional[str] = None
    endereco: Optional[str] = None
    numero: Optional[str] = None
    bairro: Optional[str] = None
    cidade: Optional[str] = None
    estado: Optional[str] = None


class PacienteCreate(PacienteBase):
    """Usado no POST /pacientes — CPF é obrigatório."""

    cpf: str = Field(..., min_length=11, max_length=11)


class PacienteUpdate(BaseModel):
    """Usado no PUT /pacientes/{cpf} — todos os campos opcionais."""

    sus: Optional[str] = None
    nome: Optional[str] = None
    nome_social: Optional[str] = Field(None, alias="nomeSocial")
    naturalidade: Optional[str] = None
    dn: Optional[str] = None
    idade: Optional[str] = None
    sexo: Optional[str] = None
    civil: Optional[str] = None
    raca: Optional[str] = None
    ocupacao: Optional[str] = None
    mae: Optional[str] = None
    responsavel: Optional[str] = None
    tel: Optional[str] = None
    endereco: Optional[str] = None
    numero: Optional[str] = None
    bairro: Optional[str] = None
    cidade: Optional[str] = None
    estado: Optional[str] = None


class PacienteResponse(PacienteBase):
    """Retorno padrão para consultas de paciente."""

    model_config = {"from_attributes": True, "populate_by_name": True}


# ── ATENDIMENTOS ──────────────────────────────────────────────


class AtendimentoBase(BaseModel):
    """Campos comuns de atendimento."""

    cpf: Optional[str] = None
    sus: Optional[str] = None
    data_atendimento: Optional[str] = None
    hora_atendimento: Optional[str] = None
    registro: Optional[str] = None
    procedencia: Optional[str] = None


class AtendimentoCreate(AtendimentoBase):
    """Usado no POST /atendimentos."""


class AtendimentoResponse(AtendimentoBase):
    """Retorno de atendimento com dados do paciente."""

    id: int
    # Dados do paciente (join)
    nome: Optional[str] = None
    dn: Optional[str] = None
    tel: Optional[str] = None
    endereco: Optional[str] = None
    bairro: Optional[str] = None
    cidade: Optional[str] = None

    model_config = {"from_attributes": True, "populate_by_name": True}


# ── PAGINAÇÃO ─────────────────────────────────────────────────


class PaginatedResponse(BaseModel):
    """Wrapper para respostas paginadas."""

    items: list
    total: int
    pagina: int
    total_paginas: int
    por_pagina: int

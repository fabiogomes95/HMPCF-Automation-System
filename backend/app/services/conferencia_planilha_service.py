"""Aba BPA › Migração › "Planilha da recepção": confere a planilha das meninas
contra o sistema e lança o que faltou (paciente novo + entrada).

Duas chamadas com o mesmo arquivo: primeiro só confere (nada é gravado) e a
tela mostra a lista; depois, com aplicar=True, confere DE NOVO e lança. Cada
linha grava num savepoint próprio: erro numa linha não desfaz as outras.

Regras (combinadas com o usuário em 11/11/2026):
  - linha com só o nome (sem nascimento, CPF, SUS, sexo, endereço nem
    telefone) ou com nome genérico ("PACIENTE SEM DOCUMENTO") não entra;
  - paciente sem documento mas com os outros dados entra normalmente;
  - paciente novo precisa de nascimento e sexo (mesma regra da recepção) --
    sem eles a linha fica como pendente, pra cadastrar à mão;
  - CPF/SUS com dígito errado não é gravado no cadastro novo (o resto é);
  - nunca duplica: antes de lançar procura entrada do mesmo paciente no
    mesmo minuto.
"""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import Optional

from pydantic import ValidationError as PydanticValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.core.exceptions import HMPCFError, ValidationError
from app.importacao.conferencia_planilha import (
    AtendimentoSistema,
    LinhaPlanilha,
    faltando_no_sistema,
    ler_planilha,
    separar_endereco,
)
from app.importacao.planilhas_recepcao import nome_busca
from app.models.paciente import Paciente
from app.models.recepcao_atendimento import RecepcaoAtendimento
from app.models.usuario import Usuario
from app.repositories.paciente_repository import PacienteRepository
from app.schemas.paciente import PacienteCreate, _validar_cns, _validar_cpf
from app.schemas.recepcao import RecepcaoCreate
from app.services.paciente_service import PacienteService
from app.services.recepcao_service import _FUSO_HOSPITAL, RecepcaoService

IBGE = {"EXTREMOZ": "240360", "NATAL": "240810", "CEARA-MIRIM": "240260", "CEARA MIRIM": "240260",
        "SAO GONCALO DO AMARANTE": "241200", "JOAO CAMARA": "240580", "PARNAMIRIM": "240325"}
TAMANHO_MAXIMO = 60 * 1024 * 1024


def _idade(nasc: date, em: date) -> str:
    return str(em.year - nasc.year - ((em.month, em.day) < (nasc.month, nasc.day)))


def _erro_curto(e: Exception) -> str:
    """IntegrityError (ex.: outro PC cadastrou o mesmo CPF no mesmo instante)
    traz o SQL inteiro no texto -- na tela basta dizer o que houve."""
    if isinstance(e, IntegrityError):
        return "já existe no sistema (cadastrado por outro computador ao mesmo tempo?)"
    return str(e)


def _motivo_validacao(e: PydanticValidationError) -> str:
    msgs = [str(err.get("msg", "")).removeprefix("Value error, ") for err in e.errors()]
    return "; ".join(m for m in msgs if m) or "dados inválidos"


class ConferenciaPlanilhaService:
    def __init__(self, session: AsyncSession, usuario: Optional[Usuario] = None) -> None:
        self.session = session
        self._usuario = usuario
        self._pacientes = PacienteRepository(session)

    # ── Leitura / comparação ──────────────────────────────────────────────────
    async def _atendimentos_do_periodo(self, linhas: list[LinhaPlanilha]) -> list[AtendimentoSistema]:
        inicio = datetime.combine(min(ln.data for ln in linhas) - timedelta(days=2), datetime.min.time(), _FUSO_HOSPITAL)
        fim = datetime.combine(max(ln.data for ln in linhas) + timedelta(days=3), datetime.min.time(), _FUSO_HOSPITAL)
        stmt = (
            select(RecepcaoAtendimento.id, RecepcaoAtendimento.data_atendimento,
                   Paciente.num_cpf, Paciente.cns, Paciente.nome)
            .join(Paciente, Paciente.id == RecepcaoAtendimento.paciente_id)
            .where(RecepcaoAtendimento.data_atendimento >= inicio, RecepcaoAtendimento.data_atendimento < fim)
        )
        return [
            AtendimentoSistema(id=i, quando=quando.astimezone(_FUSO_HOSPITAL).replace(tzinfo=None),
                               cpf=cpf or None, cns=cns or None, nome_busca=nome_busca(nome or ""))
            for i, quando, cpf, cns, nome in (await self.session.execute(stmt)).all()
        ]

    async def _achar_paciente(self, ln: LinhaPlanilha) -> Optional[Paciente]:
        e = ln.entrada
        if e.cpf and (p := await self._pacientes.get_by_cpf(e.cpf)):
            return p
        if e.cns and (p := await self._pacientes.get_by_cns(e.cns)):
            return p
        # Pelo nome: primeira e última palavra no LIKE (vogais/Ç viram "_" pra
        # achar com ou sem acento), comparação exata depois, sem acento.
        palavras = e.nome_busca.split()
        if len(palavras) < 2:
            return None
        coringa = lambda s: re.sub(r"[AEIOUC]", "_", s)  # noqa: E731
        stmt = select(Paciente).where(Paciente.nome.ilike(f"{coringa(palavras[0])}%{coringa(palavras[-1])}")).limit(500)
        mesmos = [p for p in (await self.session.execute(stmt)).scalars() if nome_busca(p.nome or "") == e.nome_busca]
        if e.nascimento:
            mesmos = [p for p in mesmos if p.dtnasc == e.nascimento.strftime("%Y%m%d")]
        return mesmos[0] if len(mesmos) == 1 else None

    def _cadastro_novo(self, ln: LinhaPlanilha) -> tuple[dict, list[str]]:
        e = ln.entrada
        avisos = []
        cpf = e.cpf if e.cpf and _validar_cpf(e.cpf) else None
        cns = e.cns if e.cns and _validar_cns(e.cns) else None
        if e.cpf and not cpf:
            avisos.append(f"CPF {e.cpf} com dígito errado — cadastrado sem CPF")
        if e.cns and not cns:
            avisos.append(f"SUS {e.cns} com dígito errado — cadastrado sem SUS")
        rua, numero, bairro = separar_endereco(ln.endereco)
        cidade = ln.municipio or "EXTREMOZ"
        dados = {
            "nome": e.nome, "num_cpf": cpf, "cns": cns,
            "dtnasc": e.nascimento.strftime("%Y%m%d") if e.nascimento else None,
            "sexo": ln.sexo, "raca": ln.raca or "03",
            "logpcn": rua, "numpcn": numero, "bairro_pcnte": bairro,
            "ddtel_pcnte": ln.telefone[:2] if ln.telefone else None,
            "tel_pcnte": ln.telefone[2:] if ln.telefone else None,
            "cidade": cidade, "estado": "RN", "ibge": IBGE.get(cidade, "240360"),
            "idade": _idade(e.nascimento, ln.data) if e.nascimento else None,
        }
        return {k: v for k, v in dados.items() if v is not None}, avisos

    async def _ja_tem_entrada_no_minuto(self, paciente_id: int, quando: datetime) -> Optional[int]:
        stmt = select(RecepcaoAtendimento.id).where(
            RecepcaoAtendimento.paciente_id == paciente_id,
            RecepcaoAtendimento.data_atendimento >= quando,
            RecepcaoAtendimento.data_atendimento < quando + timedelta(minutes=1),
        ).limit(1)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    # ── Principal ─────────────────────────────────────────────────────────────
    async def executar(self, conteudo: bytes, abas: Optional[list[str]] = None, aplicar: bool = False) -> dict:
        if not conteudo:
            raise ValidationError("Escolha a planilha (.xlsx).")
        if len(conteudo) > TAMANHO_MAXIMO:
            raise ValidationError("Planilha grande demais (máx. 60 MB).")
        try:
            leitura = await run_in_threadpool(ler_planilha, conteudo, abas)
        except Exception as e:  # zip inválido, .xls antigo, arquivo corrompido...
            raise ValidationError(f"Não consegui abrir a planilha (precisa ser .xlsx): {e}") from e

        resposta = {
            "abas_disponiveis": leitura.abas_disponiveis, "abas_lidas": leitura.abas_lidas,
            "linhas_lidas": len(leitura.linhas), "periodo": None, "avisos": leitura.avisos,
            "aplicado": aplicar, "itens": [],
            "resumo": {"faltando": 0, "entrada": 0, "novo": 0, "pendente": 0, "ignorada": 0},
        }
        if not leitura.linhas:
            return resposta
        resposta["periodo"] = [min(ln.data for ln in leitura.linhas).isoformat(),
                               max(ln.data for ln in leitura.linhas).isoformat()]

        faltando = faltando_no_sistema(leitura.linhas, await self._atendimentos_do_periodo(leitura.linhas))
        resposta["resumo"]["faltando"] = len(faltando)
        if aplicar:
            resposta["resumo"].update(pacientes_criados=0, entradas_lancadas=0, ja_existiam=0, erros=0)

        # paciente novo que veio mais de uma vez no período: cadastra uma vez só
        novos_nesta_rodada: dict[tuple, int] = {}
        pacientes_svc = PacienteService(self.session, self._usuario)
        recepcao_svc = RecepcaoService(self.session, self._usuario)

        for ln in faltando:
            e = ln.entrada
            item = {
                "data": ln.data.isoformat(), "hora": ln.hora.strftime("%H:%M") if ln.hora else None,
                "nome": e.nome, "cpf": e.cpf, "cns": e.cns,
                "nascimento": e.nascimento.isoformat() if e.nascimento else None,
                "registro": ln.registro, "aba": e.aba, "linha": e.linha,
                "situacao": None, "motivo": "", "paciente_id": None, "resultado": None,
            }
            resposta["itens"].append(item)

            if ln.nome_generico() or not ln.tem_dados_alem_do_nome():
                item.update(situacao="ignorada", motivo="nome genérico" if ln.nome_generico() else "só tem o nome")
            elif not ln.hora:
                item.update(situacao="pendente", motivo="sem hora na planilha")
            else:
                chave = (e.cpf or e.cns or (e.nome_busca, e.nascimento))
                paciente = await self._achar_paciente(ln)
                if paciente:
                    item.update(situacao="entrada", paciente_id=paciente.id)
                elif chave in novos_nesta_rodada:
                    item.update(situacao="entrada", paciente_id=novos_nesta_rodada[chave],
                                motivo="paciente cadastrado nesta mesma conferência")
                else:
                    dados, avisos = self._cadastro_novo(ln)
                    try:
                        novo = PacienteCreate(**dados)
                    except PydanticValidationError as err:
                        item.update(situacao="pendente", motivo=_motivo_validacao(err) + " — cadastrar à mão")
                    else:
                        item.update(situacao="novo", motivo="; ".join(avisos))
                        if aplicar:
                            try:
                                async with self.session.begin_nested():
                                    criado = await pacientes_svc.criar(novo)
                                item["paciente_id"] = criado.id
                                resposta["resumo"]["pacientes_criados"] += 1
                            except (HMPCFError, IntegrityError) as err:
                                item["resultado"] = f"erro no cadastro: {_erro_curto(err)}"
                                resposta["resumo"]["erros"] += 1
                        else:
                            item["paciente_id"] = -1  # marcador: será criado
                        if item["paciente_id"]:
                            novos_nesta_rodada[chave] = item["paciente_id"]

            resposta["resumo"][item["situacao"]] += 1

            if aplicar and item["situacao"] in ("entrada", "novo") and item["paciente_id"] and item["paciente_id"] > 0:
                quando = datetime.combine(ln.data, ln.hora, _FUSO_HOSPITAL)
                if (existente := await self._ja_tem_entrada_no_minuto(item["paciente_id"], quando)):
                    item["resultado"] = f"já existia (atendimento {existente})"
                    resposta["resumo"]["ja_existiam"] += 1
                    continue
                try:
                    async with self.session.begin_nested():
                        atd = await recepcao_svc.criar(RecepcaoCreate(
                            paciente_id=item["paciente_id"], data_atendimento=quando,
                            registro=ln.registro, procedencia="NORMAL",
                        ))
                    item["resultado"] = f"lançada (atendimento {atd.id})"
                    resposta["resumo"]["entradas_lancadas"] += 1
                except (HMPCFError, PydanticValidationError, IntegrityError) as err:
                    item["resultado"] = f"erro na entrada: {_erro_curto(err)}"
                    resposta["resumo"]["erros"] += 1
        return resposta

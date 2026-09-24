"""Painel gerencial (aba Painel da TI) -- substitui o antigo dashboard Streamlit
(legado/dashboard_streamlit). Só leitura e só agregados: nenhum nome, CPF ou
endereço sai daqui."""
import re
import unicodedata
from pathlib import Path
from collections import Counter
from datetime import date, datetime, time, timedelta
from typing import Literal, Optional
from zoneinfo import ZoneInfo

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.services.backup_status import lotes_bpa, situacao_backup
from app.services.recepcao_service import _INICIO_DIURNO, _turno_e_dia_referencia

_FUSO = ZoneInfo("America/Sao_Paulo")

Periodo = Literal["hoje", "7d", "30d", "mes", "12m"]

FAIXAS_ETARIAS = [
    (0, 12, "0-12"),
    (13, 17, "13-17"),
    (18, 29, "18-29"),
    (30, 44, "30-44"),
    (45, 59, "45-59"),
    (60, 74, "60-74"),
    (75, 200, "75+"),
]
SEXO_ROTULO = {"M": "Masculino", "F": "Feminino"}

# Grafias diferentes da mesma cidade digitadas na recepção.
_CIDADE_ALIAS = {
    "SAO G DO AMARANTE": "SAO GONCALO DO AMARANTE",
    "S G DO AMARANTE": "SAO GONCALO DO AMARANTE",
    "SAO GONCALO": "SAO GONCALO DO AMARANTE",
    "CEARA MIRIM": "CEARA-MIRIM",
}


def _meia_noite(d: date) -> datetime:
    return datetime.combine(d, time.min, tzinfo=_FUSO)


def _inicio_periodo(periodo: Periodo, hoje: date) -> date:
    if periodo == "hoje":
        return hoje
    if periodo == "7d":
        return hoje - timedelta(days=6)
    if periodo == "30d":
        return hoje - timedelta(days=29)
    if periodo == "mes":
        return hoje.replace(day=1)
    return (hoje.replace(day=1) - timedelta(days=335)).replace(day=1)  # 12 meses fechados + o atual


def _idade(dtnasc: Optional[str], referencia: date) -> Optional[int]:
    if not dtnasc or len(dtnasc) != 8:
        return None
    try:
        nasc = datetime.strptime(dtnasc, "%Y%m%d").date()
    except ValueError:
        return None
    idade = referencia.year - nasc.year - ((referencia.month, referencia.day) < (nasc.month, nasc.day))
    return idade if 0 <= idade <= 120 else None


def _faixa(idade: int) -> str:
    for minimo, maximo, rotulo in FAIXAS_ETARIAS:
        if minimo <= idade <= maximo:
            return rotulo
    return FAIXAS_ETARIAS[-1][2]


def _cidade(bruta: Optional[str]) -> str:
    if not bruta or not bruta.strip():
        return "Não informado"
    sem_acento = unicodedata.normalize("NFKD", bruta.upper()).encode("ascii", "ignore").decode()
    chave = re.sub(r"[^A-Z]+", " ", sem_acento).strip()
    chave = re.sub(r"\s+RN$", "", chave)  # "NATAL-RN" -> "NATAL"
    return _CIDADE_ALIAS.get(chave, chave)


async def _contar(session: AsyncSession, inicio: datetime, fim: datetime) -> int:
    return (await session.execute(
        text("SELECT count(*) FROM recepcao_atendimentos WHERE data_atendimento >= :i AND data_atendimento < :f"),
        {"i": inicio, "f": fim},
    )).scalar_one()


def _variacao(atual: int, anterior: int) -> Optional[float]:
    return round((atual - anterior) / anterior * 100, 1) if anterior else None


async def montar_painel(session: AsyncSession, periodo: Periodo) -> dict:
    agora = datetime.now(_FUSO)
    hoje = agora.date()

    # ── Destaques: sempre relativos a agora, independentes do período escolhido
    hoje_total = await _contar(session, _meia_noite(hoje), agora + timedelta(minutes=1))
    ontem_mesma_hora = await _contar(session, _meia_noite(hoje - timedelta(days=1)), agora - timedelta(days=1))

    turno, dia_ref = _turno_e_dia_referencia(agora)
    inicio_plantao = datetime.combine(
        dia_ref, _INICIO_DIURNO if turno == "DIURNO" else time(19, 0), tzinfo=_FUSO
    )
    plantao_total = await _contar(session, inicio_plantao, agora + timedelta(minutes=1))

    inicio_mes = hoje.replace(day=1)
    mes_total = await _contar(session, _meia_noite(inicio_mes), agora + timedelta(minutes=1))
    # Mesmo trecho do mês anterior (dia 1 até o mesmo dia/hora), pra comparar igual com igual.
    inicio_mes_ant = (inicio_mes - timedelta(days=1)).replace(day=1)
    try:
        corte_mes_ant = agora.replace(year=inicio_mes_ant.year, month=inicio_mes_ant.month)
    except ValueError:  # dia 31 num mês de 30 dias etc.
        corte_mes_ant = _meia_noite(inicio_mes)
    mes_anterior_parcial = await _contar(session, _meia_noite(inicio_mes_ant), corte_mes_ant)

    # ── Período escolhido
    inicio = _inicio_periodo(periodo, hoje)
    linhas = (await session.execute(text("""
        SELECT (ra.data_atendimento AT TIME ZONE 'America/Sao_Paulo') AS local,
               ra.paciente_id, ra.procedencia,
               p.sexo, p.dtnasc, p.cidade, p.num_cpf, p.tel_pcnte,
               NULLIF(TRIM(p.bairro_pcnte), '') AS bairro
        FROM recepcao_atendimentos ra
        JOIN pacientes p ON p.id = ra.paciente_id
        WHERE ra.data_atendimento >= :inicio AND ra.data_atendimento < :fim
    """), {"inicio": _meia_noite(inicio), "fim": agora + timedelta(minutes=1)})).all()

    total = len(linhas)
    # Conta os dias a partir do 1º atendimento do período -- em "12 meses" o
    # sistema ainda não existia no começo, e dividir por esses dias derruba a média.
    primeiro_dia = min((l.local.date() for l in linhas), default=inicio)
    dias_no_periodo = (hoje - max(inicio, primeiro_dia)).days + 1
    por_mes = periodo == "12m"

    serie = Counter()
    horas = Counter()
    turnos = Counter()
    sexo = Counter()
    faixas = Counter()
    bairros = Counter()
    cidades = Counter()
    procedencias = Counter()
    pacientes = set()
    sem_idade = sem_cpf = sem_tel = sem_bairro = 0

    for l in linhas:
        dia = l.local.date()
        serie[dia.strftime("%Y-%m") if por_mes else dia.isoformat()] += 1
        horas[l.local.hour] += 1
        turnos["Diurno" if 7 <= l.local.hour < 19 else "Noturno"] += 1
        sexo[SEXO_ROTULO.get(l.sexo, "Não informado")] += 1
        idade = _idade(l.dtnasc, dia)
        if idade is None:
            sem_idade += 1
        else:
            faixas[_faixa(idade)] += 1
        bairros[l.bairro or "Não informado"] += 1
        cidades[_cidade(l.cidade)] += 1
        procedencias[(l.procedencia or "").strip().upper() or "Não informado"] += 1
        pacientes.add(l.paciente_id)
        sem_cpf += not l.num_cpf
        sem_tel += not (l.tel_pcnte or "").strip()
        sem_bairro += not l.bairro

    # Dias sem nenhum atendimento também entram (barra zero), senão o gráfico "pula" o dia.
    if not por_mes:
        for n in range((hoje - inicio).days + 1):
            serie.setdefault((inicio + timedelta(days=n)).isoformat(), 0)

    top_cidades = cidades.most_common(5)
    outras = total - sum(v for _, v in top_cidades)
    if outras > 0:
        top_cidades.append(("Outras", outras))

    return {
        "periodo": periodo,
        "gerado_em": agora.isoformat(timespec="seconds"),
        "destaques": {
            "hoje": hoje_total,
            "ontem_mesma_hora": ontem_mesma_hora,
            "plantao_turno": turno,
            "plantao_inicio": inicio_plantao.isoformat(timespec="minutes"),
            "plantao": plantao_total,
            "mes": mes_total,
            "mes_anterior_parcial": mes_anterior_parcial,
            "mes_variacao_pct": _variacao(mes_total, mes_anterior_parcial),
        },
        "resumo": {
            "total": total,
            "dias": dias_no_periodo,
            "media_dia": round(total / dias_no_periodo, 1) if dias_no_periodo else 0,
            "pacientes_unicos": len(pacientes),
            "retornos": total - len(pacientes),
        },
        "serie_por": "mes" if por_mes else "dia",
        "serie": [{"chave": k, "total": v} for k, v in sorted(serie.items())],
        # Média por dia em cada hora -- mostra o pico de movimento independente do período.
        "horas": [{"hora": h, "media": round(horas.get(h, 0) / dias_no_periodo, 1)} for h in range(24)],
        "turnos": [{"rotulo": r, "total": turnos.get(r, 0)} for r in ("Diurno", "Noturno")],
        "sexo": [{"rotulo": k, "total": v} for k, v in sexo.most_common()],
        "faixas": [{"rotulo": r, "total": faixas.get(r, 0)} for _, _, r in FAIXAS_ETARIAS],
        "sem_idade": sem_idade,
        "bairros": [{"rotulo": k, "total": v} for k, v in bairros.most_common(8)],
        "cidades": [{"rotulo": k, "total": v} for k, v in top_cidades],
        "procedencias": [{"rotulo": k, "total": v} for k, v in procedencias.most_common()],
        "qualidade": {"sem_cpf": sem_cpf, "sem_telefone": sem_tel, "sem_bairro": sem_bairro},
        "backup": situacao_backup(Path(settings.BACKUP_DIR), agora),
        "lotes_bpa": await lotes_bpa(session),
    }

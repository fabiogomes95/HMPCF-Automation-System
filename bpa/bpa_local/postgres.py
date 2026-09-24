"""Leitura do PostgreSQL do servidor (usuário bpa_leitura — só SELECT em
pacientes e recepcao_atendimentos)."""
import re

import psycopg2

from bpa_local.config import POSTGRES, POSTGRES_FALSO

NOMES_MES = ["", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
             "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]


def nome_mes(m: int, a: int) -> str:
    return f"{NOMES_MES[m]}/{a}"


def conectar():
    if POSTGRES_FALSO:  # modo de teste: pacientes falsos do JSON
        from bpa_local.postgres_falso import ConexaoFalsa
        return ConexaoFalsa(POSTGRES_FALSO)
    try:
        return psycopg2.connect(**POSTGRES, connect_timeout=5, options="-c client_encoding=LATIN1")
    except UnicodeDecodeError as e:
        # A mensagem de erro do libpq vem em Latin1 (acentos do servidor);
        # psycopg2 tenta decodificar como UTF-8 e quebra, escondendo o erro real.
        raise psycopg2.OperationalError(e.object.decode("latin1", errors="replace")) from None


def competencias_disponiveis() -> list[dict]:
    """Meses (AAAAMM) que realmente têm atendimento no Postgres, mais recente primeiro."""
    try:
        pg = conectar()
    except Exception:
        return []
    try:
        cur = pg.cursor()
        cur.execute("""
            SELECT DISTINCT to_char(data_atendimento, 'YYYYMM') AS ym
            FROM recepcao_atendimentos
            ORDER BY ym DESC
        """)
        return [
            {"value": ym, "label": nome_mes(int(ym[4:6]), int(ym[:4]))}
            for (ym,) in cur.fetchall()
        ]
    except Exception:
        return []
    finally:
        pg.close()


def query_pacientes_mes(mes_aaaamm: str) -> str:
    if not re.fullmatch(r"\d{6}", mes_aaaamm or ""):
        raise ValueError(f"Parametro 'mes' invalido: {mes_aaaamm!r} (esperado AAAAMM)")
    ano, mes = mes_aaaamm[:4], mes_aaaamm[4:6]
    inicio = f"{ano}-{mes}-01"
    mes_i = int(mes)
    fim = f"{int(ano)+1}-01-01" if mes_i == 12 else f"{ano}-{mes_i+1:02d}-01"
    return f"""
        SELECT DISTINCT p.cns, p.num_cpf, p.nome, p.dtnasc, p.sexo, p.raca, p.maepcn,
            p.logpcn, p.numpcn, p.bairro_pcnte, p.ceppcn, p.ibge,
            p.nacionalidade, p.ddtel_pcnte, p.tel_pcnte
        FROM pacientes p
        INNER JOIN recepcao_atendimentos ra ON ra.paciente_id = p.id
        WHERE p.num_cpf IS NOT NULL AND p.num_cpf <> ''
          AND ra.data_atendimento >= '{inicio}'
          AND ra.data_atendimento <  '{fim}'
        ORDER BY p.nome
    """


def query_pacientes_periodo(inicio, fim) -> str:
    """Mesma consulta da migração, por intervalo de datas [inicio, fim) —
    usada pela migração automática (janela dos últimos dias)."""
    return f"""
        SELECT DISTINCT p.cns, p.num_cpf, p.nome, p.dtnasc, p.sexo, p.raca, p.maepcn,
            p.logpcn, p.numpcn, p.bairro_pcnte, p.ceppcn, p.ibge,
            p.nacionalidade, p.ddtel_pcnte, p.tel_pcnte
        FROM pacientes p
        INNER JOIN recepcao_atendimentos ra ON ra.paciente_id = p.id
        WHERE p.num_cpf IS NOT NULL AND p.num_cpf <> ''
          AND ra.data_atendimento >= '{inicio.isoformat()}'
          AND ra.data_atendimento <  '{fim.isoformat()}'
        ORDER BY p.nome
    """

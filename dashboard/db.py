"""Conexão compartilhada com o PostgreSQL (somente leitura) para todas as páginas do dashboard."""
import os
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import create_engine

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR.parent / "backend" / ".env")

DB_URL = (
    f"postgresql+psycopg2://{os.getenv('POSTGRES_USER', 'postgres')}:"
    f"{os.getenv('POSTGRES_PASSWORD', '')}@"
    f"{os.getenv('POSTGRES_HOST', 'localhost')}:"
    f"{os.getenv('POSTGRES_PORT', '5432')}/"
    f"{os.getenv('POSTGRES_DB', 'hmpcf')}"
)


@st.cache_resource
def get_engine():
    return create_engine(
        DB_URL,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 3},
    )


FUSO_LOCAL = "America/Sao_Paulo"


def corrigir_fuso(df: pd.DataFrame, coluna: str) -> pd.DataFrame:
    """pandas.read_sql converte timestamptz para UTC, perdendo o horário local (-03:00). Reaplica o fuso correto."""
    if pd.api.types.is_datetime64_any_dtype(df[coluna]):
        if df[coluna].dt.tz is None:
            df[coluna] = df[coluna].dt.tz_localize("UTC")
        df[coluna] = df[coluna].dt.tz_convert(FUSO_LOCAL)
    return df


LIMITE_QUASE_DUPLICADO_MIN = 30


def remover_quase_duplicados(
    df: pd.DataFrame, coluna_data: str = "data_atendimento", limite_minutos: int = LIMITE_QUASE_DUPLICADO_MIN
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Remove lançamentos repetidos do mesmo paciente por erro de digitação da recepção
    (mesmo registro, ou horário a poucos minutos de distância) — mantém só o mais recente.
    Retorna (df_limpo, df_removidos).
    """
    if df.empty or "paciente_id" not in df.columns:
        return df, df.iloc[0:0]

    mantidos, removidos = [], []
    for _, grupo in df.groupby("paciente_id", sort=False):
        grupo = grupo.sort_values(coluna_data).reset_index(drop=True)
        atual = grupo.iloc[0]
        for i in range(1, len(grupo)):
            prox = grupo.iloc[i]
            mesmo_registro = (
                pd.notna(prox.get("registro")) and pd.notna(atual.get("registro"))
                and prox["registro"] == atual["registro"]
            )
            diff_min = (prox[coluna_data] - atual[coluna_data]).total_seconds() / 60
            if mesmo_registro or diff_min <= limite_minutos:
                removidos.append(atual)
                atual = prox  # mantém o mais recente do par
            else:
                mantidos.append(atual)
                atual = prox
        mantidos.append(atual)

    df_limpo = pd.DataFrame(mantidos).sort_values(coluna_data).reset_index(drop=True) if mantidos else df.iloc[0:0]
    df_removidos = pd.DataFrame(removidos).sort_values(coluna_data).reset_index(drop=True) if removidos else df.iloc[0:0]
    return df_limpo, df_removidos


def _texto(valor) -> str | None:
    """Normaliza valores vindos do banco (podem chegar como NaN/float quando nulos)."""
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return None
    texto = str(valor).strip()
    return texto or None


def calcular_idade(dtnasc, referencia: date) -> int | None:
    dtnasc = _texto(dtnasc)
    if not dtnasc:
        return None
    try:
        nasc = datetime.strptime(dtnasc, "%Y%m%d").date()
        idade = referencia.year - nasc.year - ((referencia.month, referencia.day) < (nasc.month, nasc.day))
        return idade if 0 <= idade <= 120 else None
    except ValueError:
        return None


def formatar_data_nascimento(dtnasc) -> str:
    dtnasc = _texto(dtnasc)
    if not dtnasc:
        return "Não informado"
    try:
        return datetime.strptime(dtnasc, "%Y%m%d").strftime("%d/%m/%Y")
    except ValueError:
        return "Não informado"


def formatar_cpf(cpf) -> str:
    cpf = _texto(cpf)
    if cpf and len(cpf) == 11:
        return f"{cpf[0:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:11]}"
    return cpf or "Não informado"


def formatar_telefone(ddd, numero) -> str:
    numero = _texto(numero)
    if not numero:
        return "Não informado"
    ddd = _texto(ddd) or ""
    if len(numero) == 9:
        return f"({ddd}) {numero[:5]}-{numero[5:]}"
    if len(numero) == 8:
        return f"({ddd}) {numero[:4]}-{numero[4:]}"
    return f"({ddd}) {numero}"


def formatar_endereco(logpcn, numpcn, bairro, cidade, estado) -> str:
    logpcn, numpcn, bairro, cidade, estado = (_texto(v) for v in (logpcn, numpcn, bairro, cidade, estado))
    rua = f"{logpcn or ''}, {numpcn or ''}".strip(", ")
    partes = [p for p in [rua, bairro, f"{cidade}/{estado}" if cidade else None] if p]
    return ", ".join(partes) if partes else "Não informado"


SEXO_MAPA = {"M": "Masculino", "F": "Feminino", "I": "Indefinido"}

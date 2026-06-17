"""
Dashboard HMPCF — visão gerencial em tempo real para coordenação e TI.

Lê o PostgreSQL do sistema de recepção em modo SOMENTE LEITURA.
Não importa nem depende de nenhum módulo do backend/app — processo
totalmente independente, não interfere no sistema de digitação.
"""
from datetime import date, datetime, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import text

from db import SEXO_MAPA, calcular_idade, corrigir_fuso, get_engine, remover_quase_duplicados

st.set_page_config(
    page_title="HMPCF — Painel Gerencial",
    page_icon="📊",
    layout="wide",
)

PERIODOS = ["Hoje", "Últimos 7 dias", "Últimos 30 dias", "Mês atual", "Desde o início"]

FAIXAS_ETARIAS = [
    (0, 12, "0-12"),
    (13, 17, "13-17"),
    (18, 29, "18-29"),
    (30, 44, "30-44"),
    (45, 59, "45-59"),
    (60, 74, "60-74"),
    (75, 200, "75+"),
]


@st.cache_data(ttl=60)
def carregar_atendimentos() -> pd.DataFrame:
    """Busca todos os atendimentos uma única vez, já com fuso corrigido e duplicados removidos."""
    sql = text(
        """
        SELECT
            r.data_atendimento, r.registro, p.id AS paciente_id, p.sexo, p.dtnasc,
            COALESCE(NULLIF(TRIM(p.bairro_pcnte), ''), 'Não informado') AS bairro
        FROM recepcao_atendimentos r
        JOIN pacientes p ON p.id = r.paciente_id
        """
    )
    with get_engine().connect() as conn:
        df = pd.read_sql(sql, conn)
    df = corrigir_fuso(df, "data_atendimento")
    df, _ = remover_quase_duplicados(df)
    return df


def calcular_kpis(df: pd.DataFrame) -> dict:
    hoje = date.today()
    semana_inicio = hoje - timedelta(days=hoje.weekday())
    mes_inicio = hoje.replace(day=1)
    dias = df["data_atendimento"].dt.date
    return {
        "hoje": int((dias == hoje).sum()),
        "semana": int((dias >= semana_inicio).sum()),
        "mes": int((dias >= mes_inicio).sum()),
        "total": len(df),
    }


def filtrar_periodo(df: pd.DataFrame, periodo: str) -> pd.DataFrame:
    hoje = date.today()
    dias = df["data_atendimento"].dt.date
    if periodo == "Hoje":
        return df[dias == hoje]
    if periodo == "Mês atual":
        return df[dias >= hoje.replace(day=1)]
    if periodo == "Desde o início":
        return df
    n = {"Últimos 7 dias": 7, "Últimos 30 dias": 30}[periodo]
    return df[dias >= hoje - timedelta(days=n)]


def calcular_serie_diaria(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    contagem = df["data_atendimento"].dt.date.value_counts().reset_index()
    contagem.columns = ["dia", "total"]
    return contagem.sort_values("dia")


def calcular_sexo(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    contagem = df["sexo"].map(lambda s: SEXO_MAPA.get(s, "Não informado")).value_counts().reset_index()
    contagem.columns = ["sexo", "total"]
    return contagem


def calcular_bairros(df: pd.DataFrame, limite: int = 10) -> pd.DataFrame:
    if df.empty:
        return df
    contagem = df["bairro"].value_counts().head(limite).reset_index()
    contagem.columns = ["bairro", "total"]
    return contagem


def calcular_idades(df: pd.DataFrame) -> pd.DataFrame:
    df = df[df["dtnasc"].notna() & (df["dtnasc"] != "")]
    if df.empty:
        return df

    idades = df.apply(lambda r: calcular_idade(r["dtnasc"], r["data_atendimento"].date()), axis=1)
    df = df.assign(idade=idades).dropna(subset=["idade"])

    def faixa(idade: int) -> str:
        for minimo, maximo, rotulo in FAIXAS_ETARIAS:
            if minimo <= idade <= maximo:
                return rotulo
        return "Não informado"

    contagem = df["idade"].apply(faixa).value_counts().reset_index()
    contagem.columns = ["faixa", "total"]
    ordem = [r for _, _, r in FAIXAS_ETARIAS]
    contagem["faixa"] = pd.Categorical(contagem["faixa"], categories=ordem, ordered=True)
    return contagem.sort_values("faixa")


# ─────────────────────────────────────────────────────────────────────────────
# UI
# ─────────────────────────────────────────────────────────────────────────────

st.markdown(
    """
    <style>
    .kpi-card {
        background: linear-gradient(135deg, #1e3a5f 0%, #2c5282 100%);
        border-radius: 12px;
        padding: 1.2rem 1.5rem;
        color: white;
        text-align: center;
    }
    .kpi-card .valor { font-size: 2.2rem; font-weight: 700; line-height: 1.1; }
    .kpi-card .rotulo { font-size: 0.85rem; opacity: 0.85; text-transform: uppercase; letter-spacing: 0.05em; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("📊 HMPCF — Painel Gerencial")
st.caption(f"Atualizado automaticamente a cada 60s · {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

if st.button("🔄 Atualizar agora"):
    st.cache_data.clear()
    st.rerun()

dados = carregar_atendimentos()

kpis = calcular_kpis(dados)
col1, col2, col3, col4 = st.columns(4)
for col, (rotulo, chave) in zip(
    (col1, col2, col3, col4),
    [("Hoje", "hoje"), ("Esta semana", "semana"), ("Este mês", "mes"), ("Total geral", "total")],
):
    with col:
        st.markdown(
            f"""<div class="kpi-card">
                    <div class="valor">{kpis.get(chave, 0):,}</div>
                    <div class="rotulo">{rotulo}</div>
                </div>""".replace(",", "."),
            unsafe_allow_html=True,
        )

st.divider()

periodo = st.selectbox("Período para os gráficos abaixo", PERIODOS, index=2)
filtrado = filtrar_periodo(dados, periodo)

st.subheader("Volume de atendimentos por dia")
serie = calcular_serie_diaria(filtrado)
if serie.empty:
    st.info("Sem atendimentos no período selecionado.")
else:
    fig = px.bar(serie, x="dia", y="total", labels={"dia": "Data", "total": "Atendimentos"})
    fig.update_layout(margin=dict(t=10, b=10), height=350)
    st.plotly_chart(fig, use_container_width=True)

col_a, col_b = st.columns(2)

with col_a:
    st.subheader("Distribuição por sexo")
    sexo = calcular_sexo(filtrado)
    if sexo.empty:
        st.info("Sem dados no período.")
    else:
        fig = px.pie(sexo, names="sexo", values="total", hole=0.45)
        fig.update_layout(margin=dict(t=10, b=10), height=320)
        st.plotly_chart(fig, use_container_width=True)

with col_b:
    st.subheader("Distribuição por faixa etária")
    idades = calcular_idades(filtrado)
    if idades.empty:
        st.info("Sem dados de idade no período.")
    else:
        fig = px.bar(idades, x="faixa", y="total", labels={"faixa": "Faixa etária", "total": "Atendimentos"})
        fig.update_layout(margin=dict(t=10, b=10), height=320)
        st.plotly_chart(fig, use_container_width=True)

st.subheader("Top 10 bairros de origem dos pacientes")
bairros = calcular_bairros(filtrado)
if bairros.empty:
    st.info("Sem dados no período.")
else:
    fig = px.bar(bairros.sort_values("total"), x="total", y="bairro", orientation="h",
                 labels={"total": "Atendimentos", "bairro": "Bairro"})
    fig.update_layout(margin=dict(t=10, b=10), height=400)
    st.plotly_chart(fig, use_container_width=True)

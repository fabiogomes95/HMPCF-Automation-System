"""Histórico diário de atendimentos — lista detalhada por paciente, filtrável por dia."""
from datetime import date, datetime, timedelta

import pandas as pd
import streamlit as st
from sqlalchemy import text

from db import (
    SEXO_MAPA,
    calcular_idade,
    corrigir_fuso,
    formatar_cpf,
    formatar_data_nascimento,
    formatar_endereco,
    formatar_telefone,
    get_engine,
    remover_quase_duplicados,
)

st.set_page_config(page_title="HMPCF — Histórico Diário", page_icon="📋", layout="wide")

st.title("📋 Histórico Diário de Atendimentos")

opcao = st.radio(
    "Dia",
    ["Hoje", "Ontem", "Escolher data"],
    horizontal=True,
)

if opcao == "Hoje":
    data_selecionada = date.today()
elif opcao == "Ontem":
    data_selecionada = date.today() - timedelta(days=1)
else:
    data_selecionada = st.date_input("Selecione a data", value=date.today(), format="DD/MM/YYYY")

if st.button("🔄 Atualizar agora"):
    st.cache_data.clear()
    st.rerun()


@st.cache_data(ttl=30)
def carregar_historico_dia(data_ref: date) -> pd.DataFrame:
    sql = text(
        """
        SELECT
            r.data_atendimento,
            r.registro,
            p.id AS paciente_id,
            p.nome,
            p.num_cpf,
            p.cns,
            p.dtnasc,
            p.sexo,
            p.logpcn,
            p.numpcn,
            p.bairro_pcnte,
            p.cidade,
            p.estado,
            p.ddtel_pcnte,
            p.tel_pcnte
        FROM recepcao_atendimentos r
        JOIN pacientes p ON p.id = r.paciente_id
        WHERE r.data_atendimento::date = :data_ref
        ORDER BY r.data_atendimento
        """
    )
    with get_engine().connect() as conn:
        df = pd.read_sql(sql, conn, params={"data_ref": data_ref})
    return corrigir_fuso(df, "data_atendimento")


df_bruto = carregar_historico_dia(data_selecionada)
df, df_removidos = remover_quase_duplicados(df_bruto)

st.caption(
    f"{len(df)} atendimento(s) em {data_selecionada.strftime('%d/%m/%Y')} "
    f"· atualizado às {datetime.now().strftime('%H:%M:%S')}"
)

if not df_removidos.empty:
    with st.expander(f"🔁 {len(df_removidos)} lançamento(s) duplicado(s) ocultado(s) (mesmo paciente, mesmo registro ou horário muito próximo)"):
        st.dataframe(
            [
                {"Horário": r["data_atendimento"].strftime("%H:%M"), "Registro": r["registro"], "Nome": r["nome"]}
                for _, r in df_removidos.iterrows()
            ],
            hide_index=True, use_container_width=True,
        )

if df.empty:
    st.info("Nenhum atendimento encontrado para essa data.")
else:
    tabela = pd.DataFrame(
        {
            "Nº": range(1, len(df) + 1),
            "Horário": df["data_atendimento"].apply(lambda d: d.strftime("%H:%M")),
            "Nome": df["nome"],
            "CPF": df["num_cpf"].apply(formatar_cpf),
            "CNS (SUS)": df["cns"].fillna("Não informado"),
            "Data de nascimento": df["dtnasc"].apply(formatar_data_nascimento),
            "Idade": df.apply(lambda r: calcular_idade(r["dtnasc"], r["data_atendimento"].date()), axis=1),
            "Sexo": df["sexo"].map(lambda s: SEXO_MAPA.get(s, "Não informado")),
            "Endereço completo": df.apply(
                lambda r: formatar_endereco(r["logpcn"], r["numpcn"], r["bairro_pcnte"], r["cidade"], r["estado"]),
                axis=1,
            ),
            "Telefone": df.apply(lambda r: formatar_telefone(r["ddtel_pcnte"], r["tel_pcnte"]), axis=1),
        }
    )
    st.dataframe(tabela, use_container_width=True, hide_index=True, height=600)

"""Busca de paciente — histórico completo de entradas (data e horário), sem duplicados."""
import re

import pandas as pd
import streamlit as st
from sqlalchemy import bindparam, text

from db import (
    calcular_idade,
    corrigir_fuso,
    formatar_cpf,
    formatar_data_nascimento,
    get_engine,
    remover_quase_duplicados,
)

st.set_page_config(page_title="HMPCF — Buscar Paciente", page_icon="🔎", layout="wide")

st.title("🔎 Buscar Paciente")
st.caption("Pesquise por nome, CPF ou CNS e veja todas as entradas (data e horário) desse paciente no sistema.")

busca = st.text_input("Nome, CPF ou CNS")

if not busca.strip():
    st.info("Digite um nome, CPF ou CNS para buscar.")
    st.stop()

digitos = re.sub(r"\D", "", busca)
cpf_exato = digitos if len(digitos) == 11 else None
cns_exato = digitos if len(digitos) == 15 else None
nome_like = f"%{busca.strip().upper()}%"

sql_busca = text(
    """
    SELECT id, nome, num_cpf, cns, dtnasc, sexo
    FROM pacientes
    WHERE nome ILIKE :nome_like OR num_cpf = :cpf_exato OR cns = :cns_exato
    ORDER BY nome
    LIMIT 50
    """
)
with get_engine().connect() as conn:
    pacientes = conn.execute(sql_busca, {"nome_like": nome_like, "cpf_exato": cpf_exato, "cns_exato": cns_exato}).mappings().all()

if not pacientes:
    st.warning("Nenhum paciente encontrado.")
    st.stop()

if len(pacientes) > 1:
    st.caption(f"{len(pacientes)} pacientes encontrados.")

sql_visitas = text(
    """
    SELECT r.data_atendimento, r.registro, p.id AS paciente_id
    FROM recepcao_atendimentos r
    JOIN pacientes p ON p.id = r.paciente_id
    WHERE p.id IN :ids
    """
).bindparams(bindparam("ids", expanding=True))

ids = [p["id"] for p in pacientes]
with get_engine().connect() as conn:
    visitas = pd.read_sql(sql_visitas, conn, params={"ids": ids})
visitas = corrigir_fuso(visitas, "data_atendimento")
visitas, _ = remover_quase_duplicados(visitas)

for p in pacientes:
    visitas_paciente = visitas[visitas["paciente_id"] == p["id"]].sort_values("data_atendimento", ascending=False)

    idade_atual = calcular_idade(p["dtnasc"], visitas_paciente["data_atendimento"].max().date()) if not visitas_paciente.empty else None

    with st.expander(f"👤 {p['nome']} — {len(visitas_paciente)} entrada(s)", expanded=len(pacientes) == 1):
        col1, col2, col3 = st.columns(3)
        col1.metric("CPF", formatar_cpf(p["num_cpf"]))
        col2.metric("CNS (SUS)", p["cns"] or "Não informado")
        col3.metric("Nascimento", formatar_data_nascimento(p["dtnasc"]) + (f" ({idade_atual} anos)" if idade_atual is not None else ""))

        if visitas_paciente.empty:
            st.info("Nenhuma entrada registrada para esse paciente.")
        else:
            tabela = pd.DataFrame({
                "Data": visitas_paciente["data_atendimento"].dt.strftime("%d/%m/%Y"),
                "Horário": visitas_paciente["data_atendimento"].dt.strftime("%H:%M"),
            })
            st.dataframe(tabela, use_container_width=True, hide_index=True)

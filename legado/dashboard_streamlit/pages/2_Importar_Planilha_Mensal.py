"""Importação mensal da planilha manual de recepção (.tsv) para o PostgreSQL."""
from collections import Counter

import streamlit as st

from db import get_engine
from importador import comparar_com_banco, importar_faltantes, parsear_tsv

st.set_page_config(page_title="HMPCF — Importar Planilha", page_icon="📥", layout="wide")

st.title("📥 Importar Planilha Mensal")
st.caption(
    "Compara a planilha manual de recepção (.tsv) com o sistema e importa os atendimentos "
    "que faltam — útil quando o plantão registra no papel mas não digita no sistema."
)

arquivo = st.file_uploader("Selecione o arquivo .tsv da planilha do mês", type=["tsv", "txt"])

if arquivo is not None:
    conteudo = arquivo.read().decode("utf-8")
    registros, ignoradas = parsear_tsv(conteudo)

    if not registros:
        st.error("Não encontrei nenhum registro válido nesse arquivo. Verifique o formato (13 colunas, separadas por TAB).")
        st.stop()

    st.success(f"{len(registros)} atendimentos encontrados na planilha.")
    if ignoradas:
        with st.expander(f"⚠️ {len(ignoradas)} linha(s) com formato inesperado, ignoradas (revise manualmente)"):
            for linha in ignoradas:
                st.text(linha)

    if "faltando" not in st.session_state or st.session_state.get("_arquivo_nome") != arquivo.name:
        with st.spinner("Comparando com o sistema..."):
            faltando, sem_doc, sem_hora = comparar_com_banco(get_engine(), registros)
        st.session_state["faltando"] = faltando
        st.session_state["sem_doc"] = sem_doc
        st.session_state["sem_hora"] = sem_hora
        st.session_state["_arquivo_nome"] = arquivo.name
        st.session_state["importado"] = False

    faltando = st.session_state["faltando"]
    sem_doc = st.session_state["sem_doc"]
    sem_hora = st.session_state["sem_hora"]

    col1, col2, col3 = st.columns(3)
    col1.metric("Faltando no sistema", len(faltando))
    col2.metric("Sem CPF/CNS válido", len(sem_doc))
    col3.metric("Sem horário válido", len(sem_hora))

    if faltando:
        por_dia = Counter(r["dia"] for r in faltando)
        dias_ordenados = sorted(por_dia)
        st.subheader("Faltando por dia")
        st.dataframe(
            {"Dia": [d.strftime("%d/%m/%Y") for d in dias_ordenados], "Faltando": [por_dia[d] for d in dias_ordenados]},
            hide_index=True, use_container_width=True,
        )

        st.subheader("Prévia dos registros faltantes")
        st.dataframe(
            [
                {
                    "Dia": r["dia"].strftime("%d/%m/%Y"), "Registro": r["registro"], "Nome": r["nome"],
                    "Horário": f"{r['hora'][0]:02d}:{r['hora'][1]:02d}",
                    "CPF": r["cpf"] or "—", "CNS": r["cns"] or "—",
                }
                for r in faltando
            ],
            hide_index=True, use_container_width=True, height=300,
        )

        if sem_doc:
            with st.expander(f"⚠️ {len(sem_doc)} registros sem CPF/CNS válido (não podem ser importados automaticamente)"):
                st.dataframe(
                    [{"Dia": r["dia"].strftime("%d/%m/%Y") if r["dia"] else "—", "Registro": r["registro"], "Nome": r["nome"]} for r in sem_doc],
                    hide_index=True, use_container_width=True,
                )

        if sem_hora:
            with st.expander(f"⚠️ {len(sem_hora)} registros sem horário legível (não podem ser importados automaticamente)"):
                st.dataframe(
                    [{"Dia": r["dia"].strftime("%d/%m/%Y") if r["dia"] else "—", "Registro": r["registro"], "Nome": r["nome"], "Horário bruto": r["horario_raw"]} for r in sem_hora],
                    hide_index=True, use_container_width=True,
                )

        st.divider()
        confirmar = st.checkbox(f"Revisei a prévia acima e confirmo a importação dos {len(faltando)} atendimentos faltantes")
        if st.button("✅ Importar agora", disabled=not confirmar or st.session_state.get("importado")):
            with st.spinner("Importando..."):
                relatorio = importar_faltantes(get_engine(), faltando)
            st.session_state["importado"] = True
            st.session_state["relatorio"] = relatorio

        if st.session_state.get("importado"):
            relatorio = st.session_state["relatorio"]
            st.success(
                f"Importação concluída: {relatorio['atendimentos_criados']} atendimentos criados "
                f"({relatorio['pacientes_novos']} pacientes novos, {relatorio['pacientes_existentes']} já existiam)."
            )
            if relatorio["erros"]:
                with st.expander(f"❌ {len(relatorio['erros'])} erros durante a importação"):
                    for erro in relatorio["erros"]:
                        st.text(erro)
    else:
        st.info("Nenhum atendimento faltante — a planilha já está totalmente refletida no sistema. 🎉")
else:
    st.info("Aguardando o arquivo .tsv da planilha do mês.")

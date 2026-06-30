"""
Central de Automação BPA — Triagem, Digitação e Geração do arquivo BPA-I.

Processo Streamlit independente do backend/frontend da Recepção — usa
credenciais próprias (dashboard/.env) e fala direto com o Firebird do
BPA Magnético. Acesso restrito: só quem abre este dashboard (gestão/TI).
"""

import streamlit as st

import bpa_gerador as bpa

st.set_page_config(page_title="HMPCF — BPA", page_icon="🩺", layout="wide")

st.title("🩺 Central de Automação BPA")
st.caption("Triagem de enfermeiros, digitação de médicos e geração do arquivo BPA-I — substitui o robô antigo.")

ROTULO_CATEGORIA = {"medico": "Médico", "enfermeiro": "Enfermeiro"}


# ── Cache de pacientes (CADCNS) — recarregado manualmente ──────────────────
@st.cache_data(ttl=600)
def carregar_base_pacientes() -> list[dict]:
    return bpa.carregar_pacientes_cadcns()


@st.cache_data(ttl=600)
def carregar_profissionais() -> list[dict]:
    con = bpa.conectar()
    try:
        profissionais = bpa.listar_profissionais(con)
        mapa = bpa.mapa_categorias_por_profissional(con)
        return [
            {"cns": cns.zfill(15), "nome": nome.upper(), "categorias": sorted(mapa.get(cns, set()))}
            for cns, nome in profissionais
        ]
    finally:
        con.close()


aba_triagem, aba_digitacao, aba_geracao = st.tabs(["🧹 Triagem", "✍️ Digitação", "📦 Geração"])


# ═════════════════════════════════════════════════════════════════════════
# TRIAGEM
# ═════════════════════════════════════════════════════════════════════════
with aba_triagem:
    st.subheader("Organizar CPFs por enfermeiro")

    col1, col2 = st.columns([1, 2])
    with col1:
        data_triagem = st.text_input("Data do atendimento (DD/MM/AAAA)", key="triagem_data")
    with col2:
        enfermeiros_str = st.text_input(
            "Enfermeiros (separe por vírgula)",
            placeholder="Ex: MARIA ALVES, JOAO SILVA, ANA SOUZA",
            key="triagem_enfs",
        )

    texto_sujo = st.text_area(
        "📄 Cole aqui os dados sujos (CPF, um por linha)",
        height=280,
        key="triagem_texto_sujo",
    )

    col_btn1, col_btn2 = st.columns([1, 1])
    processar = col_btn1.button("🧹 Reordenar e dividir", use_container_width=True)
    salvar = col_btn2.button("💾 Salvar lote", use_container_width=True)

    if "triagem_resultado" not in st.session_state:
        st.session_state.triagem_resultado = ""

    if processar:
        if not data_triagem or len(data_triagem) < 10:
            st.error("Preencha a data completa (DD/MM/AAAA).")
        elif not enfermeiros_str.strip():
            st.error("Informe ao menos um enfermeiro.")
        else:
            documentos = bpa.extrair_documentos_validos(texto_sujo)
            if not documentos:
                st.error("Nenhum CPF válido encontrado no texto colado.")
                st.session_state.triagem_resultado = ""
            else:
                profissionais_lista = enfermeiros_str.split(",")
                st.session_state.triagem_resultado = bpa.dividir_em_lotes(documentos, profissionais_lista, data_triagem)
                st.success(f"{len(documentos)} documento(s) válido(s) — dividido em lotes de até 99.")

    st.text_area("🤖 Lote formatado (pronto para salvar)", value=st.session_state.triagem_resultado, height=200, key="triagem_saida")

    if salvar:
        if not st.session_state.triagem_resultado:
            st.error("Processe o texto antes de salvar.")
        elif not data_triagem or len(data_triagem) < 10:
            st.error("Preencha a data completa (DD/MM/AAAA).")
        else:
            arquivo = bpa.nome_arquivo_lote(data_triagem)
            caminho = bpa.caminho_lote(arquivo)
            atual = ""
            if __import__("os").path.exists(caminho):
                with open(caminho, encoding="utf-8") as f:
                    atual = f.read()
            novo_conteudo = f"{atual}\n{st.session_state.triagem_resultado}" if atual else st.session_state.triagem_resultado
            with open(caminho, "w", encoding="utf-8") as f:
                f.write(novo_conteudo)
            st.success(f"Lote salvo em {arquivo} (adicionado ao final, se já existia).")


# ═════════════════════════════════════════════════════════════════════════
# DIGITAÇÃO
# ═════════════════════════════════════════════════════════════════════════
with aba_digitacao:
    st.subheader("Registrar atendimentos de um médico")

    col_refresh, _ = st.columns([1, 4])
    if col_refresh.button("🔄 Recarregar pacientes/profissionais do Firebird"):
        carregar_base_pacientes.clear()
        carregar_profissionais.clear()
        st.rerun()

    profissionais = carregar_profissionais()
    opcoes_prof = {
        f"{p['nome']}" + (f" — {'/'.join(ROTULO_CATEGORIA[c] for c in p['categorias'])}" if p["categorias"] else " — sem CBO cadastrado"): p
        for p in profissionais
    }

    col1, col2 = st.columns([1, 2])
    with col1:
        data_dig = st.text_input("Data do atendimento (DD/MM/AAAA)", key="dig_data")
    with col2:
        escolha_prof = st.selectbox("Profissional (direto do Firebird, por CBO)", [""] + list(opcoes_prof.keys()), key="dig_prof")

    if st.button("✅ Confirmar profissional e data"):
        if not escolha_prof:
            st.error("Selecione o profissional!")
        elif not data_dig or len(data_dig) < 10:
            st.error("Digite a data completa (DD/MM/AAAA)!")
        else:
            prof = opcoes_prof[escolha_prof]
            arquivo = bpa.nome_arquivo_lote(data_dig)
            bpa.criar_cabecalho_lote(arquivo, prof["nome"], data_dig)
            st.session_state.dig_arquivo = arquivo
            st.session_state.dig_confirmado = True
            st.success(f"Gravando em {arquivo} — {prof['nome']}")

    if st.session_state.get("dig_confirmado"):
        st.info(f"📌 Lote ativo: **{st.session_state.dig_arquivo}**")

        base_pacientes = carregar_base_pacientes()
        termo = st.text_input("🔍 Pesquisar paciente por nome ou CPF (mín. 3 letras)", key="dig_busca")

        if termo and len(termo.strip()) >= 3:
            resultados = bpa.buscar_pacientes_memoria(termo.strip(), base_pacientes)
            if not resultados:
                st.warning("Nenhum paciente encontrado.")
            for p in resultados:
                cpf_fmt = p["cpf"]
                col_info, col_btn = st.columns([4, 1])
                with col_info:
                    st.markdown(f"**{p['nome']}**  \nDN: {p['dtnasc'] or '—'} · CPF: {cpf_fmt or '—'} · SUS: {p['sus'] or '—'}")
                with col_btn:
                    if not cpf_fmt:
                        st.button("Sem CPF", key=f"grava_{p['sus']}_{p['cpf']}", disabled=True)
                        st.caption("Cadastre o CPF na CADCNS")
                    elif st.button("Gravar", key=f"grava_{p['sus']}_{p['cpf']}"):
                        bpa.adicionar_documento_lote(st.session_state.dig_arquivo, cpf_fmt)
                        st.success(f"Gravado: {p['nome']} (CPF {cpf_fmt})")
                st.divider()


# ═════════════════════════════════════════════════════════════════════════
# GERAÇÃO
# ═════════════════════════════════════════════════════════════════════════
with aba_geracao:
    st.subheader("Montar o arquivo BPA-I pronto para importar")

    lotes = bpa.listar_lotes()
    opcoes_lote = {f"{l['nome']} ({l['tamanho'] / 1024:.1f} KB)": l["nome"] for l in lotes}

    col1, col2 = st.columns([3, 1])
    with col1:
        escolha_lote = st.selectbox("Lote de produção", [""] + list(opcoes_lote.keys()), key="ger_lote")
    with col2:
        if st.button("🔄 Atualizar lista"):
            st.rerun()

    if escolha_lote:
        nome_arquivo = opcoes_lote[escolha_lote]
        caminho = bpa.caminho_lote(nome_arquivo)

        if st.button("🔍 Analisar lote"):
            try:
                grupos = bpa.ler_arquivo_lote(caminho)
            except bpa.LoteError as e:
                st.error(str(e))
                grupos = []

            con = bpa.conectar()
            try:
                profissionais_raw = bpa.listar_profissionais(con)
                analise = []
                for idx, grupo in enumerate(grupos):
                    resolucao = bpa.resolver_profissional_por_nome(profissionais_raw, grupo["medico_raw"])
                    item = {"indice": idx, "grupo": grupo, "resolucao": resolucao}
                    if resolucao["status"] == "auto":
                        categoria, automatico = bpa.detectar_categoria(con, resolucao["cns"])
                        item["categoria_auto"] = categoria if automatico else None
                        item["categorias_possiveis"] = [categoria] if automatico else (categoria or list(bpa.PROCEDIMENTOS.keys()))
                    else:
                        item["categoria_auto"] = None
                        item["categorias_possiveis"] = list(bpa.PROCEDIMENTOS.keys())
                    analise.append(item)
                st.session_state.ger_analise = analise
            finally:
                con.close()

        analise = st.session_state.get("ger_analise")
        if analise:
            resolucoes_finais = []
            tudo_resolvido = True

            for item in analise:
                grupo = item["grupo"]
                resolucao = item["resolucao"]
                status = resolucao["status"]

                if status == "auto":
                    st.markdown(f"✅ **{grupo['medico_raw']}** ({grupo['data']}, {len(grupo['documentos'])} doc.) → **{resolucao['nome']}**")
                    cns_escolhido = resolucao["cns"]
                elif status == "ambiguo":
                    st.markdown(f"⚠️ **{grupo['medico_raw']}** ({grupo['data']}, {len(grupo['documentos'])} doc.) — múltiplos profissionais encontrados:")
                    opcoes = {f"{nome} ({cns})": cns for cns, nome in resolucao["candidatos"]}
                    escolha = st.selectbox("Escolha o profissional", [""] + list(opcoes.keys()), key=f"prof_{item['indice']}")
                    cns_escolhido = opcoes.get(escolha)
                else:
                    st.markdown(f"❌ **{grupo['medico_raw']}** ({grupo['data']}, {len(grupo['documentos'])} doc.) — profissional não encontrado:")
                    opcoes = {f"{nome} ({cns})": cns for cns, nome in resolucao["candidatos"]}
                    escolha = st.selectbox("Escolha manualmente", [""] + list(opcoes.keys()), key=f"prof_{item['indice']}")
                    cns_escolhido = opcoes.get(escolha)

                categorias_disp = item["categorias_possiveis"]
                if len(categorias_disp) == 1:
                    categoria_escolhida = categorias_disp[0]
                    st.caption(f"Categoria: {ROTULO_CATEGORIA[categoria_escolhida]}")
                else:
                    opcoes_cat = {ROTULO_CATEGORIA[c]: c for c in categorias_disp}
                    escolha_cat = st.selectbox("Categoria", [""] + list(opcoes_cat.keys()), key=f"cat_{item['indice']}")
                    categoria_escolhida = opcoes_cat.get(escolha_cat)

                if not cns_escolhido or not categoria_escolhida:
                    tudo_resolvido = False
                resolucoes_finais.append({"indice": item["indice"], "grupo": grupo, "cns_prof": cns_escolhido, "categoria": categoria_escolhida})
                st.divider()

            if st.button("✅ Gerar arquivo BPA-I", disabled=not tudo_resolvido, type="primary"):
                con = bpa.conectar()
                try:
                    todas_linhas = []
                    n_folhas_total = 0
                    competencias = []
                    todos_nao_encontrados = []

                    for r in resolucoes_finais:
                        grupo = r["grupo"]
                        try:
                            from datetime import datetime as _dt
                            data_dt = _dt.strptime(grupo["data"], "%d/%m/%Y")
                        except ValueError:
                            continue
                        data_aten = data_dt.strftime("%Y%m%d")
                        competencia = data_aten[:6]

                        cns_prof = r["cns_prof"].zfill(15)
                        categoria = r["categoria"]
                        pacientes, nao_encontrados, _inv = bpa.buscar_pacientes(con, grupo["documentos"])
                        todos_nao_encontrados.extend(nao_encontrados)
                        if not pacientes:
                            continue

                        competencias.append(competencia)
                        proc = bpa.PROCEDIMENTOS[categoria]["codigo"]
                        cbo = bpa.PROCEDIMENTOS[categoria]["cbo"]
                        linhas, n_folhas = bpa.montar_linhas(pacientes, proc, cbo, cns_prof, data_aten, competencia)
                        todas_linhas.extend(linhas)
                        n_folhas_total += n_folhas

                    if not todas_linhas:
                        st.error("Nenhuma linha gerada — confira as resoluções.")
                    else:
                        competencia_predominante = max(set(competencias), key=competencias.count)
                        cabecalho = bpa.montar_cabecalho(competencia_predominante, len(todas_linhas), n_folhas_total, todas_linhas)
                        ok, tam = bpa.validar(todas_linhas)
                        caminho_gerado = bpa.gerar_arquivo(todas_linhas, cabecalho, competencia_predominante)

                        st.success("🎯 Arquivo gerado com sucesso!")
                        col_a, col_b, col_c, col_d = st.columns(4)
                        col_a.metric("Registros", len(todas_linhas))
                        col_b.metric("Folhas", n_folhas_total)
                        col_c.metric("Competência", f"{competencia_predominante[4:]}/{competencia_predominante[:4]}")
                        col_d.metric("Não encontrados", len(todos_nao_encontrados))

                        if todos_nao_encontrados:
                            st.warning(f"CNS/CPF não encontrados na CADCNS: {', '.join(todos_nao_encontrados)}")

                        st.info(f"Arquivo salvo em: `{caminho_gerado}`")
                        with open(caminho_gerado, "rb") as f:
                            st.download_button("⬇️ Baixar arquivo BPA-I", f, file_name=__import__("os").path.basename(caminho_gerado))
                finally:
                    con.close()
    else:
        st.info("Selecione um lote acima para começar.")

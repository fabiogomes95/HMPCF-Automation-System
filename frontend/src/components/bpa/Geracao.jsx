import { useEffect, useState } from "react";
import {
  bpaListarLotes,
  bpaLerLote,
  bpaListarProfissionais,
  bpaAnalisarLote,
  bpaGerarLote,
  bpaUrlDownload,
} from "../../services/api";

const ROTULO_CATEGORIA = { medico: "Médico", enfermeiro: "Enfermeiro" };
const ROTULO_STATUS = {
  auto: { texto: "Resolvido automaticamente", classe: "bpa-badge-ok" },
  ambiguo: { texto: "Verificar profissional", classe: "bpa-badge-aviso" },
  nao_encontrado: { texto: "Profissional não encontrado", classe: "bpa-badge-erro" },
};

export default function Geracao() {
  const [lotes, setLotes] = useState([]);
  const [loteSelecionado, setLoteSelecionado] = useState("");
  const [conteudo, setConteudo] = useState("");
  const [profissionaisMap, setProfissionaisMap] = useState({});
  const [analise, setAnalise] = useState(null);
  const [resolucoes, setResolucoes] = useState({});
  const [analisando, setAnalisando] = useState(false);
  const [gerando, setGerando] = useState(false);
  const [resultado, setResultado] = useState(null);
  const [msg, setMsg] = useState(null);

  useEffect(() => {
    carregarLotes();
    bpaListarProfissionais().then((res) => {
      const mapa = {};
      res.data.forEach((p) => (mapa[p.cns] = p.categorias));
      setProfissionaisMap(mapa);
    });
  }, []);

  function carregarLotes() {
    bpaListarLotes()
      .then((res) => setLotes(res.data))
      .catch(() => setMsg({ tipo: "erro", texto: "Não foi possível listar os lotes." }));
  }

  async function selecionarLote(nome) {
    setLoteSelecionado(nome);
    setAnalise(null);
    setResolucoes({});
    setResultado(null);
    setMsg(null);
    if (!nome) {
      setConteudo("");
      return;
    }
    try {
      const res = await bpaLerLote(nome);
      setConteudo(res.data.conteudo);
    } catch {
      setConteudo("");
    }
  }

  async function analisar() {
    setAnalisando(true);
    setMsg(null);
    try {
      const res = await bpaAnalisarLote(loteSelecionado);
      setAnalise(res.data);
      setResolucoes({});
      setResultado(null);
    } catch (e) {
      setMsg({ tipo: "erro", texto: `Erro ao analisar: ${e.response?.data?.detail || e.message}` });
    } finally {
      setAnalisando(false);
    }
  }

  function atualizar(indice, patch) {
    setResolucoes((prev) => ({ ...prev, [indice]: { ...prev[indice], ...patch } }));
  }

  function dadosAtuais(grupo) {
    const r = resolucoes[grupo.indice] || {};
    const cns = r.cns_prof !== undefined ? r.cns_prof : grupo.cns_prof || "";
    const categoriasDisp = profissionaisMap[cns] || grupo.categorias_possiveis || [];
    let categoria = r.categoria !== undefined ? r.categoria : grupo.categoria || "";
    if (!categoria && categoriasDisp.length === 1) categoria = categoriasDisp[0];
    return { cns, categoriasDisp, categoria };
  }

  function candidatosDoGrupo(grupo) {
    if (grupo.candidatos_profissional.length > 0) return grupo.candidatos_profissional;
    return grupo.cns_prof ? [{ cns: grupo.cns_prof, nome: grupo.nome_prof }] : [];
  }

  async function gerar() {
    const resolvidos = analise.grupos.map((g) => {
      const d = dadosAtuais(g);
      return { indice: g.indice, cns_prof: d.cns, categoria: d.categoria };
    });
    const incompletos = resolvidos.filter((r) => !r.cns_prof || !r.categoria);
    if (incompletos.length > 0) {
      setMsg({ tipo: "erro", texto: `Resolva o profissional/categoria de ${incompletos.length} bloco(s) antes de gerar.` });
      return;
    }

    setGerando(true);
    setMsg(null);
    try {
      const res = await bpaGerarLote(loteSelecionado, resolvidos);
      setResultado(res.data);
      setMsg({ tipo: "ok", texto: "Arquivo BPA-I gerado com sucesso!" });
    } catch (e) {
      setMsg({ tipo: "erro", texto: `Erro ao gerar: ${e.response?.data?.detail || e.message}` });
    } finally {
      setGerando(false);
    }
  }

  return (
    <div className="bpa-card">
      <p className="bpa-card-titulo">📦 Geração — montar o arquivo BPA-I pronto para importar</p>

      <div className="bpa-row" style={{ marginBottom: 14 }}>
        <div className="bpa-field" style={{ flex: 1, minWidth: 280 }}>
          <label>Lote de produção</label>
          <select
            className="bpa-select"
            style={{ width: "100%" }}
            value={loteSelecionado}
            onChange={(e) => selecionarLote(e.target.value)}
          >
            <option value="">Selecione um arquivo…</option>
            {lotes.map((l) => (
              <option key={l.nome} value={l.nome}>
                {l.nome} ({(l.tamanho / 1024).toFixed(1)} KB)
              </option>
            ))}
          </select>
        </div>
        <button className="bpa-btn bpa-btn-secundario" onClick={carregarLotes}>
          🔄 Atualizar lista
        </button>
        <button className="bpa-btn bpa-btn-aviso" onClick={analisar} disabled={!loteSelecionado || analisando}>
          {analisando ? "Analisando…" : "🔍 Analisar lote"}
        </button>
      </div>

      {msg && (
        <p className="bpa-status-msg" style={{ color: msg.tipo === "ok" ? "#166534" : "#991b1b" }}>
          {msg.texto}
        </p>
      )}

      {!analise && (
        <>
          <p className="bpa-card-titulo">📄 Conteúdo do lote selecionado</p>
          <textarea className="bpa-textarea bpa-textarea--leitura" readOnly value={conteudo} placeholder="Selecione um lote acima para conferir o conteúdo..." />
        </>
      )}

      {analise && (
        <div>
          {analise.grupos.map((grupo) => {
            const status = ROTULO_STATUS[grupo.profissional_status];
            const { cns, categoriasDisp, categoria } = dadosAtuais(grupo);
            const candidatos = candidatosDoGrupo(grupo);
            const classeGrupo =
              grupo.profissional_status === "auto"
                ? "bpa-grupo--auto"
                : grupo.profissional_status === "ambiguo"
                ? "bpa-grupo--ambiguo"
                : "bpa-grupo--nao-encontrado";

            return (
              <div key={grupo.indice} className={`bpa-grupo ${classeGrupo}`}>
                <div className="bpa-grupo-topo">
                  <span className="bpa-grupo-nome">{grupo.medico_raw}</span>
                  <span className="bpa-grupo-meta">
                    {grupo.data} · {grupo.qtd_documentos} documento(s)
                  </span>
                  <span className={`bpa-badge ${status.classe}`}>{status.texto}</span>
                </div>

                <div className="bpa-grupo-escolha">
                  <div className="bpa-field">
                    <label>Profissional</label>
                    <select
                      className="bpa-select"
                      value={cns}
                      onChange={(e) => atualizar(grupo.indice, { cns_prof: e.target.value, categoria: "" })}
                    >
                      {!cns && <option value="">Escolha…</option>}
                      {candidatos.map((c) => (
                        <option key={c.cns} value={c.cns}>
                          {c.nome}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="bpa-field">
                    <label>Categoria</label>
                    <select
                      className="bpa-select"
                      value={categoria}
                      onChange={(e) => atualizar(grupo.indice, { categoria: e.target.value })}
                    >
                      {!categoria && <option value="">Escolha…</option>}
                      {(categoriasDisp.length > 0 ? categoriasDisp : ["medico", "enfermeiro"]).map((c) => (
                        <option key={c} value={c}>
                          {ROTULO_CATEGORIA[c]}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
              </div>
            );
          })}

          <div className="bpa-row" style={{ marginTop: 14 }}>
            <button className="bpa-btn bpa-btn-sucesso" onClick={gerar} disabled={gerando}>
              {gerando ? "Gerando…" : "✅ Gerar arquivo BPA-I"}
            </button>
          </div>
        </div>
      )}

      {resultado && (
        <div className="bpa-card" style={{ marginTop: 14, background: "#f0fdf4", borderColor: "#bbf7d0" }}>
          <p className="bpa-card-titulo">🎯 Arquivo gerado</p>
          <div className="bpa-resumo-grid">
            <div className="bpa-resumo-item">
              <div className="bpa-resumo-numero">{resultado.registros}</div>
              <div className="bpa-resumo-rotulo">Registros</div>
            </div>
            <div className="bpa-resumo-item">
              <div className="bpa-resumo-numero">{resultado.folhas}</div>
              <div className="bpa-resumo-rotulo">Folhas</div>
            </div>
            <div className="bpa-resumo-item">
              <div className="bpa-resumo-numero">{resultado.competencia.slice(4)}/{resultado.competencia.slice(0, 4)}</div>
              <div className="bpa-resumo-rotulo">Competência</div>
            </div>
            <div className="bpa-resumo-item">
              <div className="bpa-resumo-numero">{resultado.nao_encontrados.length}</div>
              <div className="bpa-resumo-rotulo">Não encontrados</div>
            </div>
          </div>

          {resultado.nao_encontrados.length > 0 && (
            <p className="bpa-status-msg" style={{ color: "#92400e" }}>
              CNS/CPF não encontrados na CADCNS: {resultado.nao_encontrados.join(", ")}
            </p>
          )}

          <p className="bpa-lote-info" style={{ marginBottom: 10 }}>
            Também salvo automaticamente em <strong>~/Downloads/{resultado.arquivo_gerado}</strong> na máquina do servidor.
          </p>

          <a className="bpa-btn bpa-btn-sucesso" href={bpaUrlDownload(resultado.arquivo_gerado)} download>
            ⬇️ Baixar {resultado.arquivo_gerado}
          </a>
        </div>
      )}
    </div>
  );
}

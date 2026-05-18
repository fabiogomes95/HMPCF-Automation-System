import { useState, useEffect, useCallback, useRef } from "react";
import api from "../services/api";
import "./BPA.css";

function mostrarToast(mensagem, tipo = "info") {
  const c = document.getElementById("toastContainerBPA") || (() => { const d = document.createElement("div"); d.id = "toastContainerBPA"; d.className = "toast-container-bpa"; document.body.appendChild(d); return d; })();
  const bg = { success: "#22c55e", danger: "#ef4444", warning: "#f59e0b", info: "#1a5b9c" };
  const el = document.createElement("div");
  Object.assign(el.style, { backgroundColor: bg[tipo] || bg.info, color: "#fff", padding: "12px 20px", borderRadius: "8px", fontWeight: "500", fontSize: "14px", boxShadow: "0 4px 12px rgba(0,0,0,0.15)" });
  el.textContent = mensagem;
  c.appendChild(el);
  setTimeout(() => el.remove(), 4000);
}

function maskCPF(v) {
  const d = (v || "").replace(/\D/g, "").slice(0, 11);
  let r = "";
  for (let i = 0; i < d.length; i++) {
    if (i === 3 || i === 6) r += ".";
    if (i === 9) r += "-";
    r += d[i];
  }
  return r || "---";
}

function maskSUS(v) {
  const d = (v || "").replace(/\D/g, "").slice(0, 15);
  let r = "";
  for (let i = 0; i < d.length; i++) {
    if (i === 3 || i === 7 || i === 11) r += " ";
    r += d[i];
  }
  return r || "---";
}

function maskDate(v) {
  if (!v) return "---";
  const d = v.replace(/\D/g, "");
  if (d.length === 8) {
    return `${d.slice(0, 2)}/${d.slice(2, 4)}/${d.slice(4, 8)}`;
  }
  return v;
}

/* ================================================================
   TELA PRINCIPAL — HUB DE AUTOMAÇÃO
   ================================================================ */
function TelaPrincipal({ setView }) {
  const [arquivos, setArquivos] = useState([]);
  const [arquivoSelecionado, setArquivoSelecionado] = useState("");
  const [conteudoOriginal, setConteudoOriginal] = useState("Selecione um arquivo acima...");
  const [conteudoEditado, setConteudoEditado] = useState("Selecione um arquivo acima...");
  const [salvando, setSalvando] = useState(false);

  const carregarArquivos = useCallback(async () => {
    try {
      const r = await api.get("/bpa/producoes");
      setArquivos(r.data || []);
    } catch { setArquivos([]); }
  }, []);

  const carregarConteudo = useCallback(async (nome) => {
    if (!nome) {
      setConteudoOriginal("Selecione um arquivo acima...");
      setConteudoEditado("Selecione um arquivo acima...");
      return;
    }
    try {
      const r = await api.get(`/bpa/producoes/${encodeURIComponent(nome)}`);
      const txt = r.data || "";
      setConteudoOriginal(txt);
      setConteudoEditado(txt);
    } catch {
      setConteudoOriginal("Erro ao carregar");
      setConteudoEditado("Erro ao carregar");
    }
  }, []);

  const salvarConteudo = async () => {
    if (!arquivoSelecionado) return;
    setSalvando(true);
    try {
      await api.put(`/bpa/producoes/${encodeURIComponent(arquivoSelecionado)}`, { conteudo: conteudoEditado });
      setConteudoOriginal(conteudoEditado);
      mostrarToast("Arquivo salvo com sucesso!", "success");
    } catch {
      mostrarToast("Erro ao salvar arquivo", "danger");
    } finally {
      setSalvando(false);
    }
  };

  useEffect(() => { carregarArquivos(); }, [carregarArquivos]);

  const temAlteracao = conteudoOriginal !== conteudoEditado;

  return (
    <div className="bpa-page">
      <h2 className="bpa-title">BPA - Automação</h2>
      <p className="bpa-subtitle">Boletim de Produção Ambulatorial</p>

      <div className="bpa-hub-cards">
        <button className="bpa-hub-card" onClick={() => setView("digitacao")}>
          <div className="bpa-hub-icon">✍️</div>
          <h5>Digitação Manual</h5>
          <p>Adicionar pacientes aos lotes de produção</p>
        </button>
        <button className="bpa-hub-card" onClick={() => setView("robo")}>
          <div className="bpa-hub-icon">🚀</div>
          <h5>Robô RPA</h5>
          <p>Executar digitação automática no sistema BPA</p>
        </button>
        <button className="bpa-hub-card" onClick={() => setView("triagem")}>
          <div className="bpa-hub-icon">🔍</div>
          <h5>Triagem</h5>
          <p>Extrair CPF/SUS de dados bagunçados</p>
        </button>
      </div>

      <div className="bpa-file-viewer">
        <div className="bpa-file-header">
          <span className="bpa-file-label">📂 Arquivos de Produção:</span>
          <select
            className="bpa-file-select"
            value={arquivoSelecionado}
            onChange={(e) => { setArquivoSelecionado(e.target.value); carregarConteudo(e.target.value); }}
          >
            <option value="">Selecione um lote...</option>
            {arquivos.map((a) => <option key={a} value={a}>{a}</option>)}
          </select>
          <button className="bpa-btn-sm bpa-btn-refresh" onClick={() => { carregarArquivos(); carregarConteudo(arquivoSelecionado); }}>↻</button>
        </div>
        <textarea
          className={`bpa-file-content ${temAlteracao ? "bpa-edited" : ""}`}
          value={conteudoEditado}
          onChange={(e) => setConteudoEditado(e.target.value)}
          rows={15}
        />
        {temAlteracao && (
          <div className="bpa-file-actions">
            <button className="bpa-btn-sm bpa-btn-cancel" onClick={() => setConteudoEditado(conteudoOriginal)}>
              Desfazer
            </button>
            <button className="bpa-btn-sm bpa-btn-save" onClick={salvarConteudo} disabled={salvando}>
              {salvando ? "Salvando..." : "Salvar"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

/* ================================================================
   TELA DE DIGITAÇÃO MANUAL
   ================================================================ */
function TelaDigitacao({ setView }) {
  const [medico, setMedico] = useState("");
  const [data, setData] = useState(new Date().toLocaleDateString("pt-BR"));
  const [arquivoAtual, setArquivoAtual] = useState("");
  const [cabecalhoConfirmado, setCabecalhoConfirmado] = useState(false);
  const [termo, setTermo] = useState("");
  const [resultados, setResultados] = useState([]);
  const [status, setStatus] = useState("");

  const buscaTimer = useRef(null);

  const confirmarCabecalho = async () => {
    if (!medico.trim() || !data.trim()) return mostrarToast("Preencha médico e data!", "warning");
    const nomeArquivo = data.replace(/\//g, "-") + ".txt";
    try {
      const res = await api.post("/bpa/producoes/cabecalho", { arquivo: nomeArquivo, medico, data });
      setArquivoAtual(nomeArquivo);
      setCabecalhoConfirmado(true);
      if (res.data.criado) {
        setStatus(`📌 Gravando em: ${nomeArquivo} | ${medico.toUpperCase()}`);
      } else {
        setStatus(`↻ Continuando lote existente: ${nomeArquivo} | ${medico.toUpperCase()}`);
      }
      setTimeout(() => setStatus(""), 4000);
    } catch { mostrarToast("Erro ao criar cabeçalho", "danger"); }
  };

  const pesquisar = useCallback(async (t) => {
    if (t.length < 3) { setResultados([]); return; }
    try {
      const r = await api.get("/bpa/pacientes", { params: { termo: t } });
      setResultados(r.data || []);
    } catch { setResultados([]); }
  }, []);

  useEffect(() => {
    clearTimeout(buscaTimer.current);
    buscaTimer.current = setTimeout(() => pesquisar(termo), 200);
    return () => clearTimeout(buscaTimer.current);
  }, [termo, pesquisar]);

  const gravarPaciente = async (nome, documento) => {
    if (!cabecalhoConfirmado) return mostrarToast("Confirme médico e data primeiro!", "warning");
    if (!documento) return mostrarToast("Paciente sem documento!", "warning");
    try {
      await api.post(`/bpa/producoes/${encodeURIComponent(arquivoAtual)}/paciente`, { arquivo: arquivoAtual, documento });
      setStatus(`✅ GRAVADO: ${nome}`);
      setTermo("");
      setResultados([]);
      document.getElementById("bpa-search-input")?.focus();
      setTimeout(() => setStatus(""), 3000);
    } catch { mostrarToast("Erro ao gravar", "danger"); }
  };

  const handleResultKeyDown = (e, p) => {
    const items = document.querySelectorAll(".bpa-result-item");
    const currentIndex = Array.from(items).indexOf(e.currentTarget);
    if (e.key === "Tab" || e.key === "ArrowDown") {
      e.preventDefault();
      const next = items[currentIndex + 1];
      if (next) next.focus();
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      const prev = items[currentIndex - 1];
      if (prev) prev.focus();
      else document.getElementById("bpa-search-input")?.focus();
    } else if (e.key === "Enter") {
      e.preventDefault();
      const doc = p.sus || p.cpf || "";
      gravarPaciente(p.nome, doc);
    }
  };

  const handleSearchKeyDown = (e) => {
    if (e.key === "Tab" || e.key === "ArrowDown") {
      const firstItem = document.querySelector(".bpa-result-item");
      if (firstItem) { e.preventDefault(); firstItem.focus(); }
    }
  };

  return (
    <div className="bpa-page">
      <div className="bpa-top-bar">
        <button className="bpa-btn-back" onClick={() => setView("principal")}>⬅️ Voltar</button>
        <h3>✍️ Assistente de Digitação</h3>
      </div>

      <div className="bpa-digit-panel">
        <div className="bpa-digit-header">
          <div className="bpa-digit-field">
            <label>📅 Data:</label>
            <input type="text" value={data} onChange={(e) => setData(e.target.value)} maxLength={10} placeholder="DD/MM/AAAA" />
          </div>
          <div className="bpa-digit-field bpa-digit-field--grow">
            <label>👨‍⚕️ Médico:</label>
            <input type="text" value={medico} onChange={(e) => setMedico(e.target.value.toUpperCase())} placeholder="NOME DO PROFISSIONAL" />
          </div>
          <button className="bpa-btn bpa-btn-primary" onClick={confirmarCabecalho}>✅ Confirmar</button>
        </div>
        {status && <div className="bpa-digit-status">{status}</div>}
      </div>

      <div className="bpa-search-box">
        <input
          id="bpa-search-input"
          type="text"
          className="bpa-search-input"
          placeholder="🔍 Buscar paciente por nome, CPF ou SUS..."
          value={termo}
          onChange={(e) => setTermo(e.target.value)}
          onKeyDown={handleSearchKeyDown}
          autoFocus
        />
      </div>

      <div className="bpa-search-results">
        {resultados.length === 0 && termo.length >= 3 && (
          <div className="bpa-empty">Nenhum paciente encontrado</div>
        )}
        {resultados.map((p, i) => {
          const doc = p.sus || p.cpf || "";
          return (
            <div
              key={i}
              className="bpa-result-item"
              onClick={() => gravarPaciente(p.nome, doc)}
              onKeyDown={(e) => handleResultKeyDown(e, p)}
              tabIndex={0}
            >
              <div>
                <strong>{p.nome || "(sem nome)"}</strong>
                <small className="bpa-result-details">
                  DN: &quot;{maskDate(p.dn)}&quot; / SUS: {maskSUS(p.sus)} / CPF: {maskCPF(p.cpf)}
                </small>
              </div>
              <span className="bpa-badge-gravar">GRAVAR</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ================================================================
   TELA DO ROBÔ RPA
   ================================================================ */
function TelaRobo({ setView }) {
  const [arquivos, setArquivos] = useState([]);
  const [arquivoSel, setArquivoSel] = useState("");
  const [conteudo, setConteudo] = useState("");
  const [lotes, setLotes] = useState([]);
  const [loteIndex, setLoteIndex] = useState(0);
  const [showModal, setShowModal] = useState(false);
  const [executando, setExecutando] = useState(false);
  const [mensagem, setMensagem] = useState("");
  const [profissionalTipo, setProfissionalTipo] = useState("0301060029");
  const [contagem, setContagem] = useState(0);
  const [pid, setPid] = useState(null);
  const [loteConcluido, setLoteConcluido] = useState(false);
  const pollRef = useRef(null);

  useEffect(() => {
    api.get("/bpa/producoes").then((r) => setArquivos(r.data || [])).catch(() => {});
  }, []);

  const carregarConteudo = async (nome) => {
    setArquivoSel(nome);
    if (!nome) { setConteudo(""); return; }
    try {
      const r = await api.get(`/bpa/producoes/${encodeURIComponent(nome)}`);
      setConteudo(r.data || "");
    } catch { setConteudo(""); }
  };

  const preparar = async () => {
    if (!arquivoSel) return mostrarToast("Selecione um lote!", "warning");
    try {
      const r = await api.post("/bpa/robo/preparar", { arquivo: arquivoSel });
      if (r.data.erro) return mostrarToast(r.data.erro, "danger");
      if (!r.data.lotes || r.data.lotes.length === 0) return mostrarToast("Lote vazio ou sem cabeçalho!", "warning");
      setLotes(r.data.lotes);
      setLoteIndex(0);
      setShowModal(true);
      setMensagem("");
      setContagem(0);
      setPid(null);
      setLoteConcluido(false);
    } catch { mostrarToast("Erro ao preparar", "danger"); }
  };

  const executarRobo = () => {
    setExecutando(true);
    setLoteConcluido(false);
    setContagem(5);
    setMensagem("🎯 Posicione o cursor no campo de digitação do sistema BPA!");
  };

  // Contagem regressiva
  useEffect(() => {
    if (!executando || contagem <= 0 || loteConcluido) return;
    const timer = setTimeout(() => setContagem(contagem - 1), 1000);
    return () => clearTimeout(timer);
  }, [executando, contagem, loteConcluido]);

  // Dispara RPA após contagem
  useEffect(() => {
    if (!executando || contagem > 0 || pid || loteConcluido) return;
    const disparar = async () => {
      try {
        const r = await api.post("/bpa/robo/executar", {
          medico: loteAtual.medico,
          data: loteAtual.data,
          procedimento: profissionalTipo,
          pacientes: loteAtual.validados,
        });
        if (r.data.status === "ok") {
          setPid(r.data.pid);
          setMensagem(`⏳ Executando RPA (PID ${r.data.pid})... ${loteAtual.validados.length} pacientes`);
        } else {
          setMensagem("❌ " + (r.data.mensagem || "Erro ao executar"));
          setExecutando(false);
        }
      } catch {
        setMensagem("❌ Erro ao comunicar com o servidor");
        setExecutando(false);
      }
    };
    disparar();
  }, [executando, contagem]);

  // Polling de status
  useEffect(() => {
    if (!pid) return;
    pollRef.current = setInterval(async () => {
      try {
        const r = await api.get(`/bpa/robo/status/${pid}`);
        if (r.data.status === "concluido") {
          clearInterval(pollRef.current);
          setLoteConcluido(true);
          setMensagem(`✅ Lote concluído! ${loteAtual.validados.length} pacientes digitados.`);
          setExecutando(false);
        }
      } catch {
        clearInterval(pollRef.current);
        setLoteConcluido(true);
        setMensagem("⚠️ Não foi possível verificar o status. O RPA pode ter encerrado.");
        setExecutando(false);
      }
    }, 2000);
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [pid]);

  const proximoLote = () => {
    const next = loteIndex + 1;
    if (next >= lotes.length) {
      setMensagem("🎉 Todos os lotes foram processados!");
      setShowModal(false);
      mostrarToast("Todos os lotes concluídos!", "success");
      return;
    }
    setLoteIndex(next);
    setContagem(0);
    setPid(null);
    setLoteConcluido(false);
    setMensagem("");
  };

  const loteAtual = lotes[loteIndex] || null;
  const ehUltimoLote = loteIndex >= lotes.length - 1;
  const podeFechar = !executando && contagem === 0;

  return (
    <div className="bpa-page">
      <div className="bpa-top-bar">
        <button className="bpa-btn-back" onClick={() => setView("principal")}>⬅️ Voltar</button>
        <h3>🚀 Execução Robô BPA</h3>
      </div>

      <div className="bpa-robo-panel">
        <div className="bpa-robo-controls">
          <span className="bpa-file-label">📂 Lote de Produção:</span>
          <select className="bpa-file-select" value={arquivoSel} onChange={(e) => carregarConteudo(e.target.value)}>
            <option value="">Selecione...</option>
            {arquivos.map((a) => <option key={a} value={a}>{a}</option>)}
          </select>
          <button className="bpa-btn bpa-btn-primary" onClick={preparar}>▶️ Iniciar Automação</button>
        </div>
        <textarea className="bpa-file-content" readOnly value={conteudo} rows={15} />
      </div>

      {showModal && loteAtual && (
        <div className="bpa-modal-overlay" onClick={() => podeFechar && setShowModal(false)}>
          <div className="bpa-modal" onClick={(e) => e.stopPropagation()}>
            <h4>
              📦 Lote {loteIndex + 1} de {lotes.length}
            </h4>
            <p><strong>Profissional:</strong> {loteAtual.medico}</p>
            <p><strong>Data do Lote:</strong> {loteAtual.data}</p>
            <p><strong>Pacientes:</strong> <span className="bpa-badge-success">{loteAtual.validados.length}</span> válidos de {loteAtual.pacientes.length} total</p>
            <hr />
            <div className="bpa-digit-field">
              <label>Tipo de Profissional:</label>
              <select
                className="bpa-file-select"
                value={profissionalTipo}
                onChange={(e) => setProfissionalTipo(e.target.value)}
                disabled={executando || loteConcluido}
                style={{ width: "100%", maxWidth: "100%" }}
              >
                <option value="0301060029">Médico (0301060029)</option>
                <option value="0301010048">Enfermeiro (0301010048)</option>
              </select>
            </div>
            <hr />
            <p className="bpa-robo-aviso">
              ⚠️ Certifique-se de que o sistema BPA está aberto e com o cursor no campo de digitação.<br />
              O robô vai assumir o teclado automaticamente.
            </p>
            {mensagem && <p className="bpa-digit-status">{mensagem}</p>}
            {contagem > 0 && (
              <div style={{ textAlign: "center", fontSize: "3rem", fontWeight: 800, color: "var(--color-primary)", margin: "8px 0" }}>
                {contagem}
              </div>
            )}
            <div className="bpa-modal-actions">
              {!loteConcluido ? (
                <>
                  <button className="bpa-btn bpa-btn-cancel" onClick={() => { setShowModal(false); setExecutando(false); }} disabled={executando && contagem > 0}>Fechar</button>
                  <button className="bpa-btn bpa-btn-primary" onClick={executarRobo} disabled={executando || pid}>
                    {executando && contagem > 0 ? `⏳ Preparando (${contagem}s)...` : executando ? "⏳ Executando..." : "▶️ Executar RPA"}
                  </button>
                </>
              ) : (
                <>
                  <button className="bpa-btn bpa-btn-cancel" onClick={() => setShowModal(false)}>Fechar</button>
                  <button className="bpa-btn bpa-btn-primary" onClick={proximoLote}>
                    {ehUltimoLote ? "🏁 Finalizar" : "➡️ Próximo Lote"}
                  </button>
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/* ================================================================
   TELA DE TRIAGEM
   ================================================================ */
function TelaTriagem({ setView }) {
  const [texto, setTexto] = useState("");
  const [enfermeiros, setEnfermeiros] = useState("");
  const [dataTriagem, setDataTriagem] = useState(new Date().toLocaleDateString("pt-BR"));
  const [resultado, setResultado] = useState(null);
  const [resultadoLotes, setResultadoLotes] = useState(null);
  const [gerando, setGerando] = useState(false);

  const processar = async () => {
    if (!texto.trim()) return mostrarToast("Cole o texto bagunçado!", "warning");
    try {
      const r = await api.post("/bpa/triagem", { conteudo: texto });
      setResultado(r.data);
      setResultadoLotes(null);
      mostrarToast(`${r.data.total} documentos extraídos!`, "success");
    } catch { mostrarToast("Erro ao processar", "danger"); }
  };

  const gerarLotes = async () => {
    if (!texto.trim()) return mostrarToast("Cole o texto bagunçado!", "warning");
    if (!enfermeiros.trim()) return mostrarToast("Informe os nomes dos enfermeiros!", "warning");
    if (!dataTriagem.trim()) return mostrarToast("Informe a data!", "warning");
    setGerando(true);
    try {
      const r = await api.post("/bpa/triagem/enfermeiros", {
        conteudo: texto,
        enfermeiros: enfermeiros,
        data: dataTriagem,
      });
      if (r.data.erro) return mostrarToast(r.data.erro, "danger");
      setResultadoLotes(r.data);
      mostrarToast(`Arquivo ${r.data.arquivo} gerado com ${r.data.total_validos} pacientes!`, "success");
    } catch { mostrarToast("Erro ao gerar lotes", "danger"); }
    finally { setGerando(false); }
  };

  return (
    <div className="bpa-page">
      <div className="bpa-top-bar">
        <button className="bpa-btn-back" onClick={() => setView("principal")}>⬅️ Voltar</button>
        <h3>🔍 Triagem - Enfermeiros</h3>
      </div>

      <div className="bpa-triagem-panel">
        <label className="bpa-triagem-label">1. Cole os dados bagunçados (nomes + CPF/SUS misturados):</label>
        <textarea className="bpa-file-content" value={texto} onChange={(e) => setTexto(e.target.value)} rows={8} placeholder="MARIA 123.456.789-00 898765432109876 JOAO&#10;JOSE 11122233344 123456789012345" />

        <div style={{ display: "flex", gap: "var(--spacing-md)", marginTop: 12, flexWrap: "wrap", alignItems: "flex-end" }}>
          <div className="bpa-digit-field" style={{ flex: 2, minWidth: 200 }}>
            <label>2. Nomes dos Enfermeiros (separados por vírgula):</label>
            <input type="text" value={enfermeiros} onChange={(e) => setEnfermeiros(e.target.value)} placeholder="Ex: Mirlane, Tata, Jessica" />
          </div>
          <div className="bpa-digit-field" style={{ flex: 1, minWidth: 140 }}>
            <label>3. Data do Lote:</label>
            <input type="text" value={dataTriagem} onChange={(e) => setDataTriagem(e.target.value)} placeholder="DD/MM/AAAA" />
          </div>
          <button className="bpa-btn bpa-btn-primary" onClick={gerarLotes} disabled={gerando} style={{ height: 38 }}>
            {gerando ? "⏳ Gerando..." : "📦 Gerar Lotes"}
          </button>
        </div>

        <div style={{ display: "flex", gap: "var(--spacing-md)", marginTop: 8 }}>
          <button className="bpa-btn bpa-btn-cancel" onClick={processar}>🔍 Só Extrair (teste)</button>
        </div>

        {resultado && !resultadoLotes && (
          <div className="bpa-triagem-result">
            <h4>Documentos Extraídos ({resultado.total})</h4>
            <textarea className="bpa-file-content" readOnly value={resultado.documentos.join("\n")} rows={6} />
          </div>
        )}

        {resultadoLotes && (
          <div className="bpa-triagem-result">
            <h4>Arquivo Gerado: <code>{resultadoLotes.arquivo}</code></h4>
            <p>
              <span className="bpa-badge-success">{resultadoLotes.total_extraidos} extraídos</span>{' '}
              <span className="bpa-badge-success">{resultadoLotes.total_validos} válidos</span>{' '}
              <span className="bpa-badge-cancel">{resultadoLotes.total_invalidos} ignorados</span>
            </p>
            <table style={{ width: "100%", fontSize: "0.8rem", borderCollapse: "collapse", marginTop: 8 }}>
              <thead>
                <tr style={{ borderBottom: "1px solid var(--color-border)", textAlign: "left" }}>
                  <th style={{ padding: "6px 8px" }}>Enfermeiro</th>
                  <th style={{ padding: "6px 8px" }}>Pacientes</th>
                </tr>
              </thead>
              <tbody>
                {resultadoLotes.lotes.map((l, i) => (
                  <tr key={i} style={{ borderBottom: "1px solid var(--color-border)" }}>
                    <td style={{ padding: "6px 8px" }}>{l.enfermeiro}</td>
                    <td style={{ padding: "6px 8px" }}>{l.pacientes}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

/* ================================================================
   APP BPA
   ================================================================ */
export default function BPA() {
  const [view, setView] = useState("principal");

  switch (view) {
    case "digitacao": return <TelaDigitacao setView={setView} />;
    case "robo": return <TelaRobo setView={setView} />;
    case "triagem": return <TelaTriagem setView={setView} />;
    default: return <TelaPrincipal setView={setView} />;
  }
}

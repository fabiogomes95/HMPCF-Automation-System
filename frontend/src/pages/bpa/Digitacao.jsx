import { useEffect, useMemo, useRef, useState } from "react";
import { bpaLocal, arquivoGerado, arquivoParaData, fmtCpf, fmtDoc, fmtNum, mascaraData } from "../../services/bpaLocal";

// Digitação = MÉDICOS. Enfermeiros ficam na aba Enfermeiros (dividem os CPFs
// digitados aqui). Cada "Confirmar" abre um bloco no lote do dia
// (DD-MM-AAAA.txt); blocos do mesmo médico no mesmo dia são somados pelo BPA.

const RE_LOTE_DIA = /^\d{2}-\d{2}-\d{4}\.txt$/;
// médico + dia em uso: volta sozinho depois de um F5
const CHAVE_SESSAO = "hmpcf_bpa_digitacao";

function ResultadoGeracao({ r }) {
  if (!r) return null;
  if (!r.ok) return <div className="bp-aviso erro">{r.erro}</div>;
  const a = r.arquivos.medico;
  return (
    <div className="bp-aviso ok">
      <b>{a.arquivo}</b> — {fmtNum(a.registros)} registros · {a.folhas} folha(s) · competência {a.competencia}
      <small>Salvo em {a.caminho} — importe no BPA Magnético</small>
      {r.nao_encontrados?.length > 0 && (
        <small style={{ color: "var(--bp-alerta)", opacity: 1 }}>
          Não encontrados no Firebird (ficaram de fora): {r.nao_encontrados.map(fmtCpf).join(", ")}
        </small>
      )}
    </div>
  );
}

// "Já importou esse dia?" -- digitados no lote x o que já entrou no BPA Magnético
function SituacaoDia({ s, carregando, aoAtualizar }) {
  let tag = null;
  let texto = "Conferindo o BPA Magnético…";
  if (s && !s.ok) {
    texto = s.erro;
    tag = <span className="bp-tag erro">erro</span>;
  } else if (s) {
    texto = `BPA Magnético: ${fmtNum(s.no_bpa)} de ${fmtNum(s.digitados)}`;
    if (!s.digitados) tag = <span className="bp-tag neutro">nada digitado</span>;
    else if (!s.faltando) tag = <span className="bp-tag ok">tudo importado</span>;
    else if (!s.no_bpa) tag = <span className="bp-tag alerta">ainda não importado</span>;
    else tag = <span className="bp-tag erro">faltam {fmtNum(s.faltando)}</span>;
  }
  return (
    <div className="bp-linha" style={{ marginTop: 10, alignItems: "center", fontSize: 13, color: "var(--bp-texto-2)" }}>
      <span style={{ flex: 1 }}>{carregando && !s ? "Conferindo o BPA Magnético…" : texto}</span>
      {tag}
      <button className="bp-btn-sec" style={{ padding: "2px 8px" }} onClick={aoAtualizar} disabled={carregando}
              title="Conferir de novo (depois de importar no BPA Magnético)">⟳</button>
    </div>
  );
}

export default function Digitacao({ profissionais }) {
  // ── 1. dia e médico
  const [data, setData] = useState(""); // sem data padrão: digitam o mês seguinte, pulando dias entre os 2 notebooks
  const [buscaMedico, setBuscaMedico] = useState("");
  const [medico, setMedico] = useState(null);
  const [sessao, setSessao] = useState(null); // {arquivo, nome, cns, data}
  const [totalLote, setTotalLote] = useState(0);
  const [situacao, setSituacao] = useState(null); // digitados x já no BPA Magnético, do dia
  const [conferindoDia, setConferindoDia] = useState(false);
  const [erroCab, setErroCab] = useState("");

  // ── 2. pacientes
  const [q, setQ] = useState("");
  const [resultados, setResultados] = useState([]);
  const [sel, setSel] = useState(0);
  // do médico no dia, mais novo primeiro; daSessao = gravado agora (pode desfazer)
  const [gravados, setGravados] = useState([]);
  const [desfazendo, setDesfazendo] = useState(false);
  const [msg, setMsg] = useState(null);
  const [gravando, setGravando] = useState(false);
  const buscaRef = useRef(null);
  const medicoRef = useRef(null);
  const seqBusca = useRef(0);

  // ── 3. gerar
  const [lotes, setLotes] = useState([]);
  const [arquivosPasta, setArquivosPasta] = useState([]); // inclui os BPA_* já gerados
  const [loteSel, setLoteSel] = useState("");
  const [gerando, setGerando] = useState(false);
  const [resGeracao, setResGeracao] = useState(null);

  const medicos = useMemo(
    () => profissionais.filter((p) => p.categoria !== "enfermeiro"),
    [profissionais]
  );
  const medicosFiltrados = useMemo(() => {
    const t = buscaMedico.trim().toUpperCase();
    return t ? medicos.filter((p) => p.nome.toUpperCase().includes(t)).slice(0, 12) : [];
  }, [buscaMedico, medicos]);

  async function carregarLotes(preferir) {
    try {
      const todos = await bpaLocal.lotes();
      const l = todos.filter((x) => RE_LOTE_DIA.test(x.nome));
      setArquivosPasta(todos);
      setLotes(l);
      setLoteSel((atual) => (preferir && l.some((x) => x.nome === preferir) ? preferir : atual || l[0]?.nome || ""));
    } catch {
      setLotes([]);
    }
  }
  async function carregarSituacao(dataBR) {
    if (!dataBR) return;
    setConferindoDia(true);
    try {
      setSituacao(await bpaLocal.situacaoDia(dataBR));
    } catch {
      setSituacao(null);
    } finally {
      setConferindoDia(false);
    }
  }

  // O que esse médico já tem no dia (inclusive de antes de um F5)
  async function carregarDoLote(arquivo, nome) {
    try {
      const r = await bpaLocal.lote(arquivo);
      if (!r.ok) return;
      const bloco = r.blocos.find((b) => b.profissional.toUpperCase() === nome.toUpperCase());
      setGravados((bloco?.pacientes || []).map((p) => ({ doc: p.doc, nome: p.nome, hora: "", daSessao: false })).reverse());
      setTotalLote(r.blocos.reduce((t, b) => t + b.pacientes.length, 0));
    } catch {
      /* status do topo mostra se o BPA caiu */
    }
  }

  // Abre (ou reabre) o bloco do médico no dia. Sempre grava um cabeçalho novo:
  // o paciente entra embaixo do ÚLTIMO cabeçalho do arquivo, então reabrir sem
  // ele poderia jogar o paciente no bloco de outro médico.
  async function abrirSessao(nome, cns, dataBR) {
    const r = await bpaLocal.cabecalho(nome, cns, dataBR);
    if (!r.ok) throw new Error(r.erro);
    const s = { arquivo: r.arquivo, nome, cns, data: dataBR };
    setSessao(s);
    setData(dataBR); // mantém a data no campo (inclusive quando a sessão volta após F5) pro "Trocar"
    sessionStorage.setItem(CHAVE_SESSAO, JSON.stringify(s));
    setMsg(null);
    await carregarDoLote(r.arquivo, nome);
    carregarLotes(r.arquivo);
    carregarSituacao(dataBR);
    setTimeout(() => buscaRef.current?.focus(), 0);
  }

  useEffect(() => {
    carregarLotes();
    try {
      const salvo = JSON.parse(sessionStorage.getItem(CHAVE_SESSAO) || "null");
      if (salvo?.nome && salvo?.data) {
        abrirSessao(salvo.nome, salvo.cns, salvo.data).catch(() => sessionStorage.removeItem(CHAVE_SESSAO));
      }
    } catch {
      sessionStorage.removeItem(CHAVE_SESSAO);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  async function confirmar() {
    setErroCab("");
    if (!medico) return setErroCab("Escolha o médico na lista.");
    if (data.length < 10) return setErroCab("Digite a data completa (DD/MM/AAAA).");
    try {
      await abrirSessao(medico.nome, medico.cns, data);
    } catch (e) {
      setErroCab(e.message);
    }
  }

  function trocar() {
    sessionStorage.removeItem(CHAVE_SESSAO);
    setGravados([]);
    setSessao(null);
    setMedico(null);
    setBuscaMedico("");
    setQ("");
    setResultados([]);
    // a data continua; o cursor já vai pro médico
    setTimeout(() => medicoRef.current?.focus(), 0);
  }

  // Busca com espera curta; ignora resposta velha se a pessoa continuou digitando
  useEffect(() => {
    const termo = q.trim();
    if (termo.length < 2) {
      setResultados([]);
      return;
    }
    const n = ++seqBusca.current;
    const t = setTimeout(async () => {
      try {
        const lista = await bpaLocal.buscar(termo);
        if (n === seqBusca.current) {
          setResultados(lista);
          setSel(0);
        }
      } catch {
        /* status do topo mostra se o BPA caiu */
      }
    }, 120);
    return () => clearTimeout(t);
  }, [q]);

  async function gravar(p) {
    if (!sessao || !p || gravando) return;
    // Sem CPF: grava pelo número do cadastro no Firebird ("ID:n"); no arquivo do
    // BPA sai sem CPF/SUS e com "sem CPF = s" (SUS não é mais usado).
    const doc = p.cpf || (p.id != null ? `ID:${p.id}` : "");
    if (!doc) {
      setMsg({ tipo: "erro", texto: `${p.nome} não tem CPF nem cadastro no Firebird — não é possível gravar.` });
      return;
    }
    setGravando(true);
    try {
      const r = await bpaLocal.gravar(sessao.arquivo, doc, p.nome);
      if (r.ok) {
        const hora = new Date().toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
        setGravados((g) => [{ doc, nome: p.nome, hora, daSessao: true }, ...g]);
        setTotalLote((t) => t + 1);
        setMsg({ tipo: "ok", texto: `✓ Gravado: ${p.nome}` });
        setQ("");
        setResultados([]);
      } else {
        setMsg({ tipo: "erro", texto: r.erro });
      }
    } catch (e) {
      setMsg({ tipo: "erro", texto: e.message });
    } finally {
      setGravando(false);
      // volta o cursor pra busca depois que a tela atualizar -- pronto pro próximo paciente
      setTimeout(() => buscaRef.current?.focus(), 0);
    }
  }

  function teclaBusca(e) {
    // Tab anda na lista como a seta pra baixo (e volta ao 1º no fim); Shift+Tab sobe.
    // Sem resultados, o Tab funciona normal.
    if (e.key === "Tab" && resultados.length) {
      e.preventDefault();
      const n = resultados.length;
      setSel((s) => (e.shiftKey ? (s - 1 + n) % n : (s + 1) % n));
      return;
    }
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSel((s) => Math.min(s + 1, resultados.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSel((s) => Math.max(s - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      gravar(resultados[sel]);
    } else if (e.key === "Escape") {
      setQ("");
    }
  }

  async function desfazer(g) {
    if (!window.confirm(`Tirar ${g.nome || fmtDoc(g.doc)} do lote?`)) return;
    setDesfazendo(true);
    try {
      const r = await bpaLocal.desfazer(sessao.arquivo, g.doc);
      if (r.ok) {
        setGravados((lista) => lista.slice(1));
        setTotalLote((t) => t - 1);
        setMsg({ tipo: "ok", texto: `Desfeito: ${g.nome || fmtDoc(g.doc)} saiu do lote.` });
      } else {
        setMsg({ tipo: "erro", texto: r.erro });
      }
    } catch (e) {
      setMsg({ tipo: "erro", texto: e.message });
    } finally {
      setDesfazendo(false);
      setTimeout(() => buscaRef.current?.focus(), 0);
    }
  }

  // Arquivo dos médicos desse dia já gerado antes? (importar de novo duplica a produção)
  const jaGerado = loteSel ? arquivosPasta.find((a) => a.nome === arquivoGerado(loteSel, "medico")) : null;

  async function gerar() {
    if (!loteSel) return;
    if (jaGerado && !window.confirm(
      `O arquivo dos médicos deste dia já foi gerado (${jaGerado.modificado_em}).\n\n` +
      "Se ele já foi importado no BPA Magnético, importar de novo DUPLICA a produção.\n\nGerar de novo mesmo assim?"
    )) return;
    setGerando(true);
    setResGeracao(null);
    try {
      setResGeracao(await bpaLocal.gerar(loteSel, "medico"));
      carregarLotes(loteSel);
      if (sessao) carregarSituacao(sessao.data);
    } catch (e) {
      setResGeracao({ ok: false, erro: e.message });
    } finally {
      setGerando(false);
    }
  }


  return (
    <div className="bp-grade bp-grade-lado">
      <div className="bp-coluna">
        <section className="bp-cartao">
          <h2>1. Dia e médico</h2>
          <p className="bp-desc">Um lote por dia; cada médico abre um bloco. Enfermeiros ficam na aba Enfermeiros.</p>
          {sessao ? (
            <>
              <div className="bp-fixo">
                <div>
                  <b>{sessao.nome}</b>
                  {arquivoParaData(sessao.arquivo)} · lote {sessao.arquivo}
                </div>
                <button className="bp-btn-sec" onClick={trocar}>Trocar</button>
              </div>
              <div className="bp-contadores">
                <div><strong>{fmtNum(gravados.length)}</strong><span>Deste médico</span></div>
                <div><strong>{fmtNum(totalLote)}</strong><span>Total do dia</span></div>
              </div>
              <SituacaoDia s={situacao} carregando={conferindoDia} aoAtualizar={() => carregarSituacao(sessao.data)} />
            </>
          ) : (
            <>
              <label className="bp-rot" htmlFor="dig-data">Data do atendimento</label>
              <input id="dig-data" className="bp-campo curto" value={data} inputMode="numeric" placeholder="DD/MM/AAAA"
                     onChange={(e) => setData(mascaraData(e.target.value))} />
              <label className="bp-rot" htmlFor="dig-medico">Médico</label>
              <input id="dig-medico" ref={medicoRef} className="bp-campo" placeholder="Digite o nome…" value={buscaMedico}
                     onChange={(e) => { setBuscaMedico(e.target.value); setMedico(null); }} autoComplete="off" />
              {medicosFiltrados.length > 0 && !medico && (
                <div className="bp-opcoes">
                  {medicosFiltrados.map((p) => (
                    <div key={p.cns} className="bp-opcao simples"
                         onClick={() => { setMedico(p); setBuscaMedico(p.nome); }}>
                      <span><b>{p.nome}</b></span>
                      {p.categoria === "medico" ? <span className="bp-tag neutro">CBO {p.cbo}</span>
                                                : <span className="bp-tag alerta">sem CBO</span>}
                    </div>
                  ))}
                </div>
              )}
              {buscaMedico.trim() && !medico && medicosFiltrados.length === 0 && (
                <p className="bp-vazio">Nenhum médico com esse nome no Firebird.</p>
              )}
              <button className="bp-btn largo" onClick={confirmar} disabled={!medico}>Confirmar</button>
              {erroCab && <div className="bp-aviso erro">{erroCab}</div>}
            </>
          )}
        </section>

        <section className="bp-cartao">
          <h2>3. Gerar arquivo dos médicos</h2>
          <p className="bp-desc">Depois importe no BPA Magnético, como sempre.</p>
          <label className="bp-rot" htmlFor="dig-lote">Lote (dia)</label>
          <select id="dig-lote" className="bp-campo" value={loteSel} onChange={(e) => { setLoteSel(e.target.value); setResGeracao(null); }}>
            {lotes.length === 0 && <option value="">Nenhum lote digitado ainda</option>}
            {lotes.map((l) => (
              <option key={l.nome} value={l.nome}>{arquivoParaData(l.nome)} · alterado {l.modificado_em}</option>
            ))}
          </select>
          {jaGerado && !resGeracao && (
            <div className="bp-aviso alerta">
              Já gerado em {jaGerado.modificado_em}. Se já importou no BPA Magnético, importar de novo duplica a produção.
            </div>
          )}
          <button className="bp-btn verde largo" onClick={gerar} disabled={!loteSel || gerando}>
            {gerando ? "Gerando…" : "Gerar BPA dos médicos"}
          </button>
          <ResultadoGeracao r={resGeracao} />
        </section>
      </div>

      <section className="bp-cartao">
        <h2>2. Pacientes atendidos</h2>
        <p className="bp-desc">
          Digite o CPF ou o nome, escolha com <span className="bp-tecla">↑</span> <span className="bp-tecla">↓</span> ou <span className="bp-tecla">Tab</span> e
          aperte <span className="bp-tecla">Enter</span> para gravar. Digite <b>sem doc</b> para ver todos os pacientes sem documento.
        </p>
        <input ref={buscaRef} className="bp-campo" value={q} disabled={!sessao} autoComplete="off"
               placeholder={sessao ? "CPF ou nome do paciente" : "Confirme o dia e o médico primeiro"}
               onChange={(e) => setQ(e.target.value)} onKeyDown={teclaBusca} />
        {msg && <div className={`bp-aviso ${msg.tipo === "ok" ? "ok" : "erro"}`}>{msg.texto}</div>}

        {q.trim().length >= 2 && (
          resultados.length === 0 ? <p className="bp-vazio">Nenhum paciente encontrado no Firebird deste notebook.</p> : (
            <div className="bp-opcoes">
              {resultados.map((p, i) => (
                <div key={`${p.cpf}-${p.sus}-${p.id}-${i}`} className={`bp-opcao${i === sel ? " sel" : ""}`}
                     onMouseEnter={() => setSel(i)} onClick={() => gravar(p)}>
                  <span><b>{p.nome}</b><br /><small>nasc. {p.dtnasc || "—"}</small></span>
                  <span>{p.cpf ? fmtCpf(p.cpf) : <span style={{ color: "var(--bp-texto-3)" }}>sem CPF</span>}</span>
                  {p.cpf ? <span className="bp-tag ok">CPF ok</span>
                    : <span className="bp-tag alerta" title="Vai no BPA sem CPF/SUS, com 'sem CPF = Sim'">sem documento</span>}
                  <span style={{ justifySelf: "end" }}>{i === sel ? <span className="bp-tecla">Enter ↵</span> : ""}</span>
                </div>
              ))}
            </div>
          )
        )}

        <h3>Pacientes gravados</h3>
        {gravados.length === 0 ? (
          <p className="bp-vazio">{sessao ? "Nenhum paciente deste médico no dia ainda." : "—"}</p>
        ) : (
          <table className="bp-tabela">
            <thead><tr><th>#</th><th>Paciente</th><th>CPF</th><th className="num">Hora</th><th></th></tr></thead>
            <tbody>
              {gravados.map((g, i) => (
                <tr key={`${g.doc}-${gravados.length - i}`}>
                  <td>{gravados.length - i}</td>
                  <td>{g.nome || <span style={{ color: "var(--bp-texto-3)" }}>fora do Firebird</span>}</td>
                  <td>{fmtDoc(g.doc)}</td>
                  <td className="num">{g.hora || "—"}</td>
                  <td className="num">
                    {i === 0 && g.daSessao && (
                      <button className="bp-btn-sec" style={{ padding: "2px 8px" }} onClick={() => desfazer(g)} disabled={desfazendo}>
                        desfazer
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}


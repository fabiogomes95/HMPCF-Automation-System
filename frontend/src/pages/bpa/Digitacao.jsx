import { useEffect, useMemo, useRef, useState } from "react";
import { bpaLocal, arquivoParaData, fmtCpf, fmtNum, hojeBR, mascaraData } from "../../services/bpaLocal";

// Digitação = MÉDICOS. Enfermeiros ficam na aba Enfermeiros (dividem os CPFs
// digitados aqui). Cada "Confirmar" abre um bloco novo no lote do dia
// (DD-MM-AAAA.txt); o BPA local vira a folha sozinho a cada 99 pacientes.

const RE_LOTE_DIA = /^\d{2}-\d{2}-\d{4}\.txt$/;
const POR_FOLHA = 99;

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

export default function Digitacao({ profissionais }) {
  // ── 1. dia e médico
  const [data, setData] = useState(hojeBR);
  const [buscaMedico, setBuscaMedico] = useState("");
  const [medico, setMedico] = useState(null);
  const [sessao, setSessao] = useState(null); // {arquivo, nome, existentes}
  const [erroCab, setErroCab] = useState("");

  // ── 2. pacientes
  const [q, setQ] = useState("");
  const [resultados, setResultados] = useState([]);
  const [sel, setSel] = useState(0);
  const [gravados, setGravados] = useState([]); // deste bloco, mais novo primeiro
  const [msg, setMsg] = useState(null);
  const [gravando, setGravando] = useState(false);
  const buscaRef = useRef(null);
  const seqBusca = useRef(0);

  // ── 3. gerar
  const [lotes, setLotes] = useState([]);
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
      const l = (await bpaLocal.lotes()).filter((x) => RE_LOTE_DIA.test(x.nome));
      setLotes(l);
      setLoteSel((atual) => (preferir && l.some((x) => x.nome === preferir) ? preferir : atual || l[0]?.nome || ""));
    } catch {
      setLotes([]);
    }
  }
  useEffect(() => { carregarLotes(); }, []);

  async function confirmar() {
    setErroCab("");
    if (!medico) return setErroCab("Escolha o médico na lista.");
    if (data.length < 10) return setErroCab("Digite a data completa (DD/MM/AAAA).");
    try {
      const r = await bpaLocal.cabecalho(medico.nome, medico.cns, data);
      if (!r.ok) return setErroCab(r.erro);
      setSessao({ arquivo: r.arquivo, nome: medico.nome, existentes: r.existentes || 0 });
      setGravados([]);
      setMsg(null);
      carregarLotes(r.arquivo);
      setTimeout(() => buscaRef.current?.focus(), 0);
    } catch (e) {
      setErroCab(e.message);
    }
  }

  function trocar() {
    setSessao(null);
    setMedico(null);
    setBuscaMedico("");
    setQ("");
    setResultados([]);
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
    if (!p.cpf) {
      setMsg({ tipo: "erro", texto: `${p.nome} está sem CPF no Firebird — não é possível gravar.` });
      return;
    }
    setGravando(true);
    try {
      const r = await bpaLocal.gravar(sessao.arquivo, p.cpf, p.nome);
      if (r.ok) {
        const hora = new Date().toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
        setGravados((g) => [{ doc: p.cpf, nome: p.nome, hora }, ...g]);
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
      buscaRef.current?.focus();
    }
  }

  function teclaBusca(e) {
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

  async function gerar() {
    if (!loteSel) return;
    setGerando(true);
    setResGeracao(null);
    try {
      setResGeracao(await bpaLocal.gerar(loteSel, "medico"));
    } catch (e) {
      setResGeracao({ ok: false, erro: e.message });
    } finally {
      setGerando(false);
    }
  }

  const noBloco = gravados.length;

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
                <div><strong>{fmtNum(noBloco)}</strong><span>neste bloco · folha {Math.floor(noBloco / POR_FOLHA) + 1}</span></div>
                <div><strong>{fmtNum(sessao.existentes + noBloco)}</strong><span>no lote do dia</span></div>
              </div>
            </>
          ) : (
            <>
              <label className="bp-rot" htmlFor="dig-data">Data do atendimento</label>
              <input id="dig-data" className="bp-campo curto" value={data} inputMode="numeric"
                     onChange={(e) => setData(mascaraData(e.target.value))} />
              <label className="bp-rot" htmlFor="dig-medico">Médico</label>
              <input id="dig-medico" className="bp-campo" placeholder="Digite o nome…" value={buscaMedico}
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
          <button className="bp-btn verde largo" onClick={gerar} disabled={!loteSel || gerando}>
            {gerando ? "Gerando…" : "Gerar BPA dos médicos"}
          </button>
          <ResultadoGeracao r={resGeracao} />
        </section>
      </div>

      <section className="bp-cartao">
        <h2>2. Pacientes atendidos</h2>
        <p className="bp-desc">
          Digite o CPF ou o nome, escolha com <span className="bp-tecla">↑</span> <span className="bp-tecla">↓</span> e
          aperte <span className="bp-tecla">Enter</span> para gravar.
        </p>
        <input ref={buscaRef} className="bp-campo" value={q} disabled={!sessao || gravando} autoComplete="off"
               placeholder={sessao ? "CPF ou nome do paciente" : "Confirme o dia e o médico primeiro"}
               onChange={(e) => setQ(e.target.value)} onKeyDown={teclaBusca} />
        {msg && <div className={`bp-aviso ${msg.tipo === "ok" ? "ok" : "erro"}`}>{msg.texto}</div>}

        {q.trim().length >= 2 && (
          resultados.length === 0 ? <p className="bp-vazio">Nenhum paciente encontrado no Firebird deste notebook.</p> : (
            <div className="bp-opcoes">
              {resultados.map((p, i) => (
                <div key={`${p.cpf}-${p.sus}-${i}`} className={`bp-opcao${i === sel ? " sel" : ""}${p.cpf ? "" : " bloq"}`}
                     onMouseEnter={() => setSel(i)} onClick={() => gravar(p)}>
                  <span><b>{p.nome}</b><br /><small>nasc. {p.dtnasc || "—"}</small></span>
                  <span>{p.cpf ? fmtCpf(p.cpf) : <span style={{ color: "var(--bp-texto-3)" }}>sem CPF</span>}</span>
                  {p.cpf ? <span className="bp-tag ok">CPF ok</span> : <span className="bp-tag erro">não grava</span>}
                  <span style={{ justifySelf: "end" }}>{i === sel && p.cpf ? <span className="bp-tecla">Enter ↵</span> : ""}</span>
                </div>
              ))}
            </div>
          )
        )}

        <h3>Gravados neste bloco</h3>
        {gravados.length === 0 ? (
          <p className="bp-vazio">{sessao ? "Nenhum paciente gravado neste bloco ainda." : "—"}</p>
        ) : (
          <table className="bp-tabela">
            <thead><tr><th>#</th><th>Paciente</th><th>CPF</th><th className="num">Hora</th></tr></thead>
            <tbody>
              {gravados.map((g, i) => (
                <tr key={`${g.doc}-${gravados.length - i}`}>
                  <td>{gravados.length - i}</td><td>{g.nome}</td><td>{fmtCpf(g.doc)}</td><td className="num">{g.hora}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}


import { useEffect, useRef, useState } from "react";
import { bpaLocal, fmtNum } from "../../services/bpaLocal";

// Migração de pacientes servidor (PostgreSQL) → Firebird deste notebook.
// A automática roda sozinha na 1ª abertura do dia (últimos 40 dias); a manual
// escolhe a competência. As duas nunca rodam juntas (trava no BPA local).

const SITUACAO = {
  ok: { tag: "ok", texto: "concluída" },
  rodando: { tag: "alerta", texto: "em andamento" },
  erro: { tag: "erro", texto: "falhou" },
  interrompida: { tag: "alerta", texto: "interrompida" },
};

function dataHora(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  return `${d.toLocaleDateString("pt-BR")} ${d.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}`;
}

function mesAtualAAAAMM() {
  const d = new Date();
  return `${d.getFullYear()}${String(d.getMonth() + 1).padStart(2, "0")}`;
}

function CartaoAutomatica({ m }) {
  const s = SITUACAO[m?.situacao];
  return (
    <section className="bp-cartao">
      <h2>Automática do dia</h2>
      <p className="bp-desc">
        Na primeira vez que o BPA é aberto no dia, os pacientes atendidos na recepção nos últimos 40 dias
        vão sozinhos para o Firebird deste notebook. Quem já está lá é ignorado.
      </p>
      {!m || m.situacao === "nunca" ? (
        <p className="bp-vazio">Ainda não rodou neste notebook.</p>
      ) : (
        <>
          <div className="bp-linha" style={{ alignItems: "center" }}>
            <span className={`bp-tag ${s?.tag || "neutro"}`}>{s?.texto || m.situacao}</span>
            <span style={{ fontSize: 13, color: "var(--bp-texto-2)" }}>
              início {dataHora(m.inicio)}{m.fim ? ` · fim ${dataHora(m.fim)}` : ""}
            </span>
          </div>
          {m.situacao === "rodando" && m.total > 0 && (
            <>
              <div className="bp-barra"><span style={{ width: `${Math.round((m.i / m.total) * 100)}%` }} /></div>
              <div className="bp-barra-info"><span>{fmtNum(m.i)} / {fmtNum(m.total)}</span></div>
            </>
          )}
          {m.situacao === "ok" && (
            <div className="bp-kpis">
              <div className="bp-kpi"><strong>{fmtNum(m.inseridos)}</strong><span>novos</span></div>
              <div className="bp-kpi"><strong>{fmtNum(m.duplicatas)}</strong><span>já estavam</span></div>
              <div className="bp-kpi">
                <strong className={m.erros || m.cpf_invalidos ? "alerta" : ""}>{fmtNum((m.erros || 0) + (m.cpf_invalidos || 0))}</strong>
                <span>erros / CPF inválido</span>
              </div>
            </div>
          )}
          {m.erro && <div className="bp-aviso erro">{m.erro}</div>}
        </>
      )}
    </section>
  );
}

export default function Migracao({ migracaoAuto, aoTerminar }) {
  const [competencias, setCompetencias] = useState([]);
  const [mes, setMes] = useState(mesAtualAAAAMM);
  const [resumo, setResumo] = useState(null);
  const [consultando, setConsultando] = useState(false);
  const [erro, setErro] = useState("");
  const [rodando, setRodando] = useState(false);
  const [progresso, setProgresso] = useState(null); // {i, total}
  const [log, setLog] = useState([]);
  const [fim, setFim] = useState(null);
  const logRef = useRef(null);
  const esRef = useRef(null);

  useEffect(() => {
    bpaLocal.competencias()
      .then((c) => { setCompetencias(c); if (c[0]) setMes(c[0].value); })
      .catch(() => {});
    return () => esRef.current?.close();
  }, []);

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [log]);

  const autoRodando = migracaoAuto?.situacao === "rodando";

  async function verResumo() {
    setConsultando(true);
    setErro("");
    setResumo(null);
    setFim(null);
    try {
      const r = await bpaLocal.migracaoPreview(mes);
      r.ok ? setResumo(r) : setErro(r.erro);
    } catch (e) {
      setErro(e.message);
    } finally {
      setConsultando(false);
    }
  }

  function migrar() {
    setRodando(true);
    setErro("");
    setLog([]);
    setFim(null);
    setProgresso({ i: 0, total: resumo?.total || 0 });
    const es = new EventSource(bpaLocal.migracaoStreamUrl(mes));
    esRef.current = es;
    es.onmessage = (ev) => {
      const d = JSON.parse(ev.data);
      if (d.msg) setLog((l) => [...l, d.msg]);
      if (d.tipo === "log" && d.total) setProgresso({ i: 0, total: d.total });
      if (d.tipo === "progresso") setProgresso({ i: d.i, total: d.total });
      if (d.tipo === "erro" || d.tipo === "fim") {
        es.close();
        setRodando(false);
        if (d.tipo === "erro") setErro(d.msg);
        else {
          setFim(d);
          setProgresso((p) => p && { ...p, i: p.total });
          setResumo(null);
          aoTerminar?.();
        }
      }
    };
    es.onerror = () => {
      es.close();
      setRodando(false);
      setLog((l) => [...l, "Conexão com o BPA encerrada."]);
    };
  }

  const aFazer = resumo ? resumo.novos : 0;
  const pct = progresso?.total ? Math.round((progresso.i / progresso.total) * 100) : 0;

  return (
    <div className="bp-grade bp-grade-meio">
      <div className="bp-coluna">
        <CartaoAutomatica m={migracaoAuto} />

        <section className="bp-cartao">
          <h2>Manual — por competência</h2>
          <p className="bp-desc">Para rodar de novo no meio do dia ou migrar um mês inteiro.</p>
          <div className="bp-linha">
            <div style={{ flex: 1 }}>
              <label className="bp-rot" htmlFor="mig-mes">Competência</label>
              <select id="mig-mes" className="bp-campo" value={mes} disabled={rodando}
                      onChange={(e) => { setMes(e.target.value); setResumo(null); setFim(null); }}>
                {competencias.length === 0 && <option value={mes}>{mes.slice(4)}/{mes.slice(0, 4)}</option>}
                {competencias.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
              </select>
            </div>
            <button className="bp-btn contorno" onClick={verResumo} disabled={consultando || rodando}>
              {consultando ? "Consultando…" : "Ver resumo"}
            </button>
            <button className="bp-btn verde" onClick={migrar} disabled={!resumo || !aFazer || rodando || autoRodando}>
              {rodando ? "Migrando…" : resumo ? (aFazer ? `Migrar (${fmtNum(aFazer)})` : "Nada a migrar") : "Migrar"}
            </button>
          </div>
          {autoRodando && <div className="bp-aviso alerta">A migração automática do dia está rodando — a manual libera quando ela terminar.</div>}
          {consultando && <p className="bp-vazio">Consultando servidor e Firebird… pode levar alguns minutos em meses grandes.</p>}
          {resumo && (
            <div className="bp-kpis">
              <div className="bp-kpi"><strong>{fmtNum(resumo.novos)}</strong><span>novos</span></div>
              <div className="bp-kpi"><strong>{fmtNum(resumo.ja_existem)}</strong><span>já no Firebird</span></div>
              <div className="bp-kpi"><strong className={resumo.cpf_invalido ? "alerta" : ""}>{fmtNum(resumo.cpf_invalido)}</strong><span>CPF inválido</span></div>
            </div>
          )}
          {erro && <div className="bp-aviso erro">{erro}</div>}
        </section>
      </div>

      <section className="bp-cartao">
        <h2>Andamento</h2>
        <p className="bp-desc">Pode continuar usando o sistema; não feche esta aba até terminar.</p>
        {!progresso && !fim ? (
          <p className="bp-vazio">Nenhuma migração manual em andamento.</p>
        ) : (
          <>
            <div className={`bp-barra${erro ? " erro" : ""}`}><span style={{ width: `${pct}%` }} /></div>
            <div className="bp-barra-info">
              <span>{fmtNum(progresso?.i)} / {fmtNum(progresso?.total)}</span>
              <span>{pct}%</span>
            </div>
            {fim && (
              <div className={`bp-aviso ${fim.erros ? "alerta" : "ok"}`}>
                <b>Migração concluída:</b> {fmtNum(fim.inseridos)} novos ·
                {" "}{fmtNum(fim.duplicatas)} já estavam · {fmtNum(fim.cpf_invalidos)} CPF inválido · {fmtNum(fim.erros)} erro(s)
              </div>
            )}
            {log.length > 0 && <div className="bp-log" ref={logRef}>{log.join("\n")}</div>}
          </>
        )}
      </section>
    </div>
  );
}

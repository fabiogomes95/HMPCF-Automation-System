import { useEffect, useRef, useState } from "react";
import { bpaLocal, fmtCpf, fmtNum, fmtSus } from "../../services/bpaLocal";

// Buscar prontuário: acha o paciente no Firebird e mostra em que dias / com
// qual profissional ele já foi digitado nos lotes (inclusive lotes antigos por SUS).

export default function Prontuario() {
  const [q, setQ] = useState("");
  const [pacientes, setPacientes] = useState(null);
  const [buscando, setBuscando] = useState(false);
  const [erro, setErro] = useState("");
  const seq = useRef(0);

  useEffect(() => {
    const termo = q.trim();
    if (termo.length < 3) {
      setPacientes(null);
      setErro("");
      return;
    }
    const n = ++seq.current;
    const t = setTimeout(async () => {
      setBuscando(true);
      try {
        const r = await bpaLocal.prontuario(termo);
        if (n !== seq.current) return;
        if (r.ok) {
          setPacientes(r.pacientes);
          setErro("");
        } else setErro(r.erro || "Erro na busca.");
      } catch (e) {
        if (n === seq.current) setErro(e.message);
      } finally {
        if (n === seq.current) setBuscando(false);
      }
    }, 250);
    return () => clearTimeout(t);
  }, [q]);

  return (
    <section className="bp-cartao">
      <h2>Buscar prontuário</h2>
      <p className="bp-desc">Nome, CPF ou SUS — mostra em quais dias e com qual profissional o paciente já foi digitado.</p>
      <input className="bp-campo" value={q} onChange={(e) => setQ(e.target.value)} autoComplete="off"
             placeholder="Mínimo 3 letras ou números" autoFocus />
      {buscando && <p className="bp-vazio">Buscando…</p>}
      {erro && <div className="bp-aviso erro">{erro}</div>}
      {pacientes && !buscando && pacientes.length === 0 && <p className="bp-vazio">Nenhum paciente encontrado no Firebird.</p>}
      {pacientes?.map((p, i) => {
        const total = p.ocorrencias.reduce((s, o) => s + o.qtd, 0);
        return (
          <div key={`${p.cpf}-${p.sus}-${i}`} className="bp-pac">
            <div className="bp-pac-topo">
              <div>
                <b>{p.nome}</b><br />
                <small>nasc. {p.dtnasc || "—"} · SUS {fmtSus(p.sus) || "—"} · CPF {fmtCpf(p.cpf) || "—"}</small>
              </div>
              {!p.cpf ? <span className="bp-tag erro">sem CPF cadastrado</span>
                : total ? <span className="bp-tag ok">{fmtNum(total)} lançamento(s)</span>
                : <span className="bp-tag neutro">não digitado em nenhum lote</span>}
            </div>
            {p.ocorrencias.map((o, j) => (
              <div key={j} className="bp-oc">
                <span>{o.data}</span>
                <span><b>{o.medico_raw}</b>{o.subpasta ? <small style={{ color: "var(--bp-texto-2)" }}> · {o.subpasta}/{o.arquivo}</small> : null}</span>
                <span style={{ textAlign: "right", color: "var(--bp-texto-2)" }}>{o.qtd > 1 ? `${o.qtd}x` : ""}</span>
              </div>
            ))}
          </div>
        );
      })}
    </section>
  );
}

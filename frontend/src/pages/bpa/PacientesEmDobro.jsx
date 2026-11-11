import { useState } from "react";
import { bpaLocal, fmtNum } from "../../services/bpaLocal";

// Aba BPA › Migração: paciente com dois cadastros no Firebird DESTE notebook
// (um sem CPF + um com CPF, mesmo nome e nascimento). "Verificar" só mostra;
// "Corrigir" unifica (backup antes, tudo ou nada). Regras: bpa/bpa_local/services/unificar.py

export default function PacientesEmDobro() {
  const [r, setR] = useState(null);
  const [ocupado, setOcupado] = useState("");
  const [erro, setErro] = useState("");

  async function chamar(aplicar) {
    if (aplicar && !window.confirm(`Unificar ${r.total} paciente(s) no Firebird deste notebook? Um backup é gravado antes.`)) return;
    setOcupado(aplicar ? "corrigindo" : "verificando");
    setErro("");
    try {
      const res = await bpaLocal.unificar(aplicar);
      res.ok ? setR(res) : setErro(res.erro);
    } catch (e) {
      setErro(e.message);
    } finally {
      setOcupado("");
    }
  }

  return (
    <section className="bp-cartao" style={{ marginTop: 16 }}>
      <h2>Pacientes em dobro no Firebird</h2>
      <p className="bp-desc">
        Mesmo paciente com mais de um cadastro neste notebook: um sem CPF e outro com CPF (a migração já não faz
        mais isso), ou CPFs diferentes — aí vale o CPF que está hoje no cadastro do servidor (o último gravado na
        recepção). <b>Corrigir</b> deixa um cadastro só, sem quebrar os lotes, e grava backup antes. A produção já
        lançada não muda. Rode uma vez em cada notebook.
      </p>
      <div className="bp-linha">
        <button className="bp-btn contorno" onClick={() => chamar(false)} disabled={!!ocupado}>
          {ocupado === "verificando" ? "Verificando…" : "Verificar"}
        </button>
        <button className="bp-btn verde" onClick={() => chamar(true)} disabled={!r || r.aplicado || !r.total || !!ocupado}>
          {ocupado === "corrigindo" ? "Corrigindo…" : r && !r.aplicado ? (r.total ? `Corrigir (${fmtNum(r.total)})` : "Nada a corrigir") : "Corrigir"}
        </button>
      </div>
      {erro && <div className="bp-aviso erro">{erro}</div>}
      {r && (
        <>
          <div className={`bp-aviso ${r.aplicado ? "ok" : r.total ? "alerta" : "ok"}`} style={{ marginTop: 12 }}>
            {r.aplicado
              ? <><b>{fmtNum(r.total)} paciente(s) unificados.</b> Backup: {r.backup}</>
              : r.total ? <><b>{fmtNum(r.total)} paciente(s) em dobro</b> (um sem CPF + um com CPF).</>
                : "Nenhum paciente em dobro (sem CPF + com CPF) neste notebook."}
          </div>
          {r.acoes.length > 0 && (
            <div style={{ overflowX: "auto", maxHeight: 300, marginTop: 8 }}>
              <table className="bp-tabela">
                <thead><tr><th>Paciente</th><th>Nascimento</th><th>CPF que fica</th><th>Fica (ID)</th><th>Sai (ID)</th><th>Motivo</th></tr></thead>
                <tbody>
                  {r.acoes.map((a) => (
                    <tr key={a.fica}>
                      <td>{a.nome}</td><td>{a.nascimento}</td><td>{a.cpf}</td><td>{a.fica}</td><td>{a.sai.join(", ")}</td>
                      <td style={{ fontSize: 12 }}>{a.motivo}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {(r.avisos.length > 0 || r.cpfs_diferentes.length > 0) && (
            <div className="bp-aviso alerta" style={{ marginTop: 8 }}>
              <b>Conferir à mão (não mexidos):</b>
              <ul style={{ margin: "6px 0 0 18px" }}>
                {r.cpfs_diferentes.map((g) => (
                  <li key={g.nome + g.nascimento}>
                    {g.nome} ({g.nascimento}) — CPFs diferentes: {g.cadastros.map((c) => `${c.cpf || "sem CPF"} (ID ${c.id})`).join(", ")}
                  </li>
                ))}
                {r.avisos.map((a) => <li key={a}>{a}</li>)}
              </ul>
            </div>
          )}
        </>
      )}
    </section>
  );
}

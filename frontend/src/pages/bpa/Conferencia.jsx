import { Fragment, useEffect, useState } from "react";
import { bpaLocal, fmtCpf, fmtNum, mascaraData } from "../../services/bpaLocal";

// Conferência: lotes digitados × produção que já entrou no BPA Magnético
// (Firebird S_PRD). "Reenviar faltantes" sempre SIMULA primeiro e só grava
// depois de confirmar — escreve direto na produção do BPA Magnético.

const ddmm = (d) => d.slice(0, 5);

function Reenvio({ dia, aoConcluir, aoFechar }) {
  const [simulacao, setSimulacao] = useState(null);
  const [erro, setErro] = useState("");
  const [gravando, setGravando] = useState(false);
  const [gravado, setGravado] = useState(null);

  useEffect(() => {
    bpaLocal.reenviar(dia, dia, false)
      .then((r) => (r.ok ? setSimulacao(r) : setErro(r.erro)))
      .catch((e) => setErro(e.message));
  }, [dia]);

  async function confirmar() {
    if (!window.confirm(`Gravar ${simulacao.total} atendimento(s) de ${dia} DIRETO na produção do BPA Magnético (S_PRD)?`)) return;
    setGravando(true);
    try {
      const r = await bpaLocal.reenviar(dia, dia, true);
      if (r.ok) {
        setGravado(r);
        aoConcluir();
      } else setErro(r.erro);
    } catch (e) {
      setErro(e.message);
    } finally {
      setGravando(false);
    }
  }

  const res = gravado || simulacao;
  const profs = res?.dias?.[0]?.profissionais || [];

  return (
    <section className="bp-cartao" style={{ marginTop: 16, borderColor: "var(--bp-alerta-borda)" }}>
      <div className="bp-linha" style={{ justifyContent: "space-between", alignItems: "center" }}>
        <h2>Reenviar faltantes de {dia}</h2>
        <button className="bp-btn-sec" onClick={aoFechar}>Fechar</button>
      </div>
      {!res && !erro && <p className="bp-vazio">Simulando o que seria lançado…</p>}
      {erro && <div className="bp-aviso erro">{erro}</div>}
      {res && (
        <>
          <p className="bp-desc" style={{ marginTop: 6 }}>
            {gravado
              ? <>Gravado na produção: <b>{fmtNum(gravado.total)}</b> atendimento(s).</>
              : <>Simulação — nada foi gravado ainda. Seriam lançados <b>{fmtNum(simulacao.total)}</b> atendimento(s):</>}
          </p>
          <table className="bp-tabela">
            <thead><tr><th>Profissional</th><th className="num">Qtd</th><th>Folha / seq.</th><th>Observação</th></tr></thead>
            <tbody>
              {profs.map((p, i) => (
                <tr key={i}>
                  <td>{p.nome}{p.categoria ? <small style={{ color: "var(--bp-texto-2)" }}> · {p.categoria}</small> : null}</td>
                  <td className="num">{p.qtd ? fmtNum(p.qtd) : "—"}</td>
                  <td>{p.qtd ? `${p.folha_ini}/${p.seq_ini} → ${p.folha_fim}/${p.seq_fim}` : "—"}</td>
                  <td>
                    {p.erro && <span className="bp-tag erro">{p.erro}</span>}
                    {p.nao_encontrados?.length > 0 && (
                      <div className="bp-docs">fora do Firebird: {p.nao_encontrados.map(fmtCpf).join(", ")}</div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {!gravado && simulacao.total > 0 && (
            <button className="bp-btn perigo" style={{ marginTop: 14 }} onClick={confirmar} disabled={gravando}>
              {gravando ? "Gravando…" : `Confirmar: gravar ${fmtNum(simulacao.total)} na produção`}
            </button>
          )}
          {gravado && <div className="bp-aviso ok">Pronto. A conferência abaixo já foi atualizada.</div>}
        </>
      )}
    </section>
  );
}

export default function Conferencia() {
  const [ini, setIni] = useState("");
  const [fim, setFim] = useState("");
  const [r, setR] = useState(null);
  const [conferindo, setConferindo] = useState(false);
  const [erro, setErro] = useState("");
  const [aberto, setAberto] = useState(new Set()); // linhas com CPFs à mostra
  const [reenvioDia, setReenvioDia] = useState(null);

  async function conferir() {
    if ((ini && ini.length < 10) || (fim && fim.length < 10) || (!!ini !== !!fim)) {
      return setErro("Preencha as duas datas completas (DD/MM/AAAA) ou deixe as duas em branco (últimos 7 dias).");
    }
    setConferindo(true);
    setErro("");
    try {
      const res = await bpaLocal.conferencia(ini, fim);
      res.sucesso ? setR(res) : setErro(res.erro);
    } catch (e) {
      setErro(e.message);
    } finally {
      setConferindo(false);
    }
  }

  useEffect(() => { conferir(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const dias = r?.dias || [];
  const faltando = dias.reduce((s, d) => s + d.profissionais.reduce((t, p) => t + p.faltando_no_banco.length, 0), 0);
  const divergentes = dias.filter((d) => !d.ok).length;

  function alternar(chave) {
    setAberto((a) => {
      const n = new Set(a);
      n.has(chave) ? n.delete(chave) : n.add(chave);
      return n;
    });
  }

  return (
    <>
      <section className="bp-cartao">
        <h2>Conferência — digitado × produção no BPA Magnético</h2>
        <p className="bp-desc">
          Compara os lotes digitados com o que já entrou no Firebird (S_PRD). Nos dias com falta, "Reenviar faltantes"
          mostra antes o que vai ser lançado e só grava depois de confirmar.
        </p>
        <div className="bp-linha">
          <div>
            <label className="bp-rot" htmlFor="conf-ini">De</label>
            <input id="conf-ini" className="bp-campo curto" placeholder="últimos 7 dias" value={ini} inputMode="numeric"
                   onChange={(e) => setIni(mascaraData(e.target.value))} />
          </div>
          <div>
            <label className="bp-rot" htmlFor="conf-fim">Até</label>
            <input id="conf-fim" className="bp-campo curto" value={fim} inputMode="numeric"
                   onChange={(e) => setFim(mascaraData(e.target.value))} />
          </div>
          <button className="bp-btn" onClick={conferir} disabled={conferindo}>{conferindo ? "Conferindo…" : "Conferir"}</button>
        </div>
        {erro && <div className="bp-aviso erro">{erro}</div>}

        {r && (
          dias.length === 0 ? (
            <p className="bp-vazio">Nenhum lote digitado entre {r.data_ini} e {r.data_fim}.</p>
          ) : (
            <>
              <div className="bp-kpis">
                <div className="bp-kpi"><strong>{dias.length}</strong><span>dias conferidos ({r.data_ini} a {r.data_fim})</span></div>
                <div className="bp-kpi"><strong className="ok">{dias.length - divergentes}</strong><span>dias batendo</span></div>
                <div className="bp-kpi"><strong className={divergentes ? "erro" : ""}>{divergentes}</strong><span>dias com diferença</span></div>
                <div className="bp-kpi"><strong className={faltando ? "erro" : ""}>{fmtNum(faltando)}</strong><span>pacientes faltando</span></div>
              </div>
              <table className="bp-tabela" style={{ marginTop: 16 }}>
                <thead>
                  <tr><th>Dia</th><th>Profissional</th><th className="num">Digitados</th><th className="num">No BPA Magnético</th><th>Situação</th><th></th></tr>
                </thead>
                <tbody>
                  {dias.map((d) => {
                    const temFalta = d.profissionais.some((p) => p.faltando_no_banco.length);
                    return d.profissionais.map((p, i) => {
                      const chave = `${d.data}-${i}`;
                      const falt = p.faltando_no_banco.length;
                      const sobr = p.sobrando_no_banco.length;
                      return (
                        <Fragment key={chave}>
                          <tr className={i === 0 ? "dia-novo" : ""}>
                            <td>{i === 0 ? ddmm(d.data) : ""}</td>
                            <td>{p.nome}</td>
                            <td className="num">{fmtNum(p.digitado)}</td>
                            <td className="num">{fmtNum(p.banco)}</td>
                            <td>
                              {p.ok && <span className="bp-tag ok">confere</span>}
                              {falt > 0 && <span className="bp-tag erro">faltam {falt}</span>}{" "}
                              {sobr > 0 && <span className="bp-tag alerta">{sobr} a mais no BPA</span>}{" "}
                              {(falt > 0 || sobr > 0) && (
                                <button className="bp-btn-sec" style={{ padding: "2px 8px" }} onClick={() => alternar(chave)}>
                                  {aberto.has(chave) ? "ocultar CPFs" : "ver CPFs"}
                                </button>
                              )}
                            </td>
                            <td>
                              {i === 0 && temFalta && (
                                <button className="bp-btn-sec" onClick={() => setReenvioDia(d.data)}>Reenviar faltantes</button>
                              )}
                            </td>
                          </tr>
                          {aberto.has(chave) && (
                            <tr>
                              <td></td>
                              <td colSpan={5}>
                                {falt > 0 && <div className="bp-docs">faltando no BPA: {p.faltando_no_banco.map(fmtCpf).join(", ")}</div>}
                                {sobr > 0 && <div className="bp-docs">no BPA sem estar digitado: {p.sobrando_no_banco.map(fmtCpf).join(", ")}</div>}
                              </td>
                            </tr>
                          )}
                        </Fragment>
                      );
                    });
                  })}
                </tbody>
              </table>
            </>
          )
        )}
      </section>

      {reenvioDia && (
        <Reenvio key={reenvioDia} dia={reenvioDia} aoConcluir={conferir} aoFechar={() => setReenvioDia(null)} />
      )}
    </>
  );
}

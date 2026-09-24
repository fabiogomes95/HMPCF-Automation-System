import { useCallback, useEffect, useMemo, useState } from "react";
import { bpaLocal, dataParaArquivo, fmtCpf, fmtNum, hojeBR, mascaraData } from "../../services/bpaLocal";

// Enfermeiros: divide os CPFs que os MÉDICOS já digitaram no dia entre os
// enfermeiros marcados e gera o BPA dos enfermeiros. Refazer a divisão
// descarta a anterior (não duplica) — regra do BPA local.

export default function Enfermeiros({ profissionais }) {
  const [data, setData] = useState(hojeBR);
  const [lote, setLote] = useState(null); // {ok, blocos} | {ok:false, erro}
  const [carregando, setCarregando] = useState(false);
  const [marcados, setMarcados] = useState(new Set());
  const [dividindo, setDividindo] = useState(false);
  const [erro, setErro] = useState("");
  const [gerando, setGerando] = useState(false);
  const [resGeracao, setResGeracao] = useState(null);

  const enfermeiros = useMemo(() => profissionais.filter((p) => p.categoria === "enfermeiro"), [profissionais]);
  const dataCompleta = data.length === 10;

  const carregarLote = useCallback(async () => {
    if (!dataCompleta) return;
    setCarregando(true);
    setErro("");
    try {
      const r = await bpaLocal.lote(dataParaArquivo(data));
      setLote(r);
      if (r.ok) {
        // já marca quem está na divisão salva
        setMarcados(new Set(r.blocos.filter((b) => b.categoria === "enfermeiro").map((b) => b.cns)));
      }
    } catch (e) {
      setLote({ ok: false, erro: e.message });
    } finally {
      setCarregando(false);
    }
  }, [data, dataCompleta]);

  useEffect(() => {
    setResGeracao(null);
    carregarLote();
  }, [carregarLote]);

  const blocos = lote?.ok ? lote.blocos : [];
  const cpfsMedicos = blocos.filter((b) => b.categoria !== "enfermeiro").reduce((s, b) => s + b.pacientes.length, 0);
  const divisaoSalva = blocos.filter((b) => b.categoria === "enfermeiro");

  function alternar(cns) {
    setMarcados((m) => {
      const n = new Set(m);
      n.has(cns) ? n.delete(cns) : n.add(cns);
      return n;
    });
  }

  async function dividir() {
    const sel = enfermeiros.filter((e) => marcados.has(e.cns)).map((e) => ({ cns: e.cns, nome: e.nome }));
    if (!sel.length) return setErro("Marque ao menos um enfermeiro.");
    setDividindo(true);
    setErro("");
    setResGeracao(null);
    try {
      const r = await bpaLocal.dividir(data, sel);
      if (!r.ok) setErro(r.erro);
      await carregarLote();
    } catch (e) {
      setErro(e.message);
    } finally {
      setDividindo(false);
    }
  }

  async function gerar() {
    setGerando(true);
    setResGeracao(null);
    try {
      setResGeracao(await bpaLocal.gerar(dataParaArquivo(data), "enfermeiro"));
    } catch (e) {
      setResGeracao({ ok: false, erro: e.message });
    } finally {
      setGerando(false);
    }
  }

  const totalDividido = divisaoSalva.reduce((s, b) => s + b.pacientes.length, 0);
  const nMarcados = [...marcados].filter((c) => enfermeiros.some((e) => e.cns === c)).length;

  return (
    <div className="bp-grade bp-grade-meio">
      <section className="bp-cartao">
        <h2>1. Dia e enfermeiros</h2>
        <p className="bp-desc">
          Os CPFs já digitados pelos médicos nesse dia são divididos igualmente entre os enfermeiros marcados.
          Refazer não duplica.
        </p>
        <label className="bp-rot" htmlFor="enf-data">Data</label>
        <input id="enf-data" className="bp-campo curto" value={data} inputMode="numeric"
               onChange={(e) => setData(mascaraData(e.target.value))} />

        {!dataCompleta ? null : carregando ? (
          <p className="bp-vazio">Carregando o lote do dia…</p>
        ) : lote && !lote.ok ? (
          <div className="bp-aviso alerta">Nenhum lote digitado nesse dia ainda — digite os médicos primeiro.</div>
        ) : (
          <div className={`bp-aviso ${cpfsMedicos ? "info" : "alerta"}`}>
            <b>{fmtNum(cpfsMedicos)}</b> CPFs digitados pelos médicos neste dia
          </div>
        )}

        <label className="bp-rot">Enfermeiros</label>
        {enfermeiros.length === 0 ? (
          <p className="bp-vazio">Nenhum enfermeiro (CBO 223505) cadastrado no Firebird.</p>
        ) : (
          <div className="bp-opcoes">
            {enfermeiros.map((e) => (
              <label key={e.cns} className="bp-check">
                <input type="checkbox" checked={marcados.has(e.cns)} onChange={() => alternar(e.cns)} />
                <span>{e.nome}</span>
              </label>
            ))}
          </div>
        )}
        <button className="bp-btn largo" onClick={dividir} disabled={dividindo || !cpfsMedicos || !nMarcados}>
          {dividindo ? "Dividindo…" : `Dividir os ${fmtNum(cpfsMedicos)} CPFs entre ${nMarcados} enfermeiro(s)`}
        </button>
        {erro && <div className="bp-aviso erro">{erro}</div>}
      </section>

      <section className="bp-cartao">
        <h2>2. Divisão e arquivo</h2>
        <p className="bp-desc">Confira a divisão e gere o arquivo dos enfermeiros para importar no BPA Magnético.</p>
        {divisaoSalva.length === 0 ? (
          <p className="bp-vazio">Ainda não há divisão para este dia.</p>
        ) : (
          <table className="bp-tabela">
            <thead><tr><th>Enfermeiro</th><th className="num">CPFs</th></tr></thead>
            <tbody>
              {divisaoSalva.map((b) => (
                <tr key={b.cns}><td>{b.profissional}</td><td className="num">{fmtNum(b.pacientes.length)}</td></tr>
              ))}
              <tr><td><b>Total</b></td><td className="num"><b>{fmtNum(totalDividido)}</b></td></tr>
            </tbody>
          </table>
        )}
        <button className="bp-btn verde largo" onClick={gerar} disabled={!divisaoSalva.length || gerando}>
          {gerando ? "Gerando…" : "Gerar BPA dos enfermeiros"}
        </button>
        {resGeracao && (resGeracao.ok ? (
          <div className="bp-aviso ok">
            <b>{resGeracao.arquivos.enfermeiro.arquivo}</b> — {fmtNum(resGeracao.arquivos.enfermeiro.registros)} registros
            · {resGeracao.arquivos.enfermeiro.folhas} folha(s) · competência {resGeracao.arquivos.enfermeiro.competencia}
            <small>Salvo em {resGeracao.arquivos.enfermeiro.caminho} — importe no BPA Magnético</small>
            {resGeracao.nao_encontrados?.length > 0 && (
              <small style={{ color: "var(--bp-alerta)", opacity: 1 }}>
                Não encontrados no Firebird: {resGeracao.nao_encontrados.map(fmtCpf).join(", ")}
              </small>
            )}
          </div>
        ) : <div className="bp-aviso erro">{resGeracao.erro}</div>)}
      </section>
    </div>
  );
}

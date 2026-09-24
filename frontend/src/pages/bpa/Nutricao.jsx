import { useCallback, useEffect, useMemo, useState } from "react";
import { bpaLocal, fmtDoc, fmtNum, mascaraData } from "../../services/bpaLocal";

// Nutrição: lê a planilha do mês (DADOS NUTRIÇÃO.xlsx), mostra de quem é cada
// dia e gera UM arquivo com as nutricionistas e todos os dias, pra importar no
// BPA Magnético. Regras da planilha em bpa/nutricao.py; não mexe nos lotes
// DD-MM-AAAA.txt da digitação.

const SITUACAO = {
  ok: { tag: "ok", texto: "CPF ok" },
  corrigido: { tag: "alerta", texto: "CPF corrigido" },
  sem_doc: { tag: "neutro", texto: "sem documento" },
  nao_achado: { tag: "erro", texto: "não achado" },
};

function lerBase64(arquivo) {
  return new Promise((ok, falha) => {
    const r = new FileReader();
    r.onload = () => ok(String(r.result).split(",")[1] || "");
    r.onerror = () => falha(new Error("Não consegui ler o arquivo."));
    r.readAsDataURL(arquivo);
  });
}

// Mesma divisão do BPA local (nutricao.dividir): em ordem, um pra cada
function dividir(docs, nutris) {
  const por = Object.fromEntries(nutris.map((c) => [c, 0]));
  docs.forEach((_, i) => { por[nutris[i % nutris.length]] += 1; });
  return por;
}

export default function Nutricao() {
  const [arquivo, setArquivo] = useState(null); // {nome, b64}
  const [abas, setAbas] = useState([]);
  const [aba, setAba] = useState("");
  const [lido, setLido] = useState(null);
  const [dias, setDias] = useState([]); // cópia editável: nutricionistas e data do "sem dia"
  const [aberto, setAberto] = useState(null); // índice do dia expandido
  const [lendo, setLendo] = useState(false);
  const [erro, setErro] = useState("");
  const [gerando, setGerando] = useState(false);
  const [resGeracao, setResGeracao] = useState(null);
  const [arquivosPasta, setArquivosPasta] = useState([]);

  const carregarPasta = useCallback(() => {
    bpaLocal.lotes().then(setArquivosPasta).catch(() => setArquivosPasta([]));
  }, []);
  useEffect(() => { carregarPasta(); }, [carregarPasta]);

  async function escolherArquivo(e) {
    const f = e.target.files?.[0];
    if (!f) return;
    setErro("");
    setLido(null);
    setResGeracao(null);
    setLendo(true);
    try {
      const b64 = await lerBase64(f);
      const r = await bpaLocal.nutricaoLer(b64, "");
      if (!r.ok) throw new Error(r.erro);
      setArquivo({ nome: f.name, b64 });
      setAbas(r.abas);
      await lerAba(b64, r.abas[0]);
    } catch (e2) {
      setErro(e2.message);
      setArquivo(null);
      setAbas([]);
    } finally {
      setLendo(false);
      e.target.value = "";
    }
  }

  async function lerAba(b64, nomeAba) {
    setAba(nomeAba);
    setErro("");
    setResGeracao(null);
    setAberto(null);
    setLendo(true);
    try {
      const r = await bpaLocal.nutricaoLer(b64, nomeAba);
      if (!r.ok) throw new Error(r.erro);
      setLido(r);
      setDias(r.dias.map((d) => ({ ...d })));
    } catch (e) {
      setErro(e.message);
      setLido(null);
    } finally {
      setLendo(false);
    }
  }

  function alternarNutri(i, cns) {
    setResGeracao(null);
    setDias((ds) => ds.map((d, j) => {
      if (j !== i) return d;
      const tem = d.nutricionistas.includes(cns);
      return { ...d, nutricionistas: tem ? d.nutricionistas.filter((c) => c !== cns) : [...d.nutricionistas, cns] };
    }));
  }

  function mudarData(i, valor) {
    setResGeracao(null);
    setDias((ds) => ds.map((d, j) => (j === i ? { ...d, data: mascaraData(valor) } : d)));
  }

  const nutris = lido?.nutricionistas || [];
  const curto = (cns) => nutris.find((n) => n.cns === cns)?.curto || cns;
  const mesAba = lido ? `${lido.competencia.slice(4)}/${lido.competencia.slice(0, 4)}` : "";

  // Dias prontos pra gerar, pendências e o total de cada nutricionista
  const resumo = useMemo(() => {
    const porNutri = Object.fromEntries(nutris.map((n) => [n.cns, 0]));
    const pendencias = [];
    dias.forEach((d, i) => {
      const docs = d.pacientes.filter((p) => p.doc).map((p) => p.doc);
      if (!docs.length) return;
      const dataOk = d.data.length === 10 && d.data.slice(3) === mesAba;
      if (!dataOk) pendencias.push({ i, texto: `${fmtNum(docs.length)} paciente(s) sem dia — digite a data` });
      else if (!d.nutricionistas.length) pendencias.push({ i, texto: `${d.data.slice(0, 5)} sem nutricionista — escolha de quem é` });
      if (d.nutricionistas.length) {
        Object.entries(dividir(docs, d.nutricionistas)).forEach(([c, q]) => { porNutri[c] = (porNutri[c] || 0) + q; });
      }
    });
    return { porNutri, pendencias };
  }, [dias, nutris, mesAba]);

  const naoAchados = dias.flatMap((d) => d.pacientes.filter((p) => p.situacao === "nao_achado").map((p) => ({ ...p, data: d.data })));
  const nomeArquivo = lido ? `BPA_NUTRICAO_${lido.competencia}.txt` : "";
  const jaGerado = arquivosPasta.find((a) => a.nome === nomeArquivo);
  const totalGerar = Object.values(resumo.porNutri).reduce((s, q) => s + q, 0);

  async function gerar() {
    if (jaGerado && !window.confirm(
      `O arquivo da nutrição de ${mesAba} já foi gerado (${jaGerado.modificado_em}).\n\n` +
      "Se ele já foi importado no BPA Magnético, importar de novo DUPLICA a produção.\n\nGerar de novo mesmo assim?"
    )) return;
    setGerando(true);
    setResGeracao(null);
    try {
      const corpo = dias.map((d) => ({
        data: d.data, nutricionistas: d.nutricionistas, docs: d.pacientes.filter((p) => p.doc).map((p) => p.doc),
      })).filter((d) => d.docs.length);
      setResGeracao(await bpaLocal.nutricaoGerar(lido.competencia, corpo));
      carregarPasta();
    } catch (e) {
      setResGeracao({ ok: false, erro: e.message });
    } finally {
      setGerando(false);
    }
  }

  const c = lido?.contagem;

  return (
    <div className="bp-grade bp-grade-lado">
      <div className="bp-coluna">
        <section className="bp-cartao">
          <h2>1. Planilha do mês</h2>
          <p className="bp-desc">
            Escolha a planilha da nutrição (.xlsx) e o mês. Cada dia vai para a nutricionista escrita nele;
            dia com mais de uma (ou "TODAS NUT") é dividido igualmente entre elas.
          </p>
          <label className="bp-btn contorno largo" style={{ textAlign: "center", cursor: "pointer" }}>
            {arquivo ? "Trocar planilha" : "Escolher planilha…"}
            <input type="file" accept=".xlsx" onChange={escolherArquivo} style={{ display: "none" }} />
          </label>
          {arquivo && <p className="bp-desc" style={{ marginTop: 8 }}>{arquivo.nome}</p>}

          {abas.length > 0 && (
            <>
              <label className="bp-rot" htmlFor="nut-aba">Mês (aba da planilha)</label>
              <select id="nut-aba" className="bp-campo" value={aba} disabled={lendo}
                      onChange={(e) => lerAba(arquivo.b64, e.target.value)}>
                {abas.map((a) => <option key={a} value={a}>{a}</option>)}
              </select>
            </>
          )}
          {lendo && <p className="bp-vazio">Lendo a planilha e procurando os pacientes…</p>}
          {erro && <div className="bp-aviso erro">{erro}</div>}

          {lido && !lendo && (
            <div className="bp-kpis estreito">
              <div className="bp-kpi"><strong>{fmtNum(c.ok + c.corrigido + c.sem_doc + c.nao_achado)}</strong><span>Pacientes</span></div>
              <div className="bp-kpi"><strong className="ok">{fmtNum(c.ok)}</strong><span>CPF ok</span></div>
              <div className="bp-kpi"><strong className="alerta">{fmtNum(c.corrigido)}</strong><span>Corrigidos</span></div>
              <div className="bp-kpi"><strong>{fmtNum(c.sem_doc)}</strong><span>Sem doc.</span></div>
              <div className="bp-kpi"><strong className={c.nao_achado ? "erro" : ""}>{fmtNum(c.nao_achado)}</strong><span>Não achados</span></div>
            </div>
          )}
        </section>

        {lido && !lendo && (
          <section className="bp-cartao">
            <h2>2. Arquivo para o BPA Magnético</h2>
            <p className="bp-desc">Um arquivo só, com as nutricionistas e todos os dias de {mesAba}.</p>
            <table className="bp-tabela">
              <thead><tr><th>Nutricionista</th><th className="num">Atendimentos</th></tr></thead>
              <tbody>
                {nutris.map((n) => (
                  <tr key={n.cns}><td>{n.nome}</td><td className="num">{fmtNum(resumo.porNutri[n.cns] || 0)}</td></tr>
                ))}
                <tr><td><b>Total</b></td><td className="num"><b>{fmtNum(totalGerar)}</b></td></tr>
              </tbody>
            </table>

            {resumo.pendencias.length > 0 && (
              <div className="bp-aviso alerta">
                Resolva antes de gerar:
                {resumo.pendencias.map((p) => (
                  <small key={p.i} style={{ cursor: "pointer" }} onClick={() => setAberto(p.i)}>• {p.texto}</small>
                ))}
              </div>
            )}
            {naoAchados.length > 0 && (
              <div className="bp-aviso erro">
                {fmtNum(naoAchados.length)} paciente(s) não achados no BPA Magnético ficam de fora.
                Migre esses pacientes (aba Migração) e escolha a planilha de novo.
              </div>
            )}
            {jaGerado && !resGeracao && (
              <div className="bp-aviso alerta">
                {nomeArquivo} já gerado em {jaGerado.modificado_em}. Se já importou, importar de novo duplica a produção.
              </div>
            )}
            <button className="bp-btn verde largo" onClick={gerar}
                    disabled={gerando || resumo.pendencias.length > 0 || !totalGerar}>
              {gerando ? "Gerando…" : `Gerar BPA da nutrição (${fmtNum(totalGerar)})`}
            </button>
            {resGeracao && (resGeracao.ok ? (
              <div className="bp-aviso ok">
                <b>{resGeracao.arquivo}</b> — {fmtNum(resGeracao.registros)} registros · {resGeracao.folhas} folha(s)
                · competência {resGeracao.competencia}
                <small>Salvo em {resGeracao.caminho} — importe no BPA Magnético</small>
                {resGeracao.nutricionistas.filter((n) => n.ja_importados > 0).map((n) => (
                  <small key={n.nome} style={{ color: "var(--bp-alerta)", opacity: 1 }}>
                    {n.nome} já tem {fmtNum(n.ja_importados)} atendimento(s) no BPA Magnético nesses dias — importar duplica.
                  </small>
                ))}
                {resGeracao.nao_encontrados?.length > 0 && (
                  <small style={{ color: "var(--bp-alerta)", opacity: 1 }}>
                    Não encontrados no Firebird: {resGeracao.nao_encontrados.map(fmtDoc).join(", ")}
                  </small>
                )}
              </div>
            ) : <div className="bp-aviso erro">{resGeracao.erro}</div>)}
          </section>
        )}
      </div>

      <section className="bp-cartao">
        <h2>3. Dias de {mesAba || "…"}</h2>
        <p className="bp-desc">
          Clique na nutricionista para trocar ou juntar outra no dia. Clique no dia para ver os pacientes.
        </p>
        {!lido ? (
          <p className="bp-vazio">Escolha a planilha para ver os dias.</p>
        ) : (
          <>
            {lido.avisos.length > 0 && (
              <div className="bp-aviso info">
                {lido.avisos.map((a) => <small key={a}>{a}</small>)}
              </div>
            )}
            <table className="bp-tabela">
              <thead><tr><th>Dia</th><th>Nutricionista</th><th className="num">Pacientes</th><th className="num">Atenção</th></tr></thead>
              <tbody>
                {dias.map((d, i) => {
                  const atencao = d.pacientes.filter((p) => p.situacao !== "ok").length;
                  const semNutri = !d.nutricionistas.length;
                  return [
                    <tr key={`d${i}`}>
                      <td>
                        {lido.dias[i].data ? (
                          <button className="bp-btn-sec" style={{ padding: "2px 8px" }} onClick={() => setAberto(aberto === i ? null : i)}>
                            {aberto === i ? "▾" : "▸"} {d.data.slice(0, 5)}
                          </button>
                        ) : (
                          <input className="bp-campo curto" style={{ width: 120 }} value={d.data} placeholder={`DD/${mesAba}`}
                                 inputMode="numeric" onChange={(e) => mudarData(i, e.target.value)} onFocus={() => setAberto(i)} />
                        )}
                      </td>
                      <td>
                        <div className="bp-linha" style={{ gap: 4, flexWrap: "wrap" }}>
                          {nutris.map((n) => (
                            <button key={n.cns} onClick={() => alternarNutri(i, n.cns)}
                                    className={`bp-tag ${d.nutricionistas.includes(n.cns) ? "ok" : "neutro"}`}
                                    style={{ border: 0, cursor: "pointer", opacity: d.nutricionistas.includes(n.cns) ? 1 : 0.5 }}>
                              {n.curto}
                            </button>
                          ))}
                          {semNutri && <span className="bp-tag alerta">escolha</span>}
                        </div>
                      </td>
                      <td className="num">{fmtNum(d.pacientes.length)}</td>
                      <td className="num">{atencao ? <span className="bp-tag alerta">{atencao}</span> : "—"}</td>
                    </tr>,
                    aberto === i && (
                      <tr key={`p${i}`}>
                        <td colSpan={4} style={{ background: "var(--bp-fundo-2, transparent)" }}>
                          <table className="bp-tabela">
                            <thead><tr><th>Paciente (planilha)</th><th>CPF na planilha</th><th>Vai no BPA</th><th></th></tr></thead>
                            <tbody>
                              {d.pacientes.map((p) => (
                                <tr key={p.linha}>
                                  <td>{p.nome}<br /><small style={{ color: "var(--bp-texto-3)" }}>linha {p.linha} · nasc. {p.nascimento || "—"}</small></td>
                                  <td>{p.cpf_planilha || "—"}</td>
                                  <td>
                                    {p.doc ? fmtDoc(p.doc) : "—"}
                                    {p.motivo && <><br /><small style={{ color: "var(--bp-texto-3)" }}>pelo {p.motivo}</small></>}
                                  </td>
                                  <td className="num">
                                    <span className={`bp-tag ${SITUACAO[p.situacao].tag}`}>{SITUACAO[p.situacao].texto}</span>
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                          {d.nutricionistas.length > 1 && (
                            <p className="bp-desc" style={{ marginTop: 6 }}>
                              Dividido entre {d.nutricionistas.map(curto).join(", ")}:{" "}
                              {Object.entries(dividir(d.pacientes.filter((p) => p.doc), d.nutricionistas))
                                .map(([c2, q]) => `${curto(c2)} ${q}`).join(" · ")}
                            </p>
                          )}
                        </td>
                      </tr>
                    ),
                  ];
                })}
              </tbody>
            </table>
          </>
        )}
      </section>
    </div>
  );
}


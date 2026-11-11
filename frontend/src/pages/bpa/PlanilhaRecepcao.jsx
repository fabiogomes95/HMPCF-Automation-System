import { useState } from "react";
import { conferirPlanilhaRecepcao, mensagemErro } from "../../services/api";
import { fmtNum } from "../../services/bpaLocal";

// Aba BPA › Migração › "Planilha da recepção": quando o sistema fica fora e a
// recepção anota só na planilha, aqui se escolhe o .xlsx das meninas, o
// servidor confere com o sistema e mostra o que faltou; "Lançar" cadastra os
// pacientes novos e cria as entradas com data, hora e nº da planilha.
// Regras e proteção contra duplicata: backend/app/services/conferencia_planilha_service.py

const SITUACAO = {
  entrada: { tag: "ok", texto: "lançar entrada" },
  novo: { tag: "ok", texto: "cadastrar + entrada" },
  pendente: { tag: "alerta", texto: "pendente" },
  ignorada: { tag: "neutro", texto: "não entra" },
};

function dataBR(iso) {
  if (!iso) return "—";
  const [a, m, d] = iso.split("-");
  return `${d}/${m}/${a}`;
}

export default function PlanilhaRecepcao() {
  const [arquivo, setArquivo] = useState(null);
  const [abas, setAbas] = useState([]);          // escolhidas
  const [disponiveis, setDisponiveis] = useState([]);
  const [r, setR] = useState(null);              // resposta da conferência
  const [lancado, setLancado] = useState(null);  // resposta do lançamento
  const [ocupado, setOcupado] = useState("");    // "" | "conferindo" | "lancando"
  const [erro, setErro] = useState("");
  const [filtro, setFiltro] = useState("todos");

  function escolherArquivo(e) {
    setArquivo(e.target.files?.[0] || null);
    setAbas([]); setDisponiveis([]); setR(null); setLancado(null); setErro("");
  }

  function alternarAba(aba) {
    setAbas((atual) => (atual.includes(aba) ? atual.filter((a) => a !== aba) : [...atual, aba]));
    setR(null); setLancado(null);
  }

  async function chamar(aplicar) {
    setOcupado(aplicar ? "lancando" : "conferindo");
    setErro("");
    try {
      const { data } = await conferirPlanilhaRecepcao(arquivo, { abas, aplicar });
      setDisponiveis(data.abas_disponiveis);
      setAbas(data.abas_lidas);
      if (aplicar) setLancado(data);
      else { setR(data); setLancado(null); }
    } catch (e) {
      setErro(mensagemErro(e, "Não consegui conferir a planilha."));
    } finally {
      setOcupado("");
    }
  }

  const base = lancado || r;
  const aLancar = r ? r.resumo.entrada + r.resumo.novo : 0;
  const itens = (base?.itens || []).filter((i) => filtro === "todos" || i.situacao === filtro);

  return (
    <section className="bp-cartao" style={{ marginTop: 16 }}>
      <h2>Planilha da recepção → sistema</h2>
      <p className="bp-desc">
        Para quando o sistema ficou fora e a recepção anotou só na planilha. Escolha o .xlsx das meninas: o
        servidor compara com o sistema e mostra quem está na planilha e não foi lançado. Nada é gravado até
        clicar em <b>Lançar</b>. Paciente que já existe ganha só a entrada; paciente novo é cadastrado com os
        dados da planilha. Linha só com o nome não entra; paciente novo sem nascimento ou sexo fica pendente
        (cadastrar à mão). Rodar de novo não duplica.
      </p>

      <div className="bp-linha" style={{ alignItems: "flex-end", flexWrap: "wrap" }}>
        <div style={{ flex: 1, minWidth: 220 }}>
          <label className="bp-rot" htmlFor="plan-recep">Planilha (.xlsx)</label>
          <input id="plan-recep" className="bp-campo" type="file" accept=".xlsx"
                 onChange={escolherArquivo} disabled={!!ocupado} />
        </div>
        <button className="bp-btn contorno" onClick={() => chamar(false)} disabled={!arquivo || !!ocupado}>
          {ocupado === "conferindo" ? "Conferindo…" : "Conferir"}
        </button>
        <button className="bp-btn verde" onClick={() => chamar(true)}
                disabled={!r || !aLancar || !!ocupado || !!lancado}>
          {ocupado === "lancando" ? "Lançando…" : r ? (aLancar ? `Lançar (${fmtNum(aLancar)})` : "Nada a lançar") : "Lançar"}
        </button>
      </div>

      {disponiveis.length > 0 && (
        <div style={{ marginTop: 10, display: "flex", gap: 12, flexWrap: "wrap", fontSize: 13 }}>
          <span className="bp-rot" style={{ margin: 0 }}>Meses conferidos:</span>
          {disponiveis.map((a) => (
            <label key={a} style={{ display: "flex", gap: 4, alignItems: "center" }}>
              <input type="checkbox" checked={abas.includes(a)} disabled={!!ocupado} onChange={() => alternarAba(a)} />
              {a}
            </label>
          ))}
          {r === null && !ocupado && arquivo && <span style={{ color: "var(--bp-texto-2)" }}>mudou os meses? clique em Conferir de novo</span>}
        </div>
      )}

      {ocupado && <p className="bp-vazio">Lendo a planilha e comparando com o sistema… leva uns 20–60 segundos.</p>}
      {erro && <div className="bp-aviso erro">{erro}</div>}

      {r && !lancado && (
        <>
          <p className="bp-desc" style={{ marginTop: 12 }}>
            {fmtNum(r.linhas_lidas)} linhas lidas ({r.abas_lidas.join(", ")}
            {r.periodo ? `, ${dataBR(r.periodo[0])} a ${dataBR(r.periodo[1])}` : ""}).
          </p>
          <div className="bp-kpis">
            <div className="bp-kpi"><strong>{fmtNum(r.resumo.faltando)}</strong><span>faltando no sistema</span></div>
            <div className="bp-kpi"><strong>{fmtNum(r.resumo.entrada)}</strong><span>só a entrada</span></div>
            <div className="bp-kpi"><strong>{fmtNum(r.resumo.novo)}</strong><span>pacientes novos</span></div>
            <div className="bp-kpi">
              <strong className={r.resumo.pendente ? "alerta" : ""}>{fmtNum(r.resumo.pendente + r.resumo.ignorada)}</strong>
              <span>pendentes / não entram</span>
            </div>
          </div>
          {r.resumo.faltando === 0 && <div className="bp-aviso ok">Tudo da planilha já está no sistema.</div>}
        </>
      )}

      {lancado && (
        <div className={`bp-aviso ${lancado.resumo.erros ? "alerta" : "ok"}`} style={{ marginTop: 12 }}>
          <b>Lançamento concluído:</b> {fmtNum(lancado.resumo.pacientes_criados)} paciente(s) cadastrado(s) ·{" "}
          {fmtNum(lancado.resumo.entradas_lancadas)} entrada(s) lançada(s) · {fmtNum(lancado.resumo.ja_existiam)} já
          existiam · {fmtNum(lancado.resumo.pendente)} pendente(s) · {fmtNum(lancado.resumo.erros)} erro(s)
        </div>
      )}

      {base && base.itens.length > 0 && (
        <>
          <div className="bp-linha" style={{ marginTop: 12, gap: 8, flexWrap: "wrap" }}>
            {["todos", "entrada", "novo", "pendente", "ignorada"].map((f) => (
              <button key={f} className={`bp-btn ${filtro === f ? "" : "contorno"}`} onClick={() => setFiltro(f)}>
                {f === "todos" ? "Todos" : SITUACAO[f].texto}
              </button>
            ))}
          </div>
          <div style={{ overflowX: "auto", maxHeight: 420, marginTop: 8 }}>
            <table className="bp-tabela">
              <thead>
                <tr>
                  <th>Data</th><th>Hora</th><th>Nº</th><th>Nome</th><th>CPF / SUS</th><th>Situação</th>
                  <th>{lancado ? "Resultado" : "Observação"}</th>
                </tr>
              </thead>
              <tbody>
                {itens.map((i) => (
                  <tr key={`${i.aba}-${i.linha}`} title={`${i.aba}, linha ${i.linha}`}>
                    <td>{dataBR(i.data)}</td>
                    <td>{i.hora || "—"}</td>
                    <td>{i.registro ?? "—"}</td>
                    <td>{i.nome}</td>
                    <td style={{ fontSize: 12 }}>{i.cpf || i.cns || "—"}</td>
                    <td><span className={`bp-tag ${SITUACAO[i.situacao]?.tag || "neutro"}`}>{SITUACAO[i.situacao]?.texto || i.situacao}</span></td>
                    <td style={{ fontSize: 12 }}>{(lancado && i.resultado) || i.motivo || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </section>
  );
}

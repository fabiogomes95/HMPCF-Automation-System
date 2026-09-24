import { useEffect, useRef, useState } from "react";
import { buscarEntradas, mensagemErro, resumoPlanilhas } from "../services/api";
import "./Entradas.css";

// Aba Entradas (faturamento e TI): em que dias o paciente deu entrada e quantas
// vezes — no sistema e/ou nas planilhas manuais (ago/2021 em diante) — pra achar o
// boletim impresso, que é guardado por data. Regras em backend entradas_service.py.

const FONTES = [
  { valor: "ambos", rotulo: "Sistema + planilhas" },
  { valor: "sistema", rotulo: "Só o sistema" },
  { valor: "planilhas", rotulo: "Só as planilhas" },
];
const DIAS_SEMANA = ["dom", "seg", "ter", "qua", "qui", "sex", "sáb"];

const fmt = (n) => (n ?? 0).toLocaleString("pt-BR");
function fmtData(iso) {
  if (!iso) return "—";
  const [a, m, d] = iso.split("-");
  return `${d}/${m}/${a}`;
}
function diaSemana(iso) {
  const [a, m, d] = iso.split("-").map(Number);
  return DIAS_SEMANA[new Date(a, m - 1, d).getDay()];
}
function fmtCpf(c) {
  return c && c.length === 11 ? `${c.slice(0, 3)}.${c.slice(3, 6)}.${c.slice(6, 9)}-${c.slice(9)}` : c || "—";
}

function Pessoa({ p }) {
  const porAno = {};
  p.entradas.forEach((e) => { (porAno[e.data.slice(0, 4)] ||= []).push(e); });
  const anos = Object.keys(porAno).sort((a, b) => b - a);
  return (
    <article className="en-pessoa">
      <header className="en-pessoa-topo">
        <div>
          <h2>{p.nome}</h2>
          {p.outros_nomes.length > 0 && (
            <div className="en-outros">também escrito: {p.outros_nomes.join(" · ")}</div>
          )}
          <div className="en-docs">
            <span>CPF <b>{fmtCpf(p.cpf)}</b></span>
            <span>Nascimento <b>{fmtData(p.nascimento)}</b></span>
            {p.cns && <span>SUS <b>{p.cns}</b></span>}
          </div>
        </div>
        <div className="en-total">
          <strong>{fmt(p.total)}</strong>
          <span>{p.total === 1 ? "entrada" : "entradas"}</span>
          <small>{p.total > 1 ? `de ${fmtData(p.primeira)} a ${fmtData(p.ultima)}` : fmtData(p.ultima)}</small>
        </div>
      </header>

      {anos.map((ano) => (
        <section key={ano} className="en-ano">
          <h3>{ano} <span>{fmt(porAno[ano].length)}</span></h3>
          <ul>
            {porAno[ano].map((e, i) => (
              <li key={`${e.data}-${i}`} title={e.origens.join("\n")}>
                <span className="en-data">{fmtData(e.data)} <small>{diaSemana(e.data)}</small></span>
                <span className="en-hora">{e.hora || "—"}</span>
                <span className="en-fontes">
                  {e.fontes.map((f) => (
                    <span key={f} className={`en-tag en-tag-${f}`}>{f === "sistema" ? "Sistema" : "Planilha"}</span>
                  ))}
                  {e.pelo_nome && <span className="en-tag en-tag-nome" title="Linha da planilha sem CPF — achada pelo nome. Confira.">pelo nome</span>}
                </span>
                <span className="en-origem">{e.origens.filter((o) => o !== "Sistema").join(" · ")}</span>
              </li>
            ))}
          </ul>
        </section>
      ))}
    </article>
  );
}

export default function Entradas() {
  const [q, setQ] = useState("");
  const [fonte, setFonte] = useState("ambos");
  const [resultado, setResultado] = useState(null);
  const [buscando, setBuscando] = useState(false);
  const [erro, setErro] = useState("");
  const [planilhas, setPlanilhas] = useState(null);
  const ultima = useRef({ q: "", fonte: "" });

  useEffect(() => {
    resumoPlanilhas().then((r) => setPlanilhas(r.data)).catch(() => setPlanilhas(null));
  }, []);

  async function buscar(termo = q, fonteBusca = fonte) {
    const t = termo.trim();
    if (!t) return;
    ultima.current = { q: t, fonte: fonteBusca };
    setBuscando(true);
    setErro("");
    try {
      const r = await buscarEntradas(t, fonteBusca);
      setResultado(r.data);
    } catch (e) {
      setResultado(null);
      setErro(mensagemErro(e, "Não foi possível buscar."));
    } finally {
      setBuscando(false);
    }
  }

  function trocarFonte(f) {
    setFonte(f);
    if (ultima.current.q) buscar(ultima.current.q, f); // refaz a mesma busca na fonte nova
  }

  return (
    <div className="entradas">
      <div className="en-topo no-print">
        <h1>Entradas do paciente</h1>
        <p>Em que dias o paciente deu entrada e quantas vezes — pra achar o boletim impresso (guardado por data).</p>
      </div>

      <div className="en-busca no-print">
        <form onSubmit={(e) => { e.preventDefault(); buscar(); }}>
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="CPF, SUS ou nome do paciente"
                 autoFocus autoComplete="off" />
          <button type="submit" disabled={buscando || !q.trim()}>{buscando ? "Buscando…" : "Buscar"}</button>
        </form>
        <div className="en-fontes-sel" role="radiogroup" aria-label="Onde pesquisar">
          {FONTES.map((f) => (
            <button key={f.valor} type="button" role="radio" aria-checked={fonte === f.valor}
                    className={fonte === f.valor ? "ativo" : ""} onClick={() => trocarFonte(f.valor)}>
              {f.rotulo}
            </button>
          ))}
        </div>
        {planilhas?.total > 0 && (
          <p className="en-cobertura">
            Planilhas: {fmt(planilhas.total)} entradas de {fmtData(planilhas.inicio)} a {fmtData(planilhas.fim)}
            {planilhas.importado_em && ` · importadas em ${new Date(planilhas.importado_em).toLocaleDateString("pt-BR")}`}
            {" "}· meses que não estão nas planilhas não aparecem.
          </p>
        )}
      </div>

      {erro && <div className="en-erro">{erro}</div>}

      {resultado && !buscando && (
        resultado.pessoas.length === 0 ? (
          <p className="en-vazio">Nenhuma entrada encontrada {fonte === "ambos" ? "no sistema nem nas planilhas" : fonte === "sistema" ? "no sistema" : "nas planilhas"}.</p>
        ) : (
          <>
            <div className="en-barra no-print">
              <span>
                {fmt(resultado.pessoas.length)} {resultado.pessoas.length === 1 ? "paciente" : "pacientes"} ·{" "}
                {fmt(resultado.pessoas.reduce((s, p) => s + p.total, 0))} entradas
              </span>
              <button type="button" onClick={() => window.print()}>Imprimir</button>
            </div>
            <div className="en-so-impressao">
              <b>HMPCF — Entradas do paciente</b>
              <span>
                Busca: {ultima.current.q} · {FONTES.find((f) => f.valor === resultado.fonte)?.rotulo} · impresso em{" "}
                {new Date().toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" })}
              </span>
            </div>
            {resultado.limitado && (
              <div className="en-aviso">
                Mostrando {fmt(resultado.pessoas.length)} de {fmt(resultado.total_pessoas)} pessoas — digite o nome
                mais completo ou busque pelo CPF.
              </div>
            )}
            {resultado.pessoas.map((p, i) => <Pessoa key={`${p.cpf || p.nome}-${i}`} p={p} />)}
          </>
        )
      )}
    </div>
  );
}

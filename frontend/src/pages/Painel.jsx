import { useCallback, useEffect, useState } from "react";
import { buscarPainel, mensagemErro } from "../services/api";
import "./Painel.css";

// Painel gerencial (só TI) -- substitui o antigo dashboard Streamlit. Só números
// agregados; nenhum dado pessoal vem do backend (ver painel_service.py).

const PERIODOS = [
  { valor: "hoje", rotulo: "Hoje" },
  { valor: "7d", rotulo: "7 dias" },
  { valor: "30d", rotulo: "30 dias" },
  { valor: "mes", rotulo: "Este mês" },
  { valor: "12m", rotulo: "12 meses" },
];
const MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];
const DIAS_SEMANA = ["dom", "seg", "ter", "qua", "qui", "sex", "sáb"];
const ATUALIZA_MS = 60000;

const fmt = (n) => (n ?? 0).toLocaleString("pt-BR");
const pct = (parte, total) => (total ? Math.round((parte / total) * 1000) / 10 : 0);

function rotuloSerie(chave, porMes, mesAtual) {
  if (porMes) {
    const [ano, mes] = chave.split("-");
    const andamento = chave === mesAtual ? " · mês em andamento" : "";
    return { curto: MESES[+mes - 1], longo: `${MESES[+mes - 1]}/${ano}${andamento}` };
  }
  const [ano, mes, dia] = chave.split("-").map(Number);
  const d = new Date(ano, mes - 1, dia);
  return { curto: `${dia}/${mes}`, longo: `${DIAS_SEMANA[d.getDay()]}, ${dia}/${mes}/${ano}` };
}

// ── Peças visuais ────────────────────────────────────────────────────────────

function Variacao({ atual, anterior, sufixo }) {
  if (!anterior) return <span className="pn-var pn-var-neutro">sem base de comparação</span>;
  const d = ((atual - anterior) / anterior) * 100;
  const cls = Math.abs(d) < 0.5 ? "pn-var-neutro" : d > 0 ? "pn-var-sobe" : "pn-var-desce";
  const seta = Math.abs(d) < 0.5 ? "=" : d > 0 ? "▲" : "▼";
  return (
    <span className={`pn-var ${cls}`}>
      {seta} {Math.abs(d).toLocaleString("pt-BR", { maximumFractionDigits: 1 })}% {sufixo}
    </span>
  );
}

function Destaque({ rotulo, valor, detalhe, children }) {
  return (
    <div className="pn-destaque">
      <div className="pn-destaque-rotulo">{rotulo}</div>
      <div className="pn-destaque-valor">{valor}</div>
      {children}
      {detalhe && <div className="pn-destaque-detalhe">{detalhe}</div>}
    </div>
  );
}

function Cartao({ titulo, sub, children, className = "" }) {
  return (
    <section className={`pn-cartao ${className}`}>
      <header className="pn-cartao-cab">
        <h2>{titulo}</h2>
        {sub && <p>{sub}</p>}
      </header>
      {children}
    </section>
  );
}

// Colunas verticais -- uma série, valor só no pico (e na média), resto no tooltip.
function Colunas({ itens, media, formatoValor = fmt, faixaNoturna = false }) {
  const max = Math.max(1, ...itens.map((i) => i.valor));
  const iPico = itens.reduce((m, it, i) => (it.valor > itens[m].valor ? i : m), 0);
  const passoRotulo = Math.ceil(itens.length / 12);
  return (
    <div className="pn-colunas" role="img" aria-label="Gráfico de colunas">
      {media > 0 && (
        <div className="pn-media" style={{ bottom: `${(media / max) * 100}%` }}>
          <span>média {formatoValor(media)}</span>
        </div>
      )}
      {itens.map((it, i) => (
        <div
          key={it.chave}
          className={`pn-col${faixaNoturna && it.noturno ? " pn-col-noite" : ""}`}
          tabIndex={0}
        >
          <div className="pn-col-area">
            {i === iPico && it.valor > 0 && <span className="pn-col-pico">{formatoValor(it.valor)}</span>}
            <div className="pn-col-barra" style={{ height: `${(it.valor / max) * 100}%` }} />
          </div>
          <div className="pn-col-rotulo">{i % passoRotulo === 0 ? it.curto : ""}</div>
          <div className="pn-tip">
            <strong>{formatoValor(it.valor)}</strong>
            <span>{it.longo}</span>
          </div>
        </div>
      ))}
    </div>
  );
}

// Barras horizontais -- rótulo, barra, número e % do total.
function Barras({ itens, total, destacar }) {
  const max = Math.max(1, ...itens.map((i) => i.total));
  return (
    <ul className="pn-barras">
      {itens.map((it) => (
        <li key={it.rotulo} className={destacar?.(it) ? "pn-barras-fraco" : ""}>
          <span className="pn-barras-rotulo" title={it.rotulo}>{it.rotulo}</span>
          <span className="pn-barras-trilho">
            <span className="pn-barras-barra" style={{ width: `${(it.total / max) * 100}%` }} />
          </span>
          <span className="pn-barras-valor">
            {fmt(it.total)} <em>{pct(it.total, total).toLocaleString("pt-BR")}%</em>
          </span>
        </li>
      ))}
    </ul>
  );
}

// Divisão em duas partes (sexo, plantão) -- barra única com os dois lados rotulados.
function Divisao({ itens }) {
  const total = itens.reduce((s, i) => s + i.total, 0);
  const [a, b] = itens;
  if (!a || !total) return <p className="pn-vazio">Sem dados.</p>;
  return (
    <div className="pn-divisao">
      <div className="pn-divisao-barra">
        <span className="pn-divisao-a" style={{ width: `${pct(a.total, total)}%` }} />
        {b && <span className="pn-divisao-b" style={{ width: `${pct(b.total, total)}%` }} />}
      </div>
      <div className="pn-divisao-legenda">
        {itens.map((it, i) => (
          <div key={it.rotulo}>
            <i className={i === 0 ? "pn-sw-a" : i === 1 ? "pn-sw-b" : "pn-sw-c"} />
            <span>{it.rotulo}</span>
            <strong>{pct(it.total, total).toLocaleString("pt-BR")}%</strong>
            <em>{fmt(it.total)}</em>
          </div>
        ))}
      </div>
    </div>
  );
}

function Medidor({ rotulo, parte, total, dica }) {
  const p = pct(parte, total);
  return (
    <div className="pn-medidor" title={dica}>
      <div className="pn-medidor-topo">
        <span>{rotulo}</span>
        <strong>{p.toLocaleString("pt-BR")}%</strong>
      </div>
      <div className="pn-medidor-trilho">
        <span style={{ width: `${Math.min(100, p)}%` }} />
      </div>
      <em>{fmt(parte)} de {fmt(total)} atendimentos</em>
    </div>
  );
}

// ── Página ───────────────────────────────────────────────────────────────────

// ── Saúde dos backups (topo) ────────────────────────────────────────────────
function quandoFoi(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  const hoje = new Date();
  const ontem = new Date(hoje); ontem.setDate(hoje.getDate() - 1);
  const hora = d.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
  if (d.toDateString() === hoje.toDateString()) return `hoje ${hora}`;
  if (d.toDateString() === ontem.toDateString()) return `ontem ${hora}`;
  return `${d.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" })} ${hora}`;
}

const BACKUP_TEXTO = {
  ok: "em dia",
  atrasado: "ATRASADO",
  incompleto: "sem cópia na nuvem",
  sem_backup: "nenhum backup encontrado",
};

function SaudeBackup({ backup, lotes }) {
  if (!backup) return null;
  const ok = backup.situacao === "ok";
  const ex = backup.execucao;
  let detalhe = `último ${quandoFoi(backup.ultimo)}`;
  if (backup.situacao === "atrasado") detalhe += ` · há ${Math.round(backup.horas)} h — o backup das 23:00 não rodou`;
  else if (ok && ex?.nuvem) detalhe += " · copiado no Google Drive";
  if (!ok && ex?.problema) detalhe += ` · ${ex.problema}`;
  return (
    <div className={`pn-saude ${ok ? "ok" : "ruim"}`} role="status">
      <span className="pn-saude-item">
        <span className="pn-saude-ponto" aria-hidden="true" />
        <b>Backup do banco: {BACKUP_TEXTO[backup.situacao] || backup.situacao}</b>
        <span className="pn-saude-det">{detalhe}</span>
      </span>
      {lotes?.length > 0 && (
        <span className="pn-saude-item pn-saude-lotes" title="Último lote de digitação que cada notebook do BPA mandou pro servidor">
          Lotes do BPA:{" "}
          {lotes.map((l, i) => (
            <span key={l.notebook}>{i > 0 && " · "}{l.notebook} {quandoFoi(l.ultimo)}</span>
          ))}
        </span>
      )}
    </div>
  );
}

export default function Painel() {
  const [periodo, setPeriodo] = useState(() => sessionStorage.getItem("hmpcf_painel_periodo") || "30d");
  const [dados, setDados] = useState(null);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState("");

  const carregar = useCallback(async () => {
    setCarregando(true);
    try {
      const res = await buscarPainel(periodo);
      if (!res.data?.destaques) throw new Error("resposta inesperada");
      setDados(res.data);
      setErro("");
    } catch (err) {
      setErro(mensagemErro(err, "Não foi possível carregar o painel. Se acabou de ser atualizado, o servidor pode precisar ser reiniciado."));
    } finally {
      setCarregando(false);
    }
  }, [periodo]);

  useEffect(() => {
    sessionStorage.setItem("hmpcf_painel_periodo", periodo);
    carregar();
    const t = setInterval(carregar, ATUALIZA_MS);
    return () => clearInterval(t);
  }, [periodo, carregar]);

  const d = dados?.destaques;
  const r = dados?.resumo;
  const porMes = dados?.serie_por === "mes";
  const nomePeriodo = PERIODOS.find((p) => p.valor === periodo)?.rotulo.toLowerCase();
  const soHoje = dados?.periodo === "hoje";

  return (
    <div className="painel">
      <div className="pn-topo">
        <div>
          <h1>Painel gerencial</h1>
          <p className="pn-atualizado">
            {dados
              ? `Atualizado às ${new Date(dados.gerado_em).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })} · atualiza sozinho a cada minuto`
              : "Carregando…"}
            {carregando && dados && <span className="pn-girando" aria-label="atualizando" />}
          </p>
        </div>
        <div className="pn-periodos" role="tablist" aria-label="Período">
          {PERIODOS.map((p) => (
            <button
              key={p.valor}
              role="tab"
              aria-selected={periodo === p.valor}
              className={periodo === p.valor ? "ativo" : ""}
              onClick={() => setPeriodo(p.valor)}
            >
              {p.rotulo}
            </button>
          ))}
        </div>
      </div>

      {erro && <div className="pn-erro">{erro}</div>}

      {dados && (
        <>
          <SaudeBackup backup={dados.backup} lotes={dados.lotes_bpa} />

          {/* Destaques: sempre "agora", independentes do período */}
          <div className="pn-destaques">
            <Destaque rotulo="Atendimentos hoje" valor={fmt(d.hoje)}>
              <Variacao atual={d.hoje} anterior={d.ontem_mesma_hora} sufixo="vs ontem neste horário" />
            </Destaque>
            <Destaque
              rotulo={`Plantão ${d.plantao_turno === "DIURNO" ? "diurno" : "noturno"} atual`}
              valor={fmt(d.plantao)}
              detalhe={`desde ${new Date(d.plantao_inicio).toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" })}`}
            />
            <Destaque rotulo="Este mês" valor={fmt(d.mes)}>
              <Variacao atual={d.mes} anterior={d.mes_anterior_parcial} sufixo="vs mesmo período do mês passado" />
            </Destaque>
            {soHoje ? (
              <Destaque
                rotulo="Pacientes diferentes hoje"
                valor={fmt(r.pacientes_unicos)}
                detalhe={`${fmt(r.retornos)} ${r.retornos === 1 ? "voltou" : "voltaram"} mais de uma vez`}
              />
            ) : (
              <Destaque
                rotulo={`Média por dia · ${nomePeriodo}`}
                valor={r.media_dia.toLocaleString("pt-BR", { maximumFractionDigits: 1 })}
                detalhe={`${fmt(r.total)} atendimentos em ${fmt(r.dias)} dias`}
              />
            )}
          </div>

          <div className="pn-grade">
            {!soHoje && <Cartao
              className="pn-largo"
              titulo={porMes ? "Atendimentos por mês" : "Atendimentos por dia"}
              sub={`${fmt(r.total)} atendimentos · ${fmt(r.pacientes_unicos)} pacientes diferentes · ${fmt(r.retornos)} retornos (${pct(r.retornos, r.total).toLocaleString("pt-BR")}%)`}
            >
              <Colunas
                itens={dados.serie.map((s) => ({ chave: s.chave, valor: s.total, ...rotuloSerie(s.chave, porMes, dados.gerado_em.slice(0, 7)) }))}
                media={porMes ? 0 : r.media_dia}
              />
            </Cartao>}

            <Cartao
              className="pn-largo"
              titulo="Movimento por hora do dia"
              sub={soHoje
                ? `${fmt(r.total)} atendimentos hoje · ${fmt(r.pacientes_unicos)} pacientes diferentes · faixa escura = plantão noturno`
                : `Média de atendimentos em cada hora (${nomePeriodo}) · faixa escura = plantão noturno`}
            >
              <Colunas
                faixaNoturna
                formatoValor={(v) => v.toLocaleString("pt-BR", { maximumFractionDigits: 1 })}
                itens={dados.horas.map((h) => ({
                  chave: String(h.hora),
                  valor: h.media,
                  curto: `${h.hora}h`,
                  longo: `${String(h.hora).padStart(2, "0")}:00–${String(h.hora).padStart(2, "0")}:59${soHoje ? "" : " · média por dia"}`,
                  noturno: h.hora >= 19 || h.hora < 7,
                }))}
              />
            </Cartao>

            <Cartao titulo="Faixa etária" sub={dados.sem_idade ? `${fmt(dados.sem_idade)} sem data de nascimento válida` : "Idade na data do atendimento"}>
              <Colunas
                itens={dados.faixas.map((f) => ({ chave: f.rotulo, valor: f.total, curto: f.rotulo, longo: `${f.rotulo} anos · ${pct(f.total, r.total).toLocaleString("pt-BR")}% do período` }))}
              />
            </Cartao>

            <Cartao titulo="Perfil do período">
              <h3 className="pn-mini">Sexo</h3>
              <Divisao itens={dados.sexo} />
              <h3 className="pn-mini">Plantão</h3>
              <Divisao itens={dados.turnos} />
            </Cartao>

            <Cartao titulo="Bairros" sub="Os 8 com mais atendimentos">
              <Barras itens={dados.bairros} total={r.total} destacar={(i) => i.rotulo === "Não informado"} />
            </Cartao>

            <Cartao titulo="Cidades" sub="De onde vêm os pacientes">
              <Barras itens={dados.cidades} total={r.total} destacar={(i) => i.rotulo === "Não informado" || i.rotulo === "Outras"} />
            </Cartao>

            <Cartao titulo="Procedência">
              <Barras itens={dados.procedencias} total={r.total} destacar={(i) => i.rotulo === "Não informado"} />
            </Cartao>

            <Cartao titulo="Qualidade do cadastro" sub="Atendimentos do período com o dado faltando">
              <Medidor rotulo="Sem CPF" parte={dados.qualidade.sem_cpf} total={r.total} dica="Paciente sem CPF no cadastro -- complica o BPA" />
              <Medidor rotulo="Sem telefone" parte={dados.qualidade.sem_telefone} total={r.total} />
              <Medidor rotulo="Sem bairro" parte={dados.qualidade.sem_bairro} total={r.total} />
            </Cartao>
          </div>
        </>
      )}
    </div>
  );
}

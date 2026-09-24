import { useCallback, useEffect, useState } from "react";
import { bpaLocal, BpaDesligado, fmtNum, URL_BPA_LOCAL } from "../../services/bpaLocal";
import { dataLocalISO } from "../../utils";
import Digitacao from "./Digitacao";
import Enfermeiros from "./Enfermeiros";
import Nutricao from "./Nutricao";
import Migracao from "./Migracao";
import Conferencia from "./Conferencia";
import Prontuario from "./Prontuario";
import "./Bpa.css";

// Aba BPA (faturamento). As telas são do sistema, mas o trabalho é feito pelo
// BPA LOCAL do notebook (Firebird / BPA Magnético offline) — ver services/bpaLocal.js.

const GRUPOS = [
  { rotulo: "Dia a dia", abas: [{ id: "digitacao", rotulo: "Digitação" }, { id: "enfermeiros", rotulo: "Enfermeiros" }] },
  { rotulo: "Nutrição", abas: [{ id: "nutricao", rotulo: "Nutrição do mês" }] },
  { rotulo: "Mês", abas: [{ id: "migracao", rotulo: "Migração" }, { id: "conferencia", rotulo: "Conferência" }] },
  { rotulo: "Consultas", abas: [{ id: "prontuario", rotulo: "Buscar prontuário" }] },
];
const ATUALIZA_STATUS_MS = 30000;

// Selo do backup dos lotes (bpa_local/services/backup_lotes.py)
function SeloBackup({ b }) {
  if (!b || b.situacao === "desligado" || b.situacao === "nunca") return null;
  if (b.situacao === "ok") {
    const quando = b.ultimo_envio ? ` · último envio ${hora(b.ultimo_envio)}` : "";
    return <span className="bp-tag ok" title={`Lotes de digitação copiados no servidor e no backup diário${quando}`}>backup ok</span>;
  }
  return (
    <span className="bp-tag alerta" title={b.erro || "Lotes ainda não copiados no servidor"}>
      backup pendente{b.pendentes ? ` (${b.pendentes})` : ""}
    </span>
  );
}

function hora(iso) {
  return iso ? new Date(iso).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" }) : "";
}

// Linha da migração automática do dia, embaixo do título
function LinhaMigracaoAuto({ m }) {
  if (!m || m.situacao === "nunca") return null;
  const hojeISO = dataLocalISO();
  if (m.situacao === "rodando") {
    const pct = m.total ? ` · ${Math.round((m.i / m.total) * 100)}%` : "";
    return <p className="bp-sub andamento">⟳ Migração automática de hoje em andamento{pct}…</p>;
  }
  if (m.situacao === "erro") {
    return <p className="bp-sub erro">✕ Migração automática falhou ({hora(m.fim)}): {m.erro} — tenta de novo sozinha em alguns minutos</p>;
  }
  if (m.situacao === "ok" && m.data === hojeISO) {
    return (
      <p className="bp-sub ok">
        ✓ Migração automática de hoje ({hora(m.fim)}): {fmtNum(m.inseridos)} pacientes novos
        {m.erros ? ` · ${m.erros} erro(s) — veja a aba Migração` : ""}
      </p>
    );
  }
  return null;
}

export default function Bpa() {
  const [aba, setAbaState] = useState(() => sessionStorage.getItem("hmpcf_bpa_aba") || "digitacao");
  const [status, setStatus] = useState(null); // null = verificando
  const [desligado, setDesligado] = useState(false);
  // BPA respondeu, mas é a versão antiga (sem /api/status) -- notebook ainda não rodou o instalar.ps1
  const [antigo, setAntigo] = useState(false);
  const [profissionais, setProfissionais] = useState([]);
  const [recarregando, setRecarregando] = useState(false);

  function setAba(id) {
    sessionStorage.setItem("hmpcf_bpa_aba", id);
    setAbaState(id);
  }

  const verificar = useCallback(async () => {
    try {
      const st = await bpaLocal.status();
      setStatus(st);
      setDesligado(false);
      setAntigo(false);
      return true;
    } catch (e) {
      if (e instanceof BpaDesligado) setDesligado(true);
      else setAntigo(true);
      return false;
    }
  }, []);

  const carregarProfissionais = useCallback(async () => {
    try {
      setProfissionais(await bpaLocal.profissionais());
    } catch {
      /* status mostra o problema */
    }
  }, []);

  useEffect(() => {
    verificar().then((ok) => ok && carregarProfissionais());
    const t = setInterval(verificar, ATUALIZA_STATUS_MS);
    return () => clearInterval(t);
  }, [verificar, carregarProfissionais]);

  async function tentarDeNovo() {
    setStatus(null);
    if (await verificar()) carregarProfissionais();
  }

  async function recarregar() {
    setRecarregando(true);
    try {
      const r = await bpaLocal.recarregar();
      if (r.profs) setProfissionais(r.profs);
      await verificar();
    } catch {
      await verificar();
    } finally {
      setRecarregando(false);
    }
  }

  const ligado = status && !desligado && !antigo;

  return (
    <div className="bpa">
      <div className="bp-topo">
        <div>
          <h1>BPA</h1>
          <p className="bp-sub">Faturamento SUS: digitação dos atendimentos de médicos e enfermeiros e geração dos arquivos para importar no BPA Magnético</p>
          {ligado && <LinhaMigracaoAuto m={status.migracao_auto} />}
        </div>
        <div className="bp-estado">
          {antigo ? (
            <>
              <span className="bp-pontinho aviso" />
              <b>BPA deste notebook desatualizado</b>
            </>
          ) : desligado ? (
            <>
              <span className="bp-pontinho off" />
              <b>BPA deste notebook desligado</b>
              <button className="bp-btn-sec" onClick={tentarDeNovo}>Tentar de novo</button>
            </>
          ) : !status ? (
            <span>Procurando o BPA deste notebook…</span>
          ) : (
            <>
              <span className={`bp-pontinho${status.ok ? "" : " aviso"}`} />
              <b>BPA deste notebook ligado</b>
              <span className="sep">·</span>
              {status.ok ? <span>Firebird OK</span> : <span style={{ color: "var(--bp-erro)" }}>Firebird com erro</span>}
              <span className="sep">·</span>
              <span>{fmtNum(status.pacientes)} pacientes</span>
              <span className="sep">·</span>
              <span>{fmtNum(status.profissionais)} profissionais</span>
              <SeloBackup b={status.backup_lotes} />
              {status.pasta_lotes && (
                <span className="sep" title="Onde este notebook grava os lotes de digitação">·</span>
              )}
              {status.pasta_lotes && <span title="Onde este notebook grava os lotes de digitação">lotes em {status.pasta_lotes}</span>}
              <button className="bp-btn-sec" onClick={recarregar} disabled={recarregando}>
                {recarregando ? "Recarregando…" : "Recarregar"}
              </button>
            </>
          )}
        </div>
      </div>

      <nav className="bp-grupos" aria-label="Seções do BPA">
        {GRUPOS.map((g) => (
          <div key={g.rotulo} className="bp-grupo">
            <span className="bp-grupo-rot">{g.rotulo}</span>
            {g.abas.map((a) => (
              <button key={a.id} className={`bp-aba${aba === a.id ? " ativa" : ""}`} onClick={() => setAba(a.id)}>
                {a.rotulo}
              </button>
            ))}
          </div>
        ))}
      </nav>

      {antigo ? (
        <div className="bp-cartao bp-desligado">
          <div className="bp-desligado-icone" style={{ background: "var(--bp-alerta-bg)", color: "var(--bp-alerta)", borderColor: "var(--bp-alerta-borda)" }}>!</div>
          <h2 style={{ fontSize: 18 }}>O BPA deste notebook é a versão antiga</h2>
          <p className="bp-desc" style={{ marginTop: 6 }}>
            Ele funciona normalmente, mas estas telas precisam da versão nova. Enquanto isso, use o BPA antigo em outra aba.
          </p>
          <ol>
            <li>Na pasta do sistema: <code>git pull origin main</code></li>
            <li>Depois: <code>powershell -ExecutionPolicy Bypass -File bpa\instalar.ps1</code></li>
            <li>Volte aqui e clique em <b>Tentar de novo</b>.</li>
          </ol>
          <div className="bp-linha" style={{ justifyContent: "center" }}>
            <a className="bp-btn contorno" href={URL_BPA_LOCAL} target="_blank" rel="noreferrer" style={{ textDecoration: "none" }}>Abrir o BPA antigo</a>
            <button className="bp-btn" onClick={tentarDeNovo}>Tentar de novo</button>
          </div>
        </div>
      ) : desligado ? (
        <div className="bp-cartao bp-desligado">
          <div className="bp-desligado-icone">!</div>
          <h2 style={{ fontSize: 18 }}>O BPA deste notebook não está respondendo</h2>
          <p className="bp-desc" style={{ marginTop: 6 }}>
            As telas do BPA falam com o programa que roda neste computador (Firebird e BPA Magnético).
            Ele liga sozinho com o Windows.
          </p>
          <ol>
            <li>Espere 1 minuto se o notebook acabou de ligar.</li>
            <li>Clique em <b>Tentar de novo</b>.</li>
            <li>Se continuar, abra o atalho <b>BPA</b> da área de trabalho ou chame a TI.</li>
          </ol>
          <div className="bp-linha" style={{ justifyContent: "center" }}>
            <a className="bp-btn contorno" href={URL_BPA_LOCAL} target="_blank" rel="noreferrer" style={{ textDecoration: "none" }}>Abrir o BPA em outra aba</a>
            <button className="bp-btn" onClick={tentarDeNovo}>Tentar de novo</button>
          </div>
        </div>
      ) : !status ? null : (
        <>
          {!status.ok && (
            <div className="bp-aviso erro" style={{ marginTop: 0, marginBottom: 16 }}>
              <b>Firebird indisponível:</b> {status.erro_firebird}
              <small>Confira se o Firebird está ligado neste notebook e clique em Recarregar.</small>
            </div>
          )}
          {aba === "digitacao" && <Digitacao profissionais={profissionais} />}
          {aba === "enfermeiros" && <Enfermeiros profissionais={profissionais} />}
          {aba === "nutricao" && <Nutricao />}
          {aba === "migracao" && <Migracao migracaoAuto={status.migracao_auto} aoTerminar={recarregar} />}
          {aba === "conferencia" && <Conferencia />}
          {aba === "prontuario" && <Prontuario />}
        </>
      )}
    </div>
  );
}

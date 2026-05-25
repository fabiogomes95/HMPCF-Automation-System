import { Fragment, useState, useEffect, useCallback, useRef } from "react";
import { listarAtendimentos, listarAtendimentosPorPaciente } from "../services/api";
import { formatCPF, parseDateFromDB } from "../utils";
import "./Historico.css";

function formatDataHora(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  const dd   = String(d.getDate()).padStart(2, "0");
  const mm   = String(d.getMonth() + 1).padStart(2, "0");
  const yyyy = d.getFullYear();
  const hh   = String(d.getHours()).padStart(2, "0");
  const min  = String(d.getMinutes()).padStart(2, "0");
  return `${dd}/${mm}/${yyyy} ${hh}:${min}`;
}

function formatData(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  return `${String(d.getDate()).padStart(2,"0")}/${String(d.getMonth()+1).padStart(2,"0")}/${d.getFullYear()}`;
}

function formatHora(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  return `${String(d.getHours()).padStart(2,"0")}:${String(d.getMinutes()).padStart(2,"0")}`;
}

function buildEdicao(atd) {
  return {
    atendimentoId: atd.id,
    documento:     atd.paciente?.num_cpf || atd.paciente?.cns || "",
    procedencia:   atd.procedencia || "NORMAL",
    data:          formatData(atd.data_atendimento),
    hora:          formatHora(atd.data_atendimento),
  };
}

export default function Historico({ onNavigate, onEditar }) {
  const [items, setItems]         = useState([]);
  const [total, setTotal]         = useState(0);
  const [pages, setPages]         = useState(1);
  const [page, setPage]           = useState(1);
  const [busca, setBusca]         = useState("");
  const [loading, setLoading]     = useState(false);
  const [expandido, setExpandido] = useState(null);
  const [histPac, setHistPac]     = useState({});
  const debounceRef = useRef(null);
  const buscaRef    = useRef(null);

  const carregar = useCallback(async (pg, q) => {
    setLoading(true);
    try {
      const res = await listarAtendimentos(pg, q);
      setItems(res.data.items);
      setTotal(res.data.total);
      setPages(res.data.pages);
    } catch {
      setItems([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    carregar(1, "");
    buscaRef.current?.focus();
  }, [carregar]);

  // Carrega histórico do paciente ao expandir linha
  useEffect(() => {
    if (expandido === null) return;
    const atd = items.find(a => a.id === expandido);
    if (!atd?.paciente_id) return;
    const pid = atd.paciente_id;
    if (histPac[pid]?.loaded) return;

    setHistPac(prev => ({ ...prev, [pid]: { items: [], total: 0, loading: true, loaded: false } }));
    listarAtendimentosPorPaciente(pid, 1, 8)
      .then(res => setHistPac(prev => ({
        ...prev,
        [pid]: { items: res.data.items, total: res.data.total, loading: false, loaded: true },
      })))
      .catch(() => setHistPac(prev => ({
        ...prev,
        [pid]: { items: [], total: 0, loading: false, loaded: true },
      })));
  }, [expandido]); // eslint-disable-line react-hooks/exhaustive-deps

  function handleBusca(e) {
    const v = e.target.value;
    setBusca(v);
    setPage(1);
    setExpandido(null);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => carregar(1, v), 350);
  }

  function irPagina(pg) {
    setPage(pg);
    setExpandido(null);
    carregar(pg, busca);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function toggleExpandido(id) {
    setExpandido(prev => (prev === id ? null : id));
  }

  function handleEditar(e, atd) {
    e.stopPropagation();
    if (onEditar) onEditar(buildEdicao(atd));
  }

  return (
    <div className="historico">

      <div className="historico-header">
        <div className="historico-titulo">
          <h2>Histórico de Atendimentos</h2>
          {!loading && (
            <span className="historico-total">
              {total} registro{total !== 1 ? "s" : ""}
            </span>
          )}
        </div>
        <input
          ref={buscaRef}
          className="historico-busca"
          type="text"
          placeholder="Buscar por nome, CPF ou cartão SUS..."
          value={busca}
          onChange={handleBusca}
          autoComplete="off"
        />
      </div>

      <div className="historico-tabela-wrap">
        {loading && <div className="historico-loading">Carregando...</div>}

        <table className="historico-tabela">
          <thead>
            <tr>
              <th style={{ width: 44 }}>#</th>
              <th>Paciente</th>
              <th style={{ width: 130 }}>CPF</th>
              <th style={{ width: 150 }}>Cartão SUS</th>
              <th style={{ width: 130 }}>Data / Hora</th>
              <th style={{ width: 110 }}>Procedência</th>
              <th style={{ width: 70 }}></th>
            </tr>
          </thead>
          <tbody>
            {items.length === 0 && !loading && (
              <tr>
                <td colSpan={7} className="historico-vazio">
                  {busca ? `Nenhum resultado para "${busca}".` : "Nenhum atendimento registrado."}
                </td>
              </tr>
            )}

            {items.map(a => {
              const pid  = a.paciente_id;
              const pac  = histPac[pid];
              const isExp = expandido === a.id;

              return (
                <Fragment key={a.id}>
                  <tr
                    className={`historico-row${isExp ? " expandida" : ""}`}
                    onClick={() => toggleExpandido(a.id)}
                  >
                    <td className="cel-id">{a.id}</td>
                    <td className="cel-nome">
                      {a.paciente?.nome || "—"}
                      {pac?.loaded && pac.total > 1 && (
                        <span className="badge-entradas" title={`${pac.total} atendimentos no histórico`}>
                          {pac.total}×
                        </span>
                      )}
                    </td>
                    <td className="cel-cpf">
                      {a.paciente?.num_cpf ? formatCPF(a.paciente.num_cpf) : "—"}
                    </td>
                    <td className="cel-cns">{a.paciente?.cns || "—"}</td>
                    <td className="cel-data">{formatDataHora(a.data_atendimento)}</td>
                    <td className="cel-proc">{a.procedencia || "—"}</td>
                    <td className="cel-acao" onClick={e => e.stopPropagation()}>
                      <button
                        className="btn-editar-inline"
                        onClick={e => handleEditar(e, a)}
                        title="Editar este atendimento"
                      >
                        Editar
                      </button>
                    </td>
                  </tr>

                  {isExp && (
                    <tr className="detalhe-row">
                      <td colSpan={7}>
                        <div className="detalhe-corpo">

                          {/* Dados do atendimento */}
                          <div className="detalhe-grid">
                            <div><span className="detalhe-label">ID Atendimento</span>{a.id}</div>
                            <div><span className="detalhe-label">ID Paciente</span>{a.paciente_id}</div>
                            <div><span className="detalhe-label">Nome</span>{a.paciente?.nome || "—"}</div>
                            <div>
                              <span className="detalhe-label">CPF</span>
                              {a.paciente?.num_cpf ? formatCPF(a.paciente.num_cpf) : "—"}
                            </div>
                            <div><span className="detalhe-label">Cartão SUS</span>{a.paciente?.cns || "—"}</div>
                            <div>
                              <span className="detalhe-label">Nascimento</span>
                              {a.paciente?.dtnasc ? parseDateFromDB(a.paciente.dtnasc) : "—"}
                            </div>
                            <div><span className="detalhe-label">Cidade</span>{a.paciente?.cidade || "—"}</div>
                            <div><span className="detalhe-label">Data atendimento</span>{formatDataHora(a.data_atendimento)}</div>
                            <div><span className="detalhe-label">Procedência</span>{a.procedencia || "—"}</div>
                            <div><span className="detalhe-label">Registrado em</span>{formatDataHora(a.created_at)}</div>
                          </div>

                          {/* Histórico do paciente */}
                          <div className="hist-pac-secao">
                            {!pac || pac.loading ? (
                              <span className="hist-pac-loading">Carregando histórico do paciente...</span>
                            ) : (
                              <>
                                <div className="hist-pac-header">
                                  <span className="hist-pac-contador">
                                    {pac.total === 0 && "Sem atendimentos registrados"}
                                    {pac.total === 1 && "1ª entrada deste paciente"}
                                    {pac.total > 1 && `${pac.total} entradas no histórico`}
                                  </span>
                                  {pac.total > 1 && pac.items[0] && (
                                    <span className="hist-pac-ultima">
                                      Última: {formatDataHora(pac.items[0].data_atendimento)}
                                    </span>
                                  )}
                                </div>

                                {pac.total > 1 && (
                                  <table className="hist-pac-tabela">
                                    <thead>
                                      <tr>
                                        <th>ID</th>
                                        <th>Data / Hora</th>
                                        <th>Procedência</th>
                                        <th></th>
                                      </tr>
                                    </thead>
                                    <tbody>
                                      {pac.items.map(ha => (
                                        <tr key={ha.id} className={ha.id === a.id ? "hist-pac-atual" : ""}>
                                          <td className="cel-id">{ha.id}</td>
                                          <td>{formatDataHora(ha.data_atendimento)}</td>
                                          <td>{ha.procedencia || "—"}</td>
                                          <td>
                                            {ha.id !== a.id && (
                                              <button
                                                className="btn-editar-hist"
                                                onClick={e => handleEditar(e, ha)}
                                              >
                                                Editar
                                              </button>
                                            )}
                                            {ha.id === a.id && (
                                              <span className="hist-pac-este">este</span>
                                            )}
                                          </td>
                                        </tr>
                                      ))}
                                      {pac.total > 8 && (
                                        <tr>
                                          <td colSpan={4} className="hist-pac-mais">
                                            + {pac.total - 8} atendimento{pac.total - 8 !== 1 ? "s" : ""} anteriores
                                          </td>
                                        </tr>
                                      )}
                                    </tbody>
                                  </table>
                                )}
                              </>
                            )}
                          </div>

                          {/* Rodapé */}
                          <div className="detalhe-rodape">
                            <span className="detalhe-hint">
                              Para reabrir na recepção, vá para{" "}
                              <strong>Recepção</strong> e digite o CPF:{" "}
                              <strong>
                                {a.paciente?.num_cpf ? formatCPF(a.paciente.num_cpf) : "—"}
                              </strong>
                            </span>
                            <button
                              className="btn-editar-recepcao"
                              onClick={e => handleEditar(e, a)}
                            >
                              Editar Atendimento
                            </button>
                            <button
                              className="btn-ir-recepcao"
                              onClick={e => { e.stopPropagation(); onNavigate("recepcao"); }}
                            >
                              Ir para Recepção
                            </button>
                          </div>

                        </div>
                      </td>
                    </tr>
                  )}
                </Fragment>
              );
            })}
          </tbody>
        </table>
      </div>

      {pages > 1 && (
        <div className="historico-paginacao">
          <button onClick={() => irPagina(page - 1)} disabled={page <= 1}>
            ‹ Anterior
          </button>
          <span>Página {page} de {pages}</span>
          <button onClick={() => irPagina(page + 1)} disabled={page >= pages}>
            Próxima ›
          </button>
        </div>
      )}
    </div>
  );
}

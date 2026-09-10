import { Fragment, useState, useEffect, useCallback, useRef } from "react";
import {
  buscarPacientesAgrupados,
  listarAtendimentosPorPaciente,
} from "../services/api";
import { formatCPF } from "../utils";
import "./Historico.css";


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

function formatDtnasc(dtnasc) {
  if (!dtnasc || dtnasc.length !== 8) return "—";
  return `${dtnasc.slice(6, 8)}/${dtnasc.slice(4, 6)}/${dtnasc.slice(0, 4)}`;
}

export default function Historico({ onNavigate }) {
  const [items, setItems]         = useState([]);
  const [total, setTotal]         = useState(0);
  const [pages, setPages]         = useState(1);
  const [page, setPage]           = useState(1);
  const [busca, setBusca]         = useState("");
  const [loading, setLoading]     = useState(false);
  const [pacienteExpandido, setPacienteExpandido] = useState(null);
  const [histPac, setHistPac]     = useState({});
  const debounceRef = useRef(null);
  const buscaRef    = useRef(null);

  const carregar = useCallback(async (pg, q) => {
    if (!q || q.trim().length < 3) {
      setItems([]);
      setTotal(0);
      setPages(1);
      setPacienteExpandido(null);
      setHistPac({});
      return;
    }
    setLoading(true);
    setPacienteExpandido(null);
    setHistPac({});
    try {
      const res = await buscarPacientesAgrupados(q, pg);
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
    buscaRef.current?.focus();
  }, []);

  // Carrega histórico do paciente ao expandir
  useEffect(() => {
    if (pacienteExpandido === null) return;
    const pid = pacienteExpandido;
    if (histPac[pid]?.loaded) return;

    setHistPac(prev => ({ ...prev, [pid]: { items: [], total: 0, loading: true, loaded: false } }));
    listarAtendimentosPorPaciente(pid, 1, 50)
      .then(res => setHistPac(prev => ({
        ...prev,
        [pid]: { items: res.data.items, total: res.data.total, loading: false, loaded: true },
      })))
      .catch(() => setHistPac(prev => ({
        ...prev,
        [pid]: { items: [], total: 0, loading: false, loaded: true },
      })));
  }, [pacienteExpandido]); // eslint-disable-line react-hooks/exhaustive-deps

  function handleBusca(e) {
    const v = e.target.value;
    setBusca(v);
    setPage(1);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => carregar(1, v), 350);
  }

  function irPagina(pg) {
    setPage(pg);
    setPacienteExpandido(null);
    carregar(pg, busca);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function toggleExpandido(pacienteId) {
    setPacienteExpandido(prev => (prev === pacienteId ? null : pacienteId));
  }

  return (
    <div className="historico">

      <div className="historico-header">
        <div className="historico-titulo">
          <h2>Busca de Pacientes</h2>
          {!loading && (
            <span className="historico-total">
              {total} paciente{total !== 1 ? "s" : ""}
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
              <th style={{ width: 140 }}>Cartão SUS</th>
              <th style={{ width: 90 }}>Entradas</th>
              <th style={{ width: 130 }}>Última entrada</th>
            </tr>
          </thead>
          <tbody>
            {items.length === 0 && !loading && (
              <tr>
                <td colSpan={6} className="historico-vazio">
                  {busca.length >= 3
                    ? `Nenhum resultado para "${busca}".`
                    : "Digite pelo menos 3 caracteres para buscar."}
                </td>
              </tr>
            )}

            {items.map(pac => {
              const pid  = pac.paciente_id;
              const hp   = histPac[pid];
              const isExp = pacienteExpandido === pid;

              return (
                <Fragment key={pid}>
                  {/* Linha principal do paciente */}
                  <tr
                    className={`historico-row${isExp ? " expandida" : ""}`}
                    onClick={() => toggleExpandido(pid)}
                  >
                    <td className="cel-id">{pid}</td>
                    <td className="cel-nome">{pac.nome || "—"}</td>
                    <td className="cel-cpf">
                      {pac.num_cpf ? formatCPF(pac.num_cpf) : "—"}
                    </td>
                    <td className="cel-cns">{pac.cns || "—"}</td>
                    <td className="cel-entradas">
                      <span className="badge-entradas">{pac.total_entradas}x</span>
                    </td>
                    <td className="cel-ultima">
                      {pac.ultima_data ? formatData(pac.ultima_data) : "—"}
                    </td>
                  </tr>

                  {/* Linha expandida com histórico */}
                  {isExp && (
                    <tr className="detalhe-row">
                      <td colSpan={6}>
                        <div className="detalhe-corpo">
                          {/* Cabeçalho do paciente */}
                          <div className="detalhe-paciente-header">
                            <strong>{pac.nome || "—"}</strong>
                            <span className="detalhe-resumo">
                              {pac.total_entradas} entrada{pac.total_entradas !== 1 ? "s" : ""}
                              {" — última: "}{pac.ultima_data ? formatData(pac.ultima_data) : "—"}
                            </span>
                          </div>

                          {/* Lista de atendimentos */}
                          <div className="hist-pac-secao">
                            {!hp || hp.loading ? (
                              <div className="hist-pac-loading">Carregando histórico...</div>
                            ) : (
                              <>
                                <div className="hist-pac-header">
                                  <span className="hist-pac-contador">
                                    {hp.total === 0 && "Sem atendimentos registrados"}
                                    {hp.total === 1 && "1 atendimento"}
                                    {hp.total > 1 && `${hp.total} atendimentos no histórico`}
                                  </span>
                                </div>

                                {hp.total > 0 && (
                                  <table className="hist-pac-tabela">
                                    <thead>
                                      <tr>
                                        <th>ID</th>
                                        <th>Data</th>
                                        <th>Hora</th>
                                        <th>CPF</th>
                                        <th>Cartão SUS</th>
                                        <th>Dt. Nascimento</th>
                                      </tr>
                                    </thead>
                                    <tbody>
                                      {hp.items.map(ha => (
                                        <tr key={ha.id}>
                                          <td className="cel-id">{ha.id}</td>
                                          <td>{formatData(ha.data_atendimento)}</td>
                                          <td>{formatHora(ha.data_atendimento)}</td>
                                          <td>{pac.num_cpf ? formatCPF(pac.num_cpf) : "—"}</td>
                                          <td>{pac.cns || "—"}</td>
                                          <td>{formatDtnasc(pac.dtnasc)}</td>
                                        </tr>
                                      ))}
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
                                {pac.num_cpf ? formatCPF(pac.num_cpf) : "—"}
                              </strong>
                            </span>
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

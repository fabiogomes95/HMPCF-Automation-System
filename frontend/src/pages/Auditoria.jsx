import { useEffect, useState } from "react";
import api from "../services/api";
import "./Auditoria.css";

const LABEL_ACAO = { criar: "Criou", atualizar: "Editou", remover: "Removeu" };
const LABEL_RECURSO = { paciente: "Paciente", atendimento: "Atendimento", usuario: "Usuário" };

function formatDataHora(iso) {
  const d = new Date(iso);
  const data = d.toLocaleDateString("pt-BR");
  const hora = d.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
  return `${data} ${hora}`;
}

export default function Auditoria() {
  const [logs, setLogs]       = useState([]);
  const [total, setTotal]     = useState(0);
  const [page, setPage]       = useState(1);
  const [loading, setLoading] = useState(false);
  const [erro, setErro]       = useState("");
  const [filtroAcao, setFiltroAcao]       = useState("TODOS");
  const [filtroRecurso, setFiltroRecurso] = useState("TODOS");
  const [filtroUsuario, setFiltroUsuario] = useState("");
  const [desde, setDesde]                 = useState("");
  const [ate, setAte]                     = useState("");

  const PAGE_SIZE = 50;

  // Todos os filtros vão pro backend -- filtrar no navegador só pegava a
  // página atual e a paginação ficava errada.
  useEffect(() => {
    setLoading(true);
    setErro("");
    const t = setTimeout(() => {
      const params = new URLSearchParams({ page, page_size: PAGE_SIZE });
      if (filtroRecurso !== "TODOS") params.set("recurso", filtroRecurso);
      if (filtroAcao !== "TODOS") params.set("acao", filtroAcao);
      if (filtroUsuario.trim()) params.set("usuario_username", filtroUsuario.trim());
      if (desde) params.set("desde", desde);
      if (ate) params.set("ate", ate);
      api.get(`/auditoria/?${params}`)
        .then(res => {
          setLogs(res.data.items);
          setTotal(res.data.total);
        })
        .catch(() => setErro("Não foi possível carregar os registros de auditoria."))
        .finally(() => setLoading(false));
    }, 300);
    return () => clearTimeout(t);
  }, [page, filtroRecurso, filtroAcao, filtroUsuario, desde, ate]);

  const logsFiltrados = logs;

  const totalPaginas = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div className="auditoria">
      <div className="auditoria-header">
        <h2>Auditoria</h2>
        <span className="auditoria-total">{total} registro{total !== 1 ? "s" : ""}</span>
      </div>

      <div className="auditoria-filtros">
        <label>
          Recurso
          <select value={filtroRecurso} onChange={e => { setFiltroRecurso(e.target.value); setPage(1); }}>
            <option value="TODOS">Todos</option>
            <option value="paciente">Paciente</option>
            <option value="atendimento">Atendimento</option>
            <option value="usuario">Usuário</option>
          </select>
        </label>
        <label>
          Ação
          <select value={filtroAcao} onChange={e => { setFiltroAcao(e.target.value); setPage(1); }}>
            <option value="TODOS">Todas</option>
            <option value="criar">Criou</option>
            <option value="atualizar">Editou</option>
            <option value="remover">Removeu</option>
          </select>
        </label>
        <label>
          Usuário
          <input value={filtroUsuario} placeholder="login" onChange={e => { setFiltroUsuario(e.target.value); setPage(1); }} />
        </label>
        <label>
          De
          <input type="date" value={desde} onChange={e => { setDesde(e.target.value); setPage(1); }} />
        </label>
        <label>
          Até
          <input type="date" value={ate} onChange={e => { setAte(e.target.value); setPage(1); }} />
        </label>
      </div>

      {loading && <div className="auditoria-loading">Carregando...</div>}
      {erro    && <div className="auditoria-erro">{erro}</div>}

      {!loading && !erro && (
        <>
          <table className="auditoria-tabela">
            <thead>
              <tr>
                <th>Data / Hora</th>
                <th>Usuário</th>
                <th>Ação</th>
                <th>Recurso</th>
                <th>ID</th>
                <th>Campos alterados</th>
              </tr>
            </thead>
            <tbody>
              {logsFiltrados.length === 0 && (
                <tr><td colSpan={6} className="auditoria-vazio">Nenhum registro encontrado.</td></tr>
              )}
              {logsFiltrados.map((log, i) => (
                <tr key={i} className={`acao-${log.acao}`}>
                  <td className="cel-data">{formatDataHora(log.criado_em)}</td>
                  <td className="cel-usuario">{log.usuario_username}</td>
                  <td className="cel-acao">{LABEL_ACAO[log.acao] ?? log.acao}</td>
                  <td>{LABEL_RECURSO[log.recurso] ?? log.recurso} #{log.recurso_id}</td>
                  <td>{log.recurso_id}</td>
                  <td className="cel-campos">
                    {log.campos_alterados?.length ? log.campos_alterados.join(", ") : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          <div className="auditoria-paginacao">
            <button disabled={page <= 1} onClick={() => setPage(p => p - 1)}>← Anterior</button>
            <span>Página {page} de {totalPaginas}</span>
            <button disabled={page >= totalPaginas} onClick={() => setPage(p => p + 1)}>Próxima →</button>
          </div>
        </>
      )}
    </div>
  );
}

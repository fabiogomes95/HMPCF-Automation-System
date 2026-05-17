/*
 * DASHBOARD.JSX — Página inicial (Dashboard).
 *
 * FUNÇÃO:
 *   Mostra uma visão geral do sistema com cards de indicadores.
 *
 * HOOKS USADOS:
 *   useState → guarda o resultado do healthcheck
 *   useEffect → executa a chamada API quando o componente monta
 *
 * FLUXO:
 *   1. Componente monta (useEffect roda)
 *   2. Faz GET /api/v1/health
 *   3. Se sucesso: guarda resposta no state (health)
 *   4. Se erro: ignora (trata com .catch(() => {}))
 *   5. Renderiza cards com os dados
 *
 * POR QUE SEPARAR PÁGINAS EM ARQUIVOS INDIVIDUAIS?
 *   Cada página tem sua própria lógica e layout.
 *   Manter em arquivos separados:
 *   - Fácil de localizar (Dashboard.jsx, BPA.jsx, Reports.jsx)
 *   - Fácil de modificar sem afetar outras páginas
 *   - Carregamento lazy (futuro) possível página por página
 *
 * PADRÃO: PÁGINA = COMPONENTE + CSS
 *   Exemplo: Dashboard.jsx + Dashboard.css
 *   O CSS é importado diretamente no componente.
 *   Vite otimiza isso automaticamente no build.
 */
import { useEffect, useState } from "react";
import api from "../services/api";
import "./Dashboard.css";

export default function Dashboard() {
  // Estado para guardar a resposta do healthcheck
  const [health, setHealth] = useState(null);

  // useEffect: executa código após o componente renderizar
  // [] (array vazio) = executa apenas uma vez (na montagem)
  useEffect(() => {
    // Chama o endpoint de healthcheck do backend
    api
      .get("/health")
      .then((res) => setHealth(res.data))
      .catch(() => {
        /* Silencia erro para não quebrar a página */
      });
  }, []);

  return (
    <div className="dashboard">
      <h2 className="dashboard-title">Dashboard</h2>
      <p className="dashboard-subtitle">
        Visão geral do sistema HMPCF
      </p>

      {/* ── Cards de indicadores ──────────────────────── */}
      <div className="dashboard-cards">
        <div className="dashboard-card">
          <div className="card-value">
            {/* Se health existe, mostra "ok", senão "—" */}
            {health ? health.status : "—"}
          </div>
          <div className="card-label">Status da API</div>
        </div>

        {/* Futuros cards:
          <div className="dashboard-card">
            <div className="card-value">108</div>
            <div className="card-label">Pacientes Firebird</div>
          </div>
          <div className="dashboard-card">
            <div className="card-value">29.940</div>
            <div className="card-label">Pacientes SQLite</div>
          </div>
        */}
      </div>
    </div>
  );
}

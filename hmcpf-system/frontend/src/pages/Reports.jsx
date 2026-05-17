/*
 * REPORTS.JSX — Página de relatórios (placeholder).
 *
 * FUTURAS FUNCIONALIDADES:
 *   - Lista de relatórios disponíveis com descrição
 *   - Botões para gerar relatório (PDF, Excel)
 *   - Filtros por período e tipo
 *   - Preview do relatório antes do download
 *   - Histórico de relatórios gerados
 *
 * TIPOS DE RELATÓRIO PREVISTOS:
 *   - Mensal (produção do mês)
 *   - Auditoria (atendimentos no período)
 *   - Comparativo (mês atual vs anterior)
 *   - Indicadores (médias, totais, metas)
 *
 * ORIGEM DOS DADOS:
 *   Os relatórios serão gerados pelo backend usando as
 *   mesmas bibliotecas do sistema legado:
 *   - fpdf2 → PDF
 *   - openpyxl → Excel
 *   - matplotlib/seaborn → Gráficos
 */
import "./Dashboard.css";

export default function Reports() {
  return (
    <div className="dashboard">
      <h2 className="dashboard-title">Relatórios</h2>
      <p className="dashboard-subtitle">
        Relatórios gerenciais — módulo em implementação
      </p>

      <div className="dashboard-cards">
        <div className="dashboard-card">
          <div className="card-value" style={{ fontSize: "1rem", color: "var(--color-text-secondary)" }}>
            Disponível na Fase 2 da migração
          </div>
          <div className="card-label">Status do Módulo</div>
        </div>
      </div>
    </div>
  );
}

/*
 * BPA.JSX — Página do módulo BPA (placeholder).
 *
 * FUTURAS FUNCIONALIDADES:
 *   - Formulário para gerar BPA por competência
 *   - Tabela com histórico de BPAs gerados
 *   - Botão de download do arquivo
 *   - Indicadores: total de procedimentos, valor, etc.
 *
 * POR QUE UM PLACEHOLDER?
 *   Estamos na Fase 1 da migração (fundação).
 *   A lógica real do BPA será implementada na Fase 2,
 *   quando migrarmos o código de integracao/exportar_bpa.py.
 *
 *   Por enquanto:
 *   - A rota /bpa existe e funciona
 *   - O layout (sidebar) permanece consistente
 *   - O usuário vê uma mensagem clara de "em implementação"
 *
 * ESTRUTURA FUTURA:
 *   <PageHeader titulo="BPA" descricao="..." />
 *   <Filtros competencia={mes} onChange={...} />
 *   <Tabela dados={bpas} colunas={colunas} />
 *   <Botao acao="Gerar BPA" onClick={...} />
 */
import "./Dashboard.css";

export default function BPA() {
  return (
    <div className="dashboard">
      <h2 className="dashboard-title">BPA</h2>
      <p className="dashboard-subtitle">
        Boletim de Produção Ambulatorial — módulo em implementação
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

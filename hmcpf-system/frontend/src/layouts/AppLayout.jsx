/*
 * APPLAYOUT.JSX — Layout principal da aplicação.
 *
 * ESTRUTURA VISUAL:
 *
 *   ┌──────────┬──────────────────────────────────┐
 *   │          │                                  │
 *   │ Sidebar  │  <Outlet /> (conteúdo da página) │
 *   │ (fixa)   │                                  │
 *   │          │                                  │
 *   └──────────┴──────────────────────────────────┘
 *
 * O QUE É OUTLET?
 *   Outlet é um componente do react-router-dom.
 *   Ele renderiza o componente correspondente à rota atual.
 *
 *   Exemplo:
 *     URL / → Outlet = <Dashboard />
 *     URL /bpa → Outlet = <BPA />
 *
 *   Isso permite que o layout (sidebar) fique sempre visível
 *   enquanto apenas o conteúdo central muda.
 *
 * POR QUE CSS EM ARQUIVO SEPARADO?
 *   Cada componente tem seu próprio CSS.
 *   Isso mantém o código organizado e fácil de manter.
 *   Se precisar mudar o layout, você sabe exatamente qual arquivo alterar.
 */
import { Outlet } from "react-router-dom";
import Sidebar from "../components/Sidebar";
import "./AppLayout.css";

export default function AppLayout() {
  return (
    <div className="app-layout">
      <Sidebar />
      <main className="app-main">
        {/* Outlet = espaço onde o conteúdo da rota atual aparece */}
        <Outlet />
      </main>
    </div>
  );
}

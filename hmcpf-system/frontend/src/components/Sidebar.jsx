/*
 * SIDEBAR.JSX — Barra lateral de navegação.
 *
 * FUNÇÕES:
 *   1. Navegação entre páginas (Dashboard, BPA, Relatórios, etc.)
 *   2. Alternar tema claro/escuro
 *   3. Exibir logo e versão do sistema
 *
 * COMPONENTE: NavLink
 *   NavLink é um componente do react-router-dom similar a <a>,
 *   mas ele:
 *   - Navega sem recarregar a página (SPA behavior)
 *   - Aplica classe "active" automaticamente quando a rota coincide
 *
 *   A classe "sidebar-link--active" destaca visualmente
 *   a página atual na sidebar.
 *
 * ITENS DE NAVEGAÇÃO:
 *   O array NAV_ITEMS centraliza a definição dos links.
 *   Para adicionar um novo, basta inserir um objeto no array:
 *     { label: "Pacientes", path: "/pacientes", icon: "👤" }
 *
 *   O ícone e o Path também precisam existir em routes/index.jsx.
 *
 * HOOK useTheme:
 *   Importado de hooks/useTheme, dá acesso ao tema atual
 *   e à função toggleTheme para alternar dark/light.
 */
import { NavLink } from "react-router-dom";
import { useTheme } from "../hooks/useTheme";
import "./Sidebar.css";

// Lista de itens do menu. Editando aqui, toda sidebar se atualiza.
const NAV_ITEMS = [
  { label: "Dashboard", path: "/", icon: "📊" },
  { label: "BPA", path: "/bpa", icon: "📋" },
  { label: "Integração", path: "/integracao", icon: "🔌" },
  { label: "Relatórios", path: "/reports", icon: "📈" },
  { label: "Recepção", path: "/recepcao", icon: "🏥" },
];

export default function Sidebar() {
  const { theme, toggleTheme } = useTheme();

  return (
    <aside className="sidebar">
      {/* ── Cabeçalho com logo ───────────────────────── */}
      <div className="sidebar-header">
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <img src="/logo.png" alt="Logo" style={{ height: 32, width: "auto" }} />
          <h1 className="sidebar-logo" style={{ margin: 0 }}>HMPCF</h1>
        </div>
        <span className="sidebar-version">v2.0.0</span>
      </div>

      {/* ── Navegação principal ──────────────────────── */}
      <nav className="sidebar-nav">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            // end = true apenas para "/" (evita que "/" fique ativo em todas as rotas)
            end={item.path === "/"}
            // isActive vem do NavLink (true se a rota atual coincide)
            className={({ isActive }) =>
              `sidebar-link ${isActive ? "sidebar-link--active" : ""}`
            }
          >
            <span className="sidebar-icon">{item.icon}</span>
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>

      {/* ── Rodapé com controle de tema ──────────────── */}
      <div className="sidebar-footer">
        <button className="sidebar-theme-btn" onClick={toggleTheme}>
          {theme === "light" ? "🌙" : "☀️"}{" "}
          {theme === "light" ? "Modo Escuro" : "Modo Claro"}
        </button>
      </div>
    </aside>
  );
}

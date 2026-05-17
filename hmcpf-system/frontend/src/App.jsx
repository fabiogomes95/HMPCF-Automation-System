/*
 * APP.JSX — Componente raiz da aplicação.
 *
 * AQUI ACONTECE:
 *   1. ThemeProvider envolve toda a app → tema dark/light disponível globalmente
 *   2. RouterProvider gerencia as rotas (navegação entre páginas)
 *   3. router (de routes/index.jsx) define a estrutura de páginas
 *
 * ESTRUTURA DA APLICAÇÃO:
 *
 *   App
 *    └── ThemeProvider (contexto de tema)
 *         └── RouterProvider (react-router-dom)
 *              └── AppLayout (sidebar + main)
 *                   ├── Dashboard (/)
 *                   ├── BPA (/bpa)
 *                   └── Reports (/reports)
 *
 * POR QUE ThemeProvider ENVOLVE RouterProvider?
 *   Para que TODOS os componentes tenham acesso ao tema,
 *   incluindo o layout que contém a sidebar com o botão
 *   de alternar tema.
 */
import { RouterProvider } from "react-router-dom";
import { ThemeProvider } from "./contexts/ThemeContext";
import router from "./routes";

export default function App() {
  return (
    <ThemeProvider>
      <RouterProvider router={router} />
    </ThemeProvider>
  );
}

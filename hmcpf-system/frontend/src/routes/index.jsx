/*
 * ROUTES/INDEX.JSX — Configuração de rotas da aplicação.
 *
 * BIBLIOTECA: react-router-dom v6
 *
 * COMO FUNCIONA:
 *   createBrowserRouter cria um roteador que usa a URL do navegador.
 *   Cada objeto "path" mapeia uma URL para um componente.
 *
 *   Exemplo:
 *     / → Dashboard
 *     /bpa → BPA
 *     /reports → Reports
 *
 *   O AppLayout tem um <Outlet /> que renderiza o componente
 *   correspondente à rota atual. A sidebar permanece visível
 *   em todas as páginas.
 *
 *   Se o usuário digitar uma rota que não existe (*),
 *   redirecionamos para / (Navigate to="/").
 *
 * PARA ADICIONAR UMA NOVA PÁGINA:
 *   1. Crie o arquivo em pages/NovaPagina.jsx
 *   2. Importe aqui
 *   3. Adicione { path: "nova-rota", element: <NovaPagina /> }
 */
import { createBrowserRouter, Navigate } from "react-router-dom";
import AppLayout from "../layouts/AppLayout";
import BPA from "../pages/BPA";
import Dashboard from "../pages/Dashboard";
import Integracao from "../pages/Integracao";
import Recepcao from "../pages/Recepcao";
import Reports from "../pages/Reports";

const router = createBrowserRouter([
  {
    // Path "/" é o layout principal
    path: "/",
    element: <AppLayout />,
    // children = páginas que aparecem dentro do AppLayout
    children: [
      { index: true, element: <Dashboard /> },           // /
      { path: "bpa", element: <BPA /> },                  // /bpa
      { path: "integracao", element: <Integracao /> },     // /integracao
      { path: "reports", element: <Reports /> },           // /reports
      { path: "recepcao", element: <Recepcao /> },          // /recepcao
      { path: "*", element: <Navigate to="/" replace /> }, // fallback
    ],
  },
]);

export default router;

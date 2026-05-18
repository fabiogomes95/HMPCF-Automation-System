/*
 * MAIN.JSX — Ponto de entrada do frontend React.
 *
 * O QUE ACONTECE AQUI:
 *   1. React é importado (biblioteca de UI)
 *   2. ReactDOM 'rende riza' (cria) o componente App dentro da div#root
 *   3. global.css é importado — os estilos valem para TUDO
 *   4. StrictMode ativa checagens extras em desenvolvimento
 *
 * POR QUE SEPARAR main.jsx DE App.jsx?
 *   main.jsx = config (imports, providers, render)
 *   App.jsx  = estrutura da aplicação (rotas, providers lógicos)
 *
 *   Isso segue a convenção de projetos React profissionais.
 *   Fica mais fácil de testar o App separadamente.
 */
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./styles/global.css";

// createRoot é a API moderna do React 18+
// Antes era ReactDOM.render(), que está deprecated
createRoot(document.getElementById("root")).render(
  <StrictMode>
    <App />
  </StrictMode>
);

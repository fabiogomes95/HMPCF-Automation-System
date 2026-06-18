import { useState } from "react";
import Recepcao from "./pages/Recepcao";
import Historico from "./pages/Historico";
import Bpa from "./pages/Bpa";
import "./App.css";

export default function App() {
  const [tela, setTela]     = useState("recepcao");
  const [edicao, setEdicao] = useState(null);

  function navRecepcao() {
    setEdicao(null);
    setTela("recepcao");
  }

  function navHistorico() {
    setTela("historico");
  }

  function navBpa() {
    setTela("bpa");
  }

  function abrirEdicao(dadosEdicao) {
    setEdicao(dadosEdicao);
    setTela("recepcao");
  }

  function fecharEdicao() {
    setEdicao(null);
    setTela("historico");
  }

  return (
    <>
      <nav className="app-nav no-print">
        <span className="app-nav-brand">HMPCF</span>
        <button
          className={`app-nav-btn${tela === "recepcao" ? " ativo" : ""}`}
          onClick={navRecepcao}
        >
          Recepção
        </button>
        <button
          className={`app-nav-btn${tela === "historico" ? " ativo" : ""}`}
          onClick={navHistorico}
        >
          Histórico
        </button>
        <button
          className={`app-nav-btn${tela === "bpa" ? " ativo" : ""}`}
          onClick={navBpa}
        >
          BPA
        </button>
      </nav>

      {tela === "recepcao" && <Recepcao edicao={edicao} onVoltar={fecharEdicao} />}
      {tela === "historico" && <Historico onNavigate={setTela} onEditar={abrirEdicao} />}
      {tela === "bpa" && <Bpa />}
    </>
  );
}

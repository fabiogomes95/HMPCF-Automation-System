import { useEffect, useState } from "react";
import Recepcao from "./pages/Recepcao";
import Historico from "./pages/Historico";
import Login from "./pages/Login";
import { getMe, logout } from "./services/auth";
import { setOnUnauthorized } from "./services/api";
import "./App.css";

export default function App() {
  const [tela, setTela]     = useState("recepcao");
  const [edicao, setEdicao] = useState(null);

  // null = ainda verificando sessão · undefined-like "sem usuário" = false
  const [usuario, setUsuario]     = useState(null);
  const [verificando, setVerificando] = useState(true);

  useEffect(() => {
    // Qualquer chamada que volte 401 (sessão expirou no meio do uso) derruba
    // a tela pro login de novo, sem precisar cada página tratar isso na mão.
    setOnUnauthorized(() => setUsuario(null));

    getMe()
      .then((res) => setUsuario(res.data))
      .catch(() => setUsuario(null))
      .finally(() => setVerificando(false));
  }, []);

  async function handleSair() {
    try {
      await logout();
    } finally {
      setUsuario(null);
    }
  }

  function navRecepcao() {
    setEdicao(null);
    setTela("recepcao");
  }

  function navHistorico() {
    setTela("historico");
  }

  function abrirEdicao(dadosEdicao) {
    setEdicao(dadosEdicao);
    setTela("recepcao");
  }

  function fecharEdicao() {
    setEdicao(null);
    setTela("historico");
  }

  if (verificando) {
    return null; // evita "piscar" a tela de login antes de saber se já tem sessão
  }

  if (!usuario) {
    return <Login onLogin={setUsuario} />;
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
        <button className="app-nav-btn app-nav-sair" onClick={handleSair}>
          Sair ({usuario.username})
        </button>
      </nav>

      {tela === "recepcao" ? (
        <Recepcao edicao={edicao} onVoltar={fecharEdicao} />
      ) : (
        <Historico onNavigate={setTela} onEditar={abrirEdicao} />
      )}
    </>
  );
}

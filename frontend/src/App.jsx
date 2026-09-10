import { useEffect, useState } from "react";
import Recepcao from "./pages/Recepcao";
import Historico from "./pages/Historico";
import PlanilhaAtendimentos from "./pages/PlanilhaAtendimentos";
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
  const [avisoRelogin, setAvisoRelogin] = useState(null); // username pro qual recaiu, se trocou

  // Busca /auth/me e reflete no estado. Usado tanto na carga inicial quanto
  // depois de "Sair" -- no terminal fixo da recepção (acesso local) o backend
  // loga de volta sozinho aqui, então os dois pontos usam a mesma lógica.
  async function refreshUsuario() {
    try {
      const res = await getMe();
      setUsuario(res.data);
      return res.data;
    } catch {
      setUsuario(null);
      return null;
    }
  }

  useEffect(() => {
    // Qualquer chamada que volte 401 (sessão expirou no meio do uso) derruba
    // a tela pro login de novo, sem precisar cada página tratar isso na mão.
    setOnUnauthorized(() => setUsuario(null));

    refreshUsuario().finally(() => setVerificando(false));
  }, []);

  async function handleSair() {
    const usuarioAnterior = usuario;
    try {
      await logout();
    } finally {
      const novoUsuario = await refreshUsuario();
      // Se voltou logado como outro usuário (auto-login local), avisa --
      // "Sair" não deixou o terminal deslogado, só voltou pro padrão.
      if (novoUsuario && usuarioAnterior && novoUsuario.username !== usuarioAnterior.username) {
        setAvisoRelogin(novoUsuario.username);
        setTimeout(() => setAvisoRelogin(null), 6000);
      }
    }
  }

  function navRecepcao() {
    setEdicao(null);
    setTela("recepcao");
  }

  function navHistorico() {
    setTela("historico");
  }

  function navPlanilha() {
    setTela("planilha");
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
      {avisoRelogin && (
        <div className="app-aviso-relogin no-print">
          Sessão encerrada — este terminal continua liberado como {avisoRelogin}.
        </div>
      )}
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
          className={`app-nav-btn${tela === "planilha" ? " ativo" : ""}`}
          onClick={navPlanilha}
        >
          Planilha
        </button>
        <button className="app-nav-btn app-nav-sair" onClick={handleSair}>
          Sair ({usuario.username})
        </button>
      </nav>

      {tela === "recepcao" && (
        <Recepcao edicao={edicao} onVoltar={fecharEdicao} />
      )}
      {tela === "historico" && (
        <Historico onNavigate={setTela} onEditar={abrirEdicao} />
      )}
      {tela === "planilha" && <PlanilhaAtendimentos />}
    </>
  );
}

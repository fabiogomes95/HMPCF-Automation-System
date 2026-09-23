import { useEffect, useState } from "react";
import Recepcao from "./pages/Recepcao";
import Historico from "./pages/Historico";
import PlanilhaAtendimentos from "./pages/PlanilhaAtendimentos";
import Auditoria from "./pages/Auditoria";
import Painel from "./pages/Painel";
import GerenciarUsuarios from "./pages/GerenciarUsuarios";
import Correcao from "./pages/Correcao";
import AlterarSenha from "./pages/AlterarSenha";
import Login from "./pages/Login";
import { getMe, logout } from "./services/auth";
import { setOnUnauthorized } from "./services/api";
import "./App.css";

export default function App() {
  const [tela, setTelaState] = useState(() => {
    const salva = sessionStorage.getItem("hmpcf_tela");
    return ["recepcao", "historico", "planilha", "painel", "auditoria", "usuarios", "correcao", "senha"].includes(salva) ? salva : "recepcao";
  });
  const [edicao, setEdicao] = useState(null);
  // Atendimento manual vindo da Correção (TI): A4 completa, atendimento NOVO,
  // com data/hora escolhidas lá. Ver Recepcao `manual`.
  const [manual, setManual] = useState(null);

  function setTela(novaTela) {
    sessionStorage.setItem("hmpcf_tela", novaTela);
    setTelaState(novaTela);
  }

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
    setManual(null);
    setTela("recepcao");
  }

  function navHistorico() {
    setTela("historico");
  }

  function navPlanilha() {
    setTela("planilha");
  }

  function navPainel() {
    setTela("painel");
  }

  function navAuditoria() {
    setTela("auditoria");
  }

  function navUsuarios() {
    setTela("usuarios");
  }

  function navCorrecao() {
    setTela("correcao");
  }

  function navSenha() {
    setTela("senha");
  }

  function abrirEdicao(dadosEdicao) {
    setEdicao(dadosEdicao);
    setTela("recepcao");
  }

  function fecharEdicao() {
    setEdicao(null);
    setTela("historico");
  }

  function abrirManual(dados) {
    setEdicao(null);
    setManual(dados);
    setTela("recepcao");
  }

  function fecharManual() {
    setManual(null);
    setTela("correcao");
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
        {usuario.role === "ti" && (
          <button
            className={`app-nav-btn${tela === "painel" ? " ativo" : ""}`}
            onClick={navPainel}
          >
            Painel
          </button>
        )}
        {usuario.role === "ti" && (
          <button
            className={`app-nav-btn${tela === "auditoria" ? " ativo" : ""}`}
            onClick={navAuditoria}
          >
            Auditoria
          </button>
        )}
        {usuario.role === "ti" && (
          <button
            className={`app-nav-btn${tela === "usuarios" ? " ativo" : ""}`}
            onClick={navUsuarios}
          >
            Usuários
          </button>
        )}
        {usuario.role === "ti" && (
          <button
            className={`app-nav-btn${tela === "correcao" ? " ativo" : ""}`}
            onClick={navCorrecao}
          >
            Correção
          </button>
        )}
        {usuario.role === "ti" && (
          <button
            className={`app-nav-btn${tela === "senha" ? " ativo" : ""}`}
            onClick={navSenha}
          >
            Senha
          </button>
        )}
        <button className="app-nav-btn app-nav-sair" onClick={handleSair}>
          Sair ({usuario.username})
        </button>
      </nav>

      {tela === "recepcao" && (
        <Recepcao
          // key: trocar de modo (normal/edição/manual) remonta a tela do zero
          key={manual ? "manual" : edicao ? `edicao-${edicao.atendimentoId}` : "normal"}
          edicao={edicao}
          manual={manual}
          onVoltar={manual ? fecharManual : fecharEdicao}
        />
      )}
      {tela === "historico" && (
        <Historico onNavigate={setTela} onEditar={abrirEdicao} />
      )}
      {tela === "planilha" && <PlanilhaAtendimentos />}
      {tela === "painel" && usuario.role === "ti" && <Painel />}
      {tela === "auditoria" && usuario.role === "ti" && <Auditoria />}
      {tela === "usuarios" && usuario.role === "ti" && <GerenciarUsuarios />}
      {tela === "correcao" && usuario.role === "ti" && <Correcao onAbrirA4={abrirManual} />}
      {tela === "senha" && <AlterarSenha />}
    </>
  );
}

import { useEffect, useState } from "react";
import Recepcao from "./pages/Recepcao";
import Historico from "./pages/Historico";
import PlanilhaAtendimentos from "./pages/PlanilhaAtendimentos";
import Auditoria from "./pages/Auditoria";
import Painel from "./pages/Painel";
import Entradas from "./pages/Entradas";
import Bpa from "./pages/bpa/Bpa";
import GerenciarUsuarios from "./pages/GerenciarUsuarios";
import Correcao from "./pages/Correcao";
import AlterarSenha from "./pages/AlterarSenha";
import Login from "./pages/Login";
import { getMe, logout } from "./services/auth";
import { setOnUnauthorized } from "./services/api";
import "./App.css";

// Abas do menu e quais papéis enxergam cada uma. O backend também bloqueia
// o que é só da TI (TIUser) -- esconder aqui é conveniência, não segurança.
const TELAS = [
  { id: "recepcao",  rotulo: "Recepção",  papeis: ["recepcao", "ti", "faturamento"] },
  { id: "historico", rotulo: "Histórico", papeis: ["recepcao", "ti", "faturamento"] },
  { id: "planilha",  rotulo: "Planilha",  papeis: ["recepcao", "ti", "faturamento"] },
  { id: "painel",    rotulo: "Painel",    papeis: ["ti"] },
  { id: "auditoria", rotulo: "Auditoria", papeis: ["ti"] },
  { id: "usuarios",  rotulo: "Usuários",  papeis: ["ti"] },
  { id: "correcao",  rotulo: "Correção",  papeis: ["ti", "faturamento"] },
  // BPA fala com o BPA local do notebook (Firebird/BPA Magnético) -- em PC sem BPA mostra "desligado"
  { id: "bpa",       rotulo: "BPA",       papeis: ["faturamento", "ti"] },
  // Em que dias o paciente veio (sistema + planilhas manuais desde 2021) — achar o boletim impresso
  { id: "entradas",  rotulo: "Entradas",  papeis: ["faturamento", "ti"] },
  { id: "senha",     rotulo: "Senha",     papeis: ["ti"] },
];

// Abas que vêm primeiro no menu de cada papel (a 1ª é a que abre ao entrar) --
// o faturamento trabalha no BPA e nas Entradas.
const PRIMEIRAS = { faturamento: ["bpa", "entradas"] };

export default function App() {
  const [tela, setTelaState] = useState(() => {
    const salva = sessionStorage.getItem("hmpcf_tela");
    return TELAS.some((t) => t.id === salva) ? salva : null; // null = primeira aba do papel
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
    return (
      <Login
        onLogin={(u) => {
          sessionStorage.removeItem("hmpcf_tela"); // login novo abre na primeira aba do papel
          setTelaState(null);
          setUsuario(u);
        }}
      />
    );
  }

  // Tela salva de outro login (ex.: TI -> faturamento no mesmo navegador) cai
  // na primeira aba permitida em vez de abrir algo que esse papel não vê.
  const primeiras = PRIMEIRAS[usuario.role] || [];
  const ordem = (t) => (primeiras.includes(t.id) ? primeiras.indexOf(t.id) : primeiras.length);
  const telasPermitidas = TELAS.filter((t) => t.papeis.includes(usuario.role))
    .sort((a, b) => ordem(a) - ordem(b));
  const telaAtual = telasPermitidas.some((t) => t.id === tela) ? tela : telasPermitidas[0]?.id;

  return (
    <>
      {avisoRelogin && (
        <div className="app-aviso-relogin no-print">
          Sessão encerrada — este terminal continua liberado como {avisoRelogin}.
        </div>
      )}
      <nav className="app-nav no-print">
        <span className="app-nav-brand">HMPCF</span>
        {telasPermitidas.map((t) => (
          <button
            key={t.id}
            className={`app-nav-btn${telaAtual === t.id ? " ativo" : ""}`}
            onClick={t.id === "recepcao" ? navRecepcao : () => setTela(t.id)}
          >
            {t.rotulo}
          </button>
        ))}
        <button className="app-nav-btn app-nav-sair" onClick={handleSair}>
          Sair ({usuario.username})
        </button>
      </nav>

      {telaAtual === "recepcao" && (
        <Recepcao
          // key: trocar de modo (normal/edição/manual) remonta a tela do zero
          key={manual ? "manual" : edicao ? `edicao-${edicao.atendimentoId}` : "normal"}
          edicao={edicao}
          manual={manual}
          onVoltar={manual ? fecharManual : fecharEdicao}
        />
      )}
      {telaAtual === "historico" && (
        <Historico onNavigate={setTela} onEditar={abrirEdicao} />
      )}
      {telaAtual === "planilha" && <PlanilhaAtendimentos />}
      {telaAtual === "painel" && <Painel />}
      {telaAtual === "entradas" && <Entradas />}
      {telaAtual === "auditoria" && <Auditoria />}
      {telaAtual === "usuarios" && <GerenciarUsuarios />}
      {telaAtual === "correcao" && (
        <Correcao onAbrirA4={abrirManual} podeExcluir={usuario.role === "ti"} />
      )}
      {telaAtual === "senha" && <AlterarSenha />}
      {telaAtual === "bpa" && <Bpa />}
    </>
  );
}

import { useEffect, useState } from "react";
import { listarUsuarios, criarUsuario, resetarSenhaUsuario, toggleAtivoUsuario, mensagemErro } from "../services/api";
import "./GerenciarUsuarios.css";

const ROLES = ["recepcao", "ti"];

function formatDataHora(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleDateString("pt-BR") + " " + d.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
}

export default function GerenciarUsuarios() {
  const [usuarios, setUsuarios] = useState([]);
  const [loading, setLoading]   = useState(false);
  const [erro, setErro]         = useState("");
  const [msg, setMsg]           = useState("");

  // Formulário novo usuário
  const [novoForm, setNovoForm] = useState(false);
  const [novoUsername, setNovoUsername] = useState("");
  const [novoSenha, setNovoSenha]       = useState("");
  const [novoRole, setNovoRole]         = useState("recepcao");
  const [salvando, setSalvando]         = useState(false);

  // Reset de senha inline
  const [resetId, setResetId]     = useState(null);
  const [resetSenha, setResetSenha] = useState("");

  function aviso(texto) {
    setMsg(texto);
    setTimeout(() => setMsg(""), 3000);
  }

  async function carregar() {
    setLoading(true);
    setErro("");
    try {
      const res = await listarUsuarios();
      setUsuarios(res.data);
    } catch {
      setErro("Não foi possível carregar usuários.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { carregar(); }, []);

  async function handleCriar(e) {
    e.preventDefault();
    if (!novoUsername.trim() || !novoSenha.trim()) return;
    setSalvando(true);
    try {
      await criarUsuario({ username: novoUsername.trim(), password: novoSenha, role: novoRole });
      setNovoForm(false);
      setNovoUsername(""); setNovoSenha(""); setNovoRole("recepcao");
      aviso("Usuário criado.");
      carregar();
    } catch (err) {
      aviso(mensagemErro(err, "Erro ao criar usuário."));
    } finally {
      setSalvando(false);
    }
  }

  async function handleResetSenha(id) {
    if (!resetSenha.trim()) return;
    if (resetSenha.length < 4) return aviso("Senha deve ter pelo menos 4 caracteres.");
    try {
      await resetarSenhaUsuario(id, resetSenha);
      setResetId(null); setResetSenha("");
      aviso("Senha redefinida — sessões abertas desse usuário foram encerradas.");
    } catch (err) {
      aviso(mensagemErro(err, "Erro ao redefinir senha."));
    }
  }

  async function handleToggleAtivo(u) {
    try {
      await toggleAtivoUsuario(u.id, !u.ativo);
      aviso(u.ativo ? "Usuário desativado." : "Usuário ativado.");
      carregar();
    } catch (err) {
      aviso(mensagemErro(err, "Erro ao alterar status."));
    }
  }

  return (
    <div className="gu">
      <div className="gu-header">
        <h2>Usuários</h2>
        {!novoForm && (
          <button className="gu-btn-novo" onClick={() => setNovoForm(true)}>+ Novo usuário</button>
        )}
      </div>

      {msg  && <div className="gu-msg">{msg}</div>}
      {erro && <div className="gu-erro">{erro}</div>}

      {novoForm && (
        <form className="gu-form-novo" onSubmit={handleCriar}>
          <h3>Novo usuário</h3>
          <label>
            Login
            <input value={novoUsername} onChange={e => setNovoUsername(e.target.value)} required autoFocus />
          </label>
          <label>
            Senha
            <input type="password" value={novoSenha} onChange={e => setNovoSenha(e.target.value)} required minLength={4} />
          </label>
          <label>
            Perfil
            <select value={novoRole} onChange={e => setNovoRole(e.target.value)}>
              {ROLES.map(r => <option key={r} value={r}>{r}</option>)}
            </select>
          </label>
          <div className="gu-form-btns">
            <button type="submit" disabled={salvando}>{salvando ? "Salvando…" : "Criar"}</button>
            <button type="button" onClick={() => setNovoForm(false)}>Cancelar</button>
          </div>
        </form>
      )}

      {loading && <div className="gu-loading">Carregando…</div>}

      {!loading && (
        <table className="gu-tabela">
          <thead>
            <tr>
              <th>Login</th>
              <th>Perfil</th>
              <th>Status</th>
              <th>Último acesso</th>
              <th>Ações</th>
            </tr>
          </thead>
          <tbody>
            {usuarios.map(u => (
              <tr key={u.id} className={u.ativo ? "" : "inativo"}>
                <td className="cel-username">{u.username}</td>
                <td>{u.role}</td>
                <td>{u.ativo ? "Ativo" : "Inativo"}</td>
                <td>{formatDataHora(u.last_login_at)}</td>
                <td className="cel-acoes">
                  {resetId === u.id ? (
                    <span className="gu-reset-inline">
                      <input
                        type="password"
                        placeholder="Nova senha"
                        value={resetSenha}
                        onChange={e => setResetSenha(e.target.value)}
                        autoFocus
                      />
                      <button onClick={() => handleResetSenha(u.id)}>Salvar</button>
                      <button onClick={() => { setResetId(null); setResetSenha(""); }}>✕</button>
                    </span>
                  ) : (
                    <>
                      <button onClick={() => { setResetId(u.id); setResetSenha(""); }}>Resetar senha</button>
                      <button onClick={() => handleToggleAtivo(u)}>{u.ativo ? "Desativar" : "Ativar"}</button>
                    </>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

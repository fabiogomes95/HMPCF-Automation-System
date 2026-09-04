import { useState } from "react";
import { login } from "../services/auth";
import "./Login.css";

export default function Login({ onLogin }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [erro, setErro] = useState("");
  const [carregando, setCarregando] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setErro("");
    setCarregando(true);
    try {
      const res = await login(username.trim(), password);
      onLogin(res.data); // { username, role }
    } catch (err) {
      const msg = err.response?.data?.message || "Não foi possível entrar. Tente novamente.";
      setErro(msg);
    } finally {
      setCarregando(false);
    }
  }

  return (
    <div className="login-page">
      <form className="login-card" onSubmit={handleSubmit}>
        <span className="login-brand">HMPCF</span>
        <h1>Recepção</h1>

        <label className="login-field">
          Usuário
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoFocus
            autoComplete="username"
          />
        </label>

        <label className="login-field">
          Senha
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
          />
        </label>

        {erro && <p className="login-erro">{erro}</p>}

        <button type="submit" disabled={carregando || !username || !password}>
          {carregando ? "Entrando…" : "Entrar"}
        </button>
      </form>
    </div>
  );
}

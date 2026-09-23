import { useState } from "react";
import { alterarSenha, mensagemErro } from "../services/api";
import "./AlterarSenha.css";

export default function AlterarSenha() {
  const [senhaAtual, setSenhaAtual]       = useState("");
  const [senhaNova, setSenhaNova]         = useState("");
  const [confirmar, setConfirmar]         = useState("");
  const [salvando, setSalvando]           = useState(false);
  const [msg, setMsg]                     = useState("");
  const [erro, setErro]                   = useState("");

  function aviso(texto, tipo = "ok") {
    if (tipo === "ok") { setMsg(texto); setErro(""); }
    else               { setErro(texto); setMsg(""); }
    setTimeout(() => { setMsg(""); setErro(""); }, 4000);
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!senhaAtual || !senhaNova || !confirmar) return aviso("Preencha todos os campos.", "erro");
    if (senhaNova !== confirmar)                  return aviso("As senhas não coincidem.", "erro");
    if (senhaNova.length < 4)                     return aviso("Senha nova deve ter pelo menos 4 caracteres.", "erro");

    setSalvando(true);
    try {
      await alterarSenha(senhaAtual, senhaNova);
      aviso("Senha alterada com sucesso!");
      setSenhaAtual(""); setSenhaNova(""); setConfirmar("");
    } catch (err) {
      aviso(mensagemErro(err, "Erro ao alterar senha."), "erro");
    } finally {
      setSalvando(false);
    }
  }

  return (
    <div className="as">
      <h2>Alterar senha</h2>
      <form className="as-form" onSubmit={handleSubmit}>
        <label>
          Senha atual
          <input
            type="password"
            value={senhaAtual}
            onChange={e => setSenhaAtual(e.target.value)}
            autoFocus
            required
          />
        </label>
        <label>
          Nova senha
          <input
            type="password"
            value={senhaNova}
            onChange={e => setSenhaNova(e.target.value)}
            required
          />
        </label>
        <label>
          Confirmar nova senha
          <input
            type="password"
            value={confirmar}
            onChange={e => setConfirmar(e.target.value)}
            required
          />
        </label>

        {msg  && <div className="as-msg">{msg}</div>}
        {erro && <div className="as-erro">{erro}</div>}

        <button type="submit" disabled={salvando}>
          {salvando ? "Salvando…" : "Salvar"}
        </button>
      </form>
    </div>
  );
}

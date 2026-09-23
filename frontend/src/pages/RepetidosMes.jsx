import { useState } from "react";
import { buscarPlanilhaMensal, excluirAtendimentoRepetido, mensagemErro } from "../services/api";
import { dataLocalISO, idsRepetidosPorPlantao, isoParaBR, JANELA_REPETIDO_MIN } from "../utils";
import "./RepetidosMes.css";

function mesAtual() {
  return dataLocalISO().slice(0, 7);
}

function formatarDtnasc(dtnasc) {
  if (!dtnasc || dtnasc.length !== 8) return "—";
  return `${dtnasc.slice(6, 8)}/${dtnasc.slice(4, 6)}/${dtnasc.slice(0, 4)}`;
}

function formatarDataHora(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  return (
    d.toLocaleDateString("pt-BR") +
    " " +
    d.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })
  );
}

export default function RepetidosMes() {
  const [mes, setMes]               = useState(mesAtual);
  const [repetidos, setRepetidos]   = useState([]);
  const [buscando, setBuscando]     = useState(false);
  const [pesquisado, setPesquisado] = useState(false);
  const [removendo, setRemovendo]   = useState(new Set());
  const [msg, setMsg]               = useState("");

  function aviso(texto) {
    setMsg(texto);
    setTimeout(() => setMsg(""), 4000);
  }

  async function buscar() {
    const [ano, mesNum] = mes.split("-").map(Number);
    if (!ano || !mesNum) return;
    setBuscando(true);
    setPesquisado(false);
    setRepetidos([]);
    try {
      const res = await buscarPlanilhaMensal(ano, mesNum);
      const items = res.data.items || [];
      const marcados = idsRepetidosPorPlantao(items);
      setRepetidos(
        items
          .filter(i => marcados.has(i.atendimento_id))
          .map(i => ({ ...i, fica: marcados.get(i.atendimento_id) }))
      );
      setPesquisado(true);
    } catch (err) {
      aviso(mensagemErro(err, "Erro ao buscar planilha."));
    } finally {
      setBuscando(false);
    }
  }

  async function remover(id) {
    setRemovendo(prev => new Set(prev).add(id));
    try {
      await excluirAtendimentoRepetido(id);
      setRepetidos(prev => prev.filter(r => r.atendimento_id !== id));
      return true;
    } catch (err) {
      aviso(mensagemErro(err, "Erro ao remover atendimento."));
      return false;
    } finally {
      setRemovendo(prev => { const s = new Set(prev); s.delete(id); return s; });
    }
  }

  async function removerTodos() {
    if (!window.confirm(`Remover todos os ${repetidos.length} atendimentos repetidos deste mês?`)) return;
    let falhas = 0;
    for (const r of [...repetidos]) {
      if (!(await remover(r.atendimento_id))) falhas++;
    }
    aviso(falhas ? `${falhas} atendimento(s) não puderam ser removidos.` : "Todos os repetidos foram removidos.");
  }

  return (
    <div className="rep">
      <h3>Repetidos por mês</h3>
      <p className="rep-sub">
        Mesmo paciente (CPF, SUS ou nome + nascimento) registrado de novo no mesmo plantão logo em seguida
        ou em até {JANELA_REPETIDO_MIN} minutos — normalmente correção de endereço/cidade. Fica o registro
        mais novo; a lista mostra o anterior, que pode ser removido. Retornos horas depois não aparecem aqui.
      </p>

      <div className="rep-filtro">
        <input type="month" value={mes} onChange={e => setMes(e.target.value)} />
        <button onClick={buscar} disabled={buscando}>{buscando ? "Buscando…" : "Buscar"}</button>
      </div>

      {msg && <div className="rep-msg">{msg}</div>}

      {pesquisado && repetidos.length === 0 && (
        <p className="rep-vazio">Nenhum repetido encontrado neste mês.</p>
      )}

      {repetidos.length > 0 && (
        <>
          <div className="rep-topo">
            <span className="rep-contador">{repetidos.length} repetido{repetidos.length !== 1 ? "s" : ""} encontrado{repetidos.length !== 1 ? "s" : ""}</span>
            <button className="rep-btn-todos" onClick={removerTodos}>Remover todos</button>
          </div>

          <table className="rep-tabela">
            <thead>
              <tr>
                <th>Paciente</th>
                <th>Nascimento</th>
                <th>Sai (anterior)</th>
                <th>Fica (mais novo)</th>
                <th>Intervalo</th>
                <th>Plantão</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {repetidos.map(r => (
                <tr key={r.atendimento_id}>
                  <td className="rep-nome">{r.nome || "—"}</td>
                  <td>{formatarDtnasc(r.dtnasc)}</td>
                  <td>{formatarDataHora(r.data_atendimento)} · reg. {r.registro ?? "—"}</td>
                  <td>{formatarDataHora(r.fica.data_atendimento)} · reg. {r.fica.registro ?? "—"}</td>
                  <td>{Math.round((new Date(r.fica.data_atendimento) - new Date(r.data_atendimento)) / 60000)} min</td>
                  <td className="rep-plantao">{r.turno} {isoParaBR(r.dia_referencia)}</td>
                  <td>
                    <button
                      className="rep-btn-remover"
                      onClick={() => remover(r.atendimento_id)}
                      disabled={removendo.has(r.atendimento_id)}
                    >
                      {removendo.has(r.atendimento_id) ? "…" : "Remover"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </div>
  );
}

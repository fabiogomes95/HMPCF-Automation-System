import { useState, useRef } from "react";
import RepetidosMes from "./RepetidosMes";
import {
  buscarPaciente,
  buscarPacientesPorNome,
  listarAtendimentosPorPaciente,
  criarAtendimentoManual,
  editarAtendimentoManual,
  excluirAtendimento,
  mensagemErro,
} from "../services/api";
import { dataLocalISO, horaLocal, isoParaBR } from "../utils";
import { procedencias } from "../components/boletim/ProcedenciaSelector";
import "./Correcao.css";

function hoje() { return dataLocalISO(); }
function hojeHora() { return horaLocal(); }

function SelectProcedencia({ value, onChange }) {
  return (
    <select value={value} onChange={e => onChange(e.target.value)}>
      {procedencias.map(p => (
        <option key={p.v} value={p.v}>{p.label}</option>
      ))}
    </select>
  );
}

// Data/hora do atendimento + botão que abre a tela A4 (cadastro completo).
function PainelNovoPacienteA4({ atd, setAtd, onAbrir, texto }) {
  return (
    <div className="cor-form-novo">
      <label>
        Data do atendimento
        <input type="date" value={atd.data} onChange={e => setAtd(p => ({ ...p, data: e.target.value }))} required />
      </label>
      <label>
        Hora
        <input type="time" value={atd.hora} onChange={e => setAtd(p => ({ ...p, hora: e.target.value }))} required />
      </label>
      <button type="button" onClick={onAbrir}>{texto} →</button>
    </div>
  );
}

function formatarDataHora(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleDateString("pt-BR") + " " + d.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
}

const VAZIO_ATD = () => ({ data: hoje(), hora: hojeHora(), registro: "", procedencia: "NORMAL" });

// podeExcluir: só a TI. Faturamento adiciona e edita, mas não exclui (o backend
// também recusa: DELETE /ti/atendimentos exige perfil TI).
export default function Correcao({ onAbrirA4 = null, podeExcluir = false }) {
  // ── Modo de busca ────────────────────────────────────────────────────────────
  const [modoBusca, setModoBusca]           = useState("doc"); // "doc" | "nome"

  // Busca por documento (CPF/CNS)
  const [docBusca, setDocBusca]             = useState("");

  // Busca por nome
  const [nomeBusca, setNomeBusca]           = useState("");
  const [resultadosNome, setResultadosNome] = useState([]);
  const [buscandoNome, setBuscandoNome]     = useState(false);
  const debounceNome                        = useRef(null);

  // Paciente selecionado / estado geral
  const [paciente, setPaciente]             = useState(null);
  const [naoEncontrado, setNaoEncontrado]   = useState(false);
  const [buscando, setBuscando]             = useState(false);
  const [erroBusca, setErroBusca]           = useState("");

  const [atendimentos, setAtendimentos]     = useState([]);

  // Formulário de novo atendimento (paciente existente)
  const [novoAtd, setNovoAtd]               = useState(VAZIO_ATD());
  const [criando, setCriando]               = useState(false);

  // Paciente novo: data/hora do atendimento que vão pra tela A4 (ver abrirA4)
  const [atdA4, setAtdA4]                   = useState(VAZIO_ATD());

  // Edição inline de atendimento
  const [editId, setEditId]                 = useState(null);
  const [editData, setEditData]             = useState("");
  const [editHora, setEditHora]             = useState("");
  const [editRegistro, setEditRegistro]     = useState("");
  const [salvandoEdit, setSalvandoEdit]     = useState(false);

  const [msg, setMsg]   = useState("");
  const [erro, setErro] = useState("");

  function aviso(texto, tipo = "ok") {
    if (tipo === "ok") { setMsg(texto); setErro(""); }
    else               { setErro(texto); setMsg(""); }
    setTimeout(() => { setMsg(""); setErro(""); }, 4000);
  }

  function limparFormNovoPaciente() {
    setAtdA4(VAZIO_ATD());
  }

  // Paciente novo é cadastrado na própria tela A4 (formulário completo, o
  // mesmo da recepção), num atendimento novo com a data/hora escolhidas aqui.
  function abrirA4(documento) {
    if (!onAbrirA4) return;
    if (!atdA4.data || !atdA4.hora) return aviso("Informe data e hora do atendimento.", "erro");
    onAbrirA4({ documento: documento || "", data: isoParaBR(atdA4.data), hora: atdA4.hora });
  }

  function limparResultado() {
    setPaciente(null);
    setNaoEncontrado(false);
    setAtendimentos([]);
    setErroBusca("");
    setResultadosNome([]);
  }

  function trocarModo(modo) {
    setModoBusca(modo);
    limparResultado();
    setDocBusca("");
    setNomeBusca("");
  }

  async function recarregarAtendimentos(pacienteId) {
    try {
      const res = await listarAtendimentosPorPaciente(pacienteId, 1, 50);
      setAtendimentos(res.data.items || []);
    } catch { /* ignora */ }
  }

  // ── Busca por documento ──────────────────────────────────────────────────────
  async function buscarPorDoc(e) {
    e.preventDefault();
    const doc = docBusca.trim();
    if (!doc) return;
    setBuscando(true);
    limparResultado();
    try {
      const res = await buscarPaciente(doc);
      setPaciente(res.data);
      await recarregarAtendimentos(res.data.id);
    } catch (err) {
      if (err.response?.status === 404) {
        setNaoEncontrado(true);
        limparFormNovoPaciente();
      } else {
        setErroBusca(mensagemErro(err, "Erro ao buscar paciente."));
      }
    } finally {
      setBuscando(false);
    }
  }

  // ── Busca por nome (debounce) ────────────────────────────────────────────────
  function handleNomeBuscaChange(e) {
    const v = e.target.value;
    setNomeBusca(v);
    setResultadosNome([]);
    setPaciente(null);
    setNaoEncontrado(false);
    setAtendimentos([]);
    if (debounceNome.current) clearTimeout(debounceNome.current);
    if (v.trim().length < 3) return;
    debounceNome.current = setTimeout(async () => {
      setBuscandoNome(true);
      try {
        // Busca em todos os pacientes, inclusive os que ainda não têm atendimento.
        const res = await buscarPacientesPorNome(v.trim(), 15);
        setResultadosNome(res.data.items || []);
      } catch {
        setResultadosNome([]);
      } finally {
        setBuscandoNome(false);
      }
    }, 400);
  }

  async function selecionarDaLista(item) {
    setNomeBusca(item.nome || "");
    setResultadosNome([]);
    setBuscando(true);
    try {
      setPaciente(item);
      await recarregarAtendimentos(item.id);
    } finally {
      setBuscando(false);
    }
  }

  // ── Criar atendimento (paciente existente) ───────────────────────────────────
  async function handleCriarAtendimento(e) {
    e.preventDefault();
    if (!paciente) return;
    setCriando(true);
    try {
      await criarAtendimentoManual({
        paciente_id: paciente.id,
        data:        novoAtd.data,
        hora:        novoAtd.hora,
        registro:    novoAtd.registro,
        procedencia: novoAtd.procedencia,
      });
      aviso("Atendimento criado.");
      setNovoAtd(VAZIO_ATD());
      await recarregarAtendimentos(paciente.id);
    } catch (err) {
      aviso(mensagemErro(err, "Erro ao criar atendimento."), "erro");
    } finally {
      setCriando(false);
    }
  }

  // ── Edição / exclusão de atendimento ─────────────────────────────────────────
  function iniciarEdicao(at) {
    const d = new Date(at.data_atendimento);
    setEditId(at.id);
    setEditData(dataLocalISO(d));
    setEditHora(horaLocal(d));
    setEditRegistro(at.registro != null ? String(at.registro) : "");
  }

  async function handleExcluirAtendimento(at) {
    if (!window.confirm(`Excluir atendimento de ${formatarDataHora(at.data_atendimento)}? Esta ação não pode ser desfeita.`)) return;
    try {
      await excluirAtendimento(at.id);
      aviso("Atendimento excluído.");
      await recarregarAtendimentos(paciente.id);
    } catch (err) {
      aviso(mensagemErro(err, "Erro ao excluir."), "erro");
    }
  }

  async function handleSalvarEdicao(id) {
    setSalvandoEdit(true);
    try {
      await editarAtendimentoManual(id, { data: editData, hora: editHora, registro: editRegistro });
      aviso("Atendimento atualizado.");
      setEditId(null);
      await recarregarAtendimentos(paciente.id);
    } catch (err) {
      aviso(mensagemErro(err, "Erro ao editar."), "erro");
    } finally {
      setSalvandoEdit(false);
    }
  }

  const nomePaciente = paciente?.nome_pcnte || paciente?.nome || "";

  return (
    <div className="cor">
      <h2>Correção de Atendimentos</h2>

      {msg  && <div className="cor-msg">{msg}</div>}
      {erro && <div className="cor-erro">{erro}</div>}

      {/* ── Seletor de modo ── */}
      <div className="cor-modo">
        <button
          className={modoBusca === "doc" ? "ativo" : ""}
          onClick={() => trocarModo("doc")}
        >CPF / CNS</button>
        <button
          className={modoBusca === "nome" ? "ativo" : ""}
          onClick={() => trocarModo("nome")}
        >Nome</button>
      </div>

      {/* ── Busca por documento ── */}
      {modoBusca === "doc" && (
        <form className="cor-busca" onSubmit={buscarPorDoc}>
          <input
            placeholder="CPF (11 dígitos) ou CNS (15 dígitos)"
            value={docBusca}
            onChange={e => setDocBusca(e.target.value)}
            autoFocus
          />
          <button type="submit" disabled={buscando}>{buscando ? "Buscando…" : "Buscar"}</button>
        </form>
      )}

      {/* ── Busca por nome ── */}
      {modoBusca === "nome" && (
        <div className="cor-busca-nome">
          <input
            placeholder="Digite o nome (mín. 3 letras)"
            value={nomeBusca}
            onChange={handleNomeBuscaChange}
            autoFocus
          />
          {buscandoNome && <span className="cor-loading-nome">Buscando…</span>}
          {resultadosNome.length > 0 && (
            <ul className="cor-lista-nome">
              {resultadosNome.map(p => (
                <li key={p.id} onClick={() => selecionarDaLista(p)}>
                  <strong>{p.nome || p.nome_pcnte}</strong>
                  <span>{p.num_cpf ? ` CPF: ${p.num_cpf}` : ""}{p.cns ? ` CNS: ${p.cns}` : ""}</span>
                </li>
              ))}
            </ul>
          )}
          {!buscandoNome && nomeBusca.trim().length >= 3 && resultadosNome.length === 0 && !paciente && (
            <div className="cor-novo-paciente">
              <p className="cor-vazio">Nenhum paciente encontrado.</p>
              <PainelNovoPacienteA4
                atd={atdA4}
                setAtd={setAtdA4}
                onAbrir={() => abrirA4("")}
                texto="Cadastrar paciente novo na tela A4"
              />
            </div>
          )}
        </div>
      )}

      {erroBusca && <div className="cor-erro">{erroBusca}</div>}

      {/* ── Paciente selecionado ── */}
      {paciente && (
        <div className="cor-paciente">
          <strong>{nomePaciente}</strong>
          <span className="cor-paciente-doc">
            CPF: {paciente.num_cpf || "—"} | CNS: {paciente.cns || "—"}
          </span>
        </div>
      )}

      {/* ── Criar atendimento (paciente existente) ── */}
      {paciente && (
        <details className="cor-novo-detalhes" open>
          <summary>Criar novo atendimento</summary>
          <form className="cor-form-novo" onSubmit={handleCriarAtendimento}>
            <label>
              Data
              <input type="date" value={novoAtd.data} onChange={e => setNovoAtd(p => ({ ...p, data: e.target.value }))} required />
            </label>
            <label>
              Hora
              <input type="time" value={novoAtd.hora} onChange={e => setNovoAtd(p => ({ ...p, hora: e.target.value }))} required />
            </label>
            <label>
              Nº registro
              <input type="number" min="1" value={novoAtd.registro} onChange={e => setNovoAtd(p => ({ ...p, registro: e.target.value }))} placeholder="Opcional" />
            </label>
            <label>
              Procedência
              <SelectProcedencia value={novoAtd.procedencia} onChange={v => setNovoAtd(p => ({ ...p, procedencia: v }))} />
            </label>
            <button type="submit" disabled={criando}>{criando ? "Salvando…" : "Criar atendimento"}</button>
          </form>
        </details>
      )}

      {/* ── Novo paciente (não encontrado via CPF/CNS) → tela A4 completa ── */}
      {naoEncontrado && (
        <div className="cor-novo-paciente">
          <div className="cor-nao-encontrado">
            Paciente não encontrado para <strong>{docBusca}</strong>.
          </div>
          <PainelNovoPacienteA4
            atd={atdA4}
            setAtd={setAtdA4}
            onAbrir={() => abrirA4(docBusca)}
            texto="Cadastrar na tela A4"
          />
        </div>
      )}

      {/* ── Atendimentos existentes ── */}
      {paciente && atendimentos.length > 0 && (
        <div className="cor-atendimentos">
          <h3>Atendimentos registrados</h3>
          <table className="cor-tabela">
            <thead>
              <tr>
                <th>Data/Hora</th>
                <th>Registro</th>
                <th>Procedência</th>
                <th>Ações</th>
              </tr>
            </thead>
            <tbody>
              {atendimentos.map(at => (
                <tr key={at.id}>
                  {editId === at.id ? (
                    <>
                      <td className="cel-edit-dt">
                        <input type="date" value={editData} onChange={e => setEditData(e.target.value)} />
                        <input type="time" value={editHora} onChange={e => setEditHora(e.target.value)} />
                      </td>
                      <td>
                        <input type="number" min="1" value={editRegistro} onChange={e => setEditRegistro(e.target.value)} style={{ width: "80px" }} />
                      </td>
                      <td>—</td>
                      <td>
                        <button onClick={() => handleSalvarEdicao(at.id)} disabled={salvandoEdit}>{salvandoEdit ? "…" : "Salvar"}</button>
                        <button onClick={() => setEditId(null)}>Cancelar</button>
                      </td>
                    </>
                  ) : (
                    <>
                      <td>{formatarDataHora(at.data_atendimento)}</td>
                      <td>{at.registro ?? "—"}</td>
                      <td>{at.procedencia || "—"}</td>
                      <td>
                        <button onClick={() => iniciarEdicao(at)}>Editar</button>
                        {podeExcluir && (
                          <button className="btn-excluir" onClick={() => handleExcluirAtendimento(at)}>Excluir</button>
                        )}
                      </td>
                    </>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {paciente && atendimentos.length === 0 && (
        <p className="cor-vazio">Nenhum atendimento registrado para este paciente.</p>
      )}

      {podeExcluir && <RepetidosMes />}
    </div>
  );
}

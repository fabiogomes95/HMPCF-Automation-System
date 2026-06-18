import { useEffect, useRef, useState } from "react";
import {
  bpaListarProfissionais,
  bpaBuscarPacientes,
  bpaCriarCabecalho,
  bpaAdicionarDocumento,
} from "../../services/api";
import { formatDateBR, formatCNS, formatCPF, nomeArquivoLote } from "../../utils";

const ROTULO_CATEGORIA = { medico: "Médico", enfermeiro: "Enfermeiro" };

export default function Digitacao() {
  const [profissionais, setProfissionais] = useState([]);
  const [cnsSelecionado, setCnsSelecionado] = useState("");
  const [data, setData] = useState("");
  const [confirmado, setConfirmado] = useState(false);
  const [arquivoAtual, setArquivoAtual] = useState("");
  const [termo, setTermo] = useState("");
  const [resultados, setResultados] = useState([]);
  const [msg, setMsg] = useState(null);
  const [indiceFoco, setIndiceFoco] = useState(-1);
  const inputRef = useRef(null);
  const itemRefs = useRef([]);

  useEffect(() => {
    bpaListarProfissionais()
      .then((res) => setProfissionais(res.data))
      .catch(() => setMsg({ tipo: "erro", texto: "Não foi possível carregar a lista de profissionais." }));
  }, []);

  const profissionalAtual = profissionais.find((p) => p.cns === cnsSelecionado);

  async function confirmarCabecalho() {
    if (!cnsSelecionado) return setMsg({ tipo: "erro", texto: "Selecione o profissional!" });
    if (!data || data.length < 10) return setMsg({ tipo: "erro", texto: "Digite a data completa (DD/MM/AAAA)!" });

    const arquivo = nomeArquivoLote(data);
    try {
      await bpaCriarCabecalho(arquivo, profissionalAtual.nome, data);
      setArquivoAtual(arquivo);
      setConfirmado(true);
      setMsg({ tipo: "ok", texto: `Gravando em ${arquivo} — ${profissionalAtual.nome}` });
      inputRef.current?.focus();
    } catch (e) {
      setMsg({ tipo: "erro", texto: `Erro ao criar cabeçalho: ${e.response?.data?.detail || e.message}` });
    }
  }

  async function pesquisar(valor) {
    setTermo(valor);
    setIndiceFoco(-1);
    if (valor.trim().length < 3) {
      setResultados([]);
      return;
    }
    try {
      const res = await bpaBuscarPacientes(valor.trim());
      setResultados(res.data);
    } catch {
      setResultados([]);
    }
  }

  async function gravar(paciente) {
    if (!confirmado) return setMsg({ tipo: "erro", texto: "Confirme o profissional e a data primeiro!" });
    const documento = paciente.sus || paciente.cpf;
    if (!documento) return setMsg({ tipo: "erro", texto: "Paciente sem documento válido!" });

    try {
      await bpaAdicionarDocumento(arquivoAtual, documento);
      setMsg({ tipo: "ok", texto: `Gravado: ${paciente.nome}` });
      setTermo("");
      setResultados([]);
      inputRef.current?.focus();
    } catch (e) {
      setMsg({ tipo: "erro", texto: `Erro ao gravar: ${e.response?.data?.detail || e.message}` });
    }
  }

  function aoApertarTeclaInput(e) {
    if ((e.key === "Tab" || e.key === "ArrowDown") && resultados.length > 0) {
      e.preventDefault();
      setIndiceFoco(0);
      itemRefs.current[0]?.focus();
    }
  }

  function aoApertarTeclaItem(e, idx) {
    if (e.key === "Tab" || e.key === "ArrowDown") {
      e.preventDefault();
      const proximo = Math.min(idx + 1, resultados.length - 1);
      setIndiceFoco(proximo);
      itemRefs.current[proximo]?.focus();
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      if (idx === 0) {
        inputRef.current?.focus();
      } else {
        setIndiceFoco(idx - 1);
        itemRefs.current[idx - 1]?.focus();
      }
    } else if (e.key === "Enter") {
      e.preventDefault();
      gravar(resultados[idx]);
    }
  }

  return (
    <div className="bpa-card">
      <p className="bpa-card-titulo">✍️ Digitação — registrar atendimentos de um médico</p>

      <div className="bpa-row" style={{ marginBottom: 14 }}>
        <div className="bpa-field">
          <label>Data do atendimento</label>
          <input
            className="bpa-input"
            placeholder="DD/MM/AAAA"
            value={data}
            maxLength={10}
            onChange={(e) => setData(formatDateBR(e.target.value))}
          />
        </div>
        <div className="bpa-field" style={{ flex: 1, minWidth: 280 }}>
          <label>Profissional (direto do Firebird, por CBO)</label>
          <select
            className="bpa-select"
            style={{ width: "100%" }}
            value={cnsSelecionado}
            onChange={(e) => setCnsSelecionado(e.target.value)}
          >
            <option value="">Selecione…</option>
            {profissionais.map((p) => (
              <option key={p.cns} value={p.cns}>
                {p.nome}
                {p.categorias.length > 0 ? ` — ${p.categorias.map((c) => ROTULO_CATEGORIA[c]).join("/")}` : " — sem CBO cadastrado"}
              </option>
            ))}
          </select>
        </div>
        <button className="bpa-btn bpa-btn-primario" onClick={confirmarCabecalho}>
          ✅ Confirmar
        </button>
      </div>

      {msg && (
        <p className="bpa-status-msg" style={{ color: msg.tipo === "ok" ? "#166534" : "#991b1b" }}>
          {msg.texto}
        </p>
      )}

      <div className="bpa-field" style={{ marginBottom: 6 }}>
        <input
          ref={inputRef}
          className="bpa-input"
          style={{ width: "100%", fontSize: "1rem", padding: "10px 14px" }}
          placeholder="🔍 Pesquisar paciente por nome, CPF ou SUS…"
          value={termo}
          onChange={(e) => pesquisar(e.target.value)}
          onKeyDown={aoApertarTeclaInput}
        />
      </div>

      <div className="bpa-busca-resultados">
        {resultados.length === 0 && termo.trim().length >= 3 && (
          <div className="bpa-vazio">Nenhum paciente encontrado.</div>
        )}
        {resultados.map((p, idx) => {
          const susFmt = p.sus && p.sus.length === 15 ? formatCNS(p.sus) : "";
          const cpfFmt = p.cpf && p.cpf.length === 11 ? formatCPF(p.cpf) : "";
          return (
            <div
              key={p.sus || p.cpf || idx}
              ref={(el) => (itemRefs.current[idx] = el)}
              className="bpa-resultado-item"
              tabIndex={0}
              onClick={() => gravar(p)}
              onKeyDown={(e) => aoApertarTeclaItem(e, idx)}
            >
              <div>
                <div className="bpa-resultado-nome">{p.nome}</div>
                <div className="bpa-resultado-info">
                  DN: {p.dtnasc || "—"} · SUS: {susFmt || "—"} · CPF: {cpfFmt || "—"}
                </div>
              </div>
              <span className="bpa-resultado-tag">GRAVAR</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

import { useState, useRef, useEffect, useCallback } from "react";
import {
  buscarPaciente,
  criarPaciente,
  atualizarPaciente,
  criarAtendimento,
  iniciarSessao,
  pingSessao,
} from "../services/api";
import {
  apenasNumeros,
  formatCPF,
  formatCNS,
  formatDateBR,
  parseDateToDB,
  parseDateFromDB,
  formatTelefone,
  getRacas,
  calcularIdade,
  formatarIdade,
  validarCPF,
  validarCNS,
  formatRegistro,
  calcularTurno,
  horaAtual,
  dataAtual,
} from "../utils";
import BoletimA4 from "../components/boletim/BoletimA4";
import ProcedenciaSelector from "../components/boletim/ProcedenciaSelector";
import "./Recepcao.css";

const vazio = {
  nome: "",
  nome_social: "",
  cns: "",
  num_cpf: "",
  dtnasc: "",
  sexo: "",
  raca: "03",
  maepcn: "",
  logpcn: "",
  numpcn: "",
  bairro_pcnte: "",
  ceppcn: "",
  cidade: "EXTREMOZ",
  estado: "RN",
  telefone: "",
  nacionalidade: "",
  estado_civil: "",
  ocupacao: "",
  responsavel: "",
};

const camposTexto = [
  "nome", "nome_social", "maepcn", "logpcn",
  "numpcn", "bairro_pcnte", "cidade", "estado",
  "nacionalidade", "estado_civil", "ocupacao", "responsavel",
];

function uc(v) {
  return v ? v.toUpperCase() : v;
}

export default function Recepcao() {
  const [form, setForm] = useState({ ...vazio });
  const [pacienteId, setPacienteId] = useState(null);
  const [msg, setMsg] = useState("");
  const [idade, setIdade] = useState("");
  const [loading, setLoading] = useState(false);
  const [erroCpf, setErroCpf] = useState("");
  const [erroCns, setErroCns] = useState("");
  const [procedencia, setProcedencia] = useState("NORMAL");
  const [atdInfo, setAtdInfo] = useState({ data: "", hora: "", registro: "" });
  const debounceRef = useRef(null);
  const pacienteEncontradoRef = useRef(false);
  const cpfRef = useRef(null);
  const nomeRef = useRef(null);
  const sexoRef = useRef(null);
  const racas = getRacas();
  const ultimoRegistroRef = useRef(null);
  const ultimoTurnoRef = useRef(null);

  function sugerirAtdInfo() {
    const data = dataAtual();
    const hora = horaAtual();
    const turno = calcularTurno(hora);
    let registro = 1;
    if (turno === ultimoTurnoRef.current && ultimoRegistroRef.current != null) {
      registro = ultimoRegistroRef.current + 1;
    }
    setAtdInfo({ data, hora, registro: formatRegistro(registro) });
  }

  useEffect(() => {
    cpfRef.current?.focus();
    const nome = localStorage.getItem("terminal_nome");
    if (nome) {
      pingSessao(nome);
    } else {
      const id =
        "RECEPCAO_" +
        Math.random().toString(36).slice(2, 6).toUpperCase();
      localStorage.setItem("terminal_nome", id);
      iniciarSessao(id, window.location.hostname);
    }
    ultimoRegistroRef.current = null;
    ultimoTurnoRef.current = null;
    sugerirAtdInfo();
  }, []);

  useEffect(() => {
    const interval = setInterval(() => {
      const nome = localStorage.getItem("terminal_nome");
      if (nome) pingSessao(nome);
    }, 120000);
    return () => clearInterval(interval);
  }, []);

  function calcIdade(dtnasc) {
    const obj = calcularIdade(dtnasc);
    setIdade(obj ? formatarIdade(obj) : "");
  }

  const autoBusca = useCallback(async (raw) => {
    if (raw.length !== 11 && raw.length !== 15) return;
    setLoading(true);
    setMsg("");
    try {
      const res = await buscarPaciente(raw);
      if (res.data) {
        pacienteEncontradoRef.current = true;
        const p = res.data;
        const dtnasc = parseDateFromDB(p.dtnasc);
        setForm({
          nome: p.nome || "",
          nome_social: p.nome_social || "",
          cns: p.cns || "",
          num_cpf: p.num_cpf || "",
          dtnasc,
          sexo: p.sexo || "",
          raca: p.raca || "03",
          maepcn: p.maepcn || "",
          logpcn: p.logpcn || "",
          numpcn: p.numpcn || "",
          bairro_pcnte: p.bairro_pcnte || "",
          ceppcn: p.ceppcn || "",
          cidade: p.cidade || "EXTREMOZ",
          estado: p.estado || "RN",
          telefone: formatTelefone(p.telefone),
          nacionalidade: p.nacionalidade || "",
          estado_civil: p.estado_civil || "",
          ocupacao: p.ocupacao || "",
          responsavel: p.responsavel || "",
        });
        setPacienteId(p.id);
        setErroCpf("");
        setErroCns("");
        calcIdade(dtnasc);
        setMsg("✓ Paciente encontrado");
      } else if (!pacienteEncontradoRef.current) {
        setMsg("+ Novo paciente — preencha os dados");
      }
    } catch {
      setMsg("Erro ao buscar paciente");
    } finally {
      setLoading(false);
    }
  }, []);

  function handleCPFChange(e) {
    const raw = apenasNumeros(e.target.value).slice(0, 11);
    setForm((prev) => ({ ...prev, num_cpf: raw }));
    setErroCpf(raw.length === 11 && !validarCPF(raw) ? "CPF inválido" : "");
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (raw.length === 11) {
      debounceRef.current = setTimeout(() => autoBusca(raw), 300);
    }
  }

  function handleCNSChange(e) {
    const raw = apenasNumeros(e.target.value).slice(0, 15);
    setForm((prev) => ({ ...prev, cns: raw }));
    setErroCns(raw.length === 15 && !validarCNS(raw) ? "CNS inválido" : "");
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (raw.length === 15) {
      debounceRef.current = setTimeout(() => autoBusca(raw), 300);
    }
  }

  function handleChange(e) {
    const { name, value } = e.target;
    if (camposTexto.includes(name)) {
      setForm((prev) => ({ ...prev, [name]: uc(value) }));
    } else {
      setForm((prev) => ({ ...prev, [name]: value }));
    }
  }

  function handleDtnascChange(e) {
    const raw = e.target.value;
    const fmt = formatDateBR(raw);
    setForm((prev) => ({ ...prev, dtnasc: fmt }));
    calcIdade(fmt);
  }

  function handleTelChange(e) {
    const raw = e.target.value;
    const fmt = formatTelefone(raw);
    setForm((prev) => ({ ...prev, telefone: fmt }));
  }

  function handleRacaChange(cod) {
    setForm((prev) => ({ ...prev, raca: cod }));
  }

  function handleSexoChange(v) {
    setForm((prev) => ({ ...prev, sexo: v }));
  }

  function handleProcedenciaChange(v) {
    setProcedencia(v);
  }

  function handleAtdDataChange(e) {
    const raw = formatDateBR(e.target.value);
    setAtdInfo((prev) => ({ ...prev, data: raw }));
  }

  function handleAtdHoraChange(e) {
    let v = e.target.value.replace(/[^0-9:]/g, "").slice(0, 5);
    if (v.length === 2 && !v.includes(":")) v += ":";
    setAtdInfo((prev) => ({ ...prev, hora: v }));
  }

  function handleAtdRegistroChange(e) {
    const v = e.target.value.replace(/\D/g, "").slice(0, 4);
    const num = parseInt(v, 10);
    if (!isNaN(num)) ultimoRegistroRef.current = num;
    setAtdInfo((prev) => ({ ...prev, registro: v }));
  }

  function prepararDados() {
    const dados = { ...form };
    dados.num_cpf = apenasNumeros(dados.num_cpf);
    dados.cns = apenasNumeros(dados.cns);
    dados.telefone = apenasNumeros(dados.telefone);
    if (dados.dtnasc) dados.dtnasc = parseDateToDB(dados.dtnasc);
    for (const k of camposTexto) {
      if (dados[k]) dados[k] = uc(dados[k]);
    }
    return dados;
  }

  function validar() {
    const erros = [];
    if (!form.nome.trim()) {
      erros.push({ campo: "nome", msg: "Informe o nome do paciente." });
    }
    if (!form.sexo) {
      erros.push({ campo: "sexo", msg: "Selecione o sexo do paciente." });
    }
    const cpfOk = form.num_cpf && validarCPF(form.num_cpf);
    const cnsOk = form.cns && validarCNS(form.cns);
    if (!cpfOk && !cnsOk) {
      erros.push({ campo: "num_cpf", msg: "Informe um CPF ou CNS válido." });
    }
    return erros;
  }

  function focusErro(erros) {
    const refs = { nome: nomeRef, sexo: sexoRef, num_cpf: cpfRef };
    const alvo = refs[erros[0].campo];
    if (alvo?.current) {
      if (alvo.current.focus) alvo.current.focus();
      else if (alvo.current.querySelector) {
        const el = alvo.current.querySelector("input, select, button");
        el?.focus();
      }
    }
  }

  async function handleAtendimento() {
    const erros = validar();
    if (erros.length > 0) {
      setMsg(erros[0].msg);
      focusErro(erros);
      return;
    }
    setLoading(true);
    setMsg("");
    try {
      const dados = prepararDados();
      let id = pacienteId;
      if (id) {
        await atualizarPaciente(id, dados);
      } else {
        const res = await criarPaciente(dados);
        id = res.data.id;
        setPacienteId(id);
      }
      const data = atdInfo.data;
      const hora = atdInfo.hora;
      await criarAtendimento({
        paciente_id: id,
        data_atendimento: data,
        hora_atendimento: hora,
        registro: atdInfo.registro,
        procedencia,
      });
      const turno = calcularTurno(hora);
      const regNum = parseInt(atdInfo.registro, 10);
      if (!isNaN(regNum)) {
        ultimoRegistroRef.current = regNum;
        ultimoTurnoRef.current = turno;
      }
      setMsg("✓ Atendimento registrado!");
    } catch (err) {
      const detail = err.response?.data?.detail || "Erro ao registrar";
      setMsg(typeof detail === "string" ? detail : JSON.stringify(detail));
    } finally {
      setLoading(false);
    }
  }

  function handleLimpar() {
    setForm({ ...vazio });
    setPacienteId(null);
    setMsg("");
    setIdade("");
    setErroCpf("");
    setErroCns("");
    setProcedencia("NORMAL");
    pacienteEncontradoRef.current = false;
    sugerirAtdInfo();
    cpfRef.current?.focus();
  }

  function handleImprimir() {
    window.print();
  }

  const racaNome = racas.find((r) => r.cod === form.raca)?.label || "";
  const pacienteBoletim = {
    nome: form.nome,
    nome_social: form.nome_social,
    num_cpf: formatCPF(form.num_cpf),
    cns: formatCNS(form.cns),
    dtnasc: form.dtnasc,
    naturalidade: form.nacionalidade,
    sexoNome:
      form.sexo === "M" ? "MASCULINO" : form.sexo === "F" ? "FEMININO" : "",
    racaNome,
    estadoCivil: form.estado_civil,
    ocupacao: form.ocupacao,
    maepcn: form.maepcn,
    responsavel: form.responsavel,
    telefone: form.telefone,
    logpcn: form.logpcn,
    numpcn: form.numpcn,
    bairro_pcnte: form.bairro_pcnte,
    cidade: form.cidade,
    estado: form.estado,
  };

  return (
    <div className="recepcao">
      <header className="recepcao-header no-print">
        <h1>HMPCF — Recepção</h1>
        <div className="header-right">
          {pacienteId && <span className="badge-ok">✓ Paciente</span>}
          {loading && <span className="badge-loading">⏳</span>}
        </div>
      </header>

      {msg && (
        <div
          className={`recepcao-msg no-print ${
            msg.startsWith("✓") ? "msg-sucesso" : "msg-erro"
          }`}
        >
          {msg}
        </div>
      )}

      <div className="no-print">
        <ProcedenciaSelector
          value={procedencia}
          onChange={handleProcedenciaChange}
        />
      </div>

      <div className="recepcao-form no-print">
        <div className="form-grid">
          <div className="campo">
            <label>CPF</label>
            <input
              ref={cpfRef}
              type="text"
              name="num_cpf"
              value={formatCPF(form.num_cpf)}
              onChange={handleCPFChange}
              placeholder="000.000.000-00"
              maxLength={14}
              className={erroCpf ? "campo-invalido" : ""}
              autoFocus
            />
            {erroCpf && <span className="texto-erro-inline">{erroCpf}</span>}
          </div>

          <div className="campo">
            <label>CNS</label>
            <input
              type="text"
              name="cns"
              value={formatCNS(form.cns)}
              onChange={handleCNSChange}
              placeholder="000 0000 0000 0000"
              maxLength={18}
              className={erroCns ? "campo-invalido" : ""}
            />
            {erroCns && <span className="texto-erro-inline">{erroCns}</span>}
          </div>

          <div className="campo" style={{ gridColumn: "1 / -1" }}>
            <label>Nome</label>
            <input
              ref={nomeRef}
              type="text"
              name="nome"
              value={form.nome}
              onChange={handleChange}
              placeholder="Nome completo"
            />
          </div>

          <div className="campo">
            <label>Nome Social</label>
            <input
              type="text"
              name="nome_social"
              value={form.nome_social}
              onChange={handleChange}
            />
          </div>

          <div className="campo">
            <label>Data Nascimento</label>
            <input
              type="text"
              name="dtnasc"
              value={form.dtnasc}
              onChange={handleDtnascChange}
              placeholder="DD/MM/AAAA"
              maxLength={10}
            />
          </div>

          <div className="campo">
            <label>Idade</label>
            <input
              type="text"
              className="campo-idade"
              value={idade}
              readOnly
              placeholder="—"
              tabIndex={-1}
            />
          </div>

          <div className="campo">
            <label>Telefone</label>
            <input
              type="text"
              name="telefone"
              value={form.telefone}
              onChange={handleTelChange}
              placeholder="(84) 99999-9999"
              maxLength={15}
            />
          </div>

          <div className="campo">
            <label>Estado Civil</label>
            <input
              type="text"
              name="estado_civil"
              value={form.estado_civil}
              onChange={handleChange}
            />
          </div>

          <div className="campo" style={{ gridColumn: "1 / -1" }}>
            <label>Raça / Cor</label>
            <div className="opcao-group">
              {racas.map((r) => (
                <label
                  key={r.cod}
                  className={`opcao-btn ${form.raca === r.cod ? "ativo" : ""}`}
                >
                  <input
                    type="radio"
                    name="raca"
                    value={r.cod}
                    checked={form.raca === r.cod}
                    onChange={() => handleRacaChange(r.cod)}
                  />
                  {r.cod} - {r.label}
                </label>
              ))}
            </div>
          </div>

          <div className="campo" style={{ gridColumn: "1 / -1" }}>
            <label>Sexo</label>
            <div className="opcao-group" ref={sexoRef}>
              {[
                { v: "M", label: "MASCULINO" },
                { v: "F", label: "FEMININO" },
              ].map((opt) => (
                <label
                  key={opt.v}
                  className={`opcao-btn ${form.sexo === opt.v ? "ativo" : ""}`}
                >
                  <input
                    type="radio"
                    name="sexo"
                    value={opt.v}
                    checked={form.sexo === opt.v}
                    onChange={() => handleSexoChange(opt.v)}
                  />
                  {opt.label}
                </label>
              ))}
            </div>
          </div>

          <div className="campo">
            <label>Ocupação</label>
            <input
              type="text"
              name="ocupacao"
              value={form.ocupacao}
              onChange={handleChange}
            />
          </div>

          <div className="campo">
            <label>Nacionalidade</label>
            <input
              type="text"
              name="nacionalidade"
              value={form.nacionalidade}
              onChange={handleChange}
            />
          </div>

          <div className="campo" style={{ gridColumn: "1 / -1" }}>
            <label>Nome da Mãe</label>
            <input
              type="text"
              name="maepcn"
              value={form.maepcn}
              onChange={handleChange}
            />
          </div>

          <div className="campo" style={{ gridColumn: "1 / -1" }}>
            <label>Endereço</label>
            <input
              type="text"
              name="logpcn"
              value={form.logpcn}
              onChange={handleChange}
            />
          </div>

          <div className="campo">
            <label>Número</label>
            <input
              type="text"
              name="numpcn"
              value={form.numpcn}
              onChange={handleChange}
            />
          </div>

          <div className="campo">
            <label>Bairro</label>
            <input
              type="text"
              name="bairro_pcnte"
              value={form.bairro_pcnte}
              onChange={handleChange}
            />
          </div>

          <div className="campo">
            <label>CEP</label>
            <input
              type="text"
              name="ceppcn"
              value={form.ceppcn}
              onChange={handleChange}
              maxLength={9}
            />
          </div>

          <div className="campo">
            <label>Cidade</label>
            <input
              type="text"
              name="cidade"
              value={form.cidade}
              onChange={handleChange}
            />
          </div>

          <div className="campo">
            <label>Estado</label>
            <input
              type="text"
              name="estado"
              value={form.estado}
              onChange={handleChange}
              maxLength={2}
            />
          </div>

          <div className="campo" style={{ gridColumn: "1 / -1" }}>
            <label>Responsável</label>
            <input
              type="text"
              name="responsavel"
              value={form.responsavel}
              onChange={handleChange}
            />
          </div>
        </div>
      </div>

      <BoletimA4
        paciente={pacienteBoletim}
        idade={idade}
        atdInfo={atdInfo}
        onDataChange={handleAtdDataChange}
        onHoraChange={handleAtdHoraChange}
        onRegistroChange={handleAtdRegistroChange}
      />

      <div className="recepcao-acoes no-print">
        <button
          onClick={handleAtendimento}
          className="btn-atendimento"
          disabled={loading}
        >
          {loading ? "Processando..." : "Registrar Atendimento"}
        </button>
        <button onClick={handleImprimir} className="btn-imprimir">
          Imprimir
        </button>
        <button onClick={handleLimpar} className="btn-limpar">
          Limpar
        </button>
      </div>
    </div>
  );
}

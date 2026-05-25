import { useState, useRef, useEffect, useCallback } from "react";
import {
  buscarPaciente,
  criarPaciente,
  atualizarPaciente,
  criarAtendimento,
  atualizarAtendimento,
  iniciarSessao,
  pingSessao,
} from "../services/api";
import {
  apenasNumeros,
  formatDateBR,
  parseDateToDB,
  parseDateFromDB,
  formatTelefone,
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

export default function Recepcao({ edicao = null, onVoltar = null }) {
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
        setMsg("+ Novo paciente");
      }
    } catch (err) {
      if (err?.response?.status === 404) {
        if (!pacienteEncontradoRef.current) setMsg("+ Novo paciente");
      } else {
        setMsg("Erro ao buscar");
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!edicao) return;
    setAtdInfo({ data: edicao.data, hora: edicao.hora, registro: "" });
    setProcedencia(edicao.procedencia || "NORMAL");
    setMsg("");
    pacienteEncontradoRef.current = false;
    if (edicao.documento) {
      autoBusca(edicao.documento);
    }
  }, [edicao, autoBusca]);

  function handleCPFChange(e) {
    const raw = apenasNumeros(e.target.value).slice(0, 11);
    setForm((prev) => ({ ...prev, num_cpf: raw }));
    if (raw.length === 11 && !validarCPF(raw)) {
      setErroCpf("CPF inválido");
      setMsg("CPF inválido");
      return;
    }
    setErroCpf("");
    if (raw.length < 11) setMsg("");
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (raw.length === 11) {
      debounceRef.current = setTimeout(() => autoBusca(raw), 300);
    }
  }

  function handleCNSChange(e) {
    const raw = apenasNumeros(e.target.value).slice(0, 15);
    setForm((prev) => ({ ...prev, cns: raw }));
    if (raw.length === 15 && !validarCNS(raw)) {
      setErroCns("CNS inválido");
      setMsg("CNS inválido");
      return;
    }
    setErroCns("");
    if (raw.length < 15) setMsg("");
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
    const fmt = formatDateBR(e.target.value);
    setForm((prev) => ({ ...prev, dtnasc: fmt }));
    calcIdade(fmt);
  }

  function handleTelChange(e) {
    const fmt = formatTelefone(e.target.value);
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

  async function handleAtendimento() {
    const erros = validar();
    if (erros.length > 0) {
      setMsg(erros[0].msg);
      return;
    }
    setLoading(true);
    setMsg("");
    try {
      const dados = prepararDados();
      let id = pacienteId;

      if (edicao) {
        // Modo edição: atualiza paciente + atendimento existente
        if (id) await atualizarPaciente(id, dados);
        await atualizarAtendimento(edicao.atendimentoId, {
          data_atendimento: atdInfo.data,
          hora_atendimento: atdInfo.hora,
          procedencia,
        });
        setMsg("✓ Atendimento atualizado!");
      } else {
        // Modo novo: cria ou atualiza paciente + cria atendimento
        if (id) {
          await atualizarPaciente(id, dados);
        } else {
          const res = await criarPaciente(dados);
          id = res.data.id;
          setPacienteId(id);
        }
        await criarAtendimento({
          paciente_id: id,
          data_atendimento: atdInfo.data,
          hora_atendimento: atdInfo.hora,
          registro: atdInfo.registro,
          procedencia,
        });
        const turno = calcularTurno(atdInfo.hora);
        const regNum = parseInt(atdInfo.registro, 10);
        if (!isNaN(regNum)) {
          ultimoRegistroRef.current = regNum;
          ultimoTurnoRef.current = turno;
        }
        setMsg("✓ Registrado!");
      }
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

  const msgOk = msg.startsWith("✓");

  return (
    <div className="recepcao">
      <header className="recepcao-header no-print">
        <div className="header-left">
          <img src="/img/brasao-extremoz.png" className="header-brasao" alt="Brasão" />
          <h1>HMPCF — Recepção</h1>
          {edicao && (
            <span className="badge-edicao">Editando #{edicao.atendimentoId}</span>
          )}
        </div>
        <div className="header-right">
          {pacienteId && <span className="badge-ok">✓ Paciente</span>}
          {loading && <span className="badge-loading">⏳</span>}
          {msg && (
            <span className={`msg-badge ${msgOk ? "msg-badge-ok" : "msg-badge-erro"}`}>
              {msg}
            </span>
          )}
        </div>
      </header>

      <div className="recepcao-acoes no-print">
        <button
          onClick={handleAtendimento}
          className="btn-atendimento"
          disabled={loading}
        >
          {loading ? "Processando..." : edicao ? "Salvar Alterações" : "Registrar Atendimento"}
        </button>
        <button onClick={handleImprimir} className="btn-imprimir">
          Imprimir
        </button>
        {edicao ? (
          <button onClick={onVoltar} className="btn-limpar">
            ← Voltar ao Histórico
          </button>
        ) : (
          <button onClick={handleLimpar} className="btn-limpar">
            Limpar
          </button>
        )}
      </div>

      <div className="recepcao-main">
        <div className="recepcao-sidebar no-print">
          <ProcedenciaSelector
            value={procedencia}
            onChange={handleProcedenciaChange}
          />
        </div>

        <BoletimA4
          form={form}
          idade={idade}
          atdInfo={atdInfo}
          onDataChange={handleAtdDataChange}
          onHoraChange={handleAtdHoraChange}
          onRegistroChange={handleAtdRegistroChange}
          onCPFChange={handleCPFChange}
          onCNSChange={handleCNSChange}
          onDtnascChange={handleDtnascChange}
          onTelChange={handleTelChange}
          onRacaChange={handleRacaChange}
          onSexoChange={handleSexoChange}
          onFieldChange={handleChange}
          cpfRef={cpfRef}
          erroCpf={erroCpf}
          erroCns={erroCns}
        />
      </div>
    </div>
  );
}

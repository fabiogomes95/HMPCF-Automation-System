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
  naturalidade: "",
  nacionalidade: "010",
  estado_civil: "",
  ocupacao: "",
  responsavel: "",
};

const camposTexto = [
  "nome", "nome_social", "maepcn", "logpcn",
  "numpcn", "bairro_pcnte", "cidade", "estado",
  "naturalidade", "estado_civil", "ocupacao", "responsavel",
];

function uc(v) {
  return v ? v.toUpperCase() : v;
}

export default function Recepcao({ edicao = null, onVoltar = null }) {
  const [form, setForm] = useState({ ...vazio });
  const [pacienteId, setPacienteId] = useState(null);
  const [msg, setMsg] = useState("");
  const [aviso, setAviso] = useState("");
  const [idade, setIdade] = useState("");
  const [loading, setLoading] = useState(false);
  const [erroCpf, setErroCpf] = useState("");
  const [erroCns, setErroCns] = useState("");
  const [erroDtnasc, setErroDtnasc] = useState("");
  const [procedencia, setProcedencia] = useState("NORMAL");
  const [atdInfo, setAtdInfo] = useState({ data: "", hora: "", registro: "" });
  const debounceRef = useRef(null);
  const pacienteEncontradoRef = useRef(false);
  const cpfRef = useRef(null);
  const ultimoRegistroRef = useRef(null);
  const ultimoTurnoRef = useRef(null);
  const horaManualRef = useRef(false);
  const dataManualRef = useRef(false);

  function sugerirAtdInfo() {
    const data = dataAtual();
    const hora = horaAtual();
    const turno = calcularTurno(hora);
    let registro = 1;
    if (ultimoRegistroRef.current != null) {
      if (ultimoTurnoRef.current === null || turno === ultimoTurnoRef.current) {
        // Mesmo turno (ou primeiro uso): incrementa
        registro = ultimoRegistroRef.current + 1;
      }
      // Turno diferente: reseta para 01
    }
    ultimoTurnoRef.current = turno;
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
    // Restaura último registro/turno do localStorage (sobrevive à navegação)
    const regSalvo = parseInt(localStorage.getItem("ultimo_registro"), 10);
    const turnoSalvo = localStorage.getItem("ultimo_turno");
    ultimoRegistroRef.current = isNaN(regSalvo) ? null : regSalvo;
    ultimoTurnoRef.current = turnoSalvo || null;
    sugerirAtdInfo();
  }, []);

  // Relógio em tempo real — atualiza hora/data automaticamente a cada 10s
  // Para de atualizar o campo se o usuário tiver editado manualmente
  useEffect(() => {
    const tick = setInterval(() => {
      setAtdInfo(prev => {
        const novaHora = horaAtual();
        const novaData = dataAtual();
        const atualizaHora = !horaManualRef.current && novaHora !== prev.hora;
        const atualizaData = !dataManualRef.current && novaData !== prev.data;
        if (!atualizaHora && !atualizaData) return prev;
        return {
          ...prev,
          ...(atualizaHora ? { hora: novaHora } : {}),
          ...(atualizaData ? { data: novaData } : {}),
        };
      });
    }, 10000);
    return () => clearInterval(tick);
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
          naturalidade: p.naturalidade || "",
          nacionalidade: "010",
          estado_civil: p.estado_civil || "",
          ocupacao: p.ocupacao || "",
          responsavel: p.responsavel || "",
        });
        setPacienteId(p.id);
        setErroCpf("");
        setErroCns("");
        calcIdade(dtnasc);
        setMsg("✓ Paciente encontrado");
        if (!p.dtnasc || p.dtnasc.trim() === "") {
          setAviso("⚠️ Data de nascimento ausente — atualize");
        } else {
          setAviso("");
        }
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
    dataManualRef.current = true;
    const raw = formatDateBR(e.target.value);
    setAtdInfo((prev) => ({ ...prev, data: raw }));
  }

  function handleAtdHoraChange(e) {
    horaManualRef.current = true;
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

    const nomeStr = (form.nome || "").trim();
    if (!nomeStr) {
      erros.push({ campo: "nome", msg: "Nome é obrigatório." });
    } else if (nomeStr.length < 3) {
      erros.push({ campo: "nome", msg: "Nome muito curto (mínimo 3 caracteres)." });
    }

    if (!form.sexo) {
      erros.push({ campo: "sexo", msg: "Selecione o sexo (M ou F)." });
    }

    const cpfOk = form.num_cpf && validarCPF(form.num_cpf);
    const cnsOk = form.cns && validarCNS(form.cns);
    if (!cpfOk && !cnsOk) {
      erros.push({ campo: "num_cpf", msg: "Informe um CPF ou CNS válido." });
    }

    if (!form.dtnasc || form.dtnasc.trim() === "") {
      erros.push({ campo: "dtnasc", msg: "Data de nascimento é obrigatória." });
    } else {
      const partes = form.dtnasc.split("/");
      if (partes.length !== 3 || partes[2].length !== 4) {
        erros.push({ campo: "dtnasc", msg: "Data de nascimento inválida." });
      } else {
        const nasc = new Date(
          parseInt(partes[2], 10),
          parseInt(partes[1], 10) - 1,
          parseInt(partes[0], 10)
        );
        const hoje = new Date();
        hoje.setHours(0, 0, 0, 0);
        if (isNaN(nasc.getTime())) {
          erros.push({ campo: "dtnasc", msg: "Data de nascimento inválida." });
        } else if (nasc > hoje) {
          erros.push({ campo: "dtnasc", msg: "Data de nascimento não pode ser futura." });
        } else if ((hoje - nasc) / (1000 * 60 * 60 * 24 * 365) > 130) {
          erros.push({ campo: "dtnasc", msg: "Data de nascimento absurda (mais de 130 anos)." });
        }
      }
    }

    return erros;
  }

  async function handleAtendimento() {
    const erros = validar();
    if (erros.length > 0) {
      setErroDtnasc(erros.find(e => e.campo === "dtnasc")?.msg || "");
      setMsg(erros[0].msg);
      return;
    }
    setErroDtnasc("");
    setLoading(true);
    setMsg("");
    setAviso("");
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
        // Salva endereço para o botão Família — só atualiza se o paciente tem endereço
        if (dados.logpcn || dados.numpcn || dados.bairro_pcnte) {
          localStorage.setItem("ultimo_endereco", JSON.stringify({
            logpcn:       dados.logpcn       || "",
            numpcn:       dados.numpcn       || "",
            bairro_pcnte: dados.bairro_pcnte || "",
          }));
        }
        const turno = calcularTurno(atdInfo.hora);
        const regNum = parseInt(atdInfo.registro, 10);
        if (!isNaN(regNum)) {
          ultimoRegistroRef.current = regNum;
          ultimoTurnoRef.current = turno;
          localStorage.setItem("ultimo_registro", regNum);
          localStorage.setItem("ultimo_turno", turno);
        }
        setMsg("✓ Registrado!");
      }
    } catch (err) {
      const data = err.response?.data || {};
      const msg = data.detail || data.message || "Erro ao registrar";
      setMsg(typeof msg === "string" ? msg : JSON.stringify(msg));
    } finally {
      setLoading(false);
    }
  }

  function handleFamilia() {
    try {
      const salvo = localStorage.getItem("ultimo_endereco");
      if (!salvo) return;
      const { logpcn, numpcn, bairro_pcnte } = JSON.parse(salvo);
      setForm(prev => ({
        ...prev,
        logpcn,
        numpcn,
        bairro_pcnte,
      }));
    } catch {
      // localStorage corrompido — ignora
    }
  }

  function handleLimpar() {
    // Persiste o registro/turno atuais para que sugerirAtdInfo possa incrementar
    const regAtual = parseInt(atdInfo.registro, 10);
    const turnoAtual = calcularTurno(atdInfo.hora || horaAtual());
    if (!isNaN(regAtual) && regAtual > 0) {
      ultimoRegistroRef.current = regAtual;
      localStorage.setItem("ultimo_registro", regAtual);
    }
    ultimoTurnoRef.current = turnoAtual;
    localStorage.setItem("ultimo_turno", turnoAtual);

    // Reativa atualização automática de hora e data
    horaManualRef.current = false;
    dataManualRef.current = false;

    setForm({ ...vazio });
    setPacienteId(null);
    setMsg("");
    setAviso("");
    setIdade("");
    setErroCpf("");
    setErroCns("");
    setErroDtnasc("");
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
          {aviso && (
            <span className="msg-badge msg-badge-aviso">
              {aviso}
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
          erroDtnasc={erroDtnasc}
          onFamilia={handleFamilia}
        />
      </div>
    </div>
  );
}

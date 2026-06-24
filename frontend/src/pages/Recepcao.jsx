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
  const [registrado, setRegistrado] = useState(false);
  const [erroCpf, setErroCpf] = useState("");
  const [erroCns, setErroCns] = useState("");
  const [erroDtnasc, setErroDtnasc] = useState("");
  const [procedencia, setProcedencia] = useState("NORMAL");
  const [atdInfo, setAtdInfo] = useState({ data: "", hora: "", registro: "" });
  const [relogioAtivo, setRelogioAtivo] = useState(true);
  const debounceRef = useRef(null);
  const pacienteEncontradoRef = useRef(false);
  const cpfRef = useRef(null);
  const formRef = useRef(form);

  useEffect(() => {
    formRef.current = form;
  }, [form]);

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
    setAtdInfo(prev => ({ ...prev, data: dataAtual(), hora: horaAtual(), registro: "" }));
  }, []);

  // Relógio em tempo real — para completamente ao primeiro campo digitado
  useEffect(() => {
    if (!relogioAtivo) return;
    const tick = setInterval(() => {
      setAtdInfo(prev => ({
        ...prev,
        hora: horaAtual(),
        data: dataAtual(),
      }));
    }, 10000);
    return () => clearInterval(tick);
  }, [relogioAtivo]);

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
        const dtnascEncontrada = parseDateFromDB(p.dtnasc);
        // Regra: dados digitados manualmente têm prioridade máxima.
        // CPF/CNS/integrações só preenchem campos que ainda estão vazios.
        // dtnascFinal precisa ser calculado ANTES do setForm: o callback do
        // setForm só roda quando o React processa a atualização (assíncrono
        // aqui, pois estamos fora de um event handler), então usar seu valor
        // logo abaixo (calcIdade/setAviso) pegaria undefined.
        const preencheSeVazio = (atual, encontrado) =>
          atual && String(atual).trim() !== "" ? atual : encontrado || "";
        const dtnascFinal = preencheSeVazio(formRef.current.dtnasc, dtnascEncontrada);
        setForm((prev) => {
          return {
            ...prev,
            nome: preencheSeVazio(prev.nome, p.nome),
            nome_social: preencheSeVazio(prev.nome_social, p.nome_social),
            cns: preencheSeVazio(prev.cns, p.cns),
            num_cpf: preencheSeVazio(prev.num_cpf, p.num_cpf),
            dtnasc: dtnascFinal,
            sexo: preencheSeVazio(prev.sexo, p.sexo),
            raca: preencheSeVazio(prev.raca, p.raca || "03"),
            maepcn: preencheSeVazio(prev.maepcn, p.maepcn),
            logpcn: preencheSeVazio(prev.logpcn, p.logpcn),
            numpcn: preencheSeVazio(prev.numpcn, p.numpcn),
            bairro_pcnte: preencheSeVazio(prev.bairro_pcnte, p.bairro_pcnte),
            ceppcn: preencheSeVazio(prev.ceppcn, p.ceppcn),
            cidade: preencheSeVazio(prev.cidade, p.cidade || "EXTREMOZ"),
            estado: preencheSeVazio(prev.estado, p.estado || "RN"),
            telefone: preencheSeVazio(prev.telefone, formatTelefone(p.telefone)),
            naturalidade: preencheSeVazio(prev.naturalidade, p.naturalidade),
            nacionalidade: preencheSeVazio(prev.nacionalidade, "010"),
            estado_civil: preencheSeVazio(prev.estado_civil, p.estado_civil),
            ocupacao: preencheSeVazio(prev.ocupacao, p.ocupacao),
            responsavel: preencheSeVazio(prev.responsavel, p.responsavel),
          };
        });
        setPacienteId(p.id);
        setErroCpf("");
        setErroCns("");
        calcIdade(dtnascFinal);
        setMsg("✓ Paciente encontrado");
        if (!dtnascFinal || dtnascFinal.trim() === "") {
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
    setRegistrado(false);
    pacienteEncontradoRef.current = false;
    if (edicao.documento) {
      autoBusca(edicao.documento);
    }
  }, [edicao, autoBusca]);

  function congelarRelogio() {
    setRelogioAtivo(false);
  }

  function handleCPFChange(e) {
    const raw = apenasNumeros(e.target.value).slice(0, 11);
    if (raw.length >= 1) congelarRelogio();
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
    if (raw.length >= 1) congelarRelogio();
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
    congelarRelogio();
    const { name, value } = e.target;
    if (camposTexto.includes(name)) {
      setForm((prev) => ({ ...prev, [name]: uc(value) }));
    } else {
      setForm((prev) => ({ ...prev, [name]: value }));
    }
  }

  function handleDtnascChange(e) {
    congelarRelogio();
    const fmt = formatDateBR(e.target.value);
    setForm((prev) => ({ ...prev, dtnasc: fmt }));
    calcIdade(fmt);
    if (calcularIdade(fmt)) setErroDtnasc("");
  }

  function handleTelChange(e) {
    congelarRelogio();
    const fmt = formatTelefone(e.target.value);
    setForm((prev) => ({ ...prev, telefone: fmt }));
  }

  function handleRacaChange(cod) {
    congelarRelogio();
    setForm((prev) => ({ ...prev, raca: cod }));
  }

  function handleSexoChange(v) {
    congelarRelogio();
    setForm((prev) => ({ ...prev, sexo: v }));
  }

  function handleProcedenciaChange(v) {
    setProcedencia(v);
  }

  function handleAtdDataChange(e) {
    congelarRelogio();
    const raw = formatDateBR(e.target.value);
    setAtdInfo((prev) => ({ ...prev, data: raw }));
  }

  function handleAtdHoraChange(e) {
    congelarRelogio();
    let v = e.target.value.replace(/[^0-9:]/g, "").slice(0, 5);
    if (v.length === 2 && !v.includes(":")) v += ":";
    setAtdInfo((prev) => ({ ...prev, hora: v }));
  }

  function handleAtdRegistroChange(e) {
    const v = e.target.value.replace(/\D/g, "").slice(0, 4);
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
        setMsg("✓ Registrado!");
        setRegistrado(true);
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
    setRelogioAtivo(true);
    setRegistrado(false);
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
    setAtdInfo({ data: dataAtual(), hora: horaAtual(), registro: "" });
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
          disabled={loading || registrado}
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

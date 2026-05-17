import { useState, useCallback, useRef, Fragment, useEffect } from "react";
import api from "../services/api";
import FichaA4Print from "../components/FichaA4Print";
import "./Recepcao.css";

function nowStr() {
  const n = new Date();
  return {
    data: n.toLocaleDateString("pt-BR"),
    hora: n.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" }),
  };
}

const INITIAL_STATE = () => ({
  ...nowStr(),
  cpf: "",
  sus: "",
  registro: "",
  nome: "",
  nomeSocial: "",
  naturalidade: "",
  dn: "",
  idade: "",
  sexo: "",
  civil: "",
  raca: "",
  ocupacao: "",
  mae: "",
  responsavel: "",
  tel: "",
  endereco: "",
  numero: "",
  bairro: "",
  cidade: "EXTREMOZ",
  estado: "RN",
  procedencia: "NORMAL",
});

function formatDateBR(v) {
  if (!v) return "";
  const d = v.replace(/\D/g, "");
  if (d.length === 8) {
    const y = parseInt(d.slice(0, 4), 10);
    if (y >= 1900 && y <= 2099) {
      return `${d.slice(6,8)}/${d.slice(4,6)}/${d.slice(0,4)}`;
    }
    return `${d.slice(0,2)}/${d.slice(2,4)}/${d.slice(4,8)}`;
  }
  return v;
}

function calcularIdade(dn) {
  if (!dn) return "";
  const partes = dn.split("/");
  if (partes.length !== 3) return "";
  const dia = parseInt(partes[0], 10);
  const mes = parseInt(partes[1], 10) - 1;
  const ano = parseInt(partes[2], 10);
  const nasc = new Date(ano, mes, dia);
  if (isNaN(nasc.getTime())) return "";
  const hoje = new Date();
  let anos = hoje.getFullYear() - nasc.getFullYear();
  let meses = hoje.getMonth() - nasc.getMonth();
  let dias = hoje.getDate() - nasc.getDate();
  if (dias < 0) { meses--; const ultimoMes = new Date(hoje.getFullYear(), hoje.getMonth(), 0); dias += ultimoMes.getDate(); }
  if (meses < 0) { anos--; meses += 12; }
  if (anos >= 2) return anos + " ANOS";
  if (anos === 1) return "1 ANO";
  if (meses >= 1 || anos >= 1) {
    const m = anos * 12 + meses;
    return m + (m === 1 ? " MES" : " MESES");
  }
  return dias + (dias === 1 ? " DIA" : " DIAS");
}

function validarCPF(cpf) {
  const d = cpf.replace(/\D/g, "");
  if (d.length !== 11) return false;
  if (/^(\d)\1{10}$/.test(d)) return false;
  let soma = 0;
  for (let i = 0; i < 9; i++) soma += parseInt(d[i]) * (10 - i);
  let resto = (soma * 10) % 11;
  if (resto === 10) resto = 0;
  if (resto !== parseInt(d[9])) return false;
  soma = 0;
  for (let i = 0; i < 10; i++) soma += parseInt(d[i]) * (11 - i);
  resto = (soma * 10) % 11;
  if (resto === 10) resto = 0;
  return resto === parseInt(d[10]);
}

function validarSUS(sus) {
  const d = sus.replace(/\D/g, "");
  if (d.length !== 15 || !"12789".includes(d[0])) return false;
  let soma = 0;
  for (let i = 0; i < 15; i++) soma += parseInt(d[i]) * (15 - i);
  if ("789".includes(d[0])) return soma % 11 === 0;
  const pis = d.slice(0, 11);
  soma = 0;
  for (let i = 0; i < 11; i++) soma += parseInt(pis[i]) * (15 - i);
  let resto = soma % 11;
  let dv = 11 - resto;
  if (dv === 11) dv = 0;
  if (dv === 10) { soma += 2; resto = soma % 11; dv = 11 - resto; return d === pis + "001" + dv; }
  return d === pis + "000" + dv;
}

function maskDate(v) {
  const d = v.replace(/\D/g, "").slice(0, 8);
  let r = "";
  for (let i = 0; i < d.length; i++) {
    if (i === 2 || i === 4) r += "/";
    r += d[i];
  }
  return r;
}

function maskCPF(v) {
  const d = v.replace(/\D/g, "").slice(0, 11);
  let r = "";
  for (let i = 0; i < d.length; i++) {
    if (i === 3 || i === 6) r += ".";
    if (i === 9) r += "-";
    r += d[i];
  }
  return r;
}

function maskSUS(v) {
  const d = v.replace(/\D/g, "").slice(0, 15);
  let r = "";
  for (let i = 0; i < d.length; i++) {
    if (i === 3 || i === 7 || i === 11) r += " ";
    r += d[i];
  }
  return r;
}

function maskHora(v) {
  const d = v.replace(/\D/g, "").slice(0, 4);
  let r = "";
  for (let i = 0; i < d.length; i++) {
    if (i === 2) r += ":";
    r += d[i];
  }
  return r;
}

function maskTelefone(v) {
  const d = v.replace(/\D/g, "").slice(0, 11);
  let r = "";
  for (let i = 0; i < d.length; i++) {
    if (i === 0) r += "(";
    if (i === 2) r += ") ";
    if (i === 7) r += "-";
    r += d[i];
  }
  return r;
}

function unmask(v) { return v.replace(/\D/g, ""); }

function mostrarToast(mensagem, tipo = "info") {
  const container = document.getElementById("toastContainer") ||
    (() => { const d = document.createElement("div"); d.id = "toastContainer"; d.className = "toast-container"; document.body.appendChild(d); return d; })();
  const bgMap = { success: "#22c55e", danger: "#ef4444", warning: "#f59e0b", info: "#1a5b9c" };
  const el = document.createElement("div");
  Object.assign(el.style, { backgroundColor: bgMap[tipo] || bgMap.info, color: "#fff", padding: "12px 20px", borderRadius: "8px", fontWeight: "500", fontSize: "14px", boxShadow: "0 4px 12px rgba(0,0,0,0.15)" });
  el.textContent = mensagem;
  container.appendChild(el);
  setTimeout(() => el.remove(), 4000);
}

export default function Recepcao() {
  const [form, setForm] = useState(INITIAL_STATE());
  const [searchTerm, setSearchTerm] = useState("");
  const [results, setResults] = useState([]);
  const [totalResults, setTotalResults] = useState(0);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [isNew, setIsNew] = useState(false);
  const lastAddress = useRef(null);
  const searchTimerRef = useRef(null);
  const cpfRef = useRef(null);
  const [history, setHistory] = useState([]);
  const [totalDesdeAbril, setTotalDesdeAbril] = useState(0);
  const [errors, setErrors] = useState({});

  function validateField(name, value) {
    const d = value.replace(/\D/g, "");
    if (name === "cpf" && d.length === 11) setErrors((e) => ({ ...e, cpf: !validarCPF(value) }));
    if (name === "sus" && d.length === 15) setErrors((e) => ({ ...e, sus: !validarSUS(value) }));
  }

  // ── F2: Salvar ─────────────────────────────────────────
  useEffect(() => {
    const fn = (e) => { if (e.key === "F2") { e.preventDefault(); document.querySelector(".btn-save")?.click(); } };
    window.addEventListener("keydown", fn);
    return () => window.removeEventListener("keydown", fn);
  }, []);

  // ── Relógio automático (atualiza data/hora a cada 30s) ──
  useEffect(() => {
    const timer = setInterval(() => {
      const agora = nowStr();
      setForm((prev) => ({ ...prev, data: agora.data, hora: agora.hora }));
    }, 30000);
    return () => clearInterval(timer);
  }, []);

  // ── Auto-salvar rascunho (30s) ─────────────────────────
  const formRef = useRef(form);
  formRef.current = form;
  useEffect(() => {
    const timer = setInterval(() => {
      const { data, hora, ...draft } = formRef.current;
      localStorage.setItem("draft_recepcao", JSON.stringify(draft));
    }, 30000);
    return () => clearInterval(timer);
  }, []);

  // ── Recuperar rascunho ao montar ───────────────────────
  useEffect(() => {
    const raw = localStorage.getItem("draft_recepcao");
    if (!raw) return;
    try {
      const draft = JSON.parse(raw);
      if (draft.nome || draft.cpf) {
        setForm((prev) => ({ ...prev, ...draft }));
        mostrarToast("Rascunho recuperado! Revise os dados.", "info");
      }
    } catch { /* ignora */ }
  }, []);

  // ── Buscar pacientes ──────────────────────────────────────

  const handleSearch = useCallback(async () => {
    const term = searchTerm.trim();
    if (!term) return;
    setLoading(true);
    try {
      if (unmask(term).length === 11) {
        try {
          const res = await api.get(`/recepcao/pacientes/${unmask(term)}`);
          if (res.data) {
            setResults([res.data]);
            setTotalResults(1);
            setLoading(false);
            return;
          }
        } catch { /* não encontrou por CPF */ }
      }
      const res = await api.get("/recepcao/pacientes", {
        params: { nome: term, por_pagina: 20 },
      });
      setResults(res.data.items || []);
      setTotalResults(res.data.total || 0);
    } catch {
      mostrarToast("Erro ao buscar — o backend está rodando?", "danger");
      setResults([]);
      setTotalResults(0);
    } finally {
      setLoading(false);
    }
  }, [searchTerm]);

  const handleKeyDown = (e) => {
    if (e.key === "Enter") handleSearch();
  };

  // ── Selecionar paciente ──────────────────────────────────

  const selectPatient = (patient) => {
    setForm({
      ...nowStr(),
      cpf: maskCPF(patient.cpf || ""),
      sus: maskSUS(patient.sus || ""),
      registro: patient.registro || "",
      nome: patient.nome || "",
      nomeSocial: patient.nomeSocial || "",
      naturalidade: patient.naturalidade || "",
      dn: formatDateBR(patient.dn || ""),
      idade: calcularIdade(formatDateBR(patient.dn || "")),
      sexo: patient.sexo || "",
      civil: patient.civil || "",
      raca: patient.raca || "",
      ocupacao: patient.ocupacao || "",
      mae: patient.mae || "",
      responsavel: patient.responsavel || "",
      tel: maskTelefone(patient.tel || ""),
      endereco: patient.endereco || "",
      numero: patient.numero || "",
      bairro: patient.bairro || "",
      cidade: patient.cidade || "EXTREMOZ",
      estado: patient.estado || "RN",
      procedencia: "NORMAL",
    });
    setIsNew(false);
    setResults([]);
    setSearchTerm("");
    const maskedCPF = maskCPF(patient.cpf || "");
    const maskedSUS = maskSUS(patient.sus || "");
    setErrors({ cpf: maskedCPF && !validarCPF(maskedCPF), sus: maskedSUS && !validarSUS(maskedSUS) });
    const cleanCPF = patient.cpf?.replace(/\D/g, "");
    const doc = cleanCPF || patient.sus?.replace(/\D/g, "");
    if (doc) {
      api.get("/recepcao/atendimentos", { params: { cpf: doc, por_pagina: 5 } })
        .then((res) => setHistory(res.data.items || []))
        .catch(() => setHistory([]));
      api.get("/recepcao/atendimentos", { params: { cpf: doc, data_inicio: "01/04/2026", por_pagina: 1 } })
        .then((res) => setTotalDesdeAbril(res.data.total || 0))
        .catch(() => setTotalDesdeAbril(0));
    } else {
      setHistory([]);
      setTotalDesdeAbril(0);
    }
  };

  // ── Novo ──────────────────────────────────────────────────

  const handleNew = () => {
    setForm(INITIAL_STATE());
    setIsNew(true);
    setResults([]);
    setSearchTerm("");
    setHistory([]);
    setTotalDesdeAbril(0);
    setErrors({});
    localStorage.removeItem("draft_recepcao");
    cpfRef.current?.focus();
  };

  // ── Família (preenche endereço do último salvo) ───────────

  const handleFamily = () => {
    if (!lastAddress.current) {
      mostrarToast("Nenhum endereço anterior salvo", "warning");
      return;
    }
    setForm((prev) => ({ ...prev, ...lastAddress.current }));
  };

  // ── Atualizar campo ──────────────────────────────────────

  const handleChange = (e) => {
    const { name, value } = e.target;
    let v = value;
    if (name === "cpf") v = maskCPF(value);
    else if (name === "sus") v = maskSUS(value);
    else if (name === "dn" || name === "data") v = maskDate(value);
    else if (name === "hora") v = maskHora(value);
    else if (name === "tel") v = maskTelefone(value);
    else if (!["cpf", "sus", "dn", "data", "hora", "sexo", "civil", "raca", "procedencia", "registro", "idade", "numero"].includes(name)) v = v.toUpperCase();
    setForm((prev) => {
      const upd = { ...prev, [name]: v };
      if (name === "dn") upd.idade = calcularIdade(v);
      return upd;
    });
    if (name === "cpf" || name === "sus") {
      setErrors((e) => ({ ...e, [name]: false }));
      validateField(name, v);
    }
    if (name === "cpf" || name === "sus") {
      clearTimeout(searchTimerRef.current);
      const raw = v.replace(/\D/g, "");
      if ((name === "cpf" && raw.length === 11) || (name === "sus" && raw.length === 15)) {
        searchTimerRef.current = setTimeout(async () => {
          try {
            const res = await api.get(`/recepcao/pacientes/${raw}`);
            if (res.data) selectPatient(res.data);
          } catch { /* nao encontrado */ }
        }, 200);
      }
    }
  };

  const handleBlur = (e) => {
    const { name, value } = e.target;
    validateField(name, value);
    if (name === "cpf" || name === "sus") {
      const raw = value.replace(/\D/g, "");
      if ((name === "cpf" && raw.length === 11) || (name === "sus" && raw.length === 15)) {
        api.get(`/recepcao/pacientes/${raw}`)
          .then((res) => { if (res.data) selectPatient(res.data); })
          .catch(() => {});
      }
    }
  };

  // ── Salvar ───────────────────────────────────────────────

  const handleSave = async () => {
    const cleanCPF = unmask(form.cpf);
    const cleanSUS = unmask(form.sus);
    const cpfOk = cleanCPF.length === 11 && validarCPF(form.cpf);
    const susOk = cleanSUS.length === 15 && validarSUS(form.sus);
    if (!cpfOk && !susOk) {
      mostrarToast("Informe um CPF ou Cartão SUS válido", "warning");
      return;
    }
    const doc = cpfOk ? cleanCPF : cleanSUS;
    if (!form.sexo) { mostrarToast("Selecione o sexo (M/F)", "warning"); return; }
    if (!form.nome) { mostrarToast("Nome é obrigatório", "warning"); return; }
    if (!form.registro) { mostrarToast("Registro é obrigatório", "warning"); return; }
    if (form.cpf && !validarCPF(form.cpf)) mostrarToast("CPF inválido (dígitos verificadores não conferem)", "warning");
    if (form.sus && !validarSUS(form.sus)) mostrarToast("Cartão SUS inválido", "warning");
    if (isNew && form.nome && form.dn) {
      try {
        const dup = await api.get("/recepcao/pacientes/duplicata", { params: { nome: form.nome, dn: form.dn } });
        if (dup.data) mostrarToast("Duplicata: paciente já cadastrado com este nome e DN!", "warning");
      } catch { /* igora */ }
    }
    const { data, hora, registro, ...pacienteData } = form;
    const payload = { ...pacienteData, cpf: doc };
    setSaving(true);
    try {
      if (isNew) {
        await api.post("/recepcao/pacientes", payload);
      } else {
        await api.put(`/recepcao/pacientes/${doc}`, payload);
      }
      setIsNew(false);
      lastAddress.current = {
        endereco: form.endereco,
        numero: form.numero,
        bairro: form.bairro,
        cidade: form.cidade,
        estado: form.estado,
      };
      const atendimentoPayload = {
        cpf: doc,
        data_atendimento: data,
        hora_atendimento: hora,
        registro: registro || null,
        procedencia: form.procedencia || null,
      };
      await api.post("/recepcao/atendimentos", atendimentoPayload);
      localStorage.removeItem("draft_recepcao");
      api.get("/recepcao/atendimentos", { params: { cpf: doc, por_pagina: 5 } })
        .then((res) => setHistory(res.data.items || []))
        .catch(() => {});
      api.get("/recepcao/atendimentos", { params: { cpf: doc, data_inicio: "01/04/2026", por_pagina: 1 } })
        .then((res) => setTotalDesdeAbril(res.data.total || 0))
        .catch(() => setTotalDesdeAbril(0));
      mostrarToast("Salvo com sucesso!", "success");
    } catch (err) {
      const msg = err.response?.data?.detail || "Erro ao salvar";
      mostrarToast(msg, "danger");
    } finally {
      setSaving(false);
    }
  };

  // ── Imprimir (mesma aba) ────────────────────────────────

  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="recepcao-page">
      {/* ── Barra de busca ─────────────────────────────────── */}
      <div className="recepcao-toolbar">
        <div className="search-box">
          <input
            type="text"
            placeholder="Buscar por nome ou CPF..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            onKeyDown={handleKeyDown}
          />
          <button className="btn-search" onClick={handleSearch} disabled={loading}>
            {loading ? "..." : "Buscar"}
          </button>
        </div>
        {totalResults > 0 && (
          <span className="result-count">{totalResults} encontrado(s)</span>
        )}
      </div>

      {/* ── Lista de resultados ─────────────────────────────── */}
      {results.length > 0 && (
        <div className="result-list">
          {results.map((p) => (
            <div key={p.cpf} className="result-item" onClick={() => selectPatient(p)}>
              <div>
                <span className="nome">{p.nome || "(sem nome)"}</span>
                <span style={{ marginLeft: 12, color: "var(--color-text-secondary)", fontSize: "0.75rem" }}>
                  {formatDateBR(p.dn) || ""} {p.mae ? `| ${p.mae}` : ""}
                </span>
              </div>
              <span className="cpf">{p.cpf}</span>
            </div>
          ))}
        </div>
      )}

      {/* ── Botões de ação ── */}
      <div className="action-bar">
        <button className="btn-save" onClick={handleSave} disabled={saving}>
          {saving ? "Salvando..." : "Salvar (F2)"}
        </button>
        <button className="btn-print" onClick={handlePrint}>
          Imprimir
        </button>
        <button className="btn-clear" onClick={handleNew}>
          Limpar
        </button>
      </div>

      {/* ── FORMULÁRIO MODERNO (TELA) ─────────────────────────── */}
      <div className="screen-form">
        <div className="a4-sheet">
          <div className="form-grid">

            { /* PROCEDÊNCIA */ }
            <div className="form-group form-group--full form-group--centered">
              <label>Procedência</label>
              <div className="radio-group radio-group--centered">
                {["SAMU", "TROCA", "UBS", "GUARDA", "NORMAL"].map((op) => {
                  const id = "proc-" + op.toLowerCase();
                  return (
                    <Fragment key={op}>
                      <input type="radio" id={id} name="procedencia" value={op} checked={form.procedencia === op} onChange={handleChange} className="radio-input-hidden" />
                      <label htmlFor={id} className="radio-label">{op === "TROCA" ? "TROCA" : op.charAt(0) + op.slice(1).toLowerCase()}</label>
                    </Fragment>
                  );
                })}
              </div>
            </div>

            { /* DATA | HORA | REGISTRO */ }
            <div className="form-group">
              <label>Data</label>
              <input type="text" name="data" value={form.data} onChange={handleChange} maxLength={10} />
            </div>
            <div className="form-group">
              <label>Hora</label>
              <input type="text" name="hora" value={form.hora} onChange={handleChange} maxLength={5} />
            </div>
            <div className="form-group form-group--narrow">
              <label>Registro</label>
              <input type="text" name="registro" value={form.registro} onChange={handleChange} maxLength={3} />
            </div>

            { /* NOME COMPLETO */ }
            <div className="form-group form-group--full">
              <label>Nome Completo</label>
              <input type="text" name="nome" value={form.nome} onChange={handleChange} />
            </div>

            { /* NOME SOCIAL */ }
            <div className="form-group form-group--full">
              <label>Nome Social</label>
              <input type="text" name="nomeSocial" value={form.nomeSocial} onChange={handleChange} />
            </div>

            { /* NATURALIDADE | DN | IDADE */ }
            <div className="form-group">
              <label>Naturalidade</label>
              <input type="text" name="naturalidade" value={form.naturalidade} onChange={handleChange} />
            </div>
            <div className="form-group form-group--dn">
              <label>DN</label>
              <input type="text" name="dn" value={form.dn} onChange={handleChange} maxLength={10} placeholder="DD/MM/AAAA" />
            </div>
            <div className="form-group form-group--idade">
              <label>Idade</label>
              <input type="text" name="idade" value={form.idade} onChange={handleChange} />
            </div>

            { /* CPF | CARTÃO SUS | SEXO */ }
            <div className="form-group">
              <label>CPF</label>
              <input type="text" name="cpf" ref={cpfRef} value={form.cpf} onChange={handleChange} onBlur={handleBlur} maxLength={14} placeholder="000.000.000-00" className={errors.cpf ? "input--invalid" : ""} />
            </div>
            <div className="form-group">
              <label>Cartão SUS</label>
              <input type="text" name="sus" value={form.sus} onChange={handleChange} onBlur={handleBlur} maxLength={19} placeholder="000 0000 0000 0000" className={errors.sus ? "input--invalid" : ""} />
            </div>
            <div className="form-group">
              <label>Sexo</label>
              <div className="radio-group">
                <input type="radio" id="sexo-m" name="sexo" value="M" checked={form.sexo === "M"} onChange={handleChange} className="radio-input-hidden" />
                <label htmlFor="sexo-m" className="radio-label">M</label>
                <input type="radio" id="sexo-f" name="sexo" value="F" checked={form.sexo === "F"} onChange={handleChange} className="radio-input-hidden" />
                <label htmlFor="sexo-f" className="radio-label">F</label>
              </div>
            </div>

            { /* ESTADO CIVIL */ }
            <div className="form-group form-group--full">
              <label>Estado Civil</label>
              <div className="radio-group">
                {["SOLTEIRO", "CASADO", "UNIÃO ESTÁVEL", "DIVORCIADO", "VIÚVO"].map((op) => {
                  const id = "civil-" + op.replace(/\s+/g, "-");
                  return (
                    <Fragment key={op}>
                      <input type="radio" id={id} name="civil" value={op} checked={form.civil?.toUpperCase() === op} onChange={handleChange} className="radio-input-hidden" />
                      <label htmlFor={id} className="radio-label">{op.charAt(0) + op.slice(1).toLowerCase()}</label>
                    </Fragment>
                  );
                })}
              </div>
            </div>

            { /* RAÇA/COR | OCUPAÇÃO */ }
            <div className="form-group form-group--double">
              <label>Raça / Cor</label>
              <div className="radio-group">
                {["BRANCA", "PRETA", "PARDA", "AMARELA", "INDÍGENA"].map((op) => {
                  const id = "raca-" + op.replace(/\s+/g, "-");
                  return (
                    <Fragment key={op}>
                      <input type="radio" id={id} name="raca" value={op} checked={form.raca?.toUpperCase() === op} onChange={handleChange} className="radio-input-hidden" />
                      <label htmlFor={id} className="radio-label">{op.charAt(0) + op.slice(1).toLowerCase()}</label>
                    </Fragment>
                  );
                })}
              </div>
            </div>
            <div className="form-group">
              <label>Ocupação</label>
              <input type="text" name="ocupacao" value={form.ocupacao} onChange={handleChange} />
            </div>

            { /* NOME DA MÃE */ }
            <div className="form-group form-group--full">
              <label>Nome da Mãe</label>
              <input type="text" name="mae" value={form.mae} onChange={handleChange} />
            </div>

            { /* RESPONSÁVEL | TELEFONE */ }
            <div className="form-group form-group--double">
              <label>Responsável</label>
              <input type="text" name="responsavel" value={form.responsavel} onChange={handleChange} />
            </div>
            <div className="form-group">
              <label>Telefone</label>
              <input type="text" name="tel" value={form.tel} onChange={handleChange} />
            </div>

            { /* ENDEREÇO | N° */ }
            <div className="form-group form-group--double">
              <label>Endereço</label>
              <input type="text" name="endereco" value={form.endereco} onChange={handleChange} />
            </div>
            <div className="form-group form-group--numero">
              <label>N°</label>
              <div className="input-row">
                <input type="text" name="numero" value={form.numero} onChange={handleChange} className="input-narrow" />
                <button type="button" className="btn-family-inline" onClick={handleFamily} title="Preencher endereço do último paciente da família">Família</button>
              </div>
            </div>

            { /* BAIRRO | CIDADE | UF */ }
            <div className="form-group">
              <label>Bairro</label>
              <input type="text" name="bairro" value={form.bairro} onChange={handleChange} />
            </div>
            <div className="form-group">
              <label>Cidade</label>
              <input type="text" name="cidade" value={form.cidade} onChange={handleChange} />
            </div>
            <div className="form-group">
              <label>UF</label>
              <input type="text" name="estado" value={form.estado} onChange={handleChange} maxLength={2} />
            </div>

          </div>
        </div>
      </div>

      {/* ── Histórico do paciente ─────────────────────────── */}
      {history.length > 0 && (
        <div className="history-panel">
          <h3>Últimos atendimentos {totalDesdeAbril > 5 && <span className="total-badge">({totalDesdeAbril} desde 01/04/2026)</span>}</h3>
          <table>
            <thead>
              <tr><th>Data</th><th>Hora</th><th>Registro</th><th>Procedência</th></tr>
            </thead>
            <tbody>
              {history.map((h, i) => (
                <tr key={i}>
                  <td>{formatDateBR(h.data_atendimento)}</td>
                  <td>{h.hora_atendimento}</td>
                  <td>{h.registro || "-"}</td>
                  <td>{h.procedencia || "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* ── Ficha A4 (invisível na tela, usada só na impressão) ── */}
      <FichaA4Print
        paciente={form}
        onChange={handleChange}
      />
    </div>
  );
}

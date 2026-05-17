import { useState, useCallback } from "react";
import api from "../services/api";
import FichaA4Print from "../components/FichaA4Print";
import "./Recepcao.css";

const INITIAL_STATE = {
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
};

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
  const [form, setForm] = useState({ ...INITIAL_STATE });
  const [searchTerm, setSearchTerm] = useState("");
  const [results, setResults] = useState([]);
  const [totalResults, setTotalResults] = useState(0);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [isNew, setIsNew] = useState(false);

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
      cpf: maskCPF(patient.cpf || ""),
      sus: maskSUS(patient.sus || ""),
      registro: patient.registro || "",
      nome: patient.nome || "",
      nomeSocial: patient.nomeSocial || "",
      naturalidade: patient.naturalidade || "",
      dn: maskDate(patient.dn || ""),
      idade: patient.idade || "",
      sexo: patient.sexo || "",
      civil: patient.civil || "",
      raca: patient.raca || "",
      ocupacao: patient.ocupacao || "",
      mae: patient.mae || "",
      responsavel: patient.responsavel || "",
      tel: patient.tel || "",
      endereco: patient.endereco || "",
      numero: patient.numero || "",
      bairro: patient.bairro || "",
      cidade: patient.cidade || "EXTREMOZ",
      estado: patient.estado || "RN",
    });
    setIsNew(false);
    setResults([]);
    setSearchTerm("");
  };

  // ── Novo ──────────────────────────────────────────────────

  const handleNew = () => {
    setForm({ ...INITIAL_STATE });
    setIsNew(true);
    setResults([]);
    setSearchTerm("");
  };

  // ── Atualizar campo ──────────────────────────────────────

  const handleChange = (e) => {
    const { name, value } = e.target;
    let v = value;
    if (name === "cpf") v = maskCPF(value);
    else if (name === "sus") v = maskSUS(value);
    else if (name === "dn") v = maskDate(value);
    setForm((prev) => ({ ...prev, [name]: v }));
  };

  // ── Salvar ───────────────────────────────────────────────

  const handleSave = async () => {
    const cleanCPF = unmask(form.cpf);
    if (cleanCPF.length !== 11) {
      mostrarToast("CPF deve ter 11 dígitos", "warning");
      return;
    }
    const payload = { ...form, cpf: cleanCPF };
    setSaving(true);
    try {
      if (isNew) {
        await api.post("/recepcao/pacientes", payload);
        mostrarToast("Cadastrado com sucesso!", "success");
      } else {
        await api.put(`/recepcao/pacientes/${cleanCPF}`, payload);
        mostrarToast("Atualizado com sucesso!", "success");
      }
      setIsNew(false);
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
        <button className="btn-new" onClick={handleNew}>
          + Novo
        </button>
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
                  {p.dn || ""} {p.mae ? `| ${p.mae}` : ""}
                </span>
              </div>
              <span className="cpf">{p.cpf}</span>
            </div>
          ))}
        </div>
      )}

      {/* ── Botões de ação (fora do A4, não aparecem na impressão) ── */}
      <div className="action-bar">
        <button className="btn-save" onClick={handleSave} disabled={saving}>
          {saving ? "Salvando..." : "Salvar"}
        </button>
        <button className="btn-print" onClick={handlePrint}>
          Imprimir
        </button>
        <button className="btn-clear" onClick={handleNew}>
          Limpar
        </button>
      </div>

      {/* ── Formulário A4 (editável na tela, usado na impressão) ── */}
      <FichaA4Print
        paciente={form}
        onChange={handleChange}
      />
    </div>
  );
}

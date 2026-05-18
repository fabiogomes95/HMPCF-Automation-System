import React, { useState, useCallback } from "react";
import api from "../services/api";
import "./Integracao.css";

const FERRAMENTAS = [
  { id: "exportar-bpa", icon: "📤", label: "Exportar SQLite → TXT BPA", desc: "Gera arquivo posicional para o Datasus", download: true, fields: [
    { id: "mes_ano", label: "Mês/Ano (MMAAAA)", placeholder: "Ex: 052025", defaultValue: "" },
  ]},
  { id: "importar-csv", icon: "📥", label: "Importar CSV em Lote", desc: "Importa CSVs com Smart Update", fields: [
    { id: "separador", label: "Separador", placeholder: "Ex: ;", defaultValue: ";" },
    { id: "caminho_arquivo", label: "Caminho do CSV", placeholder: "Deixe vazio para varrer pasta", defaultValue: "" },
  ]},
  { id: "converter-csv", icon: "📂", label: "Converter CSV Antigo → TXT", desc: "Converte CSVs legados para layout BPA", fields: [
    { id: "caminho_arquivo", label: "Caminho do CSV", placeholder: "Deixe vazio para auto-detectar", defaultValue: "" },
    { id: "caminho_salvar", label: "Caminho para salvar", placeholder: "Deixe vazio para padrão", defaultValue: "" },
  ]},
  { id: "sincronizar-contingencia", icon: "🆘", label: "Sincronizar Contingência", desc: "Importa planilhas manuais offline", fields: [
    { id: "caminho_arquivo", label: "Caminho do CSV", placeholder: "C:\\planilha_contingencia.csv", defaultValue: "" },
  ]},
  { id: "sincronizar-firebird", icon: "🔄", label: "Sincronizar Firebird", desc: "Padroniza dados no BPAMAG.GDB", fields: [
    { id: "mes_ano", label: "Mês/Ano", placeholder: "Opcional", defaultValue: "" },
  ]},
  { id: "corrigir-nulls", icon: "💣", label: "Aniquilar NULLs no Firebird", desc: "Remove campos NULL do BPAMAG.GDB", fields: [] },
  { id: "limpar-duplicatas", icon: "🧹", label: "Limpar Duplicatas no Firebird", desc: "Remove fichas duplicadas por pontuação", fields: [] },
  { id: "backup", icon: "💾", label: "Fazer Backup", desc: "Cria cópia timestamp de um arquivo", fields: [
    { id: "caminho_arquivo", label: "Caminho do arquivo", placeholder: "Ex: C:\\BPA\\BPAMAG.GDB", defaultValue: "" },
  ]},
];

function ModalParams({ ferramenta, onConfirm, onCancel }) {
  const [params, setParams] = useState(() => {
    const initial = {};
    ferramenta.fields.forEach((f) => { initial[f.id] = f.defaultValue || ""; });
    return initial;
  });

  return (
    <div className="modal-overlay" onClick={onCancel}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <h3>{ferramenta.icon} {ferramenta.label}</h3>
        <p className="modal-desc">Preencha os campos ou deixe vazio para usar valores padrão:</p>
        {ferramenta.fields.map((f) => (
          <div key={f.id} className="modal-field">
            <label>{f.label}</label>
            <input
              type="text"
              placeholder={f.placeholder}
              value={params[f.id]}
              onChange={(e) => setParams((p) => ({ ...p, [f.id]: e.target.value }))}
              autoFocus={f === ferramenta.fields[0]}
            />
          </div>
        ))}
        <div className="modal-actions">
          <button className="bpa-btn-sm bpa-btn-cancel" onClick={onCancel}>Cancelar</button>
          <button className="bpa-btn-sm" onClick={() => onConfirm(params)}>Executar</button>
        </div>
      </div>
    </div>
  );
}

export default function Integracao() {
  const [linhas, setLinhas] = useState(["🚀 Clique em uma ferramenta acima para executar..."]);
  const [executando, setExecutando] = useState(null);
  const [modal, setModal] = useState(null);

  const linhaAtual = (data) => `[${data.toLocaleTimeString("pt-BR")}] `;

  const baixar = useCallback(async (ferramenta, params) => {
    setExecutando(ferramenta.id);
    setLinhas((prev) => [...prev, "", `${linhaAtual(new Date())}🚀 Baixando ${ferramenta.label}...`]);
    try {
      const r = await api.post(`/integracao/${ferramenta.id}/download`, params, { responseType: "blob" });
      const disp = r.headers["content-disposition"] || "";
      const match = disp.match(/filename="?(.+?)"?$/);
      const nome = match ? match[1] : `${ferramenta.id}.txt`;
      const url = URL.createObjectURL(r.data);
      const a = document.createElement("a");
      a.href = url;
      a.download = nome;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      setLinhas((prev) => [...prev, `✅ Arquivo "${nome}" baixado com sucesso!`, `${linhaAtual(new Date())}✅ Finalizado.`]);
    } catch (e) {
      setLinhas((prev) => [...prev, `${linhaAtual(new Date())}❌ Erro: ${e.message}`]);
    } finally {
      setExecutando(null);
    }
  }, []);

  const executar = useCallback(async (ferramenta, params) => {
    if (ferramenta.download) {
      await baixar(ferramenta, params);
      return;
    }
    setExecutando(ferramenta.id);
    setLinhas((prev) => [...prev, "", `${linhaAtual(new Date())}🚀 Executando ${ferramenta.label}...`]);
    try {
      const r = await api.post(`/integracao/${ferramenta.id}`, params);
      const texto = r.data.saida || "✅ Concluído.";
      setLinhas((prev) => [...prev, texto, `${linhaAtual(new Date())}✅ Finalizado.`]);
    } catch (e) {
      setLinhas((prev) => [...prev, `${linhaAtual(new Date())}❌ Erro: ${e.message}`]);
    } finally {
      setExecutando(null);
    }
  }, [baixar]);

  const handleCardClick = (f) => {
    if (executando) return;
    if (f.fields.length > 0) {
      setModal(f);
    } else {
      executar(f, {});
    }
  };

  const handleModalConfirm = (params) => {
    const f = modal;
    setModal(null);
    executar(f, params);
  };

  return (
    <div className="integracao-page">
      <h2 className="integracao-title">🔌 Módulo de Integração SUS</h2>
      <p className="integracao-subtitle">Ferramentas de exportação, importação e sincronização</p>

      <div className="integracao-cards">
        {FERRAMENTAS.map((f) => (
          <div
            key={f.id}
            className={`integracao-card${executando === f.id ? " integracao-card--exec" : ""}${executando && executando !== f.id ? " integracao-card--disabled" : ""}`}
            onClick={() => handleCardClick(f)}
          >
            <div className="integracao-card-icon">{executando === f.id ? "⏳" : f.icon}</div>
            <h5>{f.label}</h5>
            <p>{f.desc}</p>
          </div>
        ))}
      </div>

      {modal && (
        <ModalParams
          ferramenta={modal}
          onConfirm={handleModalConfirm}
          onCancel={() => setModal(null)}
        />
      )}

      <div className="integracao-output">
        <div className="integracao-output-header">
          <span>📋 Terminal de Saída</span>
          <button className="bpa-btn-sm bpa-btn-cancel" onClick={() => setLinhas(["🚀 Clique em uma ferramenta acima para executar..."])}>Limpar</button>
        </div>
        <textarea className="integracao-output-text" value={linhas.join("\n")} readOnly rows={16} />
      </div>
    </div>
  );
}

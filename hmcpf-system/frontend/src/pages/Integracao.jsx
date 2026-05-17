import React, { useState } from "react";
import api from "../services/api";
import "./Integracao.css";

const FERRAMENTAS = [
  { id: "exportar-bpa", icon: "📤", label: "Exportar SQLite → TXT BPA", desc: "Gera arquivo posicional para o Datasus", fields: [
    { id: "mes_ano", label: "Mês/Ano (MMAAAA)", placeholder: "Ex: 052025" },
    { id: "caminho_salvar", label: "Caminho para salvar", placeholder: "Deixe vazio para padrão" },
  ]},
  { id: "importar-csv", icon: "📥", label: "Importar CSV em Lote", desc: "Importa CSVs com Smart Update", fields: [
    { id: "separador", label: "Separador", placeholder: "Ex: ;", valor: ";" },
    { id: "caminho_arquivo", label: "Caminho do CSV", placeholder: "Deixe vazio para varrer pasta" },
  ]},
  { id: "converter-csv", icon: "📂", label: "Converter CSV Antigo → TXT", desc: "Converte CSVs legados para layout BPA", fields: [
    { id: "caminho_arquivo", label: "Caminho do CSV", placeholder: "Deixe vazio para auto-detectar" },
    { id: "caminho_salvar", label: "Caminho para salvar", placeholder: "Deixe vazio para padrão" },
  ]},
  { id: "sincronizar-firebird", icon: "🔄", label: "Sincronizar Firebird", desc: "Padroniza dados no BPAMAG.GDB", fields: [
    { id: "mes_ano", label: "Mês/Ano", placeholder: "Opcional" },
  ]},
  { id: "corrigir-nulls", icon: "💣", label: "Aniquilar NULLs no Firebird", desc: "Remove campos NULL do BPAMAG.GDB", fields: [] },
  { id: "limpar-duplicatas", icon: "🧹", label: "Limpar Duplicatas no Firebird", desc: "Remove fichas duplicadas por pontuação", fields: [] },
  { id: "backup", icon: "💾", label: "Fazer Backup", desc: "Cria cópia timestamp de um arquivo", fields: [
    { id: "caminho_arquivo", label: "Caminho do arquivo", placeholder: "Ex: C:\\BPA\\BPAMAG.GDB" },
  ]},
];

export default function Integracao() {
  const [saida, setSaida] = useState("🚀 Clique em uma ferramenta acima para executar...");
  const [executando, setExecutando] = useState(false);

  const executar = async (ferramenta) => {
    const params = {};
    if (ferramenta.fields) {
      ferramenta.fields.forEach((f) => {
        const el = document.getElementById(`param_${ferramenta.id}_${f.id}`);
        params[f.id] = el ? el.value.trim() : (f.valor || "");
      });
    }
    setExecutando(true);
    const label = ferramenta.label;
    setSaida((prev) => prev + `\n\n[${new Date().toLocaleTimeString("pt-BR")}] 🚀 Executando ${label}...\n`);
    try {
      const r = await api.post(`/integracao/${ferramenta.id}`, params);
      setSaida((prev) => prev + (r.data.saida || "") + "\n✅ Concluído.\n");
    } catch (e) {
      setSaida((prev) => prev + `\n❌ Erro: ${e.message}\n`);
    } finally {
      setExecutando(false);
    }
  };

  const limpar = () => setSaida("");

  return (
    <div className="integracao-page">
      <h2 className="integracao-title">🔌 Módulo de Integração SUS</h2>
      <p className="integracao-subtitle">Ferramentas de exportação, importação e sincronização</p>

      <div className="integracao-cards">
        {FERRAMENTAS.map((f) => (
          <div key={f.id} className="integracao-card" onClick={() => executar(f)}>
            <div className="integracao-card-icon">{f.icon}</div>
            <h5>{f.label}</h5>
            <p>{f.desc}</p>
          </div>
        ))}
      </div>

      <div className="integracao-output">
        <div className="integracao-output-header">
          <span>📋 Terminal de Saída</span>
          <button className="bpa-btn-sm bpa-btn-cancel" onClick={limpar}>Limpar</button>
        </div>
        <textarea className="integracao-output-text" value={saida} readOnly rows={16} />
      </div>
    </div>
  );
}

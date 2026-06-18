import { useState } from "react";
import { bpaLerLote, bpaSalvarLote } from "../../services/api";
import {
  extrairDocumentosValidos,
  dividirEmLotes,
  nomeArquivoLote,
  formatDateBR,
} from "../../utils";

export default function Triagem() {
  const [data, setData] = useState("");
  const [profissionaisStr, setProfissionaisStr] = useState("");
  const [textoSujo, setTextoSujo] = useState("");
  const [resultado, setResultado] = useState("");
  const [msg, setMsg] = useState(null);
  const [salvando, setSalvando] = useState(false);

  function processar() {
    if (!data || data.length < 10) {
      setMsg({ tipo: "erro", texto: "Preencha a data completa (DD/MM/AAAA)." });
      return;
    }
    if (!profissionaisStr.trim()) {
      setMsg({ tipo: "erro", texto: "Informe ao menos um enfermeiro." });
      return;
    }

    const documentos = extrairDocumentosValidos(textoSujo);
    if (documentos.length === 0) {
      setMsg({ tipo: "erro", texto: "Nenhum CNS/CPF válido encontrado no texto colado." });
      setResultado("");
      return;
    }

    const profissionais = profissionaisStr.split(",");
    const formatado = dividirEmLotes(documentos, profissionais, data);
    setResultado(formatado);
    setMsg({
      tipo: "ok",
      texto: `${documentos.length} documento(s) válido(s) — dividido em lotes de até 99.`,
    });
  }

  async function salvarLote() {
    if (!resultado) {
      setMsg({ tipo: "erro", texto: "Processe o texto antes de salvar." });
      return;
    }
    setSalvando(true);
    const arquivo = nomeArquivoLote(data);
    try {
      let atual = "";
      try {
        const res = await bpaLerLote(arquivo);
        atual = res.data.conteudo || "";
      } catch {
        // arquivo ainda não existe — começa do zero
      }
      const novoConteudo = atual ? `${atual}\n${resultado}` : resultado;
      await bpaSalvarLote(arquivo, novoConteudo);
      setMsg({ tipo: "ok", texto: `Lote salvo em ${arquivo} (adicionado ao final, se já existia).` });
    } catch (e) {
      setMsg({ tipo: "erro", texto: `Erro ao salvar: ${e.response?.data?.detail || e.message}` });
    } finally {
      setSalvando(false);
    }
  }

  return (
    <div className="bpa-card">
      <p className="bpa-card-titulo">🧹 Triagem — organizar CPF/SUS por enfermeiro</p>

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
        <div className="bpa-field" style={{ flex: 1, minWidth: 260 }}>
          <label>Enfermeiros (separe por vírgula)</label>
          <input
            className="bpa-input"
            style={{ width: "100%" }}
            placeholder="Ex: MARIA ALVES, JOAO SILVA, ANA SOUZA"
            value={profissionaisStr}
            onChange={(e) => setProfissionaisStr(e.target.value)}
          />
        </div>
        <button className="bpa-btn bpa-btn-aviso" onClick={processar}>
          Reordenar e dividir
        </button>
        <button className="bpa-btn bpa-btn-primario" onClick={salvarLote} disabled={salvando || !resultado}>
          {salvando ? "Salvando…" : "Salvar lote"}
        </button>
      </div>

      {msg && (
        <p className={`bpa-status-msg ${msg.tipo === "ok" ? "" : ""}`} style={{ color: msg.tipo === "ok" ? "#166534" : "#991b1b" }}>
          {msg.texto}
        </p>
      )}

      <div className="bpa-grid-2">
        <div>
          <p className="bpa-card-titulo">📄 Rascunho (cole os dados sujos aqui)</p>
          <textarea
            className="bpa-textarea"
            spellCheck={false}
            placeholder="Cole aqui os dados de CPF/SUS, um por linha (pode ter texto junto, ex: nome + número)..."
            value={textoSujo}
            onChange={(e) => setTextoSujo(e.target.value)}
          />
        </div>
        <div>
          <p className="bpa-card-titulo">🤖 Lote formatado (pronto para salvar)</p>
          <textarea
            className="bpa-textarea bpa-textarea--leitura"
            spellCheck={false}
            readOnly
            placeholder="O resultado fatiado de 99 em 99, por enfermeiro, aparecerá aqui..."
            value={resultado}
          />
        </div>
      </div>
    </div>
  );
}

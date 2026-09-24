// Conversa com o BPA LOCAL do notebook (http://localhost:8503) — não com o
// servidor. Firebird e BPA Magnético ficam no notebook; esta página, servida
// pelo servidor, chama o BPA do próprio PC pelo navegador (o BPA só aceita
// pedidos vindos do sistema do hospital — ver bpa/bpa_local/main.py).

export const URL_BPA_LOCAL = "http://localhost:8503";

// Erro quando o BPA do notebook não responde (desligado / PC sem BPA)
export class BpaDesligado extends Error {}

async function req(caminho, { metodo = "GET", corpo, params, timeout = 20000 } = {}) {
  const url = new URL(URL_BPA_LOCAL + caminho);
  Object.entries(params || {}).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") url.searchParams.set(k, v);
  });
  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(), timeout);
  let resp;
  try {
    resp = await fetch(url, {
      method: metodo,
      headers: corpo ? { "Content-Type": "application/json" } : undefined,
      body: corpo ? JSON.stringify(corpo) : undefined,
      signal: ctrl.signal,
    });
  } catch (e) {
    if (e.name === "AbortError") throw new Error("O BPA demorou demais para responder.");
    throw new BpaDesligado("BPA deste notebook não está respondendo.");
  } finally {
    clearTimeout(t);
  }
  if (!resp.ok) throw new Error(`BPA respondeu com erro (HTTP ${resp.status}).`);
  return resp.json();
}

// Consultas ao Firebird podem levar minutos em meses grandes
const LONGO = 5 * 60 * 1000;

export const bpaLocal = {
  status: () => req("/api/status", { timeout: 5000 }),
  recarregar: () => req("/api/recarregar", { metodo: "POST", timeout: LONGO }),
  profissionais: () => req("/api/profissionais"),
  competencias: () => req("/api/competencias"),

  // Digitação
  buscar: (q) => req("/api/buscar", { params: { q, incluir_sus: "0" } }),
  cabecalho: (medico, cns, data) => req("/api/cabecalho", { metodo: "POST", corpo: { medico, cns, data } }),
  gravar: (arquivo, cpf, nome) => req("/api/gravar", { metodo: "POST", corpo: { arquivo, cpf, nome } }),
  desfazer: (arquivo, cpf) => req("/api/desfazer", { metodo: "POST", corpo: { arquivo, cpf } }),
  lotes: () => req("/api/lotes"),
  lote: (arquivo) => req("/api/lote", { params: { arquivo } }),
  gerar: (arquivo, categoria) => req("/api/gerar", { metodo: "POST", corpo: { arquivo, categoria }, timeout: LONGO }),

  // Enfermeiros
  dividir: (data, enfermeiros) =>
    req("/api/enfermeiros/dividir", { metodo: "POST", corpo: { data, enfermeiros }, timeout: LONGO }),

  // Migração
  migracaoPreview: (mes) => req("/api/migracao/preview", { metodo: "POST", corpo: { mes }, timeout: LONGO }),
  migracaoStreamUrl: (mes) => `${URL_BPA_LOCAL}/api/migracao/stream?mes=${encodeURIComponent(mes)}`,

  // Conferência
  conferencia: (dataIni, dataFim) =>
    req("/api/conferencia", { params: { data_ini: dataIni, data_fim: dataFim }, timeout: LONGO }),
  reenviar: (dataIni, dataFim, commit) =>
    req("/api/conferencia/reenviar", { metodo: "POST", corpo: { data_ini: dataIni, data_fim: dataFim, commit }, timeout: LONGO }),

  // Consultas
  prontuario: (q) => req("/api/prontuario/buscar", { params: { q }, timeout: LONGO }),
};

// ── Formatação comum das telas do BPA ────────────────────────────────────────
export const fmtCpf = (c) => (c && c.length === 11 ? c.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, "$1.$2.$3-$4") : c || "");
export const fmtSus = (s) => (s && s.length === 15 ? s.replace(/(\d{3})(\d{4})(\d{4})(\d{4})/, "$1 $2 $3 $4") : s || "");
export const fmtNum = (n) => (n ?? 0).toLocaleString("pt-BR");

export function hojeBR() {
  const d = new Date();
  return `${String(d.getDate()).padStart(2, "0")}/${String(d.getMonth() + 1).padStart(2, "0")}/${d.getFullYear()}`;
}

// "22092026" digitado -> "22/09/2026" enquanto digita
export function mascaraData(v) {
  const n = v.replace(/\D/g, "").slice(0, 8);
  if (n.length >= 5) return `${n.slice(0, 2)}/${n.slice(2, 4)}/${n.slice(4)}`;
  if (n.length >= 3) return `${n.slice(0, 2)}/${n.slice(2)}`;
  return n;
}

export const dataParaArquivo = (dataBR) => `${dataBR.replace(/\//g, "-")}.txt`; // "22/09/2026" -> "22-09-2026.txt"
export const arquivoParaData = (arq) => arq.replace(".txt", "").replace(/-/g, "/");

// Arquivo BPA-I que o BPA local gera para o lote do dia: "22-09-2026.txt" -> "BPA_MEDICOS_22092026.txt"
export const arquivoGerado = (lote, categoria) =>
  `BPA_${categoria === "enfermeiro" ? "ENFERMEIROS" : "MEDICOS"}_${lote.replace(".txt", "").replace(/-/g, "")}.txt`;

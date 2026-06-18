import axios from "axios";

const api = axios.create({
  baseURL: "/api/v1",
  timeout: 15000,
});

// DD/MM/YYYY + HH:MM → YYYY-MM-DDTHH:MM:00 (ISO para o backend)
function toISODatetime(dataBR, hora) {
  if (!dataBR || !hora) return null;
  const partes = dataBR.split("/");
  if (partes.length !== 3) return null;
  const [dia, mes, ano] = partes;
  return `${ano}-${mes}-${dia}T${hora}:00`;
}

// Backend → Frontend: normaliza campos com nomes diferentes
function normalizePaciente(p) {
  if (!p) return p;
  return {
    ...p,
    // ddtel_pcnte ("84") + tel_pcnte ("991668229") → telefone ("84991668229")
    telefone: (p.ddtel_pcnte || "") + (p.tel_pcnte || ""),
    // civil → estado_civil
    estado_civil: p.civil || "",
  };
}

// Frontend → Backend: converte campos antes de enviar
function desnormalizePaciente(dados) {
  const out = { ...dados };
  // telefone → ddtel_pcnte + tel_pcnte
  const tel = (out.telefone || "").replace(/\D/g, "");
  out.ddtel_pcnte = tel.slice(0, 2) || null;
  out.tel_pcnte   = tel.slice(2)   || null;
  delete out.telefone;
  // estado_civil → civil
  out.civil = out.estado_civil || null;
  delete out.estado_civil;
  return out;
}

export async function buscarPaciente(documento) {
  const res = await api.get("/pacientes/busca", { params: { documento } });
  return { ...res, data: normalizePaciente(res.data) };
}

export function criarPaciente(dados) {
  return api.post("/pacientes/", desnormalizePaciente(dados));
}

export function atualizarPaciente(id, dados) {
  return api.put(`/pacientes/${id}`, desnormalizePaciente(dados));
}

export function listarAtendimentos(page = 1, q = "") {
  const params = { page, page_size: 20 };
  if (q && q.trim()) params.q = q.trim();
  return api.get("/recepcao/", { params });
}

export function buscarPacientesAgrupados(q, page = 1, pageSize = 20) {
  return api.get("/recepcao/pacientes/agrupado", { params: { q, page, page_size: pageSize } });
}

export function listarAtendimentosPorPaciente(pacienteId, page = 1, pageSize = 10) {
  return api.get(`/recepcao/paciente/${pacienteId}`, { params: { page, page_size: pageSize } });
}

export function criarRecepcao(dados) {
  return api.post("/recepcao/", dados);
}

export function atualizarRecepcao(id, dados) {
  return api.put(`/recepcao/${id}`, dados);
}

export function criarAtendimento({ paciente_id, data_atendimento, hora_atendimento, registro, procedencia }) {
  const num = parseInt(registro, 10);
  return api.post("/recepcao/", {
    paciente_id,
    data_atendimento: toISODatetime(data_atendimento, hora_atendimento),
    registro: isNaN(num) ? null : num,
    procedencia: procedencia || null,
  });
}

export function atualizarAtendimento(id, { data_atendimento, hora_atendimento, procedencia }) {
  return api.put(`/recepcao/${id}`, {
    data_atendimento: toISODatetime(data_atendimento, hora_atendimento),
    procedencia: procedencia || null,
  });
}

export function iniciarSessao(terminal_nome, ip_address) {
  return api.post("/terminal/start", { terminal_nome, ip_address: ip_address || "" });
}

export function pingSessao(terminal_nome) {
  return api.post("/terminal/ping", null, { params: { terminal_nome } });
}

// ── BPA ───────────────────────────────────────────────────────────────────
export function bpaListarProfissionais() {
  return api.get("/bpa/profissionais");
}

export function bpaBuscarPacientes(termo) {
  return api.get("/bpa/pacientes/busca", { params: { termo } });
}

export function bpaAtualizarCache() {
  return api.post("/bpa/cache/atualizar");
}

export function bpaListarLotes() {
  return api.get("/bpa/lotes");
}

export function bpaLerLote(nome) {
  return api.get(`/bpa/lotes/${encodeURIComponent(nome)}`);
}

export function bpaSalvarLote(nome, conteudo) {
  return api.put(`/bpa/lotes/${encodeURIComponent(nome)}`, { conteudo });
}

export function bpaCriarCabecalho(arquivo, medico, data) {
  return api.post("/bpa/lotes/cabecalho", { arquivo, medico, data });
}

export function bpaAdicionarDocumento(arquivo, documento) {
  return api.post("/bpa/lotes/documento", { arquivo, documento });
}

export function bpaAnalisarLote(nome) {
  return api.post(`/bpa/lotes/${encodeURIComponent(nome)}/analisar`);
}

export function bpaGerarLote(nome, resolucoes) {
  return api.post(`/bpa/lotes/${encodeURIComponent(nome)}/gerar`, { resolucoes });
}

export function bpaUrlDownload(nomeArquivo) {
  return `/api/v1/bpa/gerar/download/${encodeURIComponent(nomeArquivo)}`;
}

export default api;

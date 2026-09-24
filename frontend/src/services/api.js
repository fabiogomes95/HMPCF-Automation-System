import axios from "axios";

const api = axios.create({
  baseURL: "/api/v1",
  timeout: 15000,
  withCredentials: true, // envia/recebe o cookie de sessão (ver services/auth.js)
});

// App.jsx registra aqui o que fazer quando qualquer chamada volta 401
// (sessão ausente/expirada) — evita cada tela ter que checar isso na mão.
let _onUnauthorized = null;
export function setOnUnauthorized(fn) {
  _onUnauthorized = fn;
}

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && _onUnauthorized) {
      _onUnauthorized();
    }
    return Promise.reject(error);
  }
);

// Texto de erro legível de uma resposta do backend. Erros de domínio vêm em
// `message`; erros de validação do Pydantic vêm em `detail`.
export function mensagemErro(err, padrao) {
  const data = err?.response?.data || {};
  if (typeof data.message === "string" && data.message) return data.message;
  if (typeof data.detail === "string" && data.detail) return data.detail;
  return padrao;
}

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

export function buscarPlanilhaMensal(ano, mes) {
  return api.get("/recepcao/planilha", { params: { ano, mes } });
}

// Só um plantão (dia de referência + turno) -- leve, pro refresh rápido.
export function buscarPlanilhaPlantao(dia, turno) {
  return api.get("/recepcao/planilha/plantao", { params: { dia, turno } });
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

export function atualizarAtendimento(id, { paciente_id, data_atendimento, hora_atendimento, procedencia }) {
  return api.put(`/recepcao/${id}`, {
    ...(paciente_id ? { paciente_id } : {}),
    data_atendimento: toISODatetime(data_atendimento, hora_atendimento),
    procedencia: procedencia || null,
  });
}

// Só o nº de registro -- não reenvia data/hora (evita mexer no horário sem querer).
export function atualizarRegistroAtendimento(id, registro) {
  const num = parseInt(registro, 10);
  return api.put(`/recepcao/${id}`, { registro: isNaN(num) ? null : num });
}

// Busca pacientes por nome/CPF/CNS -- inclusive os que ainda não têm atendimento.
export function buscarPacientesPorNome(q, pageSize = 15) {
  return api.get("/pacientes/", { params: { q, page: 1, page_size: pageSize } });
}

// ── TI: usuários ─────────────────────────────────────────────────────────────
export function excluirAtendimento(id) { return api.delete(`/ti/atendimentos/${id}`); }
// Recepção e TI -- o backend só aceita se o atendimento for mesmo repetido.
export function excluirAtendimentoRepetido(id) { return api.delete(`/recepcao/${id}/repetido`); }
export function listarUsuarios() { return api.get("/ti/usuarios"); }
export function criarUsuario(dados) { return api.post("/ti/usuarios", dados); }
export function resetarSenhaUsuario(id, nova_senha) { return api.patch(`/ti/usuarios/${id}/senha`, { nova_senha }); }
export function toggleAtivoUsuario(id, ativo) { return api.patch(`/ti/usuarios/${id}/ativo`, { ativo }); }
// Painel gerencial (TI) -- só agregados; periodo: hoje | 7d | 30d | mes | tudo
export function buscarPainel(periodo) { return api.get("/ti/painel", { params: { periodo } }); }

// Aba Entradas (faturamento e TI)
export function buscarEntradas(q, fonte) { return api.get("/entradas", { params: { q, fonte } }); }
export function resumoPlanilhas() { return api.get("/entradas/planilhas"); }

// ── Alterar própria senha ─────────────────────────────────────────────────────
export function alterarSenha(senha_atual, senha_nova) { return api.post("/auth/change-password", { senha_atual, senha_nova }); }

// ── Correção manual de atendimento ────────────────────────────────────────────
export function criarAtendimentoManual({ paciente_id, data, hora, registro, procedencia }) {
  const num = parseInt(registro, 10);
  return api.post("/recepcao/", {
    paciente_id,
    data_atendimento: `${data}T${hora}:00`,
    registro: isNaN(num) ? null : num,
    procedencia: procedencia || null,
  });
}
export function editarAtendimentoManual(id, { data, hora, registro }) {
  const num = parseInt(registro, 10);
  return api.put(`/recepcao/${id}`, {
    data_atendimento: `${data}T${hora}:00`,
    registro: isNaN(num) ? null : num,
  });
}

export function iniciarSessao(terminal_nome, ip_address) {
  return api.post("/terminal/start", { terminal_nome, ip_address: ip_address || "" });
}

export function pingSessao(terminal_nome) {
  return api.post("/terminal/ping", null, { params: { terminal_nome } });
}

export default api;

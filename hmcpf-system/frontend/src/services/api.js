import axios from "axios";

const api = axios.create({
  baseURL: "/api/v1",
  timeout: 15000,
});

export function buscarPaciente(documento) {
  return api.get("/pacientes/busca", { params: { documento } });
}

export function criarPaciente(dados) {
  return api.post("/pacientes", dados);
}

export function atualizarPaciente(id, dados) {
  return api.put(`/pacientes/${id}`, dados);
}

export function criarAtendimento(dados) {
  return api.post("/atendimentos", dados);
}

export function iniciarSessao(nome, ip) {
  return api.post("/terminal/start", {
    terminal_nome: nome,
    ip_address: ip,
  });
}

export function pingSessao(nome) {
  return api.post("/terminal/ping", null, {
    params: { terminal_nome: nome },
  });
}

export default api;

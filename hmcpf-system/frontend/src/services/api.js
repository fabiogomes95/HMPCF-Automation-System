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

export function criarRecepcao(dados) {
  return api.post("/recepcao/", dados);
}

export function atualizarRecepcao(id, dados) {
  return api.put(`/recepcao/${id}`, dados);
}

export default api;

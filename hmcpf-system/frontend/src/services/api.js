/*
 * API.JS — Serviço centralizado para chamadas HTTP ao backend.
 *
 * BIBLIOTECA: Axios
 *
 * POR QUE AXIOS EM VEZ DE FETCH?
 *   fetch é nativo do navegador, mas Axios oferece:
 *   1. Interceptors (executar código antes/depois de cada requisição)
 *   2. Timeout configurável (fetch não tem timeout nativo)
 *   3. Conversão automática de JSON
 *   4. Error handling mais consistente
 *   5. Cancelamento de requisições
 *
 * COMO USAR NOS COMPONENTES:
 *   import api from "../services/api";
 *
 *   async function listarPacientes() {
 *     const response = await api.get("/pacientes");
 *     return response.data;
 *   }
 *
 *   api.get("/health")
 *     .then(res => console.log(res.data))
 *     .catch(err => console.error(err));
 *
 * POR QUE A BASE URL É "/api/v1" E NÃO "http://localhost:8000/api/v1"?
 *   O Vite tem um proxy configurado (vite.config.js) que redireciona
 *   todas as requisições /api para o backend. Isso:
 *   1. Evita problemas de CORS em desenvolvimento
 *   2. Funciona igual em produção (Tauri ou deploy)
 *   3. Não precisa mudar URL entre ambientes
 *
 * INTERCEPTOR DE ERRO:
 *   Toda requisição que der erro passa pelo interceptor abaixo.
 *   Ele loga o erro no console com uma mensagem amigável.
 *   Futuramente pode mostrar um toast/notificação na tela.
 */
import axios from "axios";

// Cria uma instância do Axios com configurações padrão
const api = axios.create({
  // Todas as requisições começam com /api/v1
  baseURL: "/api/v1",
  // Timeout de 30 segundos (se o servidor não responder, cancela)
  timeout: 30000,
  headers: {
    "Content-Type": "application/json",
  },
});

// Interceptor de resposta (executado para CADA requisição)
api.interceptors.response.use(
  // Sucesso: passa a resposta adiante sem modificar
  (response) => response,
  // Erro: loga e repassa (o componente que chamou trata)
  (error) => {
    const message =
      error.response?.data?.detail || error.message || "Erro desconhecido";
    console.error("[API Error]", message);
    return Promise.reject(error);
  }
);

export default api;

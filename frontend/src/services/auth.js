import api from "./api";

export function login(username, password, lembrar = false) {
  return api.post("/auth/login", { username, password, lembrar });
}

export function logout() {
  return api.post("/auth/logout");
}

export function getMe() {
  return api.get("/auth/me");
}

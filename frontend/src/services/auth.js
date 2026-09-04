import api from "./api";

export function login(username, password) {
  return api.post("/auth/login", { username, password });
}

export function logout() {
  return api.post("/auth/logout");
}

export function getMe() {
  return api.get("/auth/me");
}

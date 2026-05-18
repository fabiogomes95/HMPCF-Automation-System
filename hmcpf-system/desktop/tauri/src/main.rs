// MAIN.RS — Ponto de entrada do aplicativo desktop Tauri.
//
// O QUE É TAURI?
//   Tauri é um framework para criar aplicativos desktop usando
//   tecnologias web (React, HTML, CSS) como interface, mas com
//   o "esqueleto" do app escrito em Rust.
//
//   DIFERENÇA PARA ELETRON:
//   ┌────────────────┬──────────────────┬──────────────────┐
//   │                │ Tauri            │ Electron         │
//   ├────────────────┼──────────────────┼──────────────────┤
//   │ Tamanho        │ ~5 MB            │ ~150 MB          │
//   │ Memória RAM    │ ~50 MB           │ ~200 MB          │
//   │ Linguagem      │ Rust (nativo)    │ Node.js (JS)     │
//   │ Performance    │ Excelente        │ Moderada         │
//   └────────────────┴──────────────────┴──────────────────┘
//
// windows_subsystem = "windows":
//   Em produção, a janela do console NÃO aparece.
//   O app roda silenciosamente em background.
//   Em desenvolvimento (debug), o console aparece para logs.

#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
    // Chama a função run() definida em lib.rs
    // Separar main.rs de lib.rs é uma convenção Rust que permite
    // testes de integração (testes podem importar lib.rs)
    hmcpf_desktop_lib::run();
}

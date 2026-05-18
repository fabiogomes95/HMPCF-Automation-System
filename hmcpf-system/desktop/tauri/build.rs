// BUILD.RS — Script de build do Tauri.
//
// Este arquivo é executado ANTES de compilar o projeto Rust.
// Ele gera código necessário para o Tauri funcionar:
//   - Processa tauri.conf.json
//   - Gera ícones para o sistema operacional
//   - Prepara os assets do frontend (dist/)
//
// NOTA: build.rs é padrão em projetos Tauri.
//       Raramente precisa ser modificado.

fn main() {
    tauri_build::build();
}

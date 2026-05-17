// LIB.RS — Biblioteca principal do aplicativo desktop Tauri.
//
// AQUI ACONTECE:
//   1. Inicialização do Tauri com plugins
//   2. Registro de comandos Rust (que o frontend pode chamar)
//   3. Geração do contexto da janela
//
// COMANDOS TAURI (#[tauri::command]):
//   Funções Rust que o frontend React pode chamar via:
//     await invoke("greet", { name: "João" });
//
//   Isso substitui o que o Eel fazia com @eel.expose.
//   A diferença é que aqui a comunicação é via IPC (Inter-Process
//   Communication), não WebSocket.
//
// PLUGINS:
//   tauri-plugin-shell permite executar processos externos.
//   Futuramente usaremos isso para iniciar o backend FastAPI
//   junto com o app desktop:
//
//     use tauri_plugin_shell::ShellExt;
//     let _ = app.shell().sidecar("backend").unwrap().spawn();
//
//   Assim o usuário não precisa iniciar o servidor separadamente.

use tauri::Manager;

/// Comando exemplo: saudação
///
/// O frontend chama assim:
///   const msg = await invoke("greet", { name: "Maria" });
///   console.log(msg); // "Olá, Maria! Bem-vindo ao HMPCF System."
#[tauri::command]
fn greet(name: &str) -> String {
    format!("Olá, {}! Bem-vindo ao HMPCF System.", name)
}

/// Ponto de entrada do Tauri
pub fn run() {
    tauri::Builder::default()
        // Habilita o plugin shell (para executar processos)
        .plugin(tauri_plugin_shell::init())
        // Registra os comandos que o frontend pode chamar
        .invoke_handler(tauri::generate_handler![greet])
        // Constrói a janela usando a configuração de tauri.conf.json
        .run(tauri::generate_context!())
        .expect("Erro ao iniciar aplicação Tauri");
}

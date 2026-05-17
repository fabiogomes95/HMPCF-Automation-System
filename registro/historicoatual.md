# Histórico Atual — Sessão 17/05/2026

## DB Cleanup Completo

### Normalização e Deduplicação
- Script centralizado: `hmcpf-system/scripts/limpar_banco.py`
- **CPF**: normalizados (removidos ., -, espaços) em pacientes e atendimentos
- **Duplicatas por CPF**: removidas, mantendo registro mais completo, movendo atendimentos
- **Duplicatas por nome+DN**: removidas (pega CPF trocado, ex: Taise)
- **SUS**: normalizados (removidos espaços/pontos); SUS inválidos (tamanho ≠ 15) apagados (paciente mantido via CPF)
- **Pacientes sem nome**: removidos (4 registros)
- **Pacientes com CPF inválido** (≠ 11 dígitos): removidos (139 registros, 8 atendimentos deletados junto)
- **Atendimentos órfãos**: 1.255 religados (após normalizar CPF dos atendimentos)

### Resultado Final
- **28.672 pacientes**, **10.139 atendimentos**
- Zero duplicatas, zero CPF/SUS inválidos, zero órfãos
- Único paciente sem CPF: Raquel (tem SUS válido + 22 atendimentos — mantida)

### Como rodar no hospital
```powershell
python scripts\limpar_banco.py
```

## Histórico completo (sessões anteriores)

### Uppercase automático nos campos de texto
- Todo texto (nome, endereço, bairro, etc.) convertido pra maiúsculo automaticamente via `.toUpperCase()` no `handleChange`
- CPF, SUS, data, hora, sexo, civil, raça, registro, nº excluídos da conversão

### Máscara de telefone BR
- Campo **Telefone** (`tel`) agora formata como `(84) 98188-1207` (DDD + 9 dígitos)
- Máscara aplicada também ao carregar paciente do banco
- `numero` (nº da rua) **não** tem máscara de telefone, mantém livre

### Auto-preenche ao digitar CPF/SUS
- Digita CPF (11 dígitos) ou SUS (15 dígitos) que existe no banco → formulário preenche sozinho
- Dispara 200ms após parar de digitar e também ao sair do campo (onBlur)
- Usa debounce com `searchTimerRef` pra não fazer requisição a cada tecla

### Foco no CPF ao limpar
- Botão "Limpar" agora foca automaticamente no campo CPF (`cpfRef.current?.focus()`)
- Usuário pode digitar o CPF direto sem clicar no campo

### Procedência sempre NORMAL ao carregar paciente
- `selectPatient` agora inclui `procedencia: "NORMAL"` no estado do formulário
- Corrige bug onde a procedência ficava desmarcada ao auto-preenche

### Botão "+ Novo" removido
- Botão duplicado ao lado da busca removido (já existe "Limpar" ao lado de "Salvar")

### Formulário moderno em grid (tela) + A4 (impressão)
- `FichaA4Print` ficou **invisível na tela** e só aparece na impressão (`@media print`)
- Ordem dos campos segue **exatamente** a ordem do A4 de impressão:

  | Linha | Campos |
  |-------|--------|
  | 1 | Data | Hora | Registro |
  | 2 | Nome Completo (full) |
  | 3 | Nome Social (full) |
  | 4 | Naturalidade | DN | Idade |
  | 5 | CPF | Cartão SUS | Sexo (M/F) |
  | 6 | Estado Civil (rádios em botão) |
  | 7 | Raça/Cor (2 col) | Ocupação |
  | 8 | Nome da Mãe (full) |
  | 9 | Responsável (2 col) | Telefone |
  | 10 | Endereço (2 col) | N° |
  | 11 | Bairro | Cidade | UF |

### Data/Hora automáticos + editáveis
- `INITIAL_STATE` virou função que preenche data/hora atuais
- Data com máscara `DD/MM/AAAA`, Hora com máscara `HH:MM`
- Usuário pode alterar manualmente

### Rádios modernos (chip/button)
- Sexo, Estado Civil e Raça/Cor usam `<input hidden>` + `<label>` estilizada como botão
- Borda, `border-radius`, `padding` iguais aos inputs de texto
- Selecionado fica com fundo da cor primária (`--color-primary`)

### Botão Família
- Posicionado ao lado do campo **N°**
- Após **Salvar**, armazena endereço do paciente
- No próximo paciente, clica em **Família** e preenche Endereço, N°, Bairro, Cidade, UF automaticamente
- Não aparece na impressão

### Correção de bugs
- Impressão não funcionava: conflito de especificidade CSS entre `.recepcao-page .page` (tela) e `.page` (print). Resolvido com `@media screen` no hide da tela.

### Tauri Desktop
- Instalado Rust (1.95.0) + `@tauri-apps/cli`
- Criado `desktop/tauri/src-tauri/` com:
  - `Cargo.toml` — dependência `tauri` v2
  - `tauri.conf.json` — aponta para `frontend/dist` e dev server `localhost:5173`
  - `src/main.rs` + `src/lib.rs` — entry points
  - `icons/` — geradas via `npx tauri icon`
  - `capabilities/default.json` — permissões padrão
- Build Rust compilado com sucesso (`cargo build`)
- Comando para rodar: `npm run tauri:dev` (no frontend)

## Pendências para próxima sessão

- **Módulo BPA** (backend + frontend)
- **Módulo Relatórios** (PDF fpdf2, Excel openpyxl)
- **Firebird** — integração BPAMAG.GDB legado
- **Google Sheets** — "Gari da Nuvem"
- **Build produção** — `npm run tauri:build` → `.msi`

## Como continuar

```powershell
# Terminal 1 — Backend
cd C:\Users\Fabinho\Documents\Fabio\HMPCF\hmcpf-system\backend
uvicorn app.main:app --reload

# Terminal 2 — Frontend (ou Tauri desktop)
cd C:\Users\Fabinho\Documents\Fabio\HMPCF\hmcpf-system\frontend
npm run dev        # só frontend no navegador
npm run tauri:dev  # abre janela desktop nativa
```

# 📊 Frontend do Painel de Gestão (`web_painel/`)

Esta pasta contém a **interface web do módulo de Gestão** — a central de controle do sistema HMPCF. Servida pelo `app_painel.py` (Eel) na porta **8001**, ela reúne digitação assistida, triagem de documentos e controle do robô RPA em uma única interface.

---

## 📋 Arquivos

### `index.html` — Página Inicial do Painel

Dashboard com cards modulares para acesso rápido:

| Card | Descrição |
|------|-----------|
| 📊 **Análise / BI** | Relatórios gerenciais, dashboards e auditoria |
| 🔌 **Integração** | Exportação BPA, importação de CSVs e sincronização |
| 🤖 **Automação BPA** | Digitação, triagem e robô RPA |

Inclui um **Terminal de Eventos** que exibe logs do sistema em tempo real. O terminal mostra:
- Últimas operações admin (login/logout/sincronizações)
- Operações do robô RPA
- Eventos de importação e análise
- Timestamps completos para rastreabilidade

---

### `analise.html` — Central de Análise / BI

Página com 5 ferramentas de Business Intelligence acessíveis via web:

| Card | Função | Eel Endpoint |
|------|--------|-------------|
| 📈 **Dashboard Visual** | Gera PNG com 4 gráficos + relatório Top 20 | `analise_gerar_dashboard()` |
| 📋 **Planilha de Produção** | Excel com separação DIURNO/NOTURNO | `analise_gerar_relatorio_mes()` |
| 🔍 **Auditoria Periódica** | PDF Top 20 (mensal/trimestral/semestral) | `analise_gerar_auditoria_periodo()` |
| 📄 **Analisar CSVs Antigos** | PDF Top 20 a partir de CSVs legados | `analise_analisar_csvs_para_pdf()` |
| 👤 **Histórico do Paciente** | Busca completa por nome, CPF ou SUS | `analise_buscar_historico()` |

Cada card abre um modal com seus parâmetros. Resultados aparecem no terminal de saída.

---

### `automacao.html` — Central de Automação

Página que organiza os 3 submódulos de automação:

- 🔍 **Digitação** → vai para `digitacao.html`
- 🧹 **Triagem** → vai para `triagem.html`
- 🤖 **Executar Robô** → vai para `robo.html`

Inclui um visualizador de arquivos de lote (.txt) produzidos pelo sistema.

---

### `digitacao.html` — Assistente de Digitação Manual

Interface para montagem de lotes de produção do BPA:

1. **Busca pacientes** na base RAM do Firebird (nome, CPF ou SUS)
2. **Confirma médico** e data do plantão
3. **Adiciona fichas** ao lote com quebra automática a cada 99 pacientes
4. Navegação 100% por teclado (TAB, Enter, Setas)

---

### `triagem.html` — Tela de Triagem de Documentos

Para enfermeiros e administrativo:

- **Cole dados sujos** (rascunhos com CPF/SUS bagunçados)
- **Divide em lotes** de 99 pacientes por enfermeiro
- **Associa enfermeiros** a cada lote (separados por vírgula)
- **Edição manual** do resultado antes de salvar

---

### `robo.html` — Painel de Controle do Robô RPA

Interface para operar o robô digitador:

1. **Selecione o lote** de produção
2. **Valide** os pacientes contra a base do Firebird
3. **Escolha o procedimento** (médico ou enfermeiro)
4. **Inicie a automação** com contagem regressiva de 5 segundos
5. **Progresso em tempo real** com atualizações a cada paciente
6. **Pule ou cancele** lotes durante a execução

---

### `style.css` — Tema Visual do Painel (263 linhas)

- **Paleta de cores:** azul profundo (confiança), vermelho (urgência), amarelo (destaque)
- **Cards modulares** com sombreamento e hover effects
- **Terminal escuro** estilo console para logs do sistema
- **Botões customizados** com ícones e feedback visual
- Design responsivo via **Bootstrap 5**

---

## � Autenticação Admin

### Senha Padrão
- **Inicial:** `8878`
- **Arquivo:** `.admin_pass` (não versionado)
- **Mudança:** Botão "🔑 Mudar Senha" no painel (requer unlock anterior)

### Fluxo de Autenticação
1. Ao clicar em operação admin, modal aparece
2. Digite a senha de 9 dígitos
3. Sistema valida contra `.admin_pass`
4. Se correto:
   - `ADMIN_SESSION_EXPIRY = 'unlimited'` (até logout manual)
   - Banner 🔓 aparece no topo direito
   - Todas as operações admin desbloqueadas
5. Click "Logout" encerra a sessão

### Funções Eel Expostas
- `set_admin(password)` — Autentica e cria sessão
- `is_admin()` — Retorna boolean do status
- `logout_admin()` — Encerra sessão
- `change_admin_password(nova)` — Muda senha (requer admin session)

---

## 📋 Auditoria de Operações

Todas as ações sensíveis são registradas em `auditoria.log` (JSON Lines):

```json
{"timestamp": "2026-05-16 14:32:10", "evento": "admin_login", "status": "sucesso"}
{"timestamp": "2026-05-16 14:35:00", "evento": "integracao_sincronizar_firebird", "status": "concluido", "linhas": 245}
{"timestamp": "2026-05-16 14:40:00", "evento": "admin_logout", "status": "normal"}
```

Visualização: **Análise → Terminal de Eventos** → scroll para ver histórico

---

## �🚀 Como Executar

```bash
python app_painel.py
# Acesse http://localhost:8001 no navegador
```

O servidor:
1. **Carrega toda a base do Firebird** (`BPAMAG.GDB`) para a RAM
2. Sobe a interface Eel na porta 8001 (modo headless)
3. Mantém-se vivo com loop de keepalive

---

## 🧠 Integração com o Backend

O painel delega o trabalho pesado para 3 módulos Python:

| Tela | Módulo | Função |
|------|--------|--------|
| Análise / BI | `analise/dashboard_visual.py` | Dashboard PNG, Excel, PDFs e busca de histórico |
| Digitação | `automacao/digitacao.py` | Busca na RAM, montagem de lotes |
| Triagem | `automacao/cpf_sus.py` | Extração e validação de documentos |
| Robô | `automacao/executor_rpa.py` | Automação RPA com PyAutoGUI |

---

*Frontend do Painel de Gestão desenvolvido por **Fábio Gomes da Silva** para o Hospital Municipal Presidente Café Filho.*

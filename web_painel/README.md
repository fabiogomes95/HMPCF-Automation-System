# 📊 Frontend do Painel de Gestão (`web_painel/`)

Esta pasta contém a **interface web do módulo de Gestão** — a central de controle do sistema HMPCF. Servida pelo `app_painel.py` (Eel) na porta **8001**, ela reúne digitação assistida, triagem de documentos e controle do robô RPA em uma única interface.

---

## 📋 Arquivos

### `index.html` — Página Inicial do Painel

Dashboard com cards modulares para acesso rápido:

| Card | Descrição |
|------|-----------|
| 📊 **Análise Pandas** | Relatórios gerenciais e estatísticas |
| 💰 **Faturamento** | Gestão de contas e auditoria |
| 🤖 **Automação BPA** | Digitação, triagem e robô RPA |

Inclui um **Terminal de Eventos** que exibe logs do sistema em tempo real.

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

## 🚀 Como Executar

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
| Digitação | `automacao/digitacao.py` | Busca na RAM, montagem de lotes |
| Triagem | `automacao/cpf_sus.py` | Extração e validação de documentos |
| Robô | `automacao/executor_rpa.py` | Automação RPA com PyAutoGUI |

---

*Frontend do Painel de Gestão desenvolvido por **Fábio Gomes da Silva** para o Hospital Municipal Presidente Café Filho.*

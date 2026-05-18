# 🏪 Frontend da Recepção (`web_recepcao/`)

Esta pasta contém a **interface web do módulo de Recepção** — o coração do cadastro de pacientes. Servida pelo `app_recepcao.py` (Eel) na porta **8000**, ela transforma o navegador em um boletim de atendimento A4 profissional.

---

## 📋 Arquivos

### `index.html` — Formulário de Boletim de Atendimento

Layout A4 completo com:

| Seção | Campos |
|-------|--------|
| **Identificação** | Nome, Nome Social, CPF, Cartão SUS, Data de Nascimento, Idade, Sexo, Estado Civil, Raça/Cor, Ocupação |
| **Contato** | Naturalidade, Nome da Mãe, Responsável, Telefone |
| **Endereço** | Rua, Número, Bairro, Cidade, Estado |
| **Classificação de Risco** | Botões coloridos (Vermelho, Laranja, Amarelo, Verde, Azul) |
| **Sinais Vitais** | Pressão Arterial, Temperatura, Saturação, Glicemia |
| **Comorbidades** | Checkboxes (Diabetes, HAS, Tabagismo, etc.) |
| **Atendimento** | Data, Hora, Registro, Procedência, Anotações clínicas |
| **Impressão** | Design otimizado com `@media print` — imprime direto como boletim |

---

### `script.js` — Cérebro do Frontend

**Funcionalidades:**

| Função | Descrição |
|--------|-----------|
| **Relógio automático** | Atualiza data e hora em tempo real |
| **Toast notifications** | Substitui `alert()` por notificações elegantes (Bootstrap) |
| **Máscaras de entrada** | CPF (`000.000.000-00`), SUS (`000 0000 0000 0000`), telefone, data |
| **Validação CPF** | Cálculo Módulo 11 duplo (igual à Receita Federal) |
| **Validação CNS** | Cálculo Módulo 11 completo (definitivo e provisório) |
| **Busca instantânea** | Ao digitar CPF ou SUS, busca no banco via Eel e preenche o formulário |
| **Busca por nome** | Ao digitar 5+ caracteres no nome, busca pacientes com nome semelhante |
| **Debounce inteligente** | Aguarda 300ms de pausa na digitação antes de buscar (evita chamadas desnecessárias) |
| **Histórico do paciente** | Exibe os últimos 5 atendimentos do paciente encontrado |
| **Cálculo de idade** | Calcula automaticamente a partir da data de nascimento |
| **Idade pediátrica** | Exibe em meses para crianças < 2 anos |
| **Atalho F2** | Salva o formulário sem precisar clicar no botão |
| **Anti-metralhadora** | Bloqueia duplo clique no botão salvar |
| **Detecção de duplicatas** | Avisa se outro paciente com mesmo nome + DN já existe |
| **Auto-draft** | Salva rascunho a cada 30s no `localStorage` e recupera se a página fechar |
| **Copiar endereço** | Botão "Família" copia endereço do paciente anterior para novo cadastro |
| **Dark Mode** | Toggle claro/escuro com preferência salva no navegador |
| **Barra de status** | Mostra status do servidor, Gari da Nuvem e horário do último save |

---

### `style.css` — Estilos Hospitalares

- Layout A4 profissional com dimensões exatas de papel
- **CSS Variables**: todas as cores via `--var()` — fácil de customizar
- **Dark mode completo**: tema escuro para plantão noturno
- Botões de procedência coloridos (SAMU, TROCA, UBS, GUARDA, NORMAL)
- Barra de status superior com indicadores online/offline
- Painel de histórico do paciente
- Área de escrita à mão (`handwriting`) para anotações clínicas
- Regras `@media print` — esconde botões e menus na hora de imprimir
- Notificações Toast (Bootstrap) para feedback não-intrusivo

---

### `assets/` — Dependências Locais

- `bootstrap.min.css` — Bootstrap 5.3.2 (local, sem dependência de CDN)
- `bootstrap.bundle.min.js` — Bootstrap JS (local)

### `logo.png` — Logomarca do Hospital

Exibida no cabeçalho do boletim impresso.

---

## 🚀 Como Executar

```bash
python app_recepcao.py
# Abre automaticamente no navegador em http://localhost:8000
```

O servidor:
1. Inicia o banco SQLite (`hospital.db`)
2. Sobe a interface Eel na porta 8000
3. Dispara o **Gari da Nuvem** em background (sincronização com Google Sheets)
4. Expõe funções de busca por CPF/SUS, nome, histórico e verificação de duplicatas

---

## 🧠 Integração com o Backend

O frontend se comunica com o Python através do **Eel**:

| Função JS | Função Python | Descrição |
|-----------|--------------|-----------|
| `buscar_paciente()` | `app_recepcao.buscar_paciente()` | Busca CPF/SUS no banco |
| `buscar_por_nome()` | `app_recepcao.buscar_por_nome()` | Busca pacientes por nome (parcial) |
| `buscar_historico()` | `app_recepcao.buscar_historico()` | Últimos 5 atendimentos do paciente |
| `verificar_duplicata()` | `app_recepcao.verificar_duplicata()` | Checa se nome+DN já existe |
| `salvar()` | `app_recepcao.salvar()` | Salva paciente + atendimento |
| `status_gari()` | `app_recepcao.status_gari()` | Status do Gari da Nuvem |

---

*Frontend da Recepção desenvolvido por **Fábio Gomes da Silva** para o Hospital Municipal Presidente Café Filho.*

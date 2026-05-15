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

### `script.js` — Cérebro do Frontend (533 linhas)

**Funcionalidades:**

| Função | Descrição |
|--------|-----------|
| **Relógio automático** | Atualiza data e hora em tempo real |
| **Máscaras de entrada** | CPF (`000.000.000-00`), SUS (`000 0000 0000 0000`), telefone, data |
| **Validação CPF** | Cálculo Módulo 11 duplo (igual à Receita Federal) |
| **Validação CNS** | Cálculo Módulo 11 completo (definitivo e provisório) |
| **Busca instantânea** | Ao digitar CPF ou SUS, busca no banco via Eel e preenche o formulário |
| **Cálculo de idade** | Calcula automaticamente a partir da data de nascimento |
| **Idade pediátrica** | Exibe em meses para crianças < 2 anos |
| **Atalho F2** | Salva o formulário sem precisar clicar no botão |
| **Anti-metralhadora** | Bloqueia duplo clique no botão salvar |

---

### `style.css` — Estilos Hospitalares (298 linhas)

- Layout A4 profissional com dimensões exatas de papel
- Botões de procedência coloridos (SAMU, TROCA, UBS, GUARDA, NORMAL)
- Área de escrita à mão (`handwriting`) para anotações clínicas
- Regras `@media print` — esconde botões e menus na hora de imprimir
- Design responsivo para diferentes resoluções de tela

---

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

---

## 🧠 Integração com o Backend

O frontend se comunica com o Python através do **Eel**:

| Função JS | Função Python | Descrição |
|-----------|--------------|-----------|
| `buscar_paciente()` | `app_recepcao.buscar_paciente()` | Busca CPF/SUS no banco |
| `salvar()` | `app_recepcao.salvar()` | Salva paciente + atendimento |

---

*Frontend da Recepção desenvolvido por **Fábio Gomes da Silva** para o Hospital Municipal Presidente Café Filho.*

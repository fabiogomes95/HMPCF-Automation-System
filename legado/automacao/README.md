# 🤖 Módulo de Automação RPA

Este diretório contém o coração da automação do sistema HMPCF. Aqui moram o **robô digitador** (RPA), o **assistente de digitação manual** e o **extrator de documentos** — responsáveis por eliminar a digitação manual no sistema BPA governamental.

---

## 📋 Scripts

### 1. `cpf_sus.py` — Extrator e Validador de Documentos

Lê um arquivo texto bagunçado (rascunho da triagem), **caça CPFs e Cartões SUS** usando regex, valida matematicamente (Módulo 11) e devolve uma lista limpa.

**Regra de prioridade:** Se encontrar SUS e CPF na mesma linha, fica com o SUS.

**Como funciona por dentro:**
- Recebe: texto sujo tipo `"paciente 123.456.789-00 898004532690001 joão"`
- Aplica `apenas_numeros()` em cada palavra
- Testa se tem 11 dígitos (CPF) ou 15 dígitos (SUS)
- Valida matematicamente
- Retorna: `["898004532690001"]`

**Importante:** Usa as funções do `utils.py` central — sem duplicação de código.

---

### 2. `digitacao.py` — Assistente de Digitação Manual

Auxilia a montagem de lotes de produção para o BPA, rodando por trás do **Painel de Gestão** (Eel).

**Funções:**
- **`buscar_pacientes_memoria()`** — filtra a base RAM do Firebird por nome/SUS/CPF na velocidade da luz (retorna até 50 resultados)
- **`criar_cabecalho_producao()`** — escreve o cabeçalho `PROFISSIONAL: NOME | DATA: DD/MM/AAAA` no arquivo de lote
- **`adicionar_ficha_producao()`** — adiciona um documento ao lote com **quebra automática a cada 99 pacientes** (limite do BPA)

---

### 3. `executor_rpa.py` — Robô de Digitação (PyAutoGUI)

**O cérebro da automação.** Assume o controle do teclado e digita os dados diretamente no software governamental do BPA.

**Fluxo de execução:**
1. `preparar_lotes()` — lê o arquivo de produção e valida cada documento contra a base RAM do Firebird
2. `executar_pyautogui()` — para cada paciente:
   - Digita o documento → aperta F7 (busca no BPA)
   - Digita a data → TAB → digita o procedimento → "1" (quantidade)
   - TAB → TAB → TAB → digita "2" → TAB → TAB → ENTER (salva)

**Segurança:**
- **Fail-safe:** mouse no canto da tela = parada imediata
- **ESC:** interrompe o robô a qualquer momento
- **Validação tripla:** só digita se o documento existir na base do governo

---

## 🛠️ Tecnologias

| Biblioteca | Para que serve |
|------------|----------------|
| **PyAutoGUI** | Automação de teclado e mouse (RPA) |
| **keyboard** | Detecção da tecla ESC para interrupção |
| **re** | Extração de dígitos dos documentos |

---

## 🚀 Fluxo de Uso

```
Painel de Gestão (app_painel.py)
  │
  ├── Triagem (cpf_sus.py) → extrai documentos válidos
  │
  ├── Digitação (digitacao.py) → monta lotes de 99
  │
  └── Robô (executor_rpa.py) → digita no sistema BPA
```

1. Cole os dados sujos na tela de **Triagem** → `cpf_sus.py` limpa
2. Associe enfermeiros e datas → `digitacao.py` monta os lotes
3. Inicie o **Robô** → `executor_rpa.py` assume o controle

---

*Módulo de Automação desenvolvido por **Fábio Gomes da Silva** para o Hospital Municipal Presidente Café Filho.*

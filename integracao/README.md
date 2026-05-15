# 🔌 Módulo de Integração SUS

Este diretório contém os scripts responsáveis por **traduzir os dados do sistema para a linguagem do Governo**. Eles convertem cadastros do SQLite para o formato BPA (Datasus), sincronizam com o Firebird oficial, importam planilhas legadas e garantem que nenhum paciente seja perdido — mesmo em contingência.

Todas as ferramentas funcionam **via terminal** (com parâmetros opcionais) e **via interface web** no Painel de Gestão (Eel, porta 8001).

---

## 📋 Scripts

### 1. `exportar_bpa.py` — Exportador SQLite → TXT BPA

Gera o arquivo **TXT posicional** que o sistema BPA do governo importa.

**Regras de negócio:**
- Sexo vazio/inválido → `I` (Indefinido)
- Data de nascimento inválida → `19900101` (01/01/1990)
- SUS com menos de 15 dígitos → paciente **barrado** com registro no log de erros

**Formato de saída:** Layout posicional do Datasus (nome com 30 caracteres, posições fixas para cada campo).

**Como usar:**
```bash
python integracao/exportar_bpa.py
# Informe mês/ano (opcional) e caminho de saída, ou use padrões
```
Também disponível no Painel de Gestão → Integração → Exportar SQLite → TXT BPA.

---

### 2. `converter_csv.py` — Conversor de CSVs Antigos para TXT BPA

Lê o formato CSV usado antes do sistema atual (13 colunas: REGISTRO, NOME, DN, IDADE, SEXO, RAÇA, CIDADE, HORARIO, CPF, SUS, OBS, ENDERECO, TEL) e converte para o layout posicional do BPA.

**Diferenciais:**
- Faz **parse inteligente do endereço** no formato `"R. EXEMPLO, 123. CENTRO"` → separa Rua, Número e Bairro
- Data quebrada → `19900101`
- Sexo inválido → `I`
- Gera log de pacientes barrados (SUS inválido)

**Como usar:**
```bash
python integracao/converter_csv.py
# Informe o caminho do CSV e onde salvar (opcional), ou use padrões
```

---

### 3. `importador_recepcao.py` — Importador em Lote com Smart Update

Varre a pasta atual em busca de arquivos `.csv` da recepção e os importa para o SQLite com **inteligência cirúrgica**.

**Smart Update:** Se o paciente já existe, enriquece **apenas os campos vazios** — nunca sobrescreve dados preenchidos.

**Regras:**
- Detecta automaticamente se o separador é `,` ou `;`
- Ignora pacientes com SUS inválido (valida CNS)
- Gera relatório de auditoria em `.txt` com todos os novos cadastros

**Como usar:**
```bash
python importador_recepcao.py
# Informe o separador (opcional, padrão ";")
```

---

### 4. `sincronizar_firebird.py` — Sincronizador SQLite → Firebird

Integra os pacientes do `hospital.db` (SQLite) com o banco oficial do BPA (`BPAMAG.GDB` / Firebird).

**Fluxo:**
- Busca paciente por **NOME + DATA DE NASCIMENTO** no Firebird
- Se existe → **UPDATE** (atualiza endereço, telefone, CPF, SUS)
- Se não existe → **INSERT** (cadastro completo)

**Como usar:**
```bash
python integracao/sincronizar_firebird.py
# Informe o mês/ano e caminho do .gdb (opcional), ou use padrões
```

---

### 5. `sincronizar_contingencia.py` — Sincronizador de Planilhas Offline

**O salva-vidas do sistema.** Quando a recepção fica offline (falta de energia/internet) e anota em planilhas manuais, este script consegue ler esses dados bagunçados.

**Como faz:**
- Usa **regex inteligente** para "caçar" CPF, SUS, Nome e Data de Nascimento — independente da coluna onde foram digitados
- Detecta automaticamente se o CSV usa `,` ou `;`
- Se o paciente já existe no banco com SUS corrompido, atualiza com o SUS válido da planilha
- Gera dois logs: `PROCESSADOS` e `ERROS`

**Como usar:**
```bash
python sincronizar_contingencia.py
# Informe o caminho do CSV (opcional), ou use o padrão
```

---

### 6. `corrigir_nulls.py` — Aniquilador de NULLs no Firebird

Varre **todas as colunas** da tabela `CADCNS` no Firebird e substitui valores `NULL` por `''` (texto) ou `0` (número).

**Por que existe:** O sistema BPA do governo **travava** quando encontrava campos NULL, gerando o erro `UDFLIB`. Este script resolve isso de uma vez.

**Como usar:**
```bash
python integracao/corrigir_nulls.py
# Informe o caminho do .gdb (opcional), ou use o padrão
```

---

### 7. `duplicatas_gdb.py` — Caçador de Duplicatas no Firebird

Agrupa pacientes pelo **Cartão SUS**, avalia cada ficha por um **sistema de pontuação** (CPF preenchido = 5pts, endereço = 1pt, telefone = 1pt), mantém a melhor e deleta as inferiores.

**Como usar:**
```bash
python duplicatas_gdb.py
# Informe o caminho do .gdb (opcional), ou use o padrão
```

---

## 🛠️ Tecnologias

| Biblioteca | Para que serve |
|------------|----------------|
| **SQLite3** | Conexão com o banco local hospital.db |
| **Firebird SQL** | Conexão com o banco oficial BPAMAG.GDB |
| **Pandas** | Leitura e processamento de CSVs |
| **Eel** | Interface web (Painel de Gestão, porta 8001) |
| **Regex (re)** | Extração de documentos de textos sujos |

---

## 📂 Fluxo dos Dados

```
CSVs da Recepção
  │
  ├── importador_recepcao.py  →  SQLite (Smart Update)
  │
  ├── sincronizar_contingencia.py  →  SQLite (modo offline)
  │
  └── converter_csv.py  →  TXT BPA (CSVs antigos)
  
SQLite
  │
  ├── exportar_bpa.py  →  TXT BPA (Datasus)
  │
  └── sincronizar_firebird.py  →  Firebird (BPAMAG.GDB)

Firebird
  │
  ├── corrigir_nulls.py  →  Aniquila NULLs
  │
  └── duplicatas_gdb.py  →  Remove duplicatas
```

---

*Módulo de Integração desenvolvido por **Fábio Gomes da Silva** para o Hospital Municipal Presidente Café Filho.*

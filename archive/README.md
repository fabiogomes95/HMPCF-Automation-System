# 🗄️ Archive — Caixa de Ferramentas DBA

Este diretório é a **caixa de ferramentas de manutenção** do sistema HMPCF. Aqui ficam scripts de faxina profunda, correção de dados, auditoria de arquivos BPA e utilidades de debug. Não fazem parte do fluxo diário, mas são **essenciais para a saúde do banco de dados** e para resolver problemas pontuais.

---

## 📋 Scripts

### 1. `faxina.py` — Faxina Geral do SQLite

**O grande saneador do banco.** Varre todos os pacientes do `hospital.db`, valida CPF e SUS matematicamente, e aplica as seguintes ações:

- **Exclui** fichas sem nenhum documento válido
- **Mescla** duplicatas (funde dados: se um registro tem CPF e outro tem endereço, junta tudo)
- **Recria** a tabela com chave primária composta `(cpf, sus)` para evitar novas duplicatas
- **Audita** a tabela de atendimentos, limpando documentos inválidos

**Como usar:**
```bash
python archive/faxina.py
```

---

### 2. `cns_validator_tool.py` — Faxina Cirúrgica de CNS

Faxina focada **apenas em Cartão SUS** (ignora CPFs propositalmente).

- Valida cada CNS com o algoritmo completo do Ministério da Saúde (Módulo 11)
- **Exclui** pacientes com SUS inválido + suas fichas de atendimento
- **Limpa** datas de nascimento corrompidas
- Gera `relatorio_faxina.txt` com o log completo

**Como usar:**
```bash
python archive/cns_validator_tool.py
```

---

### 3. `fusao.py` — Deduplicação Inteligente V3

Faxina avançada com **inteligência artificial** para fusão de clones.

**Regras:**
- Agrupa pacientes por CPF ou SUS válido
- **Ignora CPFs genéricos** (mesmo documento usado por mais de 3 pessoas diferentes)
- Preserva o **melhor nome** (o mais completo)
- Move atendimentos dos clones para o registro master
- Exclui os clones

**Como usar:**
```bash
python archive/fusao.py
```

---

### 4. `auditor_bpa.py` — Auditor de Arquivos TXT do BPA

Lê o arquivo `ExpPaciente.txt` gerado para o governo e verifica:

- **Posição 53:** campo sexo está preenchido?
- **CNS:** validação matemática do Cartão SUS
- Gera `lista_correcao.txt` com os SUS que precisam de correção manual

**Como usar:**
```bash
python archive/auditor_bpa.py
# Coloque o ExpPaciente.txt na mesma pasta
```

---

### 5. `corrigir_sexo_bpa.py` — Robô RPA Corretor de Sexo

**Robô complementar ao auditor.** Lê a `lista_correcao.txt` e assume o teclado (PyAutoGUI) para digitar 'I' no campo sexo de cada paciente no sistema BPA governamental.

**Como usar:**
```bash
python archive/corrigir_sexo_bpa.py
# Informe data e procedimento
# Deixe o robô trabalhar no BPA
```

---

### 6. `att_sexo.py` — Atualização em Massa de Sexo no SQLite

Varre o `hospital.db` e seta sexo como `'I'` (Indefinido) para todos os pacientes com sexo nulo, vazio ou diferente de M/F.

**Como usar:**
```bash
python archive/att_sexo.py
```

---

### 7. `cpf_bpa.py` — Sincronizador BPA Alternativo

Sincroniza pacientes do SQLite com o Firebird usando **NOME + DATA DE NASCIMENTO** como chave de busca (em vez de SUS). Útil quando o SUS está inconsistente mas o nome e data estão corretos.

**Como usar:**
```bash
python archive/cpf_bpa.py
# Informe mês e ano
```

---

### 8. `gerar_txt_fusao.py` — Relatório Pós-Faxina

Gera um arquivo `RELATORIO_FINAL_FAXINA.txt` com a lista de todos os pacientes que sobreviveram à faxina, ordenados por nome.

**Como usar:**
```bash
python archive/gerar_txt_fusao.py
```

---

### 9. `sonda_db.py` — Sonda de Banco de Dados

Ferramenta de **debug** para desenvolvedores. Faz uma busca por nome no SQLite e exibe os valores **exatos** salvos no banco (incluindo espaços, formatação e caracteres).

Útil para diagnosticar problemas como:
- "Por que este paciente não aparece na busca?"
- "O sexo foi salvo com espaços?"
- "O SUS está formatado corretamente?"

**Como usar:**
```bash
python archive/sonda_db.py
```

---

## ⚠️ Aviso de Segurança

A maioria destes scripts executa comandos **DELETE** e **UPDATE** no banco de dados ou controla o mouse/teclado (RPA). Use apenas se você sabe o que está fazendo. **Sempre faça backup do `hospital.db` antes de rodar faxinas.**

---

*Ferramentas de manutenção desenvolvidas por **Fábio Gomes da Silva** para o Hospital Municipal Presidente Café Filho.*

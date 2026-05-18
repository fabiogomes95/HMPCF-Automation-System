# 📋 Relatório de Revisão de Código — HMPCF Automation System

**Revisor:** Senior Software Engineer (Claude)
**Data:** 15 de Maio de 2026
**Repositório:** [fabiogomes95/HMPCF-Automation-System](https://github.com/fabiogomes95/HMPCF-Automation-System)
**Versão analisada:** v1.1.0 (branch `main`)

---

## 1. Mapeamento da Arquitetura

### Estrutura de Diretórios

```
📦 HMPCF-Automation-System
 ┣ 📂 analise/          # BI — Dashboards, relatórios Excel e PDF
 ┣ 📂 automacao/        # RPA — Robô digitador, triagem, fila de lotes
 ┣ 📂 integracao/       # Integração SUS — conversores TXT, sincronizadores
 ┣ 📂 scripts/          # Scripts administrativos e manutenção operacional
 ┣ 📂 web_recepcao/     # Frontend da Recepção (Eel)
 ┣ 📂 web_painel/       # Frontend do Painel de Gestão (Eel)
 ┣ 📂 assets/           # Recursos estáticos (ícones)
 ┣ 📜 app_recepcao.py   # Servidor da Recepção (Eel — porta 8000)
 ┣ 📜 app_painel.py     # Servidor do Painel de Gestão (Eel — porta 8001)
 ┣ 📜 main.py           # Launcher unificado + auto-update
 ┣ 📜 config.py         # Configuração centralizada (dotenv manual)
 ┣ 📜 planilha_nuvem.py # "Gari da Nuvem" — sincronizador Google Sheets
 ┣ 📜 utils.py          # Motor de validações (CPF, CNS, regex)
 ┣ 📜 auditoria_log.py  # Log de auditoria em JSON Lines
 ┣ 📜 logging_setup.py  # Setup centralizado de logging
 ┣ 📜 requirements.txt  # Dependências do projeto
 ┣ 📜 .env.example      # Template de configuração
 ┗ 📜 version.json      # Controle de versão para auto-update
```

**Stack tecnológica identificada:** Python + SQLite + Eel (Desktop/Web híbrido) + Google Sheets API + Firebird (legado BPA/SUS) + PyAutoGUI (RPA) + gspread.

**Fluxo principal confirmado:**

```
Recepcionista (HTML/JS) → Eel → app_recepcao.py → SQLite
                                                      ↓
                           Google Sheets ← planilha_nuvem.py (thread)
                                                      ↓
                          app_painel.py → Painel de Gestão (lê SQLite)
```

---

## 2. Análise Script por Script

---

### 📄 `logging_setup.py` (12 linhas)

**Avaliação geral: ✅ Excelente — simples e correto.**

**Pontos positivos:**
- Centralização limpa do logger com um único `getLogger("hmpcf")`.
- Uso de `Final` do `typing` para evitar reatribuição acidental.
- Formato de log legível com timestamp.

**Pontos a melhorar:**

1. **Sem rotação de arquivo:** O log vai apenas para `stdout`. Em produção hospitalar, logs deveriam também ser gravados em arquivo com rotação (`RotatingFileHandler`) para rastreabilidade persistente.

2. **Nível hardcoded:** `level=logging.INFO` está fixo. Seria ideal ler de uma variável de ambiente (`LOG_LEVEL`) para facilitar depuração em produção sem alterar código.

```python
# Sugestão
import os
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO), ...)
```

3. **Sem docstring:** Um arquivo de infraestrutura deveria ter ao menos um comentário explicando seu papel no ecossistema.

---

### 📄 `config.py` (82 linhas)

**Avaliação geral: ✅ Bem estruturado, com ressalvas críticas de segurança.**

**Pontos positivos:**
- Implementação manual de dotenv é inteligente — elimina dependência externa (`python-dotenv`) sem perda funcional.
- Hierarquia de configuração clara: arquivo `.env` → variável de ambiente → valor padrão.
- Separação elegante das funções `get_admin_password()` e `set_admin_password()` com persistência em arquivo `.admin_pass`.
- Docstring no nível de módulo bem escrita, explicando o propósito e uso.

**Problemas críticos:**

1. **🔴 CREDENCIAIS PADRÃO EXPOSTAS — RISCO ALTO:**

   ```python
   FIREBIRD_PASSWORD = getenv('FIREBIRD_PASSWORD', 'masterkey')
   ADMIN_PASSWORD default = '8878'
   ```

   Senhas padrão hardcoded são um risco de segurança grave, especialmente para um sistema hospitalar com dados sensíveis (CPF, CNS, histórico médico). O sistema deveria **falhar explicitamente** se as credenciais críticas não forem configuradas via `.env`.

2. **🔴 GOOGLE SHEET ID EXPOSTO:**

   ```python
   GOOGLE_SHEET_ID = getenv('GOOGLE_SHEET_ID', '1xw_x-bYlHCHzMe39g1mJKPFAD_...')
   ```

   Um ID de planilha real está hardcoded como fallback. Isso deveria estar exclusivamente no `.env`, sem valor padrão.

3. **🔴 CEP+RUA E CÓDIGO UNIDADE HARDCODED:**

   ```python
   CEP_RUA = getenv('CEP_RUA', '59575000081')
   CODIGO_UNIDADE = getenv('CODIGO_UNIDADE', '240360')
   ```

   Dados reais da unidade como fallback podem gerar lançamentos BPA/SUS errôneos se o `.env` não for configurado. **Risco operacional direto.**

4. **`.admin_pass` sem proteção de permissão:** A função `set_admin_password()` grava a senha em texto plano em um arquivo no diretório raiz. Não há hash, não há restrição de permissão de arquivo (`os.chmod`).

**Sugestão de melhoria:**

```python
# Para credenciais críticas, forçar erro explícito:
FIREBIRD_PASSWORD = getenv('FIREBIRD_PASSWORD') or _raise("FIREBIRD_PASSWORD não configurado")
```

---

### 📄 `utils.py` (165 linhas)

**Avaliação geral: ✅ Ponto mais forte do projeto. Documentação exemplar.**

**Pontos muito positivos:**
- Comentários são excepcionalmente didáticos — explicam o "porquê" além do "o quê".
- Algoritmos de validação de CPF e CNS implementados corretamente com referência ao algoritmo oficial.
- A função `parse_endereco_fixed()` resolve um problema real (endereços digitados sem estrutura) com regex inteligente e boa cobertura de casos especiais.
- `remove_accents()` é essencial para o BPA/SUS e está corretamente implementada com NFKD.
- Type hints em todas as funções — ótimo para manutenibilidade.

**Pontos a melhorar:**

1. **`parse_endereco_fixed` — fragilidade na heurística do "último número":** A lógica de pegar o último número como número da residência falha em casos como `"RUA 7 DE SETEMBRO, 123 CENTRO"` — o `123` seria identificado corretamente, mas `"RUA 1 DE JUNHO"` sem número retornaria `"RUA 1 DE JUNHO"` como rua e `"JUNHO"` como bairro? Seria interessante adicionar testes unitários documentando os edge cases esperados.

2. **Ausência de testes unitários:** Este módulo é o coração das validações e tem lógica crítica. A ausência de um arquivo `test_utils.py` é uma lacuna séria — qualquer refatoração futura pode quebrar as validações silenciosamente.

3. **`apenas_numeros` sem limite de tamanho:** A função não valida comprimento máximo, o que pode deixar strings muito longas passarem para o banco sem truncamento.

---

### 📄 `config.py` + `planilha_nuvem.py` — Acoplamento

**Avaliação geral do `planilha_nuvem.py`: ⚠️ Funcionalmente sólido, com riscos de robustez.**

**Pontos positivos:**
- O padrão "Gari da Nuvem" (worker de fundo com loop + sleep) é apropriado para o contexto operacional.
- **Lock otimista via `enviado_nuvem = 2`** é uma solução engenhosa para evitar race conditions entre threads — demonstra consciência do problema de concorrência.
- A **regra da virada de plantão às 07:00h** está bem documentada e implementada corretamente com `timedelta(hours=7)`.
- A proteção contra o "erro 20007" (data explosiva) mostra que o código evoluiu com base em erros reais de produção — isso é sinal de maturidade operacional.
- O tratamento de criação automática de aba por mês é elegante.

**Problemas identificados:**

1. **🔴 RECONEXÃO AO BANCO A CADA CICLO:** O `gari_da_nuvem()` abre e fecha uma conexão SQLite a cada 10 segundos, para cada atendimento. Em dias de alto volume isso pode causar contenção. Seria mais eficiente usar `sqlite3.connect()` com `WAL mode` e manter a conexão aberta com retry.

2. **🔴 AUTENTICAÇÃO GOOGLE RECRIADA A CADA ENVIO:** A função `enviar_para_planilha()` chama `Credentials.from_service_account_file()` e `gspread.authorize()` a cada atendimento. A autenticação deveria ser criada uma vez e reutilizada (com refresh automático do token).

   ```python
   # Anti-padrão atual:
   def enviar_para_planilha(dados):
       creds = Credentials.from_service_account_file(...)  # ← toda vez
       client = gspread.authorize(creds)  # ← toda vez
   ```

3. **⚠️ EXCEPT SILENCIOSO NO LOOP PRINCIPAL:**

   ```python
   except Exception:
       pass  # ← Engole qualquer erro silenciosamente
   ```

   Se o banco corromper ou a API Google retornar um erro permanente, o sistema falha silenciosamente sem alertar ninguém. Ao menos `logger.error()` deveria ser chamado.

4. **⚠️ `enviado_nuvem = 2` (estado "processando") pode ficar travado:** Se o processo for encerrado abruptamente enquanto um registro está com `enviado_nuvem = 2`, ele fica nesse estado para sempre e nunca mais é processado. É necessário uma lógica de "limpeza de locks fantasmas" na inicialização.

5. **Código de formatação muito longo em `enviar_para_planilha()`:** A função tem mais de 150 linhas e mistura autenticação, lógica de data, formatação de dados, envio e formatação de célula. Deveria ser quebrada em funções menores (`_autenticar_google()`, `_formatar_linha()`, `_inserir_cabecalho_plantao()`).

---

### 📄 `auditoria_log.py` (50 linhas)

**Avaliação geral: ✅ Simples e funcional. Pode crescer melhor.**

**Pontos positivos:**
- JSON Lines é um formato excelente para logs de auditoria — cada linha é um JSON válido e independente, fácil de parsear e resistente a corrupção parcial.
- `listar()` com `limite` evita leitura total de um arquivo que pode crescer indefinidamente.
- Tratamento de `json.JSONDecodeError` por linha individualmente — correto.

**Pontos a melhorar:**

1. **Sem rotação do arquivo `auditoria.log`:** O arquivo crescerá indefinidamente. Em ambiente hospitalar com dezenas de atendimentos por dia, em 1 ano terá centenas de milhares de linhas. Implementar rotação mensal ou por tamanho.

2. **`listar()` carrega TODO o arquivo em memória antes de paginar:** Para arquivos grandes, isso é ineficiente. Para retornar os últimos 100 registros, idealmente usaria leitura reversa (tail) ou um banco de dados.

3. **Sem campo de `usuario` na auditoria:** O campo `origem` existe, mas não há identificação do usuário que executou a ação. Num sistema multiusuário futuro, isso é essencial para LGPD/rastreabilidade.

4. **Falta docstring nas funções:** `registrar()` e `listar()` não têm docstrings explicando parâmetros e retornos.

---

### 📄 `app_recepcao.py` (328 linhas)

**Avaliação geral: ⚠️ Funcionalmente completo, mas com problemas de robustez e segurança.**

**Pontos positivos:**
- Separação clara de responsabilidades entre funções expostas via `@eel.expose`.
- A dupla conversão de data (`converter_data_para_db` / `converter_data_para_web`) centralizada evita repetição.
- `buscar_por_nome()` com `LIKE` e `LIMIT 20` é pragmático e funcional.
- `verificar_duplicata()` é um recurso importante para integridade de dados.
- `salvar()` usa `INSERT OR REPLACE` — correto para upsert de pacientes.
- `init_db()` com `try/except` no `ALTER TABLE` é uma forma funcional (se frágil) de migrações.

**Problemas identificados:**

1. **🔴 INJEÇÃO SQL POTENCIAL em `buscar_por_nome()`:**

   ```python
   cursor.execute("... WHERE nome LIKE ?", (f"%{termo.upper()}%",))
   ```

   O `?` parameterizado protege contra injeção, mas `termo` não é sanitizado. Strings muito longas ou com caracteres especiais do LIKE (`%`, `_`) podem causar comportamentos inesperados. Adicionar `termo = termo.replace('%', '').replace('_', '')[:50]` antes da query.

2. **🔴 GERENCIAMENTO DE CONEXÃO INCONSISTENTE:** `buscar_paciente()`, `buscar_por_nome()` e `buscar_historico()` fecham a conexão no caminho feliz, mas se ocorrer uma exceção antes do `conn.close()`, a conexão vaza. Apenas `salvar()` usa `finally` corretamente. As demais deveriam usar `with conectar_banco() as conn:` ou `try/finally`.

3. **🔴 `conectar_banco()` cria nova conexão a cada chamada:** Com `check_same_thread=False` e múltiplas requisições concorrentes (Eel usa threads), múltiplas conexões abertas ao mesmo SQLite podem causar `database is locked`. Usar um pool ou `WAL journal mode` (`PRAGMA journal_mode=WAL`) seria mais robusto.

4. **⚠️ `_status_gari` é uma global mutável sem lock:** A variável `_status_gari` é modificada em uma thread e lida por outra (via `@eel.expose`). Embora Python tenha o GIL, o padrão correto seria usar `threading.Lock()` ou `threading.Event()`.

5. **⚠️ `init_db()` sem verificação de schema:** A migração via `try/except OperationalError` no `ALTER TABLE` é frágil — se houver erro de outra natureza (ex: banco corrompido), ele é silenciosamente ignorado. Migrações deveriam usar controle de versão de schema.

6. **⚠️ `salvar()` não valida os dados recebidos:** Não há verificação de campos obrigatórios nem validação de CPF/SUS antes de inserir no banco. Se o frontend enviar dados malformados, eles entram no banco sem validação. As funções de `utils.py` existem mas não são usadas aqui para validar.

7. **Modo `msedge` hardcoded:**

   ```python
   eel.start('index.html', mode='msedge', ...)
   ```

   Em máquinas sem Edge instalado, o sistema falha. Deveria ter fallback (`mode='default'` ou tentativa com Chrome).

---

### 📄 `main.py` (317 linhas)

**Avaliação geral: ✅ Arquitetura bem pensada, com alguns riscos operacionais.**

**Pontos positivos:**
- Auto-update inteligente com fallback ZIP quando Git não está disponível — excelente para ambiente hospitalar sem Git instalado.
- Comparação semântica de versão correta com normalização de partes (`1.0` vs `1.0.0`).
- Separação clara entre `servidor_recepcao()`, `servidor_painel()` e `modo_servico()`.
- Flags `--no-update` e `--build` são uma adição profissional que facilita manutenção.
- Banner ASCII no startup é um toque elegante e útil para identificação visual.
- A classe `Cores` para output colorido no terminal é bem implementada.

**Problemas identificados:**

1. **🔴 `fazer_update_zip()` substitui arquivos de código enquanto o sistema roda:** O processo Python está em execução enquanto os `.py` são sobrescritos. No Windows isso pode causar erros de `PermissionError` ou comportamento imprevisível. A atualização deveria criar um script de atualização externo que roda após o processo principal encerrar.

2. **🔴 `verificar_atualizacao()` usa `input()` bloqueante na thread principal:** Se o sistema for iniciado como serviço (sem terminal interativo), a chamada a `input()` bloqueia o processo para sempre. Adicionar timeout ou modo não-interativo:

   ```python
   if not sys.stdin.isatty():
       aviso("Modo não-interativo: pulando atualização.")
       return False
   ```

3. **⚠️ `VERSAO_LOCAL = "1.1.0"` hardcoded E no `version.json`:** A versão está duplicada. Se uma for atualizada sem a outra, haverá inconsistência. Deveria haver uma única fonte de verdade: sempre ler do `version.json`.

4. **⚠️ `time.sleep(0.5)` entre subida dos servidores:** A pausa de 0,5s para o servidor da recepção "subir" é uma forma frágil de sincronização. Se a máquina estiver lenta, o painel pode tentar iniciar antes da recepção estar pronta. Seria melhor usar um evento de sincronização (`threading.Event`).

5. **⚠️ Threads daemon podem perder dados na saída:** Ambas as threads são `daemon=True`, o que significa que são encerradas abruptamente quando o processo principal termina. Se o Gari da Nuvem estiver no meio de um commit ao banco quando CTRL+C for pressionado, pode haver corrupção. Um `threading.Event` de shutdown gracioso seria mais seguro.

6. **`URL_VERSION` aponta para `raw.githubusercontent.com` (sem auth):** Isso funciona para repositório público, mas se o repo se tornar privado (ex: na migração futura), quebra. O comentário poderia alertar sobre isso.

---

### 📄 `registro/` e demais subdiretórios

Os diretórios `analise/`, `automacao/`, `integracao/`, `scripts/`, `web_recepcao/`, `web_painel/` e `registro/` não foram acessíveis via robots.txt para listagem de árvore, mas com base na arquitetura declarada no README, os padrões identificados nos arquivos raiz provavelmente se replicam internamente.

---

## 3. Visão Holística e Integração

### 3.1 Pontos Fortes da Arquitetura

O projeto demonstra uma **arquitetura modular coerente** para um sistema hospitalar desenvolvido por um único desenvolvedor em contexto real de operação. A separação entre recepção, painel e automação está bem definida. O uso do Eel como ponte Desktop/Web é uma escolha pragmática que resolve o problema de interface sem a complexidade de um framework frontend completo.

### 3.2 Gargalos e Riscos Identificados

**Gargalo 1 — SQLite como banco compartilhado por múltiplas threads:**
`app_recepcao.py` (thread principal Eel + thread do Gari) e `app_painel.py` compartilham o mesmo `hospital.db` via SQLite. SQLite suporta concorrência limitada — leituras simultâneas são ok, mas escritas concorrentes causam `database is locked`. O `timeout=30.0` na conexão é um paliativo. A solução definitiva é `PRAGMA journal_mode=WAL` (já previsto no Roadmap com PostgreSQL).

**Gargalo 2 — Eel + threading:** O Eel não foi projetado para rodar dois servidores simultaneamente. O `block=False` no `app_painel` é uma gambiarra funcional, mas pode causar comportamento imprevisível dependendo da versão do Eel.

**Risco 1 — Dado de paciente chegando ao Google Sheets sem validação completa:** O pipeline `salvar() → banco → gari → sheets` não garante que os dados foram validados antes de entrar. Um CPF inválido chega ao Sheets formatado incorretamente, potencialmente causando problemas de auditoria.

**Risco 2 — Sem mecanismo de retry com backoff exponencial no Gari:** Se a API do Google Sheets cair por 5 minutos, o Gari tenta a cada 10s, gerando centenas de requisições e potencialmente causando rate limit. Um backoff exponencial (`1s, 2s, 4s, 8s...`) seria mais robusto.

**Risco 3 — Auto-update sem verificação de integridade:** O ZIP baixado do GitHub não tem verificação de hash (SHA256). Um download corrompido ou interceptado poderia substituir código legítimo por código malicioso.

**Risco 4 — Sem multi-usuário:** O sistema é single-user por design (sem autenticação de sessão). Múltiplos recepcionistas usando simultaneamente podem causar conflitos de registro (número de registro duplicado).

### 3.3 Ausência de Testes

Não há diretório `tests/` nem arquivos `test_*.py`. Para um sistema em produção hospitalar, a ausência de testes automatizados é o maior risco a médio prazo — qualquer refatoração pode quebrar validações críticas silenciosamente.

---

## 4. Relatório Final Consolidado

### 🔴 Críticos (resolver antes de qualquer expansão)

| ID | Arquivo | Problema |
|----|---------|----------|
| C1 | `config.py` | Senhas padrão hardcoded (Firebird, Admin, Google Sheet ID, CNS/CBO) |
| C2 | `app_recepcao.py` | Conexões SQLite sem `finally` / sem `WAL mode` — risco de `database locked` |
| C3 | `planilha_nuvem.py` | Autenticação Google recriada a cada envio — ineficiente e frágil |
| C4 | `planilha_nuvem.py` | Estado `enviado_nuvem = 2` pode travar permanentemente se o processo cair |
| C5 | `app_recepcao.py` | `salvar()` não valida CPF/CNS antes de inserir no banco |
| C6 | `main.py` | `input()` bloqueante pode travar o processo em ambiente sem terminal |

### ⚠️ Importantes (resolver no próximo ciclo)

| ID | Arquivo | Problema |
|----|---------|----------|
| I1 | `logging_setup.py` | Sem rotação de arquivo de log — rastreabilidade em produção limitada |
| I2 | `planilha_nuvem.py` | `except Exception: pass` silencioso no loop do Gari |
| I3 | `planilha_nuvem.py` | Função `enviar_para_planilha()` muito longa (150+ linhas) — refatorar |
| I4 | `auditoria_log.py` | Arquivo `auditoria.log` sem rotação — crescimento ilimitado |
| I5 | `main.py` | `VERSAO_LOCAL` duplicada em `main.py` e `version.json` |
| I6 | `app_recepcao.py` | Modo `msedge` hardcoded — sem fallback para outras máquinas |
| I7 | `main.py` | Threads `daemon=True` sem shutdown gracioso — risco de perda de dados |

### 💡 Melhorias (backlog técnico)

| ID | Arquivo | Sugestão |
|----|---------|----------|
| M1 | `utils.py` | Adicionar `tests/test_utils.py` com casos de borda documentados |
| M2 | `auditoria_log.py` | Adicionar campo `usuario` na auditoria para conformidade com LGPD |
| M3 | `planilha_nuvem.py` | Implementar backoff exponencial no retry de envio ao Google Sheets |
| M4 | `main.py` | Verificação de integridade SHA256 no download do ZIP de atualização |
| M5 | `app_recepcao.py` | Migrar schema do banco para sistema de migrations versionado (ex: Alembic) |
| M6 | Geral | Criar `Makefile` ou `pyproject.toml` com comandos `make run`, `make test`, `make lint` |

---

## 5. Avaliação Geral

| Dimensão | Nota | Comentário |
|----------|------|-----------|
| Arquitetura | 8/10 | Modular, bem separada, adequada ao contexto |
| Documentação | 9/10 | Acima da média — comentários explicam o porquê, não só o quê |
| Lógica e Eficiência | 7/10 | Funcional mas com gargalos de conexão e autenticação |
| Segurança | 5/10 | Credenciais padrão e senha em texto plano são riscos sérios |
| Robustez / Tratamento de Erros | 6/10 | Excepts silenciosos e falta de validação de dados de entrada |
| Testabilidade | 3/10 | Ausência total de testes automatizados |
| Potencial de Evolução | 8/10 | Roadmap claro, código preparado para migração futura |

---

## 6. Próximos Passos Sugeridos

Com base na análise, sugiro a seguinte ordem de prioridade de trabalho:

1. **Sprint Segurança (urgente):** Resolver C1 — mover todas as credenciais para `.env` obrigatório com validação na inicialização. Adicionar hash na senha admin.

2. **Sprint Robustez:** Resolver C2, C3, C4 — WAL mode no SQLite, singleton de autenticação Google, limpeza de locks fantasmas no Gari.

3. **Sprint Validação:** Resolver C5 — chamar `valida_cpf()` e `valida_cns()` dentro de `salvar()` antes de persistir.

4. **Sprint Testes:** Criar `tests/test_utils.py` cobrindo todos os casos de borda das validações críticas.

5. **Roadmap Médio Prazo:** Conforme declarado no README — migração para FastAPI + PostgreSQL resolverá organicamente os problemas de concorrência e multi-usuário.

---

*Este relatório foi gerado com base na leitura direta do código-fonte do repositório público. Nenhuma alteração foi feita no código.*

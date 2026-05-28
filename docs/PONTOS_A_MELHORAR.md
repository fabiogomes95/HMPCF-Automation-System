# Pontos a Melhorar — HMPCF Automation System

## 📊 Visão Geral

**Sistema:** HMPCF Automation System v1.1.0
**Plataforma:** Python + Eel (Web/Desktop híbrido) + SQLite + Firebird + Google Sheets
**~7.027 linhas de código (Python + HTML + JS + CSS)**

## 🗄️ Banco de Dados

| Tabela | Registros |
|--------|-----------|
| `pacientes` | **29.218** |
| `atendimentos` | **8.024** |

## ✅ Pontos Positivos

1. **Config segura** — `_require_env()` força credenciais críticas; SHA256 na senha admin
2. **Google Auth singleton** — credenciais recriadas apenas na primeira chamada
3. **WAL mode** no SQLite — `PRAGMA journal_mode=WAL` na recepção
4. **Try/finally nas conexões** — conexões fechadas corretamente
5. **Sanitização LIKE** — escape de `%` e `_` na busca por nome
6. **Validação CPF/CNS no salvar** — validação antes de inserir
7. **Código bem documentado** — docstrings explicam o "porquê"
8. **Separação Terminal Eventos × Últimas Ações** no painel
9. **Auditoria com tipo** (`sistema` vs `acao`)
10. **Auto-update inteligente** com fallback ZIP + `.py` adiados

## ⚠️ Pontos a Melhorar

### 🔴 Críticos

| # | Onde | Problema |
|---|------|----------|
| 1 | `logging_setup.py` | Sem arquivo de log — apenas stdout. Em produção hospitalar, logs deveriam persistir em arquivo com rotação |
| 2 | `app_painel.py` | Carrega Firebird inteiro na RAM — 108 pacientes hoje, mas não escala |
| 3 | `app_painel.py` | Importa módulos via `sys.path.insert` — abordagem frágil |
| 4 | `planilha_nuvem.py:308-311` | `except Exception: pass` silencioso no loop principal do Gari |
| 5 | `app_painel.py:668-669` | `while True: eel.sleep(1.0)` — consumo desnecessário de CPU |

### 🟡 Importantes

| # | Onde | Problema |
|---|------|----------|
| 6 | `app_recepcao.py:346` | `mode='msedge'` hardcoded — sem fallback se não tiver Edge |
| 7 | `main.py` | Threads daemon sem shutdown gracioso — risco de perda de dados |
| 8 | `main.py` | Versão duplicada em `main.py` e `version.json` |
| 9 | `planilha_nuvem.py` | Sem backoff exponencial — se Google Sheets cair, tenta a cada 10s |
| 10 | `auditoria_log.py` | Sem rotação — `auditoria.log` cresce indefinidamente |

### 💡 Sugestões

| # | Onde | Sugestão |
|---|------|----------|
| 11 | Geral | Sem testes automatizados — risco em refatorações |
| 12 | `auditoria_log.py` | Sem campo `usuario` — necessário para LGPD/rastreabilidade |
| 13 | `app_recepcao.py` | Sem verificação de schema — migração via `try/except` é frágil |

## 📋 Resumo

O sistema legado está funcional e em produção com boa qualidade de código. Os maiores riscos são:
1. **Ausência de logs em arquivo** — impossível depurar depois que fecham o terminal
2. **Single-user** — sem autenticação de sessão, conflitos com múltiplos recepcionistas
3. **Dependência do Eel** — tecnologia com suporte limitado
4. **Zero testes** — qualquer mudança pode quebrar validações críticas

# Validação em ambiente real — Autenticação (#1) e Auditoria (#2)

Checklist do que só dá pra confirmar numa máquina com Postgres de verdade
rodando — este sandbox de desenvolvimento não tem banco disponível, então
tudo abaixo foi validado até onde deu (testes coletam sem erro, smoke
test manual em SQLite passou), mas **nunca rodou contra o Postgres real**.

Guias completos de referência (se precisar de mais contexto):
`docs/DEPLOY_HOSPITAL.md` (seções 6.4/6.5 e checklist 11.2-11.4).

---

## Antes de começar

- [ ] `backend/.env` existe e tem `POSTGRES_PASSWORD` preenchido
- [ ] `cd backend && .venv\Scripts\pip install -r requirements.txt` — pega
      o `bcrypt` novo (item #1)
- [ ] Backend sobe normalmente antes de mexer em auth/auditoria
      (`uvicorn app.main:app --port 8001`) — se já tava quebrado por outro
      motivo, mais fácil descobrir agora do que depois

---

## Passo 1 — Autenticação

### 1.1 Criar as tabelas e as contas

```powershell
cd backend
.venv\Scripts\python scripts\criar_tabelas_auth.py
# esperado: OK: tabelas 'usuarios' e 'sessoes' garantidas (...)

.venv\Scripts\python scripts\gerenciar_usuarios.py criar --username recepcao    --role recepcao
.venv\Scripts\python scripts\gerenciar_usuarios.py criar --username coordenacao --role coordenacao
.venv\Scripts\python scripts\gerenciar_usuarios.py criar --username bpa         --role bpa
```

- [ ] As 3 contas foram criadas sem erro
- [ ] `gerenciar_usuarios.py listar` mostra as 3, todas "ativo"

### 1.2 Testar a API isolada (antes do frontend)

```powershell
# sem login -> 401 (isso é o esperado, não é bug)
Invoke-WebRequest "http://localhost:8001/api/v1/pacientes?page_size=1"

# login guardando sessão numa variável
$sessao = $null
Invoke-WebRequest -Uri "http://localhost:8001/api/v1/auth/login" -Method Post `
  -ContentType "application/json" -Body '{"username":"recepcao","password":"SUA_SENHA"}' `
  -SessionVariable sessao

# com o cookie da sessão -> 200
Invoke-WebRequest "http://localhost:8001/api/v1/pacientes?page_size=1" -WebSession $sessao
```

- [ ] Sem cookie → `401`
- [ ] Login certo → `200` + `{"username":"recepcao","role":"recepcao"}`
- [ ] Com o cookie → `200`, lista pacientes de verdade
- [ ] Login com senha errada 5x seguidas → conta bloqueada (mensagem
      menciona horário de desbloqueio); 6ª tentativa com a senha **certa**
      continua dando `401` enquanto bloqueada

### 1.3 Testar pelo frontend

```powershell
cd frontend
npm run build      # gera frontend/dist, servido pelo próprio backend
```

Depois, com o backend rodando, abra `http://localhost:8001/`:

- [ ] Aparece a tela de **login** antes de qualquer coisa (não a Recepção)
- [ ] Usuário/senha errados → mensagem de erro na tela, não trava/quebra
- [ ] Login certo (`recepcao`) → abre a tela de Recepção normalmente
- [ ] Botão **Sair** (canto direito da barra) → volta pro login
- [ ] Depois de "Sair", dar refresh na página **não** volta logado sozinho

### 1.4 Rodar os testes automatizados

```powershell
cd backend
pytest tests/ -v
```

- [ ] Os 21 testes antigos continuam passando
- [ ] Os 8 novos de `test_auth_service.py` passam
- [ ] Total: 29 (mais os 7 de auditoria abaixo = 36)

---

## Passo 2 — Log de auditoria

### 2.1 Criar a tabela

```powershell
cd backend
.venv\Scripts\python scripts\criar_tabela_auditoria.py
# esperado: OK: tabela 'logs_auditoria' garantida (...)
```

- [ ] Rodou sem erro

### 2.2 Gerar algumas ações de teste

Com o backend rodando e logado (frontend ou `$sessao` do passo 1.2):

- [ ] Cadastrar um paciente novo (de teste, não um paciente real)
- [ ] Editar um campo desse paciente (ex: cidade)
- [ ] Registrar um atendimento pra esse paciente
- [ ] Apagar o atendimento de teste

### 2.3 Conferir o log

```powershell
Invoke-WebRequest "http://localhost:8001/api/v1/auditoria?page_size=10" -WebSession $sessao | Select -Expand Content
```

- [ ] Aparecem as 4 ações na ordem certa (mais recente primeiro)
- [ ] `usuario_username` mostra `"recepcao"` (ou o papel que você usou)
- [ ] A edição de campo mostra `campos_alterados` com o(s) nome(s) certo(s)
      (ex: `["cidade"]`)
- [ ] **Nenhuma resposta contém CPF, CNS, endereço ou qualquer dado do
      paciente** — só metadados (isso é o ponto principal do item #2,
      vale conferir com atenção)
- [ ] Testar o filtro: `?recurso=paciente` só traz ações de paciente

### 2.4 Rodar os testes automatizados

```powershell
cd backend
pytest tests/test_auditoria_service.py -v
```

- [ ] Os 7 testes passam

---

## Se algo der errado

| Sintoma | Causa provável |
|---|---|
| `ModuleNotFoundError: bcrypt` | Esqueceu `pip install -r requirements.txt` depois do item #1 |
| `401` mesmo depois de logar certo | Cookie não está sendo enviado — confira se está testando em `http://localhost:8001` (mesma origem do backend), não em `5173` sem o proxy do Vite rodando |
| Script de criar tabela dá erro de conexão | `backend/.env` sem `POSTGRES_PASSWORD` ou Postgres não está rodando |
| `gerenciar_usuarios.py criar` diz "usuário já existe" | Rodou duas vezes — use `resetar-senha` em vez de `criar` |
| Tela de login não aparece, vai direto pra Recepção | `frontend/dist` antigo (buildado antes do item #1) — rode `npm run build` de novo |

---

## Depois de validar tudo

Se os dois passos passarem limpos, me avisa que eu:
1. Atualizo `README.md`/`README.pt-BR.md` (seção "Segurança e Limitações")
   pra refletir que autenticação e log de auditoria já existem — não fiz
   isso ainda de propósito, pra não documentar algo não testado.
2. Sigo pro item #3 da lista de prioridades (testes do `bpa_gerador.py`).

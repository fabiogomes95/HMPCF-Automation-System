# Pendências — backlog técnico

Lista viva de melhorias identificadas na auditoria de 04/09/2026 (ver
`docs/HISTORICO.md`). Diferente de `docs/historico/PENDENCIAS_2026-07-03.md`
(um retrato de uma data específica), este arquivo é atualizado conforme
os itens vão sendo feitos ou entrando na lista.

---

## Feito

| # | Item | Onde |
|---|------|------|
| 1 | Autenticação na recepção (login por papel, sessão em cookie) | `backend/app/services/auth_service.py` |
| 2 | Log de auditoria (quem criou/editou/apagou o quê) | `backend/app/services/auditoria_service.py` |
| 3 | Testes do layout DATASUS + rollover de folha/sequência do BPA | `bpa/tests/test_bpa_gerador.py` |
| 4 | Backup criptografado com cópia fora da máquina (OneDrive) | `scripts/windows/copiar_backup_onedrive.ps1` |
| 5 | CI no GitHub Actions (roda os testes automaticamente a cada push) | `.github/workflows/ci.yml` |
| 6 | Login automático no acesso local (terminal fixo da recepção não vê tela de login; acesso remoto continua exigindo) | `backend/app/api/deps.py`, `AUTO_LOGIN_LOCAL`/`AUTO_LOGIN_USERNAME` no `.env` |
| 7 | Nova aba "Planilha" — relatório mensal estilo planilha manual, separado por plantão diurno/noturno (07h-18h59 / 19h-06h59), com filtro de mês/turno/dia | `frontend/src/pages/PlanilhaAtendimentos.jsx`, `GET /api/v1/recepcao/planilha` |
| 8 | Botão "Imprimir" registra o atendimento sozinho se a recepção esquecer de clicar "Registrar Atendimento" antes | `frontend/src/pages/Recepcao.jsx` (`handleImprimir`) |
| 9 | Paciente sem CPF/CNS — os dois viram opcionais pra salvar; `sem_documento` é marcado sozinho no banco quando falta CPF (usado futuramente na exportação BPA/Firebird) | `backend/app/services/paciente_service.py`, coluna `pacientes.sem_documento` |

## Deploy em produção — em andamento

Ainda não foi promovido. Ambiente de teste sendo preparado em paralelo,
sem tocar no serviço em produção que já está rodando. Detalhes
operacionais (hostname, IPs, credenciais, contagens) ficam só nas
anotações locais não versionadas — nunca neste arquivo, que é público.

## Pendente

### 10. Refatorar `bpa/app.py` em camadas

Hoje é um arquivo Flask único (~950 linhas) misturando rota HTTP, regra
de negócio e acesso a dois bancos (Postgres e Firebird) — o oposto do
padrão em camadas que `backend/` já usa bem (API → Service → Repository).
É justamente onde já aconteceu o incidente real de julho/2026 (`S_PRD`
zerado). Separar em camadas reduz a chance do próximo incidente e facilita
debugar quando algo der errado.

### 11. Alembic de verdade (ou documentar como o schema é versionado hoje)

A documentação antiga citava migrations via Alembic, mas não existe
`alembic.ini` nem pasta `alembic/` no repo — achado confirmado na Fase 4
da reorganização (04/09/2026). Sem isso, mudança de schema em produção é
manual, sem histórico nem rollback. Ou implementa de verdade, ou
documenta oficialmente o processo real (scripts standalone, como os
itens 1-2 fizeram pras tabelas novas).

### 12. Validar `sem_documento` na exportação BPA/Firebird

Paciente sem CPF/CNS agora pode ser salvo na recepção (`pacientes.sem_documento
= true`, automático). BPA/SUS tem uma opção própria pra esse caso, mas o lado
do BPA (`bpa/`) ainda não lê nem valida esse campo — combinado pra ser feito
"amanhã" (a partir de 11/09/2026).

### 13. Copiar linha da Planilha pro clipboard (opcional, só se precisarem)

As meninas da recepção ainda alimentam uma planilha manual (Excel) em
paralelo com os mesmos dados. Ideia: um botão por linha na aba "Planilha"
que copia os campos daquela linha formatados com TAB entre eles (cola
direto nas colunas do Excel). Baixa prioridade — só implementar se, na
prática, elas continuarem de fato usando a planilha manual depois que a
aba nova estiver disponível.

### 14. Consolidar os 3 launchers redundantes do backend

`INICIAR.bat`, `scripts/windows/ABRIR_HMPCF.bat` e
`scripts/windows/iniciar_sistema.vbs` fazem a mesma coisa. Dívida em
aberto desde 02/07/2026 (`docs/HISTORICO.md`). **Bloqueado por você** —
depende de testar numa máquina de teste antes de saber com certeza qual
deles está registrado no Agendador de Tarefas da produção, pra não
quebrar o autostart do hospital ao remover o errado.

---

## Como usar este arquivo

Quando um item da lista "Pendente" for feito, mover pra "Feito" com a
data e o commit/arquivo principal, igual às linhas 1-5 acima.

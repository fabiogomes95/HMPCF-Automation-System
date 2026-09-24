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
| 4 | Backup criptografado com cópia fora da máquina — Google Drive desde 23/09/2026 (estava parado desde 17/06), com log por execução; restauração testada | `scripts/servidor/copiar_backup_nuvem.ps1`, `backup_postgres.bat` |
| 5 | CI no GitHub Actions (roda os testes automaticamente a cada push) | `.github/workflows/ci.yml` |
| 6 | Login automático no acesso local (terminal fixo da recepção não vê tela de login; acesso remoto continua exigindo) | `backend/app/api/deps.py`, `AUTO_LOGIN_LOCAL`/`AUTO_LOGIN_USERNAME` no `.env` |
| 7 | Nova aba "Planilha" — relatório mensal estilo planilha manual, separado por plantão diurno/noturno (07h-18h59 / 19h-06h59), com filtro de mês/turno/dia | `frontend/src/pages/PlanilhaAtendimentos.jsx`, `GET /api/v1/recepcao/planilha` |
| 8 | Botão "Imprimir" registra o atendimento sozinho se a recepção esquecer de clicar "Registrar Atendimento" antes | `frontend/src/pages/Recepcao.jsx` (`handleImprimir`) |
| 9 | Paciente sem CPF/CNS — os dois viram opcionais pra salvar; `sem_documento` é marcado sozinho no banco quando falta CPF (usado futuramente na exportação BPA/Firebird) | `backend/app/services/paciente_service.py`, coluna `pacientes.sem_documento` |
| 13 | Copiar linha da Planilha pro clipboard — botão por linha, cola direto nas colunas do Excel; aba também passou a abrir já filtrada no plantão vigente (evita travar a página com ~6mil atendimentos/mês) | `frontend/src/pages/PlanilhaAtendimentos.jsx` |
| 15 | Remoção de atendimento REPETIDO pela própria recepção — o servidor só aceita duplicata real (mesmo paciente, mesmo plantão, até 15 min) e mantém o registro mais novo; tudo na auditoria | `RecepcaoService.remover_repetido`, `DELETE /recepcao/{id}/repetido` |
| 16 | Sem bloqueio de login por tentativas erradas — travava o terminal fixo (auto-login usa a mesma conta) | `backend/app/services/auth_service.py` |
| 17 | Postgres fechado pra rede: `postgres` só local; pela rede só o usuário `bpa_leitura` (SELECT em `pacientes` e `recepcao_atendimentos`, tudo que o BPA lê). Senha antiga removida do histórico do git | `pg_hba.conf` do servidor, `docs/INSTALACAO_BPA_MIGRACAO.md` |
| 18 | Fuso do Postgres `America/Sao_Paulo` (era `America/Cayenne` — mesmo horário hoje, mas erraria se voltar o horário de verão) | `postgresql.auto.conf` do servidor |
| 19 | Log do backend troca de arquivo a cada 10 MB (nssm); arquivos com mais de 90 dias são apagados pelo backup diário | serviço `HMPCF-Backend-Svc`, `backup_postgres.bat` |
| 20 | Auditoria também registra gestão de usuários (criar, redefinir senha, ativar/desativar, trocar a própria senha) — nunca a senha em si | `endpoints/ti.py`, `endpoints/auth.py` |
| 14 | Lançadores redundantes resolvidos: produção sobe só pelo serviço `HMPCF-Backend-Svc` (nssm); `INICIAR.bat`, `ABRIR_HMPCF.bat`, `iniciar_sistema.vbs`, watchdog e as tarefas `HMPCF-Backend`/`Watchdog`/`Dashboard` (já desativadas) foram para `legado/lancadores_antigos/` (23/09/2026) | `scripts/servidor/`, `legado/` |
| 21 | Organização das pastas: `scripts/servidor/` (só o que roda no servidor), `bpa/ferramentas/`, `legado/scripts_uso_unico/`; README em português vira a documentação única | `README.pt-BR.md` |
| 22 | Perfil faturamento + BPA etapa 1 (instalador, liga com o Windows, só aceita o sistema do hospital) | `frontend/src/App.jsx`, `bpa/instalar.ps1` |
| 23 | BPA em FastAPI (mesmo padrão do backend, paridade byte a byte com o antigo) + aba BPA no sistema (Digitação, Enfermeiros, Migração, Conferência com reenviar, Prontuário) + migração automática do dia | `bpa/bpa_local/`, `frontend/src/pages/bpa/` |
| 24 | Paciente sem documento no BPA (sem CPF/SUS, `prd_possui_cpf_cns = s`); SUS nunca vai no BPA-I; backup dos lotes de digitação no servidor; situação do dia na Digitação | `bpa/bpa_gerador.py`, `bpa/bpa_local/services/backup_lotes.py` |

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

---

## Como usar este arquivo

Quando um item da lista "Pendente" for feito, mover pra "Feito" com a
data e o commit/arquivo principal, igual às linhas 1-5 acima.

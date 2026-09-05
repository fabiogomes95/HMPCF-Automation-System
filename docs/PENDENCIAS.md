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

## Pendente

### 6. Refatorar `bpa/app.py` em camadas

Hoje é um arquivo Flask único (~950 linhas) misturando rota HTTP, regra
de negócio e acesso a dois bancos (Postgres e Firebird) — o oposto do
padrão em camadas que `backend/` já usa bem (API → Service → Repository).
É justamente onde já aconteceu o incidente real de julho/2026 (`S_PRD`
zerado). Separar em camadas reduz a chance do próximo incidente e facilita
debugar quando algo der errado.

### 7. Alembic de verdade (ou documentar como o schema é versionado hoje)

A documentação antiga citava migrations via Alembic, mas não existe
`alembic.ini` nem pasta `alembic/` no repo — achado confirmado na Fase 4
da reorganização (04/09/2026). Sem isso, mudança de schema em produção é
manual, sem histórico nem rollback. Ou implementa de verdade, ou
documenta oficialmente o processo real (scripts standalone, como os
itens 1-2 fizeram pras tabelas novas).

### 8. Consolidar os 3 launchers redundantes do backend

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

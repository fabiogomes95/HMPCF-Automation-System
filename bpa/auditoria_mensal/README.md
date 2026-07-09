# Auditoria mensal — scripts de referência

Scripts usados na auditoria da competência 06/2026 (ver
`docs/AUDITORIA_BPA_2026-06.md`). Servem de base para a futura rota/aba de
"Fechamento de Mês" no Flask — ainda não estão ligados ao `app.py`.

- `fix_colisoes.py` — corrige `(PRD_CNSMED, PRD_MVM, PRD_FLH, PRD_SEQ)`
  duplicados em `S_PRD`. Idempotente (rodar de novo sem colisão não faz
  nada). Rode com `--aplicar`; sem essa flag é dry-run. **Faça backup do
  banco (`gbak`) antes de rodar com `--aplicar`.**
- `patch_lotes.py` — insere em `BPA_MEDICOS_*`/`BPA_ENFERMEIROS_*` os
  atendimentos que estão em `S_PRD` e não foram exportados. `ALVOS` está
  hardcoded pras datas da competência 06/2026 — generalizar antes de
  reusar em outra competência. Rode com `--aplicar`; sem a flag é dry-run.

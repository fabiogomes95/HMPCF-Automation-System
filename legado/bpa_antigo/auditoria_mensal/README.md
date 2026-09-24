# Auditoria mensal — scripts de referência

Scripts usados na auditoria da competência 06/2026 (ver
`docs/historico/AUDITORIA_BPA_2026-06.md`). Servem de base para a futura rota/aba de
"Fechamento de Mês" no Flask — ainda não estão ligados ao `app.py`.

- `fix_colisoes.py` — corrige `(PRD_CNSMED, PRD_MVM, PRD_FLH, PRD_SEQ)`
  duplicados em `S_PRD`. Idempotente (rodar de novo sem colisão não faz
  nada). Rode com `--aplicar`; sem essa flag é dry-run. **Faça backup do
  banco (`gbak`) antes de rodar com `--aplicar`.**
- `patch_lotes.py` — insere em `BPA_MEDICOS_*`/`BPA_ENFERMEIROS_*` os
  atendimentos que estão em `S_PRD` e não foram exportados. `ALVOS` está
  hardcoded pras datas da competência 06/2026 — generalizar antes de
  reusar em outra competência. Rode com `--aplicar`; sem a flag é dry-run.
- `reconstruir_producao_202606.py` — reconstrução de emergência de `S_PRD`
  a partir dos arquivos brutos de digitação (usado em 10/07/2026 depois de
  `S_PRD` ter sido zerado por completo). `ARQUIVOS` está hardcoded pros 10
  dias da competência 06/2026 — generalizar antes de reusar. Rode com
  `--aplicar`; sem a flag é dry-run. Ver `docs/historico/AUDITORIA_BPA_2026-06.md`
  ("Incidente — S_PRD zerado e reconstruído").
- `reinserir_achado1_pos_reconstrucao.py` — companheiro do script acima:
  depois de reconstruir a partir da digitação, acha e reinsere (com folha/
  sequência recalculada, não copiada do arquivo) os atendimentos que só
  existiam via `/api/pacientes/completar`/`/api/conferencia/reenviar`
  (nunca passam pela digitação). `ALVOS` também hardcoded pra 06/2026.

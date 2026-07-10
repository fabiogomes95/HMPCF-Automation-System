# Auditoria BPA — competência 06/2026 (09/07/2026)

> Sem dado de paciente aqui de propósito (CPF/CNS/nome não vão pro
> histórico do Git). Detalhe completo, local, em
> `C:\BPA\AUDITORIA_BPA_2026-07-09.md` na máquina de produção.

## Resumo

Auditoria da competência 06/2026 comparando `S_PRD` (Firebird) contra os
arquivos já exportados (`BPA_MEDICOS_*.txt`/`BPA_ENFERMEIROS_*.txt`) em
`C:\BPA\bpa_lotes`. Achados dois problemas e um deles já foi corrigido.

## Achado 1 — export desatualizado em relação ao banco (pendente)

`/api/pacientes/completar` e `/api/conferencia/reenviar` gravam direto em
`S_PRD` mas nunca atualizam os arquivos `BPA_MEDICOS_*`/`BPA_ENFERMEIROS_*`
já exportados. Resultado: registros existem no banco e nunca chegam no
arquivo que de fato vai pro SIASUS. `conferencia.py` não detecta isso
porque compara "digitado × banco", nunca "banco × arquivo exportado".

Na competência 06/2026, 6 atendimentos ficaram nessa situação (2 dias
afetados). Lista completa com identificação de paciente está no `.md` local
(não neste repositório).

**Status:** corrigido em 10/07/2026 — aplicado `bpa/auditoria_mensal/patch_lotes.py
--aplicar` (backup dos 4 arquivos afetados antes, em
`C:\BPA\bpa_lotes\backup_antes_patch_20260710_161403\`). As 6 linhas foram
inseridas em `BPA_MEDICOS_16062026.txt`, `BPA_ENFERMEIROS_16062026.txt`,
`BPA_MEDICOS_21062026.txt` (3 linhas) e `BPA_ENFERMEIROS_21062026.txt`,
cabeçalho recalculado em cada arquivo. Confirmado depois: dry-run do script
não acusa mais pendência.

## Achado 2 — colisão de folha/sequência (corrigido)

`calcular_atendimentos_producao()` (usada pelas duas rotas acima) recalcula
`PRD_FLH`/`PRD_SEQ` do zero a cada chamada, contando a produção já existente
do profissional. Se chamada mais de uma vez para o mesmo profissional sem os
lançamentos anteriores estarem "assentados" da forma esperada, duas
chamadas podem calcular a mesma sequência inicial → colisão (dois pacientes
diferentes com o mesmo número de atendimento).

Achado na competência 06/2026: **150 slots colididos, 302 registros, 9
profissionais** (um caso chegou a 99 slots seguidos colidindo).

**Correção aplicada em 09/07/2026** (script `bpa/auditoria_mensal/fix_colisoes.py`):
backup do banco antes (`gbak`), mantida a linha mais antiga em cada slot
colidido, demais realocadas pro próximo slot livre do profissional
(mesma regra de 99 atendimentos/folha do `bpa_gerador.py`). 152 linhas
renumeradas — só `PRD_FLH`/`PRD_SEQ`, nada de paciente/procedimento/data
tocado. Confirmado depois: 0 colisões, total de produção inalterado.

## Descoberta útil — fórmula do campo de controle (checksum) do header

Documentada no rodapé de `Layout_Exportacao_BPA.pdf` ("Observação"):
soma de `(código do procedimento + quantidade)` de cada linha, resto da
divisão por 1111, + 1111. Validada contra os 20 arquivos já exportados da
competência (100% de acerto) — é a mesma fórmula já implementada em
`bpa_gerador._calcular_checksum()`, então o gerador atual está correto.

## Achado 3 — duplicidade paciente+procedimento+data (identificado 10/07/2026, pendente de revisão humana)

A checagem 3 do "Fechamento de Mês" (ver abaixo) rodada contra 06/2026
acusou **64 grupos** de paciente+procedimento+data com mais de uma linha em
`S_PRD`. Amostra investigada (`PRD_CNSPAC`+`PRD_PA`+`PRD_DTATEN` fixos):
as duas linhas têm `PRD_CNSMED` diferentes — dois profissionais diferentes
(mesmo CBO) atenderam o mesmo paciente, com o mesmo código de procedimento,
no mesmo dia. Não é "mesma linha duplicada pelo mesmo profissional" (isso
teria pulado nesta checagem do mesmo jeito, só que com o mesmo `PRD_CNSMED`).

**Status:** não corrigido — exige revisão humana caso a caso (pode ser
atendimento legítimo, ex: turno diferente, ou erro de digitação em duplicado
por dois profissionais). Ver lista completa (com paciente) na saída de
`python bpa/fechamento_mes.py 202606` ou na aba "🏁 Fechamento de Mês".

## Pendências (fechamento de mês)

~~Criar uma rota/aba única no Flask ("Fechamento de Mês") que roda
automaticamente as 4 checagens abaixo~~ — **feito em 10/07/2026**:
`bpa/fechamento_mes.py` + rota `/api/fechamento` + aba "🏁 Fechamento de Mês"
no `index.html`. Só-leitura (nenhuma correção é aplicada automaticamente).

1. ~~Comparação `S_PRD` × arquivos exportados~~ (Achado 1) — reaproveita a
   lógica de `bpa/auditoria_mensal/patch_lotes.py`. **OK, feito.**
2. ~~Checagem de colisão de `(PRD_CNSMED, PRD_MVM, PRD_FLH, PRD_SEQ)`~~ —
   reaproveita `bpa/auditoria_mensal/fix_colisoes.py`. **OK, feito.**
3. ~~Checagem de duplicidade paciente+procedimento+data~~ — só reporta, exige
   revisão humana antes de qualquer exclusão. **OK, feito** (ver Achado 3
   acima — já rodou e achou 64 casos pendentes de revisão).
4. ~~Conferência do checksum/contagem de linha do header~~ de cada arquivo já
   exportado. **OK, feito.**

E então:

5. **Remover/aposentar `/api/conferencia/reenviar`** (`app.py`) — é a causa
   raiz da colisão. Revisar também `/api/pacientes/completar` (mesma
   `calcular_atendimentos_producao` por trás) — decidir se vira parte do
   fechamento de mês em vez de correção pontual no meio do mês.

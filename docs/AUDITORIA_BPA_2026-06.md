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

## Incidente — S_PRD zerado e reconstruído (10/07/2026)

Toda a tabela `S_PRD` (não só 06/2026 — a competência inteira que existia)
foi apagada intencionalmente pelo usuário no meio da revisão do Achado 3.
Não havia outra competência em produção além de 06/2026, e a decisão foi
reconstruir do zero em vez de restaurar backup (`C:\BPA\backups\BPAMAG_antes_fix_colisao_20260709_184507.fbk`,
disponível mas traria de volta a colisão do Achado 2, já corrigida).

**Reconstrução** (`bpa/auditoria_mensal/reconstruir_producao_202606.py`):
lê os 10 arquivos brutos de digitação (`DD-MM-2026.txt`) em `C:\BPA\bpa_lotes`
em ordem cronológica e grava direto em `S_PRD` via
`bpa_gerador.calcular_atendimentos_producao`, reaproveitando o
deduplicador já existente em `ler_arquivo_lote` (descarta CPF repetido em
*sequência* dentro do bloco — digitação dupla por engano; mantém CPF
repetido em posições diferentes — paciente atendido de novo de verdade,
confirmado como regra correta pelo usuário). 4.786 atendimentos gravados,
0 colisão, 0 "não encontrado".

**Gap remanescente:** os atendimentos lançados originalmente via
`/api/pacientes/completar`/`/api/conferencia/reenviar` (nunca passam pela
digitação) ficaram de fora dessa reconstrução por definição — 8 registros
(`bpa/auditoria_mensal/reinserir_achado1_pos_reconstrucao.py`, achados
comparando arquivo exportado × banco pós-reconstrução, direção inversa do
Achado 1).

**Dois erros cometidos durante a correção desse gap, ambos identificados
pela própria checagem de "Fechamento de Mês" rodada a cada etapa e
corrigidos na hora:**

1. Inserir os 8 registros via `calcular_atendimentos_producao` recriou o
   bug do Achado 2 — a função exclui o dia inteiro (`PRD_DTATEN`) da
   contagem de produção já existente, pensado para o caso de *regerar* um
   dia (`/api/gerar`), mas usado aqui pra *acrescentar* um registro a um
   dia que já tinha produção da reconstrução principal — recalculou do
   zero e colidiu. Corrigido de novo com `fix_colisoes.py --aplicar`
   (6 slots, 8 linhas realocadas).
2. Um dos 8 (paciente com nome preservado localmente) já tinha sido
   coberto pela reconstrução principal — o `CNS` que identificava o
   registro no arquivo exportado antigo não existe mais na `CADCNS` (só
   ficou o CPF), então a comparação por `CNS` não reconheceu que já
   estava lá e inseriu de novo, duplicando 1 atendimento médico + 1
   enfermeiro. Achado comparando o total final (4.794) contra o total
   original pré-incidente (4.792) e confirmado cruzando por CPF contra o
   arquivo bruto de digitação. As 2 linhas duplicadas foram apagadas.

**Estado final, validado via `python bpa/fechamento_mes.py 202606`:**
4.792 linhas (igual ao total antes do incidente), export OK, colisão OK,
checksum OK. Duplicidade: 64 grupos — mesmo número de antes do incidente
(Achado 3, pré-existente, não afetado pela reconstrução).

**Causa raiz identificada (ainda não corrigida no código):**
`calcular_atendimentos_producao` sempre exclui `PRD_DTATEN` da contagem de
produção anterior — correto só quando a intenção é *substituir* a
produção do dia; incorreto quando a intenção é *adicionar* (todo uso atual
da função via `/api/pacientes/completar`/`/api/conferencia/reenviar` é
sempre para adicionar, nunca substituir). É a mesma causa raiz do Achado 2
original. Ver pendência 5 abaixo.

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

5. **Corrigir a causa raiz em `calcular_atendimentos_producao`** (ver
   Incidente 10/07/2026 acima) — parar de excluir `PRD_DTATEN` da contagem
   de produção anterior, já que todo uso atual da função é para
   *adicionar*, nunca *substituir* um dia. Depois, reavaliar se ainda faz
   sentido remover `/api/conferencia/reenviar`/revisar
   `/api/pacientes/completar`, ou se a correção da causa raiz já torna as
   duas rotas seguras de manter. **Em andamento.**

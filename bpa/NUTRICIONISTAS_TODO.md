# Produção BPA-I das nutricionistas — status e próximos passos

## Situação atual (2026-07-15)

A produção de junho/2026 das 3 nutricionistas cadastradas (CBO `223710`) foi
gerada por um script **standalone**, fora do Flask:

- `bpa/gerar_producao_nutricionistas.py`

Ele lê a planilha `DADOS PACIENTES.xlsx` (Downloads, aba do mês, ex: `JUN -26`)
e grava em `C:\BPA\bpa_lotes`, em **DOIS ARQUIVOS PRÓPRIOS DA NUTRIÇÃO**
(nomes exclusivos, nunca reaproveita os arquivos de médico/enfermeiro):

1. `NUTRICAO_<competencia>.txt` — um único arquivo com todos os blocos
   `PROFISSIONAL: ... | CNS: ... | DATA: ...` + CPFs do mês inteiro,
   separados por data e profissional dentro do mesmo arquivo.
2. `BPA_NUTRICIONISTAS_<competencia>.txt` — arquivo final BPA-I (layout
   DATASUS, 350 chars/linha), pronto pra importar no BPA Magnético.

Ele **NUNCA escreve nos arquivos `DD-MM-AAAA.txt`** (esses são os lotes
diários compartilhados, digitados à mão por médico/enfermeiro) nem usa o nome
`BPAI_<cnes>_<competencia>.txt` (esse é reservado pro export oficial de
médico/enfermeiro). Ver "Incidente" logo abaixo pra entender por quê isso é
inegociável.

Ele **não mexe no `app.py`/`bpa_gerador.py`/`templates/index.html`** — o app
Flask continua exatamente como estava antes desta tarefa (decisão explícita
do usuário em 2026-07-15: "não precisa colocar a opção de nutrição no app
hoje, é só um projeto futuro pro próximo mês").

Código do procedimento usado: `0301010048` (mesmo código já usado para
enfermeiro). CBO: `223710`.

## ⚠️ Incidente em 2026-07-15 — NÃO REPETIR

A primeira versão do script anexava os blocos da nutrição **dentro dos
arquivos `DD-MM-AAAA.txt` compartilhados** (mesmo arquivo que médico/
enfermeiro digitam à mão todo dia), usando `bpa.criar_cabecalho_lote` +
`bpa.adicionar_documento_lote`. Tecnicamente era só "append" (nenhum dado foi
de fato apagado — foi conferido e restaurado bloco a bloco), mas o usuário
correu o risco de achar que tinha perdido a digitação manual do mês inteiro,
porque um script rodando em lote mexeu num arquivo que ele espera que só seja
alterado por digitação manual, uma linha de cada vez, pela interface.

**A causa raiz**: usar `bpa.nome_arquivo_lote(data_br)` (que gera
`DD-MM-AAAA.txt`, o MESMO nome usado pelo fluxo de Digitação) pra gravar
saída de um script de importação em lote.

**A correção**: o script passou a escrever em arquivos com nome
exclusivo (`NUTRICAO_<competencia>.txt` e
`BPA_NUTRICIONISTAS_<competencia>.txt`), e os 30 arquivos `DD-MM-AAAA.txt`
que tinham sido alterados foram limpos (blocos de nutricionista removidos,
conteúdo original de médico/enfermeiro 100% preservado — os arquivos que só
tinham bloco de nutricionista, e portanto não existiam antes, foram
apagados).

**Regra permanente para qualquer script/importação em lote futuro** (aqui ou
em qualquer outra categoria nova que apareça): nunca escrever, anexar ou
regravar um arquivo que a interface de Digitação também usa
(`bpa.nome_arquivo_lote` / `DD-MM-AAAA.txt` em `BPA_LOTES_DIR`) nem o nome
oficial de export (`BPAI_<cnes>_<competencia>.txt`). Todo script de
importação em lote deve gerar seus próprios arquivos, com nome que deixe
óbvio que vieram de importação automática, não de digitação manual.

Isso **não se aplica** ao fluxo normal de Digitação pela interface web: lá,
cada CPF é gravado um de cada vez, pelo usuário, com o app já cuidando de
categoria/CNS — é totalmente esperado que médico, enfermeiro e (no futuro)
nutricionista dividam o mesmo arquivo `DD-MM-AAAA.txt`, exatamente como
médico e enfermeiro já dividem hoje. O risco é específico de **scripts
rodando em lote por fora da interface**, não do uso normal do sistema.

## Regra de atribuição usada na leitura da planilha

A coluna A da planilha mistura data / nome da nutricionista / anotações; a
coluna D é o CPF do paciente. Confirmado com o usuário:

- O nome da nutricionista, uma vez escrito na coluna A, vale para as linhas
  seguintes até aparecer um nome novo — inclusive atravessando dias sem nome
  novo escrito (ex: dia sem nenhum nome na coluna A herda a última
  nutricionista citada, mesmo que tenha sido em um dia anterior).
- `FDS` é só anotação de fim de semana — ignorada.
- `TODAS NUT` (as 3 atenderam) é atribuída a só 1 delas, em rodízio.
- CPF repetido em dias diferentes é esperado (paciente internado com dieta
  todo dia) — não deduplicado entre dias. Só duplicata *consecutiva* dentro
  do mesmo bloco é descartada (mesma regra que o resto do sistema já usa).

## Próximo passo: integrar no Flask (fazer só quando for pedido)

Quando o usuário pedir pra não precisar mais rodar o script na mão todo mês,
estas são as mudanças exatas (já foram feitas e testadas nesta sessão, depois
revertidas a pedido — é só reaplicar):

### 1. `bpa/bpa_gerador.py`
Adicionar ao dict `PROCEDIMENTOS`:
```python
PROCEDIMENTOS = {
    "medico":        {"codigo": "0301060029", "cbo": "225125"},
    "enfermeiro":    {"codigo": "0301010048", "cbo": "223505"},
    "nutricionista": {"codigo": "0301010048", "cbo": "223710"},
}
```
Isso sozinho já faz `detectar_categoria`/`CBO_PARA_CATEGORIA` reconhecerem
profissionais com CBO 223710 automaticamente em qualquer fluxo existente
(Digitação, `/api/gerar`, `/api/pacientes/completar`, `/api/conferencia/*`).

### 2. `bpa/app.py`
- `_ROTULO_ARQUIVO`: acrescentar `"nutricionista": "NUTRICIONISTAS"`.
- Em `api_gerar`, o dict `por_categoria` inicial: acrescentar
  `"nutricionista": {"linhas": [], "n_folhas": 0, "competencias": []}`.

Com isso o botão "Gerar BPA-I" já existente passa a gerar também
`BPA_NUTRICIONISTAS_DDMMAAAA.txt` automaticamente quando o lote do dia tiver
blocos de nutricionista — sem precisar de nenhuma aba nova (o fluxo de
Digitação já é genérico por profissional/CNS).

### 3. `bpa/templates/index.html`
Só cosmético (rótulo "Nutrição" em vez de "Sem CBO"/"—" na busca de
profissional). ~6 pontos com ternários `p.categoria==="medico"?...:...`
— procurar por `"enfermeiro"?"Enfermeiro"` e acrescentar mais um `:`
para `"nutricionista"`. Não é obrigatório pro funcionamento, só estética.

### 4. Fonte de dados — planilha → CSV
O usuário mencionou que no futuro a fonte não vai mais ser o `.xlsx` do
Downloads, e sim um `.csv` a ser configurado depois. Quando isso acontecer,
só a função `extrair_registros()` (e o `pd.read_excel(...)` dentro dela) em
`gerar_producao_nutricionistas.py` precisa trocar pra `pd.read_csv(...)` —
o resto do script (classificação de coluna A, agrupamento, geração do BPA-I)
não muda. **Continua valendo a regra do incidente acima**: mesmo lendo de
`.csv`, o script de importação em lote nunca escreve em `DD-MM-AAAA.txt`.

## Não fazer sem confirmar de novo
- Não rodar `gerar_producao_nutricionistas.py` duas vezes pro mesmo mês sem
  avisar o usuário: o arquivo `NUTRICAO_<competencia>.txt` e o
  `BPA_NUTRICIONISTAS_<competencia>.txt` são **sempre reescritos do zero** a
  cada execução (não são incrementais) — rodar de novo depois de já ter
  importado o anterior no BPA Magnético duplicaria a produção real.
- Nunca fazer um script/importação em lote (aqui ou em categoria nova
  qualquer) escrever em `DD-MM-AAAA.txt` (`bpa.nome_arquivo_lote`) ou em
  `BPAI_<cnes>_<competencia>.txt` — ver "Incidente em 2026-07-15" acima.
  Sempre usar nome de arquivo próprio e exclusivo da importação.

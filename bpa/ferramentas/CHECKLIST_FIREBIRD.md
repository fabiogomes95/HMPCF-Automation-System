# Checklist — Validação BPA-I com Firebird (Ambiente de Teste)

> Roteiro para amanhã na máquina do hospital que tem o BPA Magnético instalado.
>
> ⚠️ **Estratégia segura:** usaremos um **usuário/BPA de teste** com cópia da produção real.
> O BPA de produção **NUNCA** será tocado durante esses testes. Toda a validação
> acontece no ambiente isolado — só depois de tudo aprovado é que pensamos em rodar
> contra a produção.

---

## 0. Preparação do ambiente de TESTE (isolado da produção)

### 0.1 Criar ambiente isolado

- [ ] Identificar a pasta da produção real (provavelmente `C:\BPA\`)
- [ ] Criar pasta de teste **completamente separada**:
  ```cmd
  mkdir C:\BPA_TESTE
  ```
- [ ] **Fechar o BPA Magnético de produção** (libera o `.GDB` para cópia)
- [ ] Copiar o banco de produção para o ambiente de teste:
  ```cmd
  copy C:\BPA\BPAMAG.GDB C:\BPA_TESTE\BPAMAG.GDB
  ```
- [ ] Copiar também a pasta `Exporta` (se existir):
  ```cmd
  xcopy C:\BPA\Exporta C:\BPA_TESTE\Exporta\ /E /I
  ```

### 0.2 Configurar usuário/BPA de teste

- [ ] Abrir o BPA Magnético usando o **banco de teste** (`C:\BPA_TESTE\BPAMAG.GDB`)
  - Geralmente trocar o caminho no atalho ou no `.ini` do BPA
  - Confirmar no topo da tela que está apontando para `BPA_TESTE`
- [ ] Logar com o usuário de teste (não o de produção)
- [ ] **Confirmar duas vezes** antes de seguir:
  - Caminho do banco aberto = `C:\BPA_TESTE\BPAMAG.GDB`? ✅
  - Usuário logado = teste? ✅

### 0.3 Preparar Python no ambiente

- [ ] Verificar Python instalado:
  ```cmd
  python --version
  ```
  Se não tiver, instalar Python 3.10+ (marcar "Add to PATH").
- [ ] Instalar dependência:
  ```cmd
  pip install firebirdsql
  ```
- [ ] Copiar a pasta `scripts/bpa/` do repo para a máquina (via git pull ou pen drive).

### 0.4 Ajustar o script para apontar para teste

Editar `gerar_bpa_i.py` temporariamente:
```python
DB_PATH = r"C:\BPA_TESTE\BPAMAG.GDB"   # ← apontar para teste
```
⚠️ Reverter para `C:\BPA\BPAMAG.GDB` antes do commit final.

---

## 1. Localizar arquivo `.txt` exportado pelo BPA

Antes de gerar qualquer coisa nova, precisamos de uma referência real para comparar.

- [ ] Procurar arquivo `.txt` já gerado pelo BPA em:
  - `C:\BPA\Exporta\` (produção — só **copiar**, não modificar)
  - `C:\BPA\`
  - `C:\Users\<usuario>\Documents\BPA\`
- [ ] Copiar um arquivo recente para `C:\BPA_TESTE\amostra_real.txt`

Se **não houver** arquivo exportado pela produção: usar o BPA de teste (com a cópia do banco real) para **exportar** um TXT pequeno com a produção existente — vai sair idêntico ao que a produção exportaria, mas sem mexer no banco real.

---

## 2. Inspecionar o banco Firebird

Criar arquivo `inspecionar_banco.py` na pasta `scripts/bpa/`:

```python
import firebirdsql

con = firebirdsql.connect(
    host="localhost", database=r"C:\BPA_TESTE\BPAMAG.GDB",   # ← TESTE
    user="SYSDBA", password="masterkey", charset="WIN1252",
)
cur = con.cursor()

print("\n=== CADMED — colunas ===")
cur.execute("""
    SELECT RDB$FIELD_NAME, RDB$FIELD_SOURCE
    FROM RDB$RELATION_FIELDS
    WHERE RDB$RELATION_NAME = 'CADMED'
    ORDER BY RDB$FIELD_POSITION
""")
for f in cur.fetchall():
    print(f"  {f[0].strip()}")

print("\n=== CADCNS — colunas ===")
cur.execute("""
    SELECT RDB$FIELD_NAME
    FROM RDB$RELATION_FIELDS
    WHERE RDB$RELATION_NAME = 'CADCNS'
    ORDER BY RDB$FIELD_POSITION
""")
for f in cur.fetchall():
    print(f"  {f[0].strip()}")

print("\n=== CADCNS — 3 pacientes reais ===")
cur.execute("""
    SELECT FIRST 3 CNS, NOME, DTNASC, SEXO, IBGE, RACA, ETNIA, NACIONALIDADE,
                   CO_LOGRAD, CEPPCN, LOGPCN, NUMPCN, CPLPCN, BAIRRO_PCNTE,
                   DDTEL_PCNTE, TEL_PCNTE, EMAIL_PCNTE
    FROM CADCNS
    WHERE CNS IS NOT NULL AND TRIM(CNS) <> ''
""")
for row in cur.fetchall():
    print(f"\n  CNS:    {row[0]!r}  (tipo: {type(row[0]).__name__})")
    print(f"  NOME:   {row[1]!r}")
    print(f"  DTNASC: {row[2]!r}  (tipo: {type(row[2]).__name__})")
    print(f"  SEXO:   {row[3]!r}")
    print(f"  IBGE:   {row[4]!r}  (tipo: {type(row[4]).__name__})")
    print(f"  RACA:   {row[5]!r}  (tipo: {type(row[5]).__name__})")
    print(f"  ETNIA:  {row[6]!r}")
    print(f"  NACION: {row[7]!r}")
    print(f"  LOGRAD: {row[8]!r}")
    print(f"  CEP:    {row[9]!r}")
    print(f"  LOGPCN: {row[10]!r}")
    print(f"  NUMPCN: {row[11]!r}")
    print(f"  CPLPCN: {row[12]!r}")
    print(f"  BAIRRO: {row[13]!r}")
    print(f"  DDD:    {row[14]!r}")
    print(f"  TEL:    {row[15]!r}")
    print(f"  EMAIL:  {row[16]!r}")

print("\n=== S_PRD — 5 registros já digitados (referência) ===")
cur.execute("""
    SELECT FIRST 5
        PRD_CMP, PRD_CNSMED, PRD_CBO, PRD_DTATEN,
        PRD_FLH, PRD_SEQ, PRD_PA, PRD_CNSPAC,
        PRD_NMPAC, PRD_DTNASC, PRD_SEXO, PRD_IBGE,
        PRD_CID, PRD_IDADE, PRD_QT_P, PRD_CATEN,
        PRD_NAUT, PRD_ORG, PRD_RACA, PRD_ETNIA, PRD_NAC
    FROM S_PRD
    WHERE PRD_CNSPAC IS NOT NULL
""")
cols = ["CMP", "CNSMED", "CBO", "DTATEN", "FLH", "SEQ", "PA", "CNSPAC",
        "NMPAC", "DTNASC", "SEXO", "IBGE", "CID", "IDADE", "QT_P",
        "CATEN", "NAUT", "ORG", "RACA", "ETNIA", "NAC"]
for i, row in enumerate(cur.fetchall(), 1):
    print(f"\n--- Registro {i} ---")
    for col, val in zip(cols, row):
        print(f"  {col:8} = {val!r}  ({type(val).__name__})")

con.close()
```

Rodar e **salvar a saída**:
```cmd
python inspecionar_banco.py > inspecao.txt
```

### Perguntas que essa saída precisa responder

- [x] `DTNASC` retorna `str` ou objeto `date`? → **`str`**, formato `AAAAMMDD` (ex: `'20011014'`). Tratado em `_normalizar_dtnasc()`.
- [x] `RACA`, `ETNIA`, `NACIONALIDADE` vêm com zeros à esquerda ou não? → **Sim, zero-padded como `str`** (`RACA='03'`, `NACIONALIDADE='010'`; `ETNIA` vem em branco `'    '` quando raça ≠ indígena — só preenchida quando `RACA='05'`).
- [x] `IBGE` é `int` ou `str`? → **`str`** (ex: `'240360'`).
- [x] `CADMED` tem coluna `CADMED_CBO`? → **Não direto** — a categoria (médico/enfermeiro) vem de `CADMED_CBO_CNES` (tabela separada, `MED_CNS`/`MED_CBO`). Já implementado em `mapa_categorias_por_profissional()` / `detectar_categoria()`.
- [x] `PRD_QT_P` é `1`, `"001"` ou `"000001"`? → **`float`** (`1.0`). No layout de saída usamos `"000001"` fixo (6 dígitos), já que cada linha = 1 atendimento.
- [x] `PRD_CATEN` é `2` ou `"02"`? → **`str` zero-padded, `'02'`**.
- [x] `PRD_ORG` é `"BPA"` ou outro valor?  → **`'BPI'`** no `S_PRD` real (registros já digitados manualmente pelo BPA Magnético). No layout de exportação BPA-I gerado por nós usamos `"BPA"` fixo (campo `prd-org`, ver `_linha_detalhe()`) — são contextos diferentes (registro interno do BPA vs. arquivo de exportação), sem conflito.

⚠️ **Descoberta extra (não prevista neste checklist):** `TRIM()` no Firebird falha — `Use of UDF library at location udflib.DLL is not allowed by server configuration`. O servidor bloqueia essa UDF. **Nunca usar `TRIM()` em SQL** — sempre trazer a coluna raw e fazer `.strip()` em Python (já é assim em todo o `bpa_gerador.py`).

✅ Respostas confirmadas em `scripts/bpa/inspecao.txt` (consulta real, somente leitura, rodada em 18/06/2026) e já incorporadas em `dashboard/bpa_gerador.py`.

---

## 3. Comparar layout byte a byte com arquivo real

✅ **Já feito em 18/06/2026** — `scripts/bpa/verificar_checksum.py` reproduziu a fórmula do
checksum (`cbc-smt-vrf`) contra `C:\BPA\EXPORTA\PAkauan-.MAR` (export real de produção) e bateu
exatamente. Layout de 350 chars/linha de detalhe e 130 chars de cabeçalho confirmado em
`dashboard/bpa_gerador.py`. Os passos abaixo (script `comparar_layout.py`) descrevem o método
manual usado, mantidos aqui como referência caso seja preciso revalidar contra um novo export.

Criar `comparar_layout.py`:

```python
ARQ_REAL = r"C:\BPA_TESTE\amostra_real.txt"

with open(ARQ_REAL, encoding="latin-1", newline="") as f:
    for i, linha in enumerate(f):
        s = linha.rstrip("\r\n")
        print(f"\n[{i}] tipo={s[:2]!r} len={len(s)}")
        if s.startswith("03"):
            # Quebrar nas posições conforme nosso layout
            campos = [
                ("tipo",       0,   2),
                ("CNES",       2,   9),
                ("comp",       9,  15),
                ("cns_prof",  15,  30),
                ("CBO",       30,  36),
                ("data_aten", 36,  44),
                ("folha",     44,  47),
                ("seq",       47,  49),
                ("proc",      49,  59),
                ("cns_pac",   59,  74),
                ("sexo",      74,  76),
                ("ibge",      76,  82),
                ("CID",       82,  86),
                ("reserv",    86,  87),
                ("idade",     87,  90),
                ("qt",        90,  96),
                ("car",       96,  98),
                ("autoriz",   98, 111),
                ("origem",   111, 114),
                ("dt_nasc",  114, 122),
                ("tipo_bpa", 122, 123),
                ("raca",     123, 125),
                ("etnia",    125, 129),
                ("nacion",   129, 132),
                ("servico",  132, 135),
                ("classif",  135, 138),
                ("eq_seq",   138, 142),
                ("eq_area",  142, 148),
                ("cod_log",  148, 151),
                ("cep",      151, 159),
                ("endereco", 159, 189),
                # próximos campos: ORDEM DESCONHECIDA — descobrir aqui
                ("?_30",     189, 219),  # 30 chars - bairro?
                ("?_10",     219, 229),  # 10 chars - compl?
                ("?_5",      229, 234),  # 5 chars - num?
                ("ddd",      234, 236),
                ("tel",      236, 245),
                ("email",    245, 285),
            ]
            for nome, ini, fim in campos:
                print(f"  [{ini:3}-{fim:3}] {nome:10} = {s[ini:fim]!r}")
        if i >= 3: break
```

- [ ] Rodar e **comparar campo a campo** com nossa documentação
- [ ] Anotar divergências em comprimento total da linha
- [ ] **Confirmar ordem real** dos campos: bairro / complemento / número
- [ ] Confirmar tamanho do campo de e-mail (40? 60?)

---

## 4. Ajustar o `gerar_bpa_i.py`

Com base no que descobriu nas etapas 2 e 3, atualizar no script:

- [ ] **Linha 152** — função `_normalizar_dtnasc`: simplificar se confirmar formato único
- [ ] **Linhas 174-189** — função `buscar_pacientes`: ajustar ordem dos campos compl/num/bairro se divergir
- [ ] **Linha 113** — função `escolher_profissional`: se `CADMED` tiver `CADMED_CBO`, detectar categoria automática
- [ ] **Linhas 252-289** — função `_linha_detalhe`: corrigir ordem dos campos no final da linha
- [ ] Se houver coluna de CPF na `CADCNS`, adicionar suporte a entrada por CPF além de CNS

---

## 5. Primeiro teste pequeno (3 pacientes reais)

- [ ] Escolher 3 CNS reais de pacientes que **já têm registro em S_PRD** (atendimento já lançado)
- [ ] Criar `teste_3_pacientes.txt` com esses 3 CNS
- [ ] Gerar:
  ```cmd
  python gerar_bpa_i.py --entrada teste_3_pacientes.txt
  ```
- [ ] Conferir saída no `~/Downloads/BPAI_*.txt`
- [ ] **Comparar com os 3 registros do S_PRD** — campo a campo

---

## 6. Importação no BPA de TESTE

⚠️ **Atenção:** essa importação acontece **no BPA de teste** apontando para `C:\BPA_TESTE\BPAMAG.GDB`. O BPA de produção continua intocado.

- [ ] **Reconfirmar** que o BPA aberto está apontando para `C:\BPA_TESTE\BPAMAG.GDB`
- [ ] **Backup do banco de teste** antes de importar (para poder repetir testes):
  ```cmd
  copy C:\BPA_TESTE\BPAMAG.GDB C:\BPA_TESTE\BPAMAG.GDB.antes_import
  ```
- [ ] Menu → Importação → Importar Produção BPA
- [ ] Selecionar o arquivo gerado
- [ ] **Conferir:**
  - [ ] Aceitou sem erro de layout?
  - [ ] Os 3 pacientes aparecem com nome correto?
  - [ ] Data de nascimento bate?
  - [ ] CBO/procedimento bate?
  - [ ] Idade calculada confere?

Se aceitar: ✅ layout confirmado. Se rejeitar: anotar o erro exato do BPA e voltar à etapa 3.

**Para repetir testes**: restaurar o banco de teste:
```cmd
copy C:\BPA_TESTE\BPAMAG.GDB.antes_import C:\BPA_TESTE\BPAMAG.GDB
```

---

## 7. Teste em escala (50 pacientes) — ainda no banco de teste

- [ ] Restaurar banco de teste limpo:
  ```cmd
  copy C:\BPA_TESTE\BPAMAG.GDB.antes_import C:\BPA_TESTE\BPAMAG.GDB
  ```
- [ ] Selecionar 50 CNS reais de um dia completo de atendimento
- [ ] Gerar arquivo
- [ ] Importar no BPA de TESTE
- [ ] Conferir contagem: registros = 50, folhas = 1 (51-99 = 1 folha, 100+ = 2 folhas)
- [ ] Verificar se há pacientes "não encontrados" → analisar caso a caso

---

## 8. Teste de quebra de folha (150 pacientes) — ainda no banco de teste

- [ ] Restaurar banco de teste novamente
- [ ] Selecionar 150 CNS reais
- [ ] Gerar e importar no BPA de TESTE
- [ ] Verificar que o BPA aceita 2 folhas (001 com seq 01-99, 002 com seq 01-51)

---

## 9. Validar fluxo completo (simulação de produção)

- [ ] Restaurar banco de teste limpo
- [ ] Fluxo de uso real: pegar a lista do dia (como já fazem no legado), passar pro script, importar no BPA de teste
- [ ] Tempo total da operação vs. fluxo do robô atual
- [ ] **Decisão**: substituir o robô ou rodar em paralelo por uma semana (sempre no banco de teste)?

---

## 10. Documentar achados finais

Atualizar este arquivo com:

- [ ] Estrutura real confirmada de `CADCNS` e `CADMED`
- [ ] Layout do BPA-I confirmado (com posições corretas dos últimos campos)
- [ ] Bugs encontrados e corrigidos
- [ ] Procedimento operacional para os usuários do hospital
- [ ] **Reverter `DB_PATH`** no `gerar_bpa_i.py` para `C:\BPA\BPAMAG.GDB` antes do commit final

Commit final:
```cmd
git add scripts/bpa/
git commit -m "fix(bpa): ajustes apos validacao em ambiente de teste"
git push
```

---

## 11. Quando (e SE) for usar em produção real

> Etapa separada — só executar depois que tudo acima estiver ✅ por vários dias de teste.

- [ ] Decisão tomada com a equipe do hospital
- [ ] **Backup** do banco de produção:
  ```cmd
  copy C:\BPA\BPAMAG.GDB C:\BPA\BPAMAG.GDB.backup_AAAAMMDD
  ```
- [ ] Confirmar com olho humano: o script lê `C:\BPA\BPAMAG.GDB` (produção)
- [ ] Rodar com lista pequena primeiro (5-10 pacientes)
- [ ] Verificar importação no BPA de produção
- [ ] Só então liberar volume completo

---

## Bugs/melhorias já identificados

1. ✅ **Corrigido** — `ler_arquivo_lote()` valida a existência/conteúdo do arquivo (`LoteError`) antes de qualquer pergunta interativa de profissional/categoria, tanto no CLI (`gerar_bpa_i.py`) quanto no dashboard.

2. ✅ **Corrigido** — `CADCNS` tem coluna `NUM_CPF`. `buscar_pacientes()` aceita CNS (15 dígitos) e CPF (11 dígitos) misturados na mesma lista.

3. ✅ **Corrigido** — `detectar_categoria()` usa `CADMED_CBO_CNES` (`MED_CNS`/`MED_CBO`) para detectar Médico/Enfermeiro automaticamente quando há exatamente 1 CBO conhecido; pede escolha manual só em caso de ambiguidade ou CBO desconhecido.

4. ✅ **Corrigido (2026-06-22)** — `gerar_arquivo()` aceita pasta de saída customizada (parâmetro `pasta`, ou env `BPA_SAIDA_DIR`); padrão continua `~/Downloads` se nada for configurado. CLI ganhou `--saida`.

5. 🟡 **Pendente (depende do banco real)** — `firebirdsql` estava no `requirements.txt` do dashboard mas não instalado no venv em produção (`Desktop-9c4s1co`); corrigido manualmente em 2026-06-22, mas vale conferir após qualquer reinstalação/rebuild do venv.

---

## Plano de contingência

Como tudo acontece em `C:\BPA_TESTE\`, qualquer problema durante os testes:

1. Fechar o BPA de teste
2. Restaurar o banco de teste: `copy C:\BPA_TESTE\BPAMAG.GDB.antes_import C:\BPA_TESTE\BPAMAG.GDB`
3. Recomeçar — produção segue intocada

Se algum dia for usar em produção (etapa 11) e algo der errado:

1. **PARAR** imediatamente
2. Restaurar backup: `copy C:\BPA\BPAMAG.GDB.backup_AAAAMMDD C:\BPA\BPAMAG.GDB`
3. Fechar BPA, reabrir, verificar integridade

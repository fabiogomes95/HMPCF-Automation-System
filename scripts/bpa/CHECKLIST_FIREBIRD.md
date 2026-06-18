# Checklist — Validação BPA-I com Firebird Real

> Roteiro para amanhã na máquina do hospital que tem o BPA Magnético instalado.
> Objetivo: validar o `gerar_bpa_i.py` contra dados e arquivo real, ajustar o que for necessário e deixar o gerador pronto para uso em produção.

---

## 0. Preparação da máquina

- [ ] **Backup obrigatório** do banco antes de qualquer teste:
  ```cmd
  copy C:\BPA\BPAMAG.GDB C:\BPA\BPAMAG.GDB.backup_AAAAMMDD
  ```
- [ ] Fechar o BPA Magnético (libera o arquivo `.GDB` para leitura)
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

---

## 1. Localizar arquivo `.txt` exportado pelo BPA

Antes de gerar qualquer coisa nova, precisamos de uma referência real para comparar.

- [ ] Procurar arquivo `.txt` já gerado pelo BPA em:
  - `C:\BPA\Exporta\`
  - `C:\BPA\`
  - `C:\Users\<usuario>\Documents\BPA\`
- [ ] Copiar um arquivo recente para `C:\BPA\amostra_real.txt`

Se **não houver** arquivo exportado: gerar um pequeno pelo próprio BPA Magnético com 2-3 pacientes manuais como referência.

---

## 2. Inspecionar o banco Firebird

Criar arquivo `inspecionar_banco.py` na pasta `scripts/bpa/`:

```python
import firebirdsql

con = firebirdsql.connect(
    host="localhost", database=r"C:\BPA\BPAMAG.GDB",
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

- [ ] `DTNASC` retorna `str` ou objeto `date`?
- [ ] `RACA`, `ETNIA`, `NACIONALIDADE` vêm com zeros à esquerda ou não?
- [ ] `IBGE` é `int` ou `str`?
- [ ] `CADMED` tem coluna `CADMED_CBO`? (se sim, conseguimos automatizar a categoria)
- [ ] `PRD_QT_P` é `1`, `"001"` ou `"000001"`?
- [ ] `PRD_CATEN` é `2` ou `"02"`?
- [ ] `PRD_ORG` é `"BPA"` ou outro valor?

**Anotar respostas neste arquivo** e ajustar `gerar_bpa_i.py` conforme necessário.

---

## 3. Comparar layout byte a byte com arquivo real

Criar `comparar_layout.py`:

```python
ARQ_REAL = r"C:\BPA\amostra_real.txt"

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

## 6. Importação real no BPA Magnético

- [ ] Abrir o BPA Magnético
- [ ] **Backup novamente** (`copy C:\BPA\BPAMAG.GDB ...`)
- [ ] Menu → Importação → Importar Produção BPA
- [ ] Selecionar o arquivo gerado
- [ ] **Conferir:**
  - [ ] Aceitou sem erro de layout?
  - [ ] Os 3 pacientes aparecem com nome correto?
  - [ ] Data de nascimento bate?
  - [ ] CBO/procedimento bate?
  - [ ] Idade calculada confere?

Se aceitar: ✅ layout confirmado. Se rejeitar: anotar o erro exato do BPA e voltar à etapa 3.

---

## 7. Teste em escala (50 pacientes)

- [ ] Selecionar 50 CNS reais de um dia completo de atendimento
- [ ] Gerar arquivo
- [ ] Importar no BPA
- [ ] Conferir contagem: registros = 50, folhas = 1 (51-99 = 1 folha, 100+ = 2 folhas)
- [ ] Verificar se há pacientes "não encontrados" → analisar caso a caso

---

## 8. Teste de quebra de folha (150 pacientes)

- [ ] Selecionar 150 CNS reais
- [ ] Gerar e importar
- [ ] Verificar que o BPA aceita 2 folhas (001 com seq 01-99, 002 com seq 01-51)

---

## 9. Validar fluxo completo de produção

- [ ] Fluxo de uso real: pegar a lista do dia (como já fazem no legado), passar pro script, importar no BPA
- [ ] Tempo total da operação vs. fluxo do robô atual
- [ ] **Decisão**: substituir o robô ou rodar em paralelo por uma semana?

---

## 10. Documentar achados finais

Atualizar este arquivo com:

- [ ] Estrutura real confirmada de `CADCNS` e `CADMED`
- [ ] Layout do BPA-I confirmado (com posições corretas dos últimos campos)
- [ ] Bugs encontrados e corrigidos
- [ ] Procedimento operacional para os usuários do hospital

Commit final:
```cmd
git add scripts/bpa/
git commit -m "fix(bpa): ajustes apos validacao com banco real e BPA Magnetico"
git push
```

---

## Bugs/melhorias já identificados para corrigir amanhã

1. ⚠️  **`--entrada` valida arquivo tarde demais** — se o caminho está errado, usuário responde data + competência antes de ver o erro. Validar no `parse_args`.

2. 🟡 **Sem suporte a CPF como entrada** — só aceita CNS. Se a lista do legado vem com CPF, precisamos saber qual coluna da `CADCNS` tem o CPF e adicionar lógica de detecção (CPF tem 11 dígitos, CNS tem 15).

3. 🟡 **Sem detecção automática de categoria** — usuário escolhe Médico/Enfermeiro toda vez. Se `CADMED` tiver CBO, dá pra automatizar.

4. 🟡 **Sem `--saida`** — arquivo sempre vai pra `~/Downloads`. Talvez precisemos permitir customizar.

---

## Contato de emergência

Se algo der errado no banco em produção:

1. **PARAR** imediatamente
2. Restaurar backup: `copy C:\BPA\BPAMAG.GDB.backup_AAAAMMDD C:\BPA\BPAMAG.GDB`
3. Fechar BPA, reabrir, verificar integridade

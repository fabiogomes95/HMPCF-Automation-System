# 📋 CHANGELOG — RPA BPA / DATASUS
**Projeto:** Robô de produção BPA-Magnético  
**Banco:** Firebird `C:\BPA\BPAMAG.GDB`  
**Data do registro:** 2025-05

---

## 📄 Script 1 — `limpeza.py` (processador de lista)

### O que era
- Lia um arquivo sujo linha por linha
- Extraía CPF (11 dígitos) ou CNS/SUS (15 dígitos) usando regex
- Priorizava SUS sobre CPF quando os dois apareciam na mesma linha
- **Não tinha controle de duplicatas** — o mesmo número podia aparecer várias vezes no resultado

### O que mudou

| # | Problema | Solução |
|---|---|---|
| 1 | Duplicatas silenciosas | Adicionado `vistos = set()` — cada documento só entra uma vez |
| 2 | Lógica de escolha espalhada em dois `if/elif` com `append` separados | Colapsado em `escolhido = sus_encontrado or cpf_encontrado` antes do append |
| 3 | Risco de append duplo na mesma linha (SUS + CPF) | Eliminado — apenas `escolhido` é avaliado e inserido |

### Comportamento garantido após a mudança
- Retorna **um único documento por paciente** (SUS tem prioridade)
- Retorna **zero duplicatas**, mesmo que o arquivo repita linhas
- Busca em `set` é O(1) — sem impacto de performance em listas grandes

---

## 📄 Script 2 — `executor_rpa.py` (robô pyautogui)

### O que era
- `preparar_lotes()` recebia um `base_pacientes_ram` (dicionário em memória enviado pelo painel)
- A validação era feita comparando o documento contra esse dict local
- **Nenhuma consulta ao banco Firebird**
- Erro de sintaxe na linha do `set()` (código partido/incompleto)
- O robô recebia strings cruas (só o número do documento)

### O que mudou

| # | Problema | Solução |
|---|---|---|
| 1 | Erro de sintaxe (`set() o robo tem que...`) | Linha removida e reescrita corretamente |
| 2 | Validação em RAM sem garantia de completude | Nova função `buscar_paciente_no_banco()` consulta a tabela `CADCNS` do Firebird |
| 3 | `preparar_lotes` dependia de dado externo (`base_pacientes_ram`) | Agora autônoma — consulta o banco internamente por linha |
| 4 | Nenhuma verificação de campos obrigatórios | SQL exige `NOME`, `DTNASC`, `SEXO` e `RACA` preenchidos |
| 5 | Robô recebia string crua do documento | Robô recebe `dict` completo com `nome`, `nascimento`, `sexo`, `raca`, `documento` |
| 6 | Pacientes ignorados sumiam sem rastro | `lote['ignorados']` guarda todos os documentos rejeitados para exibição no painel |

### Schema confirmado — tabela `CADCNS`

```
CADCNS
├── CNS            ← chave de busca quando doc tem 15 dígitos
├── NUM_CPF        ← chave de busca quando doc tem 11 dígitos
├── NOME           ← obrigatório (NOT NULL e não vazio)
├── DTNASC         ← obrigatório (NOT NULL)
├── SEXO           ← obrigatório (NOT NULL e não vazio)
├── RACA           ← obrigatório (NOT NULL e não vazio)
└── demais campos opcionais (LOGPCN, CEPPCN, BAIRRO_PCNTE, etc.)
```

### Fluxo atual entre as funções

```
painel.py
   │
   ├── preparar_lotes(arquivo)
   │       └── buscar_paciente_no_banco(doc)   ← consulta CADCNS no Firebird
   │               ├── aprovado  → lote['pacientes']
   │               └── rejeitado → lote['ignorados']
   │
   └── executar_pyautogui(lote['pacientes'])   ← digita só os aprovados
```

### Dependências adicionadas
```
pip install fdb
```

---

## ⚠️ Pendências / Atenção

- Confirmar credenciais do Firebird (`SYSDBA` / `masterkey`) no ambiente de produção
- Se outros campos além de `NOME`, `DTNASC`, `SEXO`, `RACA` forem obrigatórios (ex: `LOGPCN`, `CEPPCN`), adicionar no `WHERE` da `buscar_paciente_no_banco`
- O `callback` do painel deve exibir `lote['ignorados']` para auditoria dos documentos pulados
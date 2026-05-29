# Boletim de Atendimento A4 — Especificação Visual

Documento de referência do layout do boletim impresso. Qualquer ajuste futuro
deve partir destas medidas como base.

---

## Visão geral

O boletim ocupa **exatamente uma folha A4** (210 × 297 mm) tanto na tela quanto
na impressão. Tela e print são idênticos — não há override de fontes no
`@media print`.

**Arquivo:** `frontend/src/components/boletim/BoletimA4.jsx`  
**CSS:** `frontend/src/components/boletim/boletim.css`

---

## Margens / Padding da página

| | Valor |
|---|---|
| Topo / baixo | **5 mm** |
| Laterais | **6 mm** |

```css
.page { padding: 5mm 6mm; }
```

Em `@media print` o `.page` usa `width: 100%` e `height: 297mm` fixo para
eliminar a faixa cinza que o browser adiciona nas bordas.

---

## Tipografia dos campos de dados

| Elemento | Tamanho | Peso |
|---|---|---|
| Label (NOME, CPF, ENDEREÇO…) | **15 px** | bold |
| Input (valor digitado) | **15 px** | normal |
| Checkbox/radio labels (SOLTEIRO, PARDA…) | **14 px** | normal |
| Padding interno da linha | **4 px** topo/baixo, **6 px** laterais |

Altura resultante de cada linha de dado: **~23 px**.

---

## Cabeçalho (HeaderHospital)

| Elemento | Tamanho |
|---|---|
| Logo (brasão de Extremoz) | max-height **70 px** |
| Nome / texto central (Prefeitura, Hospital…) | **16 px**, line-height 1.5 |
| Prioridades (Gestante, Criança, TEA…) | **13 px** |

---

## Títulos de seção

Aplicados a: **CLASSIFICAÇÃO DE RISCO SSVV**, **ANOTAÇÕES DA CLASSIFICAÇÃO**,
**RESUMO DA HISTÓRIA CLÍNICA**, **HIPÓTESE DIAGNÓSTICA**.

```css
.section-title {
  font-size: 14px;
  font-weight: bold;
  background: #d9d9d9;   /* cinza médio — destaque sem ser escuro */
  padding: 5px 4px;
  border: 1px solid #000;
  border-top: none;
}
```

---

## Tabela de Classificação de Risco SSVV

| Propriedade | Valor |
|---|---|
| Fonte (VERMELHO, LARANJA…) | **13 px**, bold |
| Inputs (PA, FC, TEMP…) | **13 px** |
| Padding das células | **4 px** laterais, **4 px** topo/baixo |

---

## Áreas de escrita (pautado)

Três seções idênticas: **ANOTAÇÕES DA CLASSIFICAÇÃO**, **RESUMO DA HISTÓRIA
CLÍNICA** e **HIPÓTESE DIAGNÓSTICA**.

```css
/* Tela: alturas fixas de referência */
.ha-anotacoes { height: 75px; }
.ha-historia  { height: 125px; }
.ha-hipotese  { height: 125px; border-bottom: none; }

/* Print: as três crescem igualmente para preencher o restante da folha */
@media print {
  #formBoletim { height: calc(297mm - 10mm); }

  .ha-anotacoes,
  .ha-historia,
  .ha-hipotese {
    flex: 1 1 0;
    height: auto;
    min-height: 0;
  }

  .ha-hipotese { border-bottom: none; } /* evita linha dupla no final */
}
```

**Pautado:** `repeating-linear-gradient` de 25 px — uma linha preta de 1 px
a cada 25 px de espaço transparente.

---

## Placeholders na impressão

Máscaras como `DD/MM/AAAA`, `000.000.000-00` e `000 0000 0000 0000` são
**ocultadas** na impressão quando o campo está vazio:

```css
@media print {
  input::placeholder { color: transparent; }
}
```

---

## Spacer rows

Três linhas têm `class="row spacer-row"`: Data de Atendimento, Bairro/Cidade/UF
e Alergias. Na tela têm `margin-bottom: 10px`; no print `margin-bottom: 4px`.
Não usam `flex-grow` — a folha é preenchida pelo crescimento das áreas de
escrita, não das linhas de dados.

---

## Atalho e favicon

- **Favicon (aba do browser):** brasão de Extremoz em `frontend/public/img/brasao-extremoz.png`  
- **Atalho na área de trabalho:** criado pelo deploy em `C:\Users\Public\Desktop\HMPCF - Recepcao.lnk`  
  Abre Chrome (ou Edge) em modo `--app` sem barra de endereço.  
  Ícone: `frontend/dist/img/hmpcf.ico` (gerado pelo deploy a partir do brasão PNG).

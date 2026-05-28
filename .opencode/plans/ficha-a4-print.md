# Plano — Ficha A4 idêntica ao legado

## 1. Copiar logo
`web_recepcao/logo.png` → `hmpcf-system/frontend/public/logo.png`

## 2. Criar `components/FichaA4Print.jsx`
Componente oculto na tela que renderiza o HTML exato do legado:
- Cabeçalho: logo + "PREFEITURA MUNICIPAL DE EXTREMOZ / SECRETARIA MUNICIPAL DE SAÚDE / HOSPITAL M. PRES. CAFÉ FILHO / BOLETIM DE ATENDIMENTO" + grid PRIORIDADE
- Data / Hora / Registro (preenchido automaticamente)
- Nome completo (uppercase), Nome social, Naturalidade, DN, Idade
- CPF, Cartão SUS, Sexo (rádio M/F)
- Estado Civil (rádio), Raça/Cor (rádio), Ocupação
- Nome da Mãe, Responsável, Telefone
- Endereço / Nº / Bairro / Cidade / UF
- **Tabela CLASSIFICAÇÃO DE RISCO SSVV** colorida (VERMELHO, LARANJA, AMARELO, VERDE, AZUL)
- Comorbidades (checkboxes: HAS, DM, DISLIPIDEMIA, ETILISTA, TABAGISTA, OUTROS)
- Medicamentos em uso? / Alergias? (rádio + texto)
- Áreas de escrita manual com linhas (75px / 125px / 125px)

## 3. Criar `components/FichaA4Print.css`
CSS idêntico ao legado:
- `@page { size: A4; margin: 0; }`
- `.page { width: 210mm; min-height: 297mm; padding: 8mm 10mm; }`
- `@media print` com `print-color-adjust: exact`
- Tabela de risco com cores (`td.vermelho { background: red }`, etc.)
- `.handwriting-area` com fundo de linhas `repeating-linear-gradient`
- `.print-only { display: none }` na tela / `display: block` no print

## 4. Modificar `Recepcao.jsx`
- Importar `FichaA4Print` e `<FichaA4Print paciente={form} />` no final do JSX
- Ajustar botão Imprimir

## 5. Modificar `Sidebar.jsx`
- Adicionar `<img src="/logo.png" />` ao lado do "HMPCF"

## 6. Atualizar `registro/MIGRACAO.md` (Sessão 5)

## Arquivos finais
- `frontend/public/logo.png` (cópia)
- `frontend/src/components/FichaA4Print.jsx` (novo)
- `frontend/src/components/FichaA4Print.css` (novo)
- `frontend/src/pages/Recepcao.jsx` (modificado)
- `frontend/src/components/Sidebar.jsx` (modificado)
- `registro/MIGRACAO.md` (modificado)

# Histórico Atual — Sessão 17/05/2026

## O que fizemos

### Layout A4 editável (FichaA4Print.jsx + CSS)
- O formulário principal da Recepção agora **é o próprio layout A4** do Boletim de Atendimento (substituiu a grade moderna de 3 colunas)
- Inputs sem `border-bottom` — só as linhas pretas da grade (`.row`/`.field`)
- Tabela SSVV sem cores de fundo — só os nomes em negrito (preenchimento manual após impressão)
- Logo do hospital adicionado ao lado de "HMPCF" no cabeçalho

### Impressão (mesma aba, sem nova janela)
- `handlePrint` usa `window.print()` direto
- `@page { size: A4; margin: 0; }` suprime cabeçalho/rodapé do navegador (localhost, data/hora, página 1/1)
- `.page` na impressão: `width: 100%; max-width: none; min-height: 297mm; padding: 8mm 12mm;`
- Logo na impressão: preenche todo `.header-logo` (`max-height: none; width: 100%; height: auto`)
- Ancestrais resetados para `display: block; width: 100%` no `@media print`

### Botões (action-bar)
- Salvar / Imprimir / Limpar ficam **fora** do formulário A4 (classe `.action-bar`)
- Não aparecem na impressão (`display: none` no `@media print`)

### Máscaras de input
- CPF: `000.000.000-00`
- SUS: `000 0000 0000 0000`
- DN: `DD/MM/AAAA`

### Busca com feedback
- Toast de erro quando a API falha: *"Erro ao buscar — o backend está rodando?"*

### Campo Registro
- Adicionado ao formulário (tela + impressão)

### Cidade/Estado padrão
- Cidade: EXTREMOZ
- Estado: RN

## Decisões tomadas

| Decisão | Opção escolhida |
|---------|----------------|
| Formulário principal | Layout A4 editável (não grade moderna) |
| Impressão | Mesma aba (`window.print()`) com `@page { margin: 0 }` |
| Cores SSVV | Sem cores — nomes em negrito (marca-texto após imprimir) |
| Input borders | Sem `border-bottom` — só linhas da grade |
| Botões | Fora do A4 (`.action-bar`) |
| Logo impressão | Sem `max-height` — preenche o container |
| `@page margin` | `0` (suprime cabeçalho/rodapé do navegador) |

## Pendências para próxima sessão

- **Validar busca**: Backend FastAPI precisa estar rodando (`uvicorn app.main:app --reload` na porta 8000)
- **Validação matemática CPF (dígitos verificadores)**
- **Validação matemática SUS (dígito módulo 11)**
- **Cálculo automático da idade ao digitar DN**
- **Campos obrigatórios** (nome, CPF, DN, cor, etc.)
- **Módulo BPA** (backend + frontend)
- **Módulo Relatórios** (PDF fpdf2, Excel openpyxl)
- **Tauri sidecar** para iniciar FastAPI junto com o app desktop
- **Testar impressão A4**: verificar se preenche a folha corretamente

## Como continuar

```powershell
# Terminal 1 — Backend
cd C:\Users\Fabinho\Documents\Fabio\HMPCF\hmcpf-system\backend
uvicorn app.main:app --reload

# Terminal 2 — Frontend
cd C:\Users\Fabinho\Documents\Fabio\HMPCF\hmcpf-system\frontend
npm run dev
```

Abrir `http://localhost:5173`

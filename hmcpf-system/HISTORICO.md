# HMPCF — Histórico de Desenvolvimento

## Visão Geral

Novo sistema hospitalar HMPCF (Hospital M. Pres. Café Filho) construído do zero com FastAPI + React + Vite + Tauri. A arquitetura segue o padrão HTTP → api/v1 (controllers) → services (business) → repositories (SQL) → Database. Foco inicial no módulo de Recepção com boletim A4 em tempo real.

---

## Etapas Concluídas

### Etapa 1 — Backend FastAPI skeleton
- Configuração do projeto (app.main, app.config, app.logging)
- Health check (`GET /api/v1/health`)
- CORS liberado para todas origens (desenvolvimento)
- SQLite + SQLAlchemy assíncrono
- Base e TimestampMixin em `database/base.py` (id, created_at, updated_at)

### Etapa 2 — Paciente domain
- Modelo, schemas (Pydantic), repository, service, controller REST CRUD
- Endpoints: `GET /api/v1/pacientes`, `GET /api/v1/pacientes/{id}`, `POST`, `PUT`, `DELETE`
- Busca por CPF ou CNS: `GET /api/v1/pacientes/busca?documento=`

### Etapa 3 — Atendimento domain
- FK → pacientes com relacionamento SQLAlchemy
- Schemas de criação/retorno
- Rotas aninhadas sob pacientes: `GET /api/v1/pacientes/{id}/atendimentos`, `POST`

### Etapa 4 — Terminal session domain
- Sessão por UUID fixo no navegador (armazenado em localStorage)
- Endpoints: `POST /api/v1/term_session/start`, `POST /api/v1/term_session/{session_id}/ping`, `GET /api/v1/term_session/{session_id}`
- Sem login/senha

### Etapa 5 — Frontend React + Vite + Axios
- Proxy `/api` → `http://127.0.0.1:8000`
- Página de recepção com formulário de paciente completo

### Etapa 5.1 — Refinamentos do formulário
- Máscaras de CPF (000.000.000-00) e CNS (000 0000 0000 0000)
- Caixa alta automática em todos campos de texto
- Botões de rádio para raça/cor (IBGE: 01-BRANCA a 05-INDÍGENA), default 03-PARDA
- Botões de rádio para sexo (MASCULINO/FEMININO)
- Cidade default EXTREMOZ, estado default RN
- Botão "Limpar" limpa o formulário

### Etapa 5.2 — Busca integrada + validação + ações
- CPF e CNS são o mecanismo de busca (sem barra de busca separada)
- Debounce de 300ms na digitação dos campos de documento
- Validação matemática de CPF (algoritmo Receita Federal, rejeita dígitos repetidos)
- Validação matemática de CNS (algoritmo DATASUS: 15 dígitos, inicia com 1/2/7/8/9, soma % 11 === 0)
- Cálculo automático de idade a partir da data de nascimento
- Máscara de telefone ao carregar paciente existente
- Validação de campos obrigatórios (nome, sexo, CPF ou CNS)
- Feedback inline de erro para CPF/CNS inválidos
- 3 botões: Registrar Atendimento, Imprimir, Limpar
- Auto-salva paciente ao registrar atendimento (cria se novo, atualiza se existente)
- Flag `pacienteEncontradoRef` persiste "Paciente encontrado" mesmo após CNS não localizar

### Etapa 5.5.1 — Estrutura base do Boletim A4
- Componentes: HeaderHospital, BoletimA4, ProcedenciaSelector
- CSS com estilos A4, linhas, campos, tabela SSVV, áreas de escrita manual
- Header com brasão + PREFEITURA MUNICIPAL DE EXTREMOZ / SECRETARIA MUNICIPAL DE SAÚDE / HOSPITAL M. PRES. CAFÉ FILHO

### Etapa 5.5.2 — Boletim A4 completo
- Seção de prioridades com checkboxes
- 11 linhas de dados do paciente
- Tabela SSVV (Sinais Vitais) em preto e branco
- Seções de comorbidades, medicamentos, alergias
- 3 áreas de escrita manual: ANOTAÇÕES DA CLASSIFICAÇÃO, RESUMO DA HISTÓRIA CLÍNICA, HIPÓTESE DIAGNÓSTICA

### Etapa 5.2 AJUSTES — Campos editáveis + registro por turno
- DATA/HORA/REGISTRO no boletim A4 tornaram-se editáveis
- Lógica de registro baseada em turno:
  - DIURNO (07:00–18:59) — registro começa em 1
  - NOTURNO (19:00–06:59, pertencente ao dia anterior) — registro começa em 1
  - Se turno não mudou, incrementa o último registro salvo
  - Se usuário edita manualmente, a sugestão seguinte continua daquele número
- Funções utilitárias: `formatRegistro`, `calcularTurno`, `horaAtual`, `dataAtual`

### Ajustes visuais finais
- Pontilhados (`border-bottom: dotted`) removidos dos campos digitáveis
- Linhas de escrita manual (repeating-linear-gradient) preservadas nas áreas clínicas
- Visual mais limpo e profissional, sem poluição visual

---

## Decisões Técnicas

- CPF e CNS armazenados como dígitos crus no backend, formatados no frontend
- ProcedenciaSelector fora da folha A4, oculto na impressão (`.no-print`)
- Boletim A4 renderizado inline (não quebrado em micro-componentes) para fidelidade visual
- Tabela SSVV em P&B — enfermeiro marca cores manualmente com caneta após triagem
- Backend recria `hmpcf.db` a cada startup limpa via `Base.metadata.create_all()`
- Porta 8000: usar `fuser -k 8000/tcp` ou `pkill -f "python -m app.main"` antes de re-testar
- Frontend testado manualmente no Windows (`npm install && npm run dev`)
- npm não disponível no ambiente Linux atual

---

## Arquivos Relevantes

| Caminho | Descrição |
|---|---|
| `backend/app/main.py` | Entrypoint FastAPI |
| `backend/app/api/v1/pacientes.py` | CRUD + busca de pacientes |
| `backend/app/repositories/paciente_repository.py` | Consultas SQL |
| `frontend/src/pages/Recepcao.jsx` | Página central da recepção |
| `frontend/src/pages/Recepcao.css` | Estilos da recepção |
| `frontend/src/utils.js` | Helpers (formatadores, validadores, turno) |
| `frontend/src/components/boletim/BoletimA4.jsx` | Boletim A4 completo |
| `frontend/src/components/boletim/HeaderHospital.jsx` | Header com brasão |
| `frontend/src/components/boletim/ProcedenciaSelector.jsx` | Seletor de procedência |
| `frontend/src/components/boletim/boletim.css` | Estilos A4 e impressão |
| `frontend/public/img/brasao-extremoz.png` | Brasão do município |

---

## Próximos Passos (Sugeridos)

1. Integrar backend para persistência do último registro por turno
2. Implementar PDF generation (impressão server-side)
3. Módulo de triagem ( Classificação de Risco)
4. Módulo de evolução médica
5. Integração Tauri para aplicação desktop

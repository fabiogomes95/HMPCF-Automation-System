# Pendências — retomar em 03/07/2026

Sessão de 02/07/2026 cobriu: rotação de senha do Postgres, incidente e
correção (senha com `@` quebrando a connection string), consolidação dos
mecanismos de auto-restart do backend, backup criptografado, e reorganização
de pastas. Detalhes completos em `docs/HISTORICO.md` (entrada de 02/07/2026).

O que falta:

## 1. Autenticação da API — não implementado ainda

Requisito combinado com o usuário: **sem login para a recepção** (acesso
direto pelo PC/servidor principal, via `localhost`) e **senha obrigatória
para qualquer acesso remoto** (outra máquina na rede).

Senha de acesso remoto já gerada e comunicada ao usuário via chat em
02/07/2026 (guardar em local seguro — gerenciador de senhas — não está e não
deve entrar em nenhum arquivo deste repositório, que é público).

Plano de implementação:

1. **Backend** — middleware em `backend/app/main.py` (ou dependency
   aplicada globalmente) que:
   - Libera sem senha se `request.client.host` for `127.0.0.1`/`::1`.
   - Para qualquer outro IP, exige um header (ex: `X-Access-Password`) ou
     `Authorization: Bearer <senha>` comparando com uma nova setting
     `REMOTE_ACCESS_PASSWORD` (via `backend/.env`, nunca hardcoded).
   - Resposta 401 com corpo simples se ausente/errada.
2. **Frontend** — interceptor no `frontend/src/services/api.js` (axios):
   ao receber 401, pedir a senha (prompt simples ou modal), guardar em
   `sessionStorage` pra não pedir de novo na mesma aba, e reenviar a
   requisição com o header.
3. **Testes** — adicionar teste em `backend/tests/` cobrindo: request de
   `127.0.0.1` passa sem header; request de outro IP sem header dá 401;
   com header correto dá 200.
4. **Deploy** — testar primeiro no ambiente de teste (Vite dev server
   apontando pro backend de produção, já usado antes nesta sessão) antes de
   reiniciar o backend de produção. **Confirmar com o usuário antes de
   reiniciar** — hoje um restart already causou um incidente por outro
   motivo (senha com caractere especial), então ir com calma.

## 2. Mecanismos de restart duplicados — resolvido, mas falta confirmar boot

Tarefas Agendadas `HMPCF-Backend`/`HMPCF-Watchdog` foram desativadas hoje;
só o Serviço NSSM `HMPCF-Backend-Svc` deve reiniciar o backend agora. Isso
foi validado com o serviço já rodando, mas **não foi testado um reboot
completo da máquina** — vale confirmar em algum momento que o boot também
sobe corretamente só com o serviço NSSM (sem a Tarefa Agendada).

## 3. Launchers duplicados — não resolvido, decisão pendente

`INICIAR.bat` (raiz), `scripts/windows/ABRIR_HMPCF.bat` e
`scripts/windows/iniciar_sistema.vbs` fazem coisas parecidas. Não foram
consolidados porque não foi possível confirmar remotamente qual está
registrado em algum atalho/Tarefa Agendada (`Get-ScheduledTask` trava por
limitação de duplo-hop do WinRM nesta topologia — funciona `schtasks
/change` mas não `/query` nem o cmdlet `Get-ScheduledTask`). Para resolver
com segurança, seria preciso checar isso **fisicamente no servidor** (Task
Scheduler local, ou botão direito nos atalhos da área de trabalho) — ou
aceitar o risco e consolidar mesmo assim.

## 4. IP fixo da desktop-9c4s1co — adiado a pedido do usuário

Usuário quer IP estático configurado direto na máquina (não reserva de
DHCP no roteador), e confirmou que tem acesso físico/alternativo caso a
mudança tire a máquina da rede. Só fazer com o usuário presente/avisado,
dado o risco de lockout remoto (a própria `DEPLOY_HMPCF_REMOTO.ps1` documenta
que esse servidor é operado "sem acesso físico" no dia a dia).

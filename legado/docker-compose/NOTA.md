# Docker Compose — descontinuado

Este `docker-compose.yml` (PostgreSQL + pgAdmin + backend) foi usado no
início do projeto para desenvolvimento local. Desde setembro/2026 o
PostgreSQL roda como instalação nativa ("real"), não mais via Docker —
este compose **não é mais usado** e foi movido pra cá só como referência.

## Bug conhecido, não corrigido (não vale mais a pena)

O serviço `backend` tem `build.context: ../backend`, que era relativo à
raiz do repositório (onde este arquivo vivia originalmente). Rodando
`docker compose up` da raiz, esse caminho **saía do repositório**
(`../backend` a partir da raiz cai fora da pasta do projeto) — o build do
backend provavelmente nunca funcionou direto assim, sem ajuste manual do
`context` ou do diretório de execução. Como o compose não é mais usado,
não fizemos a correção — só documentamos aqui caso alguém queira reativar
esse fluxo no futuro (o certo seria `context: ../../backend` a partir
deste novo local, ou apontar pra um caminho absoluto).

## Se precisar reativar

1. Corrija `build.context` em `docker-compose.yml`.
2. Copie `.env.example` pra `.env` nesta mesma pasta e preencha
   `POSTGRES_PASSWORD` e `PGADMIN_PASSWORD`.
3. Rode `docker compose -f legado/docker-compose/docker-compose.yml up -d`
   (ou `cd legado/docker-compose && docker compose up -d`).

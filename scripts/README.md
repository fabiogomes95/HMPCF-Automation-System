# scripts/

Só o que roda **no servidor**. O que é do BPA fica em `bpa/` (inclusive
`bpa/ferramentas/`); o que saiu de uso fica em `legado/`.

## servidor/

| Arquivo | Para quê |
|---|---|
| `backup_postgres.bat` | Backup diário: `pg_dump` → criptografa (AES) → copia pro Google Drive → log em `C:\HMPCF\backups\backup.log`. Chamado pelo serviço `HMPCF-Backup-Svc` (23:00); dois cliques também funciona |
| `encrypt_backup.ps1` / `decrypt_backup.ps1` | Criptografa / restaura um backup (senha em `.backup_passphrase`, fora do git) |
| `copiar_backup_nuvem.ps1` | Cópia pra fora da máquina: `C:\HMPCF\backups_nuvem` (pasta que o app do Google Drive sincroniza) e, rodando como o usuário, também `G:\Meu Drive\HMPCF-Backups` |
| `agendador_backup.py` | Serviço do backup: todo dia às 23:00, na hora se o último tiver mais de 26 h, ou quando existir `C:\HMPCF\backups\RODAR_AGORA`. Substitui a tarefa agendada desde 24/09/2026 (o Agendador de Tarefas do servidor parou de executar) |
| `instalar_servico_backup.ps1` | Instala/atualiza o serviço `HMPCF-Backup-Svc` (nssm; rodar como administrador) |
| `DEPLOY_HMPCF_REMOTO.ps1` | Instalação completa de um servidor novo (Python, Postgres, serviço nssm) |
| `CONFIGURAR_WINRM.bat` | Habilita administração remota (WinRM) do servidor |

Restaurar um backup:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\servidor\decrypt_backup.ps1 -Path "C:\HMPCF\backups\hmpcf_AAAA-MM-DD.sql.enc"
```

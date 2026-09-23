# scripts/

Só o que roda **no servidor**. O que é do BPA fica em `bpa/` (inclusive
`bpa/ferramentas/`); o que saiu de uso fica em `legado/`.

## servidor/

| Arquivo | Para quê |
|---|---|
| `backup_postgres.bat` | Backup diário: `pg_dump` → criptografa (AES) → copia pro Google Drive → log em `C:\HMPCF\backups\backup.log`. Chamado pela tarefa `HMPCF-Backup-Diario` (23:00) |
| `encrypt_backup.ps1` / `decrypt_backup.ps1` | Criptografa / restaura um backup (senha em `.backup_passphrase`, fora do git) |
| `copiar_backup_nuvem.ps1` | Cópia pra fora da máquina (`G:\Meu Drive\HMPCF-Backups`) |
| `agendar_backup.ps1` | (Re)registra a tarefa `HMPCF-Backup-Diario` |
| `DEPLOY_HMPCF_REMOTO.ps1` | Instalação completa de um servidor novo (Python, Postgres, serviço nssm) |
| `CONFIGURAR_WINRM.bat` | Habilita administração remota (WinRM) do servidor |

Restaurar um backup:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\servidor\decrypt_backup.ps1 -Path "C:\HMPCF\backups\hmpcf_AAAA-MM-DD.sql.enc"
```

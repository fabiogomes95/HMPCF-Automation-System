"""Saúde dos backups, pro topo do Painel da TI.

- Backup do banco: o arquivo hmpcf_<data>.sql.enc mais novo em BACKUP_DIR e o
  fim do backup.log (o backend roda como LocalSystem e não enxerga o G: do
  Google Drive, então a cópia na nuvem é conferida pelo log).
- Lotes do BPA: quando cada notebook mandou lote pela última vez.

Existe porque o backup das 23:00 de 23/09/2026 falhou sem ninguém ver."""
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

_FUSO = ZoneInfo("America/Sao_Paulo")
LIMITE_HORAS = 26  # roda às 23:00 todo dia; passou disso, a noite anterior falhou
_RE_CABECALHO = re.compile(r"^===== (\d{2}/\d{2}/\d{4})\s+(\d{1,2}:\d{2}:\d{2})")


def _ultima_execucao(log: Path) -> dict | None:
    """Bloco da última execução no backup.log (o .bat acrescenta um por vez)."""
    try:
        linhas = log.read_text(encoding="latin-1", errors="replace").splitlines()
    except OSError:
        return None
    inicio = max((i for i, l in enumerate(linhas) if _RE_CABECALHO.match(l)), default=None)
    if inicio is None:
        return None
    m = _RE_CABECALHO.match(linhas[inicio])
    bloco = [l.strip() for l in linhas[inicio + 1:] if l.strip()]
    try:
        quando = datetime.strptime(f"{m.group(1)} {m.group(2)}", "%d/%m/%Y %H:%M:%S").replace(tzinfo=_FUSO)
    except ValueError:
        quando = None
    erros = [l for l in bloco if "ERRO" in l.upper() or "AVISO" in l.upper()]
    return {
        "quando": quando.isoformat(timespec="minutes") if quando else None,
        "terminou": any(l.startswith("[OK] Fim do backup") for l in bloco),
        "nuvem": any(l.startswith("[OK] Copia externa") for l in bloco),
        "problema": erros[-1] if erros else "",
    }


def situacao_backup(pasta: Path, agora: datetime) -> dict:
    arquivos = sorted(pasta.glob("hmpcf_*.sql*"), key=lambda p: p.stat().st_mtime, reverse=True) if pasta.is_dir() else []
    if not arquivos:
        return {"situacao": "sem_backup", "ultimo": None, "horas": None, "tamanho": 0,
                "execucao": _ultima_execucao(pasta / "backup.log")}
    ultimo = arquivos[0]
    quando = datetime.fromtimestamp(ultimo.stat().st_mtime, _FUSO)
    horas = max(0.0, round((agora - quando).total_seconds() / 3600, 1))
    execucao = _ultima_execucao(pasta / "backup.log")
    if horas > LIMITE_HORAS:
        situacao = "atrasado"
    elif execucao and (not execucao["terminou"] or not execucao["nuvem"]):
        situacao = "incompleto"  # arquivo recente, mas a última execução não chegou na nuvem
    else:
        situacao = "ok"
    return {
        "situacao": situacao,
        "ultimo": quando.isoformat(timespec="minutes"),
        "horas": horas,
        "tamanho": ultimo.stat().st_size,
        "execucao": execucao,
    }


async def lotes_bpa(session: AsyncSession) -> list[dict]:
    """Último lote recebido de cada notebook do BPA."""
    try:
        linhas = (await session.execute(text(
            "SELECT notebook, max(recebido_em) AS ultimo, count(*) AS lotes "
            "FROM bpa_lotes_backup GROUP BY notebook ORDER BY notebook"
        ))).all()
    except Exception:  # tabela ausente (banco de teste antigo): o Painel não pode cair por isso
        await session.rollback()
        return []
    return [
        {"notebook": n, "ultimo": u.astimezone(_FUSO).isoformat(timespec="minutes"), "lotes": q}
        for n, u, q in linhas
    ]

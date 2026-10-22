"""Ajustes manuais da Planilha de Atendimentos: a recepção muda a posição de
um paciente ou a hora mostrada, só pra organizar a planilha. É visual — não
mexe no atendimento: fica num arquivo JSON (settings.PLANILHA_AJUSTES_FILE),
fora do PostgreSQL, compartilhado entre os computadores da recepção.

Formato: {"AAAA-MM-DD|DIURNO": {"ordem": [ids...], "horas": {"id": "HH:MM"}}}.
Plantões com mais de DIAS_GUARDADOS dias são descartados a cada gravação."""
import json
import os
import re
import threading
from datetime import date, timedelta
from pathlib import Path

from app.core.config import settings
from app.core.exceptions import ValidationError

DIAS_GUARDADOS = 120
_HORA = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
_trava = threading.Lock()


def _arquivo() -> Path:
    return Path(settings.PLANILHA_AJUSTES_FILE)


def _ler() -> dict:
    try:
        dados = json.loads(_arquivo().read_text(encoding="utf-8"))
        return dados if isinstance(dados, dict) else {}
    except (FileNotFoundError, ValueError):
        return {}


def _gravar(dados: dict) -> None:
    arq = _arquivo()
    arq.parent.mkdir(parents=True, exist_ok=True)
    tmp = arq.with_suffix(".tmp")
    tmp.write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, arq)  # troca atômica: nunca fica um arquivo pela metade


def chave(dia: date, turno: str) -> str:
    return f"{dia.isoformat()}|{turno}"


def do_mes(ano: int, mes: int) -> dict:
    """Ajustes de todos os plantões do mês (inclui o noturno do último dia)."""
    prefixo = f"{ano:04d}-{mes:02d}-"
    return {k: v for k, v in _ler().items() if k.startswith(prefixo)}


def salvar(dia: date, turno: str, ordem: list[int], horas: dict[str, str]) -> dict:
    for h in horas.values():
        if not _HORA.match(h):
            raise ValidationError(f"Hora inválida: {h!r} (use HH:MM).")
    horas = {str(int(k)): v for k, v in horas.items()}
    with _trava:
        dados = _ler()
        limite = (date.today() - timedelta(days=DIAS_GUARDADOS)).isoformat()
        dados = {k: v for k, v in dados.items() if k[:10] >= limite}
        k = chave(dia, turno)
        if ordem or horas:
            dados[k] = {"ordem": ordem, "horas": horas}
        else:
            dados.pop(k, None)  # "restaurar ordem": volta ao automático
        _gravar(dados)
    return dados.get(k, {"ordem": [], "horas": {}})

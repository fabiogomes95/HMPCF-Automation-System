"""Saúde do backup no Painel (app/services/backup_status.py)."""
import os
import time
from datetime import datetime

from app.services.backup_status import _FUSO, situacao_backup

OK = "===== 24/09/2026 23:00:01,10 =====\nIniciando backup...\n[OK] Copia externa: G:/HMPCF-Backups\n[OK] Fim do backup.\n"


def _backup(pasta, horas_atras, log):
    f = pasta / "hmpcf_2026-09-24.sql.enc"
    f.write_bytes(b"x" * 10)
    t = time.time() - horas_atras * 3600
    os.utime(f, (t, t))
    (pasta / "backup.log").write_text(log, encoding="latin-1")


def test_em_dia(tmp_path):
    _backup(tmp_path, 3, OK)
    r = situacao_backup(tmp_path, datetime.now(_FUSO))
    assert r["situacao"] == "ok" and r["execucao"]["nuvem"] and r["tamanho"] == 10


def test_noite_sem_backup_fica_atrasado(tmp_path):
    _backup(tmp_path, 30, OK)
    assert situacao_backup(tmp_path, datetime.now(_FUSO))["situacao"] == "atrasado"


def test_sem_copia_na_nuvem_fica_incompleto(tmp_path):
    _backup(tmp_path, 1, "===== 24/09/2026 23:00:01,10 =====\n[AVISO] G: nao encontrado\n[OK] Fim do backup.\n")
    r = situacao_backup(tmp_path, datetime.now(_FUSO))
    assert r["situacao"] == "incompleto" and "G:" in r["execucao"]["problema"]


def test_pasta_sem_backup(tmp_path):
    assert situacao_backup(tmp_path / "nao_existe", datetime.now(_FUSO))["situacao"] == "sem_backup"

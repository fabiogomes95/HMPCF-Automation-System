"""Backup dos lotes de digitação no servidor (bpa_local/services/backup_lotes.py)."""

import pytest

import bpa_gerador as bpa
from bpa_local.services import backup_lotes


class _Servidor:
    """PostgreSQL do hospital simulado: guarda o que chegou; pode 'cair'."""

    def __init__(self):
        self.tabela: dict = {}
        self.fora_do_ar = False

    def conectar(self):
        if self.fora_do_ar:
            raise Exception("could not connect to server: Connection timed out")
        srv = self

        class Cur:
            def __enter__(self): return self
            def __exit__(self, *a): pass

            def execute(self, sql, p):
                notebook, arquivo, conteudo, sha, tamanho, mtime = p
                srv.tabela[(notebook, arquivo)] = conteudo

        class Con:
            def cursor(self): return Cur()
            def commit(self): pass
            def close(self): pass
        return Con()


@pytest.fixture
def ambiente(monkeypatch, tmp_path):
    lotes = tmp_path / "lotes"
    lotes.mkdir()
    monkeypatch.setattr(bpa, "BPA_LOTES_DIR", str(lotes))
    monkeypatch.setenv("BPA_BACKUP_LOTES", "1")          # nos testes vem desligado por padrão
    monkeypatch.setattr(backup_lotes, "ARQUIVO_ESTADO", tmp_path / "backup_lotes.json")
    monkeypatch.setattr(backup_lotes, "_estado", {"enviados": {}, "situacao": "nunca"})
    monkeypatch.setattr(backup_lotes, "NOTEBOOK", "NOTE-TESTE")
    srv = _Servidor()
    monkeypatch.setattr(backup_lotes, "_conectar", srv.conectar)
    return lotes, srv


def test_envia_so_o_que_mudou(ambiente):
    lotes, srv = ambiente
    (lotes / "01-09-2026.txt").write_text("PROFISSIONAL: A | DATA: 01/09/2026\n12345678909\n", encoding="utf-8")
    (lotes / "02-09-2026.txt").write_text("PROFISSIONAL: A | DATA: 02/09/2026\nID:501\n", encoding="utf-8")
    (lotes / "BPA_MEDICOS_01092026.txt").write_text("gerado", encoding="utf-8")   # não é lote: não vai
    (lotes / "AGOSTO").mkdir()
    (lotes / "AGOSTO" / "31-08-2026.txt").write_text("PROFISSIONAL: B | DATA: 31/08/2026\n1\n", encoding="utf-8")

    e = backup_lotes.sincronizar()
    assert e["situacao"] == "ok" and e["pendentes"] == 0
    assert set(srv.tabela) == {("NOTE-TESTE", "01-09-2026.txt"), ("NOTE-TESTE", "02-09-2026.txt"),
                               ("NOTE-TESTE", "AGOSTO/31-08-2026.txt")}

    srv.tabela.clear()
    backup_lotes.sincronizar()
    assert srv.tabela == {}                                   # nada mudou: não reenvia

    (lotes / "02-09-2026.txt").write_text("PROFISSIONAL: A | DATA: 02/09/2026\nID:501\nID:502\n", encoding="utf-8")
    backup_lotes.sincronizar()
    assert list(srv.tabela) == [("NOTE-TESTE", "02-09-2026.txt")]
    assert "ID:502" in srv.tabela[("NOTE-TESTE", "02-09-2026.txt")]   # conteúdo exato (CRLF do Windows incluso)


def test_sem_servidor_fica_pendente_e_manda_depois(ambiente):
    lotes, srv = ambiente
    (lotes / "03-09-2026.txt").write_text("PROFISSIONAL: A | DATA: 03/09/2026\n12345678909\n", encoding="utf-8")
    srv.fora_do_ar = True
    e = backup_lotes.sincronizar()
    assert e["situacao"] == "pendente" and e["pendentes"] == 1 and "servidor" in e["erro"]

    srv.fora_do_ar = False
    e = backup_lotes.sincronizar()
    assert e["situacao"] == "ok" and ("NOTE-TESTE", "03-09-2026.txt") in srv.tabela
    assert backup_lotes.ARQUIVO_ESTADO.exists()               # lembra o que já foi, mesmo reiniciando


"""Backup dos lotes de digitação (DD-MM-AAAA.txt) deste notebook no servidor.

Os lotes só existem aqui; cada arquivo que muda vai pra tabela
bpa_lotes_backup do PostgreSQL do hospital (usuário bpa_leitura, que só pode
gravar nela) e, dali, entra no backup diário que vai pro Google Drive.

Roda numa thread: a cada INTERVALO e logo depois de gravar/desfazer/dividir
(pedir_envio). Só manda o que mudou (compara o SHA-256 com o último enviado,
guardado em bpa/backup_lotes.json). Sem rede do hospital fica pendente e
tenta de novo depois. Restaurar: bpa/ferramentas/restaurar_lotes.py."""
import hashlib
import json
import os
import socket
import threading
from datetime import datetime, timezone
from pathlib import Path

import psycopg2

import bpa_gerador as bpa
from bpa_local import config

INTERVALO = 300           # segundos entre verificações
ESPERA_DEPOIS_DE_MUDAR = 3  # junta várias gravações seguidas num envio só
ARQUIVO_ESTADO = config.BASE / "backup_lotes.json"
NOTEBOOK = os.getenv("BPA_NOTEBOOK", "").strip() or socket.gethostname().upper()

_SQL = """
    INSERT INTO bpa_lotes_backup (notebook, arquivo, conteudo, sha256, tamanho, modificado_em)
    VALUES (%s, %s, %s, %s, %s, %s)
    ON CONFLICT (notebook, arquivo) DO UPDATE SET
        conteudo = EXCLUDED.conteudo, sha256 = EXCLUDED.sha256, tamanho = EXCLUDED.tamanho,
        modificado_em = EXCLUDED.modificado_em, recebido_em = now()
"""

_lock = threading.Lock()
_pedido = threading.Event()
_estado: dict = {"enviados": {}, "situacao": "nunca"}


def _carregar() -> None:
    global _estado
    try:
        _estado = json.loads(ARQUIVO_ESTADO.read_text(encoding="utf-8"))
        _estado.setdefault("enviados", {})
    except Exception:
        _estado = {"enviados": {}, "situacao": "nunca"}


def _salvar() -> None:
    try:
        ARQUIVO_ESTADO.write_text(json.dumps(_estado, ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception as e:
        print(f"[BPA] não consegui salvar {ARQUIVO_ESTADO.name}: {e}")


def ligado() -> bool:
    # desligado nos testes e no modo de teste (pacientes falsos: não há servidor)
    return os.getenv("BPA_BACKUP_LOTES", "1") != "0" and not config.POSTGRES_FALSO


def estado() -> dict:
    with _lock:
        e = {k: v for k, v in _estado.items() if k != "enviados"}
    if not ligado():
        e["situacao"] = "desligado"
    return e


def _lotes() -> list[tuple[str, Path]]:
    """(nome no backup, caminho) de cada lote de digitação — raiz e subpastas de mês."""
    raiz = Path(bpa.garantir_pasta_lotes())
    return [(c.relative_to(raiz).as_posix(), c) for c in bpa.listar_arquivos_lote_dia()]


def _conectar():
    # Conexão própria em UTF-8 (a de leitura usa LATIN1 por causa das mensagens de erro)
    return psycopg2.connect(**config.POSTGRES, connect_timeout=5)


def sincronizar() -> dict:
    """Manda pro servidor os lotes que mudaram desde o último envio."""
    with _lock:
        enviados = dict(_estado.get("enviados", {}))
    mudados = []
    for nome, caminho in _lotes():
        try:
            dados = caminho.read_bytes()
        except OSError:
            continue
        sha = hashlib.sha256(dados).hexdigest()
        if enviados.get(nome) != sha:
            mtime = datetime.fromtimestamp(caminho.stat().st_mtime, tz=timezone.utc)
            mudados.append((nome, dados.decode("utf-8", errors="replace"), sha, len(dados), mtime))

    agora = datetime.now().isoformat(timespec="seconds")
    if not mudados:
        with _lock:
            _estado.update(situacao="ok", verificado_em=agora, pendentes=0, erro="")
            _salvar()
        return estado()

    try:
        con = _conectar()
        try:
            with con.cursor() as cur:
                for nome, texto, sha, tamanho, mtime in mudados:
                    cur.execute(_SQL, (NOTEBOOK, nome, texto, sha, tamanho, mtime))
            con.commit()
        finally:
            con.close()
    except Exception as e:
        erro = str(e).strip().splitlines()[0] if str(e).strip() else type(e).__name__
        with _lock:
            _estado.update(situacao="pendente", verificado_em=agora, pendentes=len(mudados),
                           erro=f"Sem acesso ao servidor do hospital ({erro}) — tenta de novo sozinho.")
            _salvar()
        return estado()

    with _lock:
        for nome, _texto, sha, _t, _m in mudados:
            _estado["enviados"][nome] = sha
        _estado.update(situacao="ok", verificado_em=agora, ultimo_envio=agora, pendentes=0, erro="",
                       ultimos_arquivos=[m[0] for m in mudados][-5:])
        _salvar()
    print(f"[BPA] backup dos lotes: {len(mudados)} arquivo(s) enviados ao servidor.")
    return estado()


def pedir_envio() -> None:
    """Chamado depois de mexer num lote: a thread manda em poucos segundos."""
    _pedido.set()


def _laco() -> None:
    while True:
        _pedido.wait(timeout=INTERVALO)
        if _pedido.is_set():
            _pedido.clear()
            # junta gravações em sequência (digitação rápida) num envio só
            _pedido.wait(timeout=ESPERA_DEPOIS_DE_MUDAR)
            _pedido.clear()
        try:
            sincronizar()
        except Exception as e:  # nunca derrubar o BPA por causa do backup
            print(f"[BPA] backup dos lotes falhou: {e}")


def iniciar() -> None:
    if ligado():
        threading.Thread(target=_laco, name="backup-lotes", daemon=True).start()
        pedir_envio()  # já confere logo que o BPA liga


_carregar()

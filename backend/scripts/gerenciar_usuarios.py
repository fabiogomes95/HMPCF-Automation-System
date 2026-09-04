"""
gerenciar_usuarios.py
======================
CLI pra criar/resetar senha/listar as contas de acesso à recepção.

A senha nunca é passada por argumento de linha de comando (ficaria no
histórico do shell) — sempre digitada via prompt (getpass, sem eco).

Uso:
    cd backend
    .venv\\Scripts\\python scripts\\gerenciar_usuarios.py criar --username recepcao --role recepcao
    .venv\\Scripts\\python scripts\\gerenciar_usuarios.py resetar-senha --username recepcao
    .venv\\Scripts\\python scripts\\gerenciar_usuarios.py listar
"""

import argparse
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import bcrypt  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.models.usuario import Usuario  # noqa: E402

ROLES_CONHECIDOS = {"recepcao", "coordenacao", "bpa"}


def _engine():
    return create_engine(settings.database_url_sync)


def _hash_senha(senha: str) -> str:
    return bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _pedir_senha_confirmada() -> str:
    senha = getpass.getpass("Senha: ")
    confirmacao = getpass.getpass("Confirme a senha: ")
    if senha != confirmacao:
        print("ERRO: as senhas não conferem.")
        sys.exit(1)
    if len(senha) < 8:
        print("ERRO: use uma senha com pelo menos 8 caracteres.")
        sys.exit(1)
    return senha


def criar(username: str, role: str) -> None:
    if role not in ROLES_CONHECIDOS:
        print(
            f"AVISO: papel '{role}' fora do padrão conhecido "
            f"({', '.join(sorted(ROLES_CONHECIDOS))}) — seguindo mesmo assim."
        )
    senha = _pedir_senha_confirmada()

    with Session(_engine()) as session:
        if session.query(Usuario).filter_by(username=username).first() is not None:
            print(f"ERRO: usuário '{username}' já existe — use 'resetar-senha' pra trocar a senha.")
            sys.exit(1)
        session.add(Usuario(username=username, password_hash=_hash_senha(senha), role=role))
        session.commit()
    print(f"OK: usuário '{username}' (papel '{role}') criado.")


def resetar_senha(username: str) -> None:
    senha = _pedir_senha_confirmada()

    with Session(_engine()) as session:
        usuario = session.query(Usuario).filter_by(username=username).first()
        if usuario is None:
            print(f"ERRO: usuário '{username}' não encontrado.")
            sys.exit(1)
        usuario.password_hash = _hash_senha(senha)
        usuario.tentativas_falhas = 0
        usuario.bloqueado_ate = None
        session.commit()
    print(f"OK: senha de '{username}' atualizada, bloqueio (se havia) removido.")


def listar() -> None:
    with Session(_engine()) as session:
        usuarios = session.query(Usuario).order_by(Usuario.username).all()
        if not usuarios:
            print("Nenhum usuário cadastrado ainda.")
            return
        for u in usuarios:
            status = "ativo" if u.ativo else "INATIVO"
            bloqueio = f" (bloqueado até {u.bloqueado_ate})" if u.bloqueado_ate else ""
            print(f"- {u.username:<15} papel={u.role:<12} {status}{bloqueio}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Gerencia contas de acesso à recepção HMPCF.")
    sub = parser.add_subparsers(dest="comando", required=True)

    p_criar = sub.add_parser("criar", help="Cria uma nova conta")
    p_criar.add_argument("--username", required=True)
    p_criar.add_argument("--role", required=True, help="ex: recepcao, coordenacao, bpa")

    p_reset = sub.add_parser("resetar-senha", help="Troca a senha de uma conta existente")
    p_reset.add_argument("--username", required=True)

    sub.add_parser("listar", help="Lista as contas cadastradas")

    args = parser.parse_args()
    if args.comando == "criar":
        criar(args.username, args.role)
    elif args.comando == "resetar-senha":
        resetar_senha(args.username)
    elif args.comando == "listar":
        listar()


if __name__ == "__main__":
    main()

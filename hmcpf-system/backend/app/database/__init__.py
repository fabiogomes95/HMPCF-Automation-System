"""
database/ — Camada de acesso a dados.

AQUI VOCÊ ENCONTRA:
  session.py  → Conexão com o banco (engine SQLAlchemy)
  base.py     → Classe Base (todo modelo herda dela)

CONCEITO: ORM (Object-Relational Mapping)
  SQLAlchemy permite escrever Python em vez de SQL puro.
  Exemplo: User.query.filter_by(name="João") em vez de
           SELECT * FROM users WHERE name = 'João'

  Vantagens: código mais limpo, portável entre bancos,
             proteção contra SQL injection.
"""

"""
models/ — Modelos SQLAlchemy (mapeamento banco de dados).

CADA MODELO = UMA TABELA NO BANCO

Exemplo de modelo:
    class Paciente(Base):
        __tablename__ = "pacientes"
        nome: str
        cpf: str
        data_nascimento: date

    Isso cria a tabela "pacientes" com colunas:
    id, created_at, updated_at, nome, cpf, data_nascimento

    (id, created_at, updated_at vêm da classe Base)

FLUXO:
  1. Defina o modelo aqui
  2. Execute create_all() para criar as tabelas
  3. Use session.query(Modelo) para consultar

  from app.database.session import engine
  Base.metadata.create_all(bind=engine)

NOTA: Esta pasta está vazia na Fase 1.
Os modelos serão criados quando migrarmos os dados
do hospital.db para a nova estrutura.
"""

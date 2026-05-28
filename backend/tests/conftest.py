import asyncio
import os
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy import NullPool
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.database.base import Base
from app.core.config import settings
from app.models.paciente import Paciente
from app.models.recepcao_atendimento import RecepcaoAtendimento

# Banco de testes isolado — nunca aponta para o banco de produção.
# Configure TEST_POSTGRES_DB no .env (ou variável de ambiente) para um banco dedicado.
# Exemplo: TEST_POSTGRES_DB=hmpcf_test
_test_db = os.getenv("TEST_POSTGRES_DB", "hmpcf_test")
TEST_DATABASE_URL = (
    f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
    f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{_test_db}"
)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def engine():
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def clean_tables(engine):
    """Limpa dados entre testes sem dropar tabelas."""
    async with engine.begin() as conn:
        await conn.execute(
            RecepcaoAtendimento.__table__.delete()
        )
        await conn.execute(
            Paciente.__table__.delete()
        )


@pytest_asyncio.fixture
async def session(engine) -> AsyncGenerator[AsyncSession, None]:
    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def paciente(session: AsyncSession) -> Paciente:
    p = Paciente(
        nome="MARIA SILVA",
        num_cpf="12345678901",
        cns="123456789012345",
        dtnasc="19900101",
        sexo="F",
    )
    session.add(p)
    await session.flush()
    await session.refresh(p)
    return p


@pytest_asyncio.fixture
async def paciente2(session: AsyncSession) -> Paciente:
    p = Paciente(
        nome="JOAO SANTOS",
        num_cpf="98765432100",
        cns="987654321098765",
        dtnasc="19850515",
        sexo="M",
    )
    session.add(p)
    await session.flush()
    await session.refresh(p)
    return p

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from orquestrador.configuracao import obter_configuracoes

configuracoes = obter_configuracoes()

motor = create_engine(configuracoes.database_url, pool_pre_ping=True)
FabricaDeSessoes = sessionmaker(bind=motor, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def obter_sessao() -> Generator[Session, None, None]:
    sessao = FabricaDeSessoes()
    try:
        yield sessao
    finally:
        sessao.close()


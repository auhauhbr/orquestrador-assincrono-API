from contextlib import asynccontextmanager

from fastapi import FastAPI

from orquestrador.api.rotas.metricas import roteador as roteador_metricas
from orquestrador.api.rotas.tarefas import roteador as roteador_tarefas
from orquestrador.api.rotas.tarefas_mortas import roteador as roteador_tarefas_mortas
from orquestrador.banco.migracoes import preparar_banco


@asynccontextmanager
async def ciclo_de_vida(_: FastAPI):
    preparar_banco()
    yield


aplicacao = FastAPI(
    title="Orquestrador Assíncrono",
    description=(
        "Central de tarefas distribuídas para enfileirar, executar e acompanhar "
        "processamento assíncrono."
    ),
    version="0.1.0",
    lifespan=ciclo_de_vida,
)
aplicacao.include_router(roteador_tarefas, prefix="/api")
aplicacao.include_router(roteador_metricas, prefix="/api")
aplicacao.include_router(roteador_tarefas_mortas, prefix="/api")


@aplicacao.get("/saude", tags=["sistema"])
def verificar_saude() -> dict[str, str]:
    return {"situacao": "ok"}

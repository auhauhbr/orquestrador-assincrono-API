import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, update

from orquestrador.banco.conexao import FabricaDeSessoes
from orquestrador.banco.modelos import RegistroTarefa, RegistroTarefaMorta

logger = logging.getLogger(__name__)


def garantir_registro_tarefa(
    tarefa_id: str,
    *,
    tipo: str,
    fila: str,
    parametros: dict[str, Any],
) -> None:
    """Cria histórico para tarefas disparadas fora da API, como o Celery Beat."""
    try:
        with FabricaDeSessoes.begin() as sessao:
            existente = sessao.scalar(
                select(RegistroTarefa).where(RegistroTarefa.tarefa_id == tarefa_id)
            )
            if existente is None:
                sessao.add(
                    RegistroTarefa(
                        tarefa_id=tarefa_id,
                        tipo=tipo.removeprefix("tarefas."),
                        fila=fila,
                        parametros=parametros,
                        estado="PENDING",
                    )
                )
    except Exception:
        logger.exception(
            "Não foi possível criar o histórico da tarefa",
            extra={"tarefa_id": tarefa_id, "tipo_tarefa": tipo},
        )


def atualizar_tarefa(
    tarefa_id: str,
    *,
    estado: str,
    iniciado_em: datetime | None = None,
    finalizado_em: datetime | None = None,
    duracao_ms: float | None = None,
    resultado: Any | None = None,
    erro: str | None = None,
) -> None:
    valores: dict[str, Any] = {
        "estado": estado,
        "atualizado_em": datetime.now(UTC),
    }
    if iniciado_em is not None:
        valores["iniciado_em"] = iniciado_em
    if finalizado_em is not None:
        valores["finalizado_em"] = finalizado_em
    if duracao_ms is not None:
        valores["duracao_ms"] = duracao_ms
    if resultado is not None:
        valores["resultado"] = resultado
    if erro is not None:
        valores["erro"] = erro
    elif estado == "SUCCESS":
        valores["erro"] = None

    try:
        with FabricaDeSessoes.begin() as sessao:
            sessao.execute(
                update(RegistroTarefa)
                .where(RegistroTarefa.tarefa_id == tarefa_id)
                .values(**valores)
            )
    except Exception:
        logger.exception(
            "Não foi possível persistir o estado da tarefa",
            extra={"tarefa_id": tarefa_id, "estado": estado},
        )


def registrar_tarefa_morta(
    tarefa_id: str,
    *,
    tentativas_realizadas: int,
    erro: str,
    duracao_ms: float | None,
) -> None:
    """Marca a tarefa original e cria a cópia da dead-letter atomicamente."""
    try:
        with FabricaDeSessoes.begin() as sessao:
            tarefa = sessao.scalar(
                select(RegistroTarefa).where(RegistroTarefa.tarefa_id == tarefa_id)
            )
            if tarefa is None:
                logger.error(
                    "Tarefa não encontrada para envio à fila morta",
                    extra={"tarefa_id": tarefa_id},
                )
                return

            agora = datetime.now(UTC)
            tarefa.estado = "FAILURE"
            tarefa.erro = erro
            tarefa.finalizado_em = agora
            tarefa.duracao_ms = duracao_ms
            tarefa.foi_para_fila_morta = True

            existente = sessao.scalar(
                select(RegistroTarefaMorta).where(
                    RegistroTarefaMorta.tarefa_original_id == tarefa_id
                )
            )
            if existente is None:
                sessao.add(
                    RegistroTarefaMorta(
                        tarefa_original_id=tarefa_id,
                        tipo=tarefa.tipo,
                        fila=tarefa.fila,
                        parametros=tarefa.parametros,
                        tentativas_realizadas=tentativas_realizadas,
                        ultimo_erro=erro,
                        falhou_em=agora,
                    )
                )
    except Exception:
        logger.exception(
            "Não foi possível registrar a tarefa na fila morta",
            extra={"tarefa_id": tarefa_id},
        )

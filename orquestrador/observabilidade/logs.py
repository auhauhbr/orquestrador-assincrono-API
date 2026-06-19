import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Any

from celery import signals

from orquestrador.banco.estado_tarefas import (
    atualizar_tarefa,
    garantir_registro_tarefa,
    registrar_tarefa_morta,
)
from orquestrador.banco.migracoes import preparar_banco
from orquestrador.configuracao import obter_configuracoes

_inicios: dict[str, float] = {}
_campos_padrao = {
    "name",
    "msg",
    "args",
    "levelname",
    "levelno",
    "pathname",
    "filename",
    "module",
    "exc_info",
    "exc_text",
    "stack_info",
    "lineno",
    "funcName",
    "created",
    "msecs",
    "relativeCreated",
    "thread",
    "threadName",
    "processName",
    "process",
    "taskName",
}


class FormatadorJson(logging.Formatter):
    """Transforma cada registro em uma linha JSON adequada para agregadores."""

    def format(self, registro: logging.LogRecord) -> str:
        conteudo: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(registro.created, tz=UTC).isoformat(),
            "nivel": registro.levelname,
            "logger": registro.name,
            "mensagem": registro.getMessage(),
        }

        for campo, valor in registro.__dict__.items():
            if campo not in _campos_padrao and not campo.startswith("_"):
                conteudo[campo] = valor

        if registro.exc_info:
            conteudo["excecao"] = self.formatException(registro.exc_info)

        return json.dumps(conteudo, ensure_ascii=False, default=str)


def _criar_manipulador_fluxo() -> logging.Handler:
    manipulador = logging.StreamHandler(sys.stdout)
    manipulador.setFormatter(FormatadorJson())
    return manipulador


def _criar_manipulador_arquivo(caminho: str) -> logging.Handler:
    arquivo = Path(caminho)
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    manipulador = logging.FileHandler(arquivo, encoding="utf-8")
    manipulador.setFormatter(FormatadorJson())
    return manipulador


@signals.setup_logging.connect
def configurar_logs_celery(*_: Any, **__: Any) -> None:
    configuracoes = obter_configuracoes()
    raiz = logging.getLogger()
    raiz.handlers.clear()
    raiz.setLevel(configuracoes.nivel_log.upper())
    raiz.addHandler(_criar_manipulador_fluxo())
    raiz.addHandler(_criar_manipulador_arquivo(configuracoes.caminho_log))


@signals.worker_ready.connect
def preparar_banco_do_trabalhador(*_: Any, **__: Any) -> None:
    preparar_banco()


def _contexto_tarefa(
    tarefa_id: str,
    tarefa: Any = None,
    *,
    estado: str,
    duracao_ms: float | None = None,
    erro: str | None = None,
    tentativa: int | None = None,
) -> dict[str, Any]:
    requisicao = getattr(tarefa, "request", tarefa)
    entrega = getattr(requisicao, "delivery_info", {}) or {}
    contexto: dict[str, Any] = {
        "tarefa_id": tarefa_id,
        "tipo_tarefa": getattr(tarefa, "name", None)
        or getattr(requisicao, "task", "desconhecida"),
        "fila": entrega.get("routing_key", "desconhecida"),
        "estado": estado,
    }
    if duracao_ms is not None:
        contexto["duracao_ms"] = round(duracao_ms, 2)
    if erro is not None:
        contexto["erro"] = erro
    if tentativa is not None:
        contexto["tentativa"] = tentativa
    return contexto


def _duracao(tarefa_id: str) -> float | None:
    inicio = _inicios.pop(tarefa_id, None)
    return None if inicio is None else (perf_counter() - inicio) * 1000


@signals.task_prerun.connect
def registrar_inicio(
    task_id: str,
    task: Any,
    kwargs: dict[str, Any] | None = None,
    *_: Any,
    **__: Any,
) -> None:
    _inicios[task_id] = perf_counter()
    entrega = task.request.delivery_info or {}
    garantir_registro_tarefa(
        task_id,
        tipo=task.name,
        fila=entrega.get("routing_key", "default"),
        parametros=kwargs or {},
    )
    atualizar_tarefa(task_id, estado="STARTED", iniciado_em=datetime.now(UTC))
    logging.getLogger("orquestrador.tarefas").info(
        "Tarefa iniciada",
        extra=_contexto_tarefa(
            task_id,
            task,
            estado="iniciado",
            tentativa=task.request.retries + 1,
        ),
    )


@signals.task_success.connect
def registrar_sucesso(
    sender: Any,
    result: Any,
    *_: Any,
    **__: Any,
) -> None:
    tarefa_id = sender.request.id
    duracao_ms = _duracao(tarefa_id)
    atualizar_tarefa(
        tarefa_id,
        estado="SUCCESS",
        finalizado_em=datetime.now(UTC),
        duracao_ms=duracao_ms,
        resultado=result,
    )
    logging.getLogger("orquestrador.tarefas").info(
        "Tarefa concluída com sucesso",
        extra=_contexto_tarefa(
            tarefa_id,
            sender,
            estado="sucesso",
            duracao_ms=duracao_ms,
            tentativa=sender.request.retries + 1,
        ),
    )


@signals.task_retry.connect
def registrar_nova_tentativa(
    request: Any,
    reason: BaseException,
    *_: Any,
    **__: Any,
) -> None:
    duracao_ms = _duracao(request.id)
    atualizar_tarefa(
        request.id,
        estado="RETRY",
        duracao_ms=duracao_ms,
        erro=str(reason),
    )
    logging.getLogger("orquestrador.tarefas").warning(
        "Tarefa será executada novamente",
        extra=_contexto_tarefa(
            request.id,
            request,
            estado="nova_tentativa",
            duracao_ms=duracao_ms,
            erro=str(reason),
            tentativa=request.retries + 1,
        ),
    )


@signals.task_failure.connect
def registrar_falha(
    task_id: str,
    exception: BaseException,
    sender: Any,
    *_: Any,
    **__: Any,
) -> None:
    duracao_ms = _duracao(task_id)
    tentativas = sender.request.retries + 1
    registrar_tarefa_morta(
        task_id,
        tentativas_realizadas=tentativas,
        duracao_ms=duracao_ms,
        erro=str(exception),
    )
    logging.getLogger("orquestrador.tarefas").error(
        "Tarefa falhou definitivamente",
        extra=_contexto_tarefa(
            task_id,
            sender,
            estado="falha",
            duracao_ms=duracao_ms,
            erro=str(exception),
            tentativa=tentativas,
        ),
    )

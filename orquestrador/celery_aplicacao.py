from celery import Celery
from celery.schedules import crontab
from kombu import Queue

from orquestrador.configuracao import obter_configuracoes
from orquestrador.observabilidade import logs as _logs  # noqa: F401

configuracoes = obter_configuracoes()

aplicacao_celery = Celery(
    "orquestrador",
    broker=configuracoes.redis_url,
    backend=configuracoes.redis_url,
    include=[
        "orquestrador.tarefas.exemplos",
        "orquestrador.tarefas.imagens",
        "orquestrador.tarefas.periodicas",
        "orquestrador.tarefas.relatorios",
    ],
)

agenda_relatorio = (
    crontab(minute="*")
    if configuracoes.agendamento_teste
    else crontab(hour=8, minute=0)
)

aplicacao_celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="America/Recife",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_default_queue="default",
    task_default_routing_key="default",
    task_queues=(
        Queue("high", routing_key="high"),
        Queue("default", routing_key="default"),
        Queue("low", routing_key="low"),
    ),
    result_expires=86_400,
    task_soft_time_limit=300,
    task_time_limit=360,
    broker_connection_retry_on_startup=True,
    beat_schedule={
        "gerar-relatorio-diario": {
            "task": "tarefas.relatorio_diario",
            "schedule": agenda_relatorio,
            "options": {"queue": "default"},
        }
    },
)

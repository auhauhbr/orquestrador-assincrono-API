from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from orquestrador.banco.modelos import RegistroTarefa
from orquestrador.esquemas.metricas import PeriodoMetricas, ResumoMetricas

_nomes_estados = {
    "PENDING": "pendente",
    "STARTED": "em_execucao",
    "SUCCESS": "sucesso",
    "FAILURE": "falha",
    "RETRY": "nova_tentativa",
    "REVOKED": "cancelada",
}


def _agrupar(
    sessao: Session,
    coluna,
    desde: datetime,
    ate: datetime,
    excluir_tarefa_id: str | None = None,
) -> dict[str, int]:
    filtros = [RegistroTarefa.criado_em.between(desde, ate)]
    if excluir_tarefa_id:
        filtros.append(RegistroTarefa.tarefa_id != excluir_tarefa_id)
    consulta = (
        select(coluna, func.count(RegistroTarefa.id))
        .where(*filtros)
        .group_by(coluna)
    )
    return {str(chave): quantidade for chave, quantidade in sessao.execute(consulta)}


def calcular_metricas(
    sessao: Session,
    desde: datetime,
    ate: datetime,
    excluir_tarefa_id: str | None = None,
) -> ResumoMetricas:
    filtros_periodo = [RegistroTarefa.criado_em.between(desde, ate)]
    if excluir_tarefa_id:
        filtros_periodo.append(RegistroTarefa.tarefa_id != excluir_tarefa_id)
    total = sessao.scalar(
        select(func.count(RegistroTarefa.id)).where(*filtros_periodo)
    ) or 0
    por_estado = _agrupar(
        sessao,
        RegistroTarefa.estado,
        desde,
        ate,
        excluir_tarefa_id,
    )
    finalizadas = por_estado.get("SUCCESS", 0) + por_estado.get("FAILURE", 0)
    taxa_sucesso = (
        por_estado.get("SUCCESS", 0) / finalizadas * 100 if finalizadas else 0.0
    )
    media_ms = sessao.scalar(
        select(func.avg(RegistroTarefa.duracao_ms)).where(
            *filtros_periodo,
            RegistroTarefa.duracao_ms.is_not(None),
            RegistroTarefa.estado.in_(("SUCCESS", "FAILURE")),
        )
    )

    return ResumoMetricas(
        periodo=PeriodoMetricas(desde=desde, ate=ate),
        total_tarefas=total,
        quantidade_por_estado={
            nome_portugues: por_estado.get(estado_celery, 0)
            for estado_celery, nome_portugues in _nomes_estados.items()
        },
        taxa_sucesso_percentual=round(taxa_sucesso, 2),
        duracao_media_segundos=round(float(media_ms) / 1000, 3)
        if media_ms is not None
        else None,
        quantidade_por_tipo=_agrupar(
            sessao,
            RegistroTarefa.tipo,
            desde,
            ate,
            excluir_tarefa_id,
        ),
        quantidade_por_fila=_agrupar(
            sessao,
            RegistroTarefa.fila,
            desde,
            ate,
            excluir_tarefa_id,
        ),
    )

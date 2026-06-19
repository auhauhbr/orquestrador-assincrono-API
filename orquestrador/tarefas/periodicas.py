from datetime import UTC, datetime, timedelta

from orquestrador.banco.conexao import FabricaDeSessoes
from orquestrador.celery_aplicacao import aplicacao_celery
from orquestrador.servicos.metricas import calcular_metricas


@aplicacao_celery.task(bind=True, name="tarefas.relatorio_diario")
def relatorio_diario(self) -> dict:
    """Resume as execuções das últimas 24 horas e persiste o resultado."""
    ate = datetime.now(UTC)
    desde = ate - timedelta(hours=24)
    with FabricaDeSessoes() as sessao:
        metricas = calcular_metricas(
            sessao,
            desde,
            ate,
            excluir_tarefa_id=self.request.id,
        )
    return metricas.model_dump(mode="json")

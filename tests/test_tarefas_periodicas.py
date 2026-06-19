from orquestrador.celery_aplicacao import aplicacao_celery


def test_relatorio_diario_esta_agendado_na_fila_default():
    agenda = aplicacao_celery.conf.beat_schedule["gerar-relatorio-diario"]

    assert agenda["task"] == "tarefas.relatorio_diario"
    assert agenda["options"]["queue"] == "default"

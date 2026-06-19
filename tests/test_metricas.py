from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from orquestrador.banco.conexao import Base
from orquestrador.banco.modelos import RegistroTarefa
from orquestrador.servicos.metricas import calcular_metricas


def test_calcula_metricas_com_agregacoes_no_banco():
    motor = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(motor)
    agora = datetime.now(UTC)

    with Session(motor) as sessao:
        sessao.add_all(
            [
                RegistroTarefa(
                    tarefa_id="sucesso",
                    tipo="calculo_pesado",
                    fila="high",
                    parametros={},
                    estado="SUCCESS",
                    duracao_ms=1_000,
                    criado_em=agora,
                ),
                RegistroTarefa(
                    tarefa_id="falha",
                    tipo="enviar_email",
                    fila="low",
                    parametros={},
                    estado="FAILURE",
                    duracao_ms=3_000,
                    criado_em=agora,
                ),
                RegistroTarefa(
                    tarefa_id="pendente",
                    tipo="calculo_pesado",
                    fila="default",
                    parametros={},
                    estado="PENDING",
                    criado_em=agora,
                ),
            ]
        )
        sessao.commit()

        metricas = calcular_metricas(
            sessao,
            agora - timedelta(minutes=1),
            agora + timedelta(minutes=1),
        )

    assert metricas.total_tarefas == 3
    assert metricas.quantidade_por_estado == {
        "pendente": 1,
        "em_execucao": 0,
        "sucesso": 1,
        "falha": 1,
        "nova_tentativa": 0,
        "cancelada": 0,
    }
    assert metricas.taxa_sucesso_percentual == 50.0
    assert metricas.duracao_media_segundos == 2.0
    assert metricas.quantidade_por_tipo["calculo_pesado"] == 2

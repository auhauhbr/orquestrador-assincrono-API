from datetime import UTC, datetime

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from orquestrador.banco.conexao import Base
from orquestrador.banco.modelos import RegistroTarefa, RegistroTarefaMorta


def test_tarefa_morta_preserva_dados_da_tarefa_original():
    motor = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(motor)

    with Session(motor) as sessao:
        original = RegistroTarefa(
            tarefa_id="original-123",
            tipo="enviar_email",
            fila="high",
            parametros={"simular_falha": True},
            estado="FAILURE",
            erro="Falha simulada",
            foi_para_fila_morta=True,
        )
        morta = RegistroTarefaMorta(
            tarefa_original_id=original.tarefa_id,
            tipo=original.tipo,
            fila=original.fila,
            parametros=original.parametros,
            tentativas_realizadas=4,
            ultimo_erro=original.erro,
            falhou_em=datetime.now(UTC),
        )
        sessao.add_all([original, morta])
        sessao.commit()

        registro = sessao.scalar(select(RegistroTarefaMorta))

    assert registro is not None
    assert registro.tarefa_original_id == "original-123"
    assert registro.tentativas_realizadas == 4
    assert registro.parametros == {"simular_falha": True}

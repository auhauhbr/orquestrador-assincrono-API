import json
import logging

from orquestrador.observabilidade.logs import FormatadorJson


def test_formatador_gera_json_com_contexto_da_tarefa():
    registro = logging.LogRecord(
        name="teste",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="Tarefa iniciada",
        args=(),
        exc_info=None,
    )
    registro.tarefa_id = "tarefa-123"
    registro.estado = "iniciado"
    registro.fila = "high"

    resultado = json.loads(FormatadorJson().format(registro))

    assert resultado["mensagem"] == "Tarefa iniciada"
    assert resultado["tarefa_id"] == "tarefa-123"
    assert resultado["estado"] == "iniciado"
    assert resultado["fila"] == "high"

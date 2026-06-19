from datetime import UTC

import pytest

from orquestrador.tarefas.relatorios import interpretar_data


def test_interpreta_data_final_como_fim_do_dia():
    resultado = interpretar_data("2026-06-30", fim_do_dia=True)

    assert resultado.tzinfo == UTC
    assert resultado.hour == 23
    assert resultado.minute == 59


def test_rejeita_data_invalida():
    with pytest.raises(ValueError, match="AAAA-MM-DD"):
        interpretar_data("30/06/2026", fim_do_dia=False)

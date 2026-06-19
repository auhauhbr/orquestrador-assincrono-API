import base64
from io import BytesIO

from PIL import Image

from orquestrador.tarefas.imagens import _decodificar_imagem


def test_decodifica_data_url_de_imagem():
    memoria = BytesIO()
    Image.new("RGB", (10, 5), "blue").save(memoria, format="PNG")
    codificada = base64.b64encode(memoria.getvalue()).decode()

    resultado = _decodificar_imagem(f"data:image/png;base64,{codificada}")

    assert resultado.startswith(b"\x89PNG")


def test_rejeita_base64_invalido():
    try:
        _decodificar_imagem("isto-nao-e-base64")
    except ValueError as erro:
        assert "base64 válido" in str(erro)
    else:
        raise AssertionError("Base64 inválido deveria ser rejeitado")

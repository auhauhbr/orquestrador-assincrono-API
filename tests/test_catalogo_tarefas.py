import pytest

from orquestrador.servicos.catalogo_tarefas import criar_assinatura
from orquestrador.servicos.seguranca import mascarar_parametros, mascarar_resultado


def test_cria_assinatura_de_tarefa_conhecida():
    assinatura = criar_assinatura("calculo_pesado", {"limite": 10})

    assert assinatura.task == "tarefas.calculo_pesado"
    assert assinatura.kwargs == {"limite": 10}


def test_rejeita_tarefa_desconhecida():
    with pytest.raises(ValueError, match="Tipo de tarefa desconhecido"):
        criar_assinatura("nao_existe", {})


def test_mascara_imagem_base64_na_resposta():
    parametros = {"imagem_base64": "abc123", "largura_maxima": 300}

    seguros = mascarar_parametros("processar_imagem", parametros)

    assert seguros["imagem_base64"] == "<base64 omitido: 6 caracteres>"
    assert parametros["imagem_base64"] == "abc123"


def test_mascara_dados_do_email_na_resposta():
    parametros = {
        "destinatario": "pessoa@exemplo.com",
        "assunto": "Teste",
        "corpo": "Mensagem privada",
    }

    seguros = mascarar_parametros("enviar_email", parametros)

    assert seguros["destinatario"] == "pe***@exemplo.com"
    assert seguros["corpo"] == "<conteúdo omitido: 16 caracteres>"
    assert seguros["assunto"] == "Teste"


def test_mascara_resultado_historico_do_email():
    resultado = {
        "situacao": "enviado",
        "destinatario": "pessoa@exemplo.com",
        "corpo": "Conteúdo antigo",
    }

    seguro = mascarar_resultado("enviar_email", resultado)

    assert seguro["destinatario"] == "pe***@exemplo.com"
    assert "corpo" not in seguro

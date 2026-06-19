from types import SimpleNamespace

from orquestrador.tarefas import exemplos


def test_chave_resend_vazia_mantem_modo_simulado():
    assert exemplos._resend_configurado("") is False
    assert exemplos._resend_configurado("re_coloque_sua_chave_aqui") is False


def test_chave_resend_real_ativa_envio():
    assert exemplos._resend_configurado("re_chave_de_teste") is True


def test_envio_resend_usa_idempotencia_e_escapa_html(monkeypatch):
    chamada = {}

    def enviar(parametros, opcoes):
        chamada["parametros"] = parametros
        chamada["opcoes"] = opcoes
        return {"id": "email_123"}

    resend_falso = SimpleNamespace(
        api_key=None,
        Emails=SimpleNamespace(send=enviar),
    )
    monkeypatch.setattr(exemplos, "_carregar_resend", lambda: resend_falso)

    email_id = exemplos._enviar_com_resend(
        chave="re_teste",
        remetente="Orquestrador Assíncrono <onboarding@resend.dev>",
        destinatario="pessoa@exemplo.com",
        assunto="Teste",
        corpo="<script>alert('x')</script>",
        idempotencia="tarefa-email/123",
    )

    assert email_id == "email_123"
    assert "&lt;script&gt;" in chamada["parametros"]["html"]
    assert chamada["opcoes"]["idempotency_key"] == "tarefa-email/123"

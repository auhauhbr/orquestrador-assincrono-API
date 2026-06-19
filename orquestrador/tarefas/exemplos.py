import html
import importlib
import math
import random
import time

from celery.utils.log import get_task_logger

from orquestrador.celery_aplicacao import aplicacao_celery
from orquestrador.configuracao import obter_configuracoes
from orquestrador.servicos.seguranca import mascarar_email

logger = get_task_logger(__name__)


def _resend_configurado(chave: str) -> bool:
    chave = chave.strip()
    return chave.startswith("re_") and chave not in {
        "re_coloque_sua_chave_aqui",
        "re_yourkey",
    }


def _carregar_resend():
    try:
        return importlib.import_module("resend")
    except ModuleNotFoundError as erro:
        raise RuntimeError(
            "O SDK da Resend não está instalado; reconstrua os contêineres"
        ) from erro


def _enviar_com_resend(
    *,
    chave: str,
    remetente: str,
    destinatario: str,
    assunto: str,
    corpo: str,
    idempotencia: str,
) -> str:
    resend = _carregar_resend()
    resend.api_key = chave
    corpo_seguro = html.escape(corpo).replace("\n", "<br>")
    parametros = {
        "from": remetente,
        "to": [destinatario],
        "subject": assunto,
        "text": corpo,
        "html": f"<p>{corpo_seguro}</p>",
    }
    resposta = resend.Emails.send(
        parametros,
        {"idempotency_key": idempotencia},
    )
    email_id = resposta.get("id")
    if not email_id:
        raise RuntimeError("A Resend não retornou o identificador do e-mail")
    return email_id


@aplicacao_celery.task(
    bind=True,
    name="tarefas.enviar_email",
    max_retries=3,
)
def enviar_email(
    self,
    destinatario: str,
    assunto: str,
    corpo: str,
    simular_falha: bool = False,
) -> dict[str, str]:
    """Envia pela Resend quando configurada; caso contrário, simula o envio."""
    logger.info("Enviando e-mail para %s", mascarar_email(destinatario))
    configuracoes = obter_configuracoes()

    try:
        if simular_falha:
            raise ConnectionError("Falha simulada no provedor de e-mail")

        if not _resend_configurado(configuracoes.resend_api_key):
            logger.warning(
                "RESEND_API_KEY não configurada; utilizando envio simulado",
                extra={"modo_envio": "simulado"},
            )
            time.sleep(random.uniform(0.5, 1.5))
            return {
                "situacao": "simulado",
                "modo": "simulado",
                "destinatario": mascarar_email(destinatario),
                "assunto": assunto,
            }

        remetente = (
            f"{configuracoes.resend_remetente_nome} "
            f"<{configuracoes.resend_remetente_email}>"
        )
        email_id = _enviar_com_resend(
            chave=configuracoes.resend_api_key,
            remetente=remetente,
            destinatario=destinatario,
            assunto=assunto,
            corpo=corpo,
            idempotencia=f"tarefa-email/{self.request.id}",
        )
        return {
            "situacao": "enviado",
            "modo": "resend",
            "email_id": email_id,
            "destinatario": mascarar_email(destinatario),
            "assunto": assunto,
        }
    except Exception as erro:
        espera = min(2 ** (self.request.retries + 1), 30)
        logger.warning(
            "Falha no envio de e-mail; nova tentativa será agendada",
            extra={
                "provedor": "resend"
                if _resend_configurado(configuracoes.resend_api_key)
                else "simulado",
                "tentativa": self.request.retries + 1,
                "erro": str(erro),
            },
        )
        raise self.retry(exc=erro, countdown=espera) from erro


@aplicacao_celery.task(name="tarefas.calculo_pesado")
def calculo_pesado(limite: int = 100_000) -> dict[str, int | float]:
    """Executa um cálculo determinístico para demonstrar processamento paralelo."""
    if limite < 1 or limite > 5_000_000:
        raise ValueError("limite deve estar entre 1 e 5.000.000")

    acumulado = sum(math.sqrt(numero) for numero in range(1, limite + 1))
    return {"limite": limite, "resultado": round(acumulado, 4)}

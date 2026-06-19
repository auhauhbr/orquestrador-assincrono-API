from celery import Signature

from orquestrador.tarefas.exemplos import calculo_pesado, enviar_email
from orquestrador.tarefas.imagens import processar_imagem
from orquestrador.tarefas.relatorios import gerar_relatorio_csv

TAREFAS_DISPONIVEIS = {
    "enviar_email": enviar_email,
    "calculo_pesado": calculo_pesado,
    "processar_imagem": processar_imagem,
    "gerar_relatorio_csv": gerar_relatorio_csv,
}


def criar_assinatura(tipo: str, parametros: dict) -> Signature:
    tarefa = TAREFAS_DISPONIVEIS.get(tipo)
    if tarefa is None:
        tipos = ", ".join(sorted(TAREFAS_DISPONIVEIS))
        raise ValueError(f"Tipo de tarefa desconhecido. Disponíveis: {tipos}")
    return tarefa.s(**parametros)

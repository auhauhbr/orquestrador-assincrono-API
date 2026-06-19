import csv
from datetime import UTC, date, datetime, time
from pathlib import Path
from uuid import uuid4

from sqlalchemy import case, func, select

from orquestrador.banco.conexao import FabricaDeSessoes
from orquestrador.banco.modelos import RegistroTarefa
from orquestrador.celery_aplicacao import aplicacao_celery
from orquestrador.configuracao import obter_configuracoes

FILTROS_DISPONIVEIS = {"tarefas_por_dia", "falhas_por_tipo"}


def interpretar_data(valor: str, *, fim_do_dia: bool) -> datetime:
    try:
        if len(valor) == 10:
            data = date.fromisoformat(valor)
            horario = time.max if fim_do_dia else time.min
            return datetime.combine(data, horario, tzinfo=UTC)
        instante = datetime.fromisoformat(valor.replace("Z", "+00:00"))
        return instante.replace(tzinfo=instante.tzinfo or UTC).astimezone(UTC)
    except ValueError as erro:
        raise ValueError(
            "Use datas no formato AAAA-MM-DD ou data/hora ISO 8601"
        ) from erro


def _dados_tarefas_por_dia(
    desde: datetime,
    ate: datetime,
    tarefa_atual_id: str,
) -> tuple[list[str], list[tuple]]:
    dia = func.date(RegistroTarefa.criado_em)
    consulta = (
        select(
            dia.label("dia"),
            func.count(RegistroTarefa.id).label("total"),
            func.sum(case((RegistroTarefa.estado == "SUCCESS", 1), else_=0)),
            func.sum(case((RegistroTarefa.estado == "FAILURE", 1), else_=0)),
        )
        .where(
            RegistroTarefa.criado_em.between(desde, ate),
            RegistroTarefa.tarefa_id != tarefa_atual_id,
        )
        .group_by(dia)
        .order_by(dia)
    )
    with FabricaDeSessoes() as sessao:
        linhas = list(sessao.execute(consulta))
    return ["data", "total", "sucesso", "falha"], linhas


def _dados_falhas_por_tipo(
    desde: datetime,
    ate: datetime,
    tarefa_atual_id: str,
) -> tuple[list[str], list[tuple]]:
    consulta = (
        select(
            RegistroTarefa.tipo,
            func.count(RegistroTarefa.id).label("quantidade_falhas"),
        )
        .where(
            RegistroTarefa.criado_em.between(desde, ate),
            RegistroTarefa.estado == "FAILURE",
            RegistroTarefa.tarefa_id != tarefa_atual_id,
        )
        .group_by(RegistroTarefa.tipo)
        .order_by(func.count(RegistroTarefa.id).desc(), RegistroTarefa.tipo)
    )
    with FabricaDeSessoes() as sessao:
        linhas = list(sessao.execute(consulta))
    return ["tipo_tarefa", "quantidade_falhas"], linhas


@aplicacao_celery.task(bind=True, name="tarefas.gerar_relatorio_csv")
def gerar_relatorio_csv(
    self,
    desde: str,
    ate: str,
    filtro: str,
) -> dict[str, str | int]:
    """Gera um CSV agregado a partir do histórico persistido no PostgreSQL."""
    if filtro not in FILTROS_DISPONIVEIS:
        disponiveis = ", ".join(sorted(FILTROS_DISPONIVEIS))
        raise ValueError(f"Filtro desconhecido. Disponíveis: {disponiveis}")

    inicio = interpretar_data(desde, fim_do_dia=False)
    fim = interpretar_data(ate, fim_do_dia=True)
    if inicio > fim:
        raise ValueError("'desde' não pode ser posterior a 'ate'")

    if filtro == "tarefas_por_dia":
        cabecalho, linhas = _dados_tarefas_por_dia(inicio, fim, self.request.id)
    else:
        cabecalho, linhas = _dados_falhas_por_tipo(inicio, fim, self.request.id)

    diretorio = Path(obter_configuracoes().diretorio_relatorios)
    diretorio.mkdir(parents=True, exist_ok=True)
    caminho = diretorio / f"{filtro}-{uuid4()}.csv"
    try:
        with caminho.open("w", encoding="utf-8-sig", newline="") as arquivo:
            escritor = csv.writer(arquivo, delimiter=";")
            escritor.writerow(cabecalho)
            escritor.writerows(linhas)
    except OSError as erro:
        raise RuntimeError("Não foi possível salvar o relatório CSV") from erro

    return {
        "caminho": str(caminho),
        "nome_arquivo": caminho.name,
        "filtro": filtro,
        "desde": inicio.isoformat(),
        "ate": fim.isoformat(),
        "quantidade_linhas": len(linhas),
    }

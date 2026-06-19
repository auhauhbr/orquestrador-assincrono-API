from pathlib import Path
from typing import Annotated

from celery.result import AsyncResult
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from orquestrador.banco.conexao import obter_sessao
from orquestrador.banco.modelos import RegistroTarefa
from orquestrador.celery_aplicacao import aplicacao_celery
from orquestrador.configuracao import obter_configuracoes
from orquestrador.esquemas.tarefa import (
    CriarTarefa,
    DetalhesTarefa,
    ListaTarefas,
    TarefaCriada,
)
from orquestrador.servicos.enfileiramento import enfileirar_tarefa
from orquestrador.servicos.seguranca import mascarar_parametros, mascarar_resultado

roteador = APIRouter(prefix="/tarefas", tags=["tarefas"])
SessaoBanco = Annotated[Session, Depends(obter_sessao)]


def _sincronizar_estado(registro: RegistroTarefa, sessao: Session) -> None:
    resultado = AsyncResult(registro.tarefa_id, app=aplicacao_celery)
    if registro.estado == resultado.state:
        return

    registro.estado = resultado.state
    if resultado.successful():
        registro.resultado = resultado.result
        registro.erro = None
    elif resultado.failed():
        registro.erro = str(resultado.result)
    sessao.commit()
    sessao.refresh(registro)


def _para_detalhes(registro: RegistroTarefa) -> DetalhesTarefa:
    return DetalhesTarefa(
        tarefa_id=registro.tarefa_id,
        tipo=registro.tipo,
        fila=registro.fila,
        estado=registro.estado,
        parametros=mascarar_parametros(registro.tipo, registro.parametros),
        resultado=mascarar_resultado(registro.tipo, registro.resultado),
        erro=registro.erro,
        foi_para_fila_morta=registro.foi_para_fila_morta,
        iniciado_em=registro.iniciado_em,
        finalizado_em=registro.finalizado_em,
        duracao_ms=registro.duracao_ms,
        criado_em=registro.criado_em,
        atualizado_em=registro.atualizado_em,
    )


@roteador.post(
    "",
    response_model=TarefaCriada,
    status_code=status.HTTP_202_ACCEPTED,
)
def criar_tarefa(dados: CriarTarefa, sessao: SessaoBanco) -> TarefaCriada:
    try:
        registro = enfileirar_tarefa(
            sessao,
            tipo=dados.tipo,
            parametros=dados.parametros,
            fila=dados.fila,
        )
    except ValueError as erro:
        raise HTTPException(status_code=400, detail=str(erro)) from erro
    return TarefaCriada(tarefa_id=registro.tarefa_id, estado="PENDING")


@roteador.get("/{tarefa_id}/download")
def baixar_resultado(tarefa_id: str, sessao: SessaoBanco) -> FileResponse:
    registro = sessao.scalar(
        select(RegistroTarefa).where(RegistroTarefa.tarefa_id == tarefa_id)
    )
    if registro is None:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")
    if registro.tipo != "gerar_relatorio_csv":
        raise HTTPException(
            status_code=409,
            detail="Esta tarefa não gera um arquivo CSV para download",
        )
    if registro.estado != "SUCCESS" or not isinstance(registro.resultado, dict):
        raise HTTPException(
            status_code=409,
            detail="O relatório ainda não foi concluído com sucesso",
        )

    diretorio = Path(obter_configuracoes().diretorio_relatorios).resolve()
    caminho_informado = registro.resultado.get("caminho")
    if not isinstance(caminho_informado, str):
        raise HTTPException(status_code=404, detail="Arquivo do relatório não encontrado")
    caminho = Path(caminho_informado).resolve()
    if not caminho.is_relative_to(diretorio) or caminho.suffix.lower() != ".csv":
        raise HTTPException(status_code=403, detail="Caminho de relatório inválido")
    if not caminho.is_file():
        raise HTTPException(status_code=404, detail="Arquivo do relatório não encontrado")

    return FileResponse(
        caminho,
        media_type="text/csv; charset=utf-8",
        filename=caminho.name,
    )


@roteador.get("/{tarefa_id}", response_model=DetalhesTarefa)
def consultar_tarefa(tarefa_id: str, sessao: SessaoBanco) -> DetalhesTarefa:
    registro = sessao.scalar(
        select(RegistroTarefa).where(RegistroTarefa.tarefa_id == tarefa_id)
    )
    if registro is None:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")

    _sincronizar_estado(registro, sessao)
    return _para_detalhes(registro)


@roteador.get("", response_model=ListaTarefas)
def listar_tarefas(
    sessao: SessaoBanco,
    estado: str | None = None,
    tipo: str | None = None,
    limite: Annotated[int, Query(ge=1, le=200)] = 50,
) -> ListaTarefas:
    filtros = []
    if estado:
        filtros.append(RegistroTarefa.estado == estado.upper())
    if tipo:
        filtros.append(RegistroTarefa.tipo == tipo)

    consulta = (
        select(RegistroTarefa)
        .where(*filtros)
        .order_by(RegistroTarefa.criado_em.desc())
        .limit(limite)
    )
    registros = list(sessao.scalars(consulta))
    total = sessao.scalar(select(func.count()).select_from(RegistroTarefa).where(*filtros))
    return ListaTarefas(
        itens=[_para_detalhes(registro) for registro in registros],
        total=total or 0,
    )


@roteador.delete("/{tarefa_id}", response_model=TarefaCriada)
def cancelar_tarefa(tarefa_id: str, sessao: SessaoBanco) -> TarefaCriada:
    registro = sessao.scalar(
        select(RegistroTarefa).where(RegistroTarefa.tarefa_id == tarefa_id)
    )
    if registro is None:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")
    if registro.estado in {"SUCCESS", "FAILURE", "REVOKED"}:
        raise HTTPException(
            status_code=409,
            detail=f"A tarefa já está no estado final {registro.estado}",
        )

    aplicacao_celery.control.revoke(tarefa_id, terminate=False)
    registro.estado = "REVOKED"
    sessao.commit()
    return TarefaCriada(tarefa_id=tarefa_id, estado="REVOKED")

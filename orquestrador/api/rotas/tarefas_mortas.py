from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from orquestrador.banco.conexao import obter_sessao
from orquestrador.banco.modelos import RegistroTarefaMorta
from orquestrador.esquemas.tarefa_morta import (
    DetalhesTarefaMorta,
    ListaTarefasMortas,
    TarefaReprocessada,
)
from orquestrador.servicos.enfileiramento import enfileirar_tarefa
from orquestrador.servicos.seguranca import mascarar_parametros

roteador = APIRouter(prefix="/tarefas-mortas", tags=["tarefas mortas"])
SessaoBanco = Annotated[Session, Depends(obter_sessao)]


def _para_detalhes(registro: RegistroTarefaMorta) -> DetalhesTarefaMorta:
    return DetalhesTarefaMorta(
        id=registro.id,
        tarefa_original_id=registro.tarefa_original_id,
        tipo=registro.tipo,
        fila=registro.fila,
        parametros=mascarar_parametros(registro.tipo, registro.parametros),
        tentativas_realizadas=registro.tentativas_realizadas,
        ultimo_erro=registro.ultimo_erro,
        falhou_em=registro.falhou_em,
        reprocessada_em=registro.reprocessada_em,
        nova_tarefa_id=registro.nova_tarefa_id,
    )


@roteador.get("", response_model=ListaTarefasMortas)
def listar_tarefas_mortas(
    sessao: SessaoBanco,
    pagina: Annotated[int, Query(ge=1)] = 1,
    por_pagina: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ListaTarefasMortas:
    total = sessao.scalar(
        select(func.count()).select_from(RegistroTarefaMorta)
    ) or 0
    consulta = (
        select(RegistroTarefaMorta)
        .order_by(RegistroTarefaMorta.falhou_em.desc())
        .offset((pagina - 1) * por_pagina)
        .limit(por_pagina)
    )
    registros = list(sessao.scalars(consulta))
    return ListaTarefasMortas(
        itens=[_para_detalhes(registro) for registro in registros],
        total=total,
        pagina=pagina,
        por_pagina=por_pagina,
    )


@roteador.post(
    "/{tarefa_morta_id}/reprocessar",
    response_model=TarefaReprocessada,
    status_code=status.HTTP_202_ACCEPTED,
)
def reprocessar_tarefa_morta(
    tarefa_morta_id: int,
    sessao: SessaoBanco,
) -> TarefaReprocessada:
    tarefa_morta = sessao.get(RegistroTarefaMorta, tarefa_morta_id)
    if tarefa_morta is None:
        raise HTTPException(status_code=404, detail="Tarefa morta não encontrada")

    nova_tarefa = enfileirar_tarefa(
        sessao,
        tipo=tarefa_morta.tipo,
        parametros=tarefa_morta.parametros,
        fila=tarefa_morta.fila,
    )
    tarefa_morta.reprocessada_em = datetime.now(UTC)
    tarefa_morta.nova_tarefa_id = nova_tarefa.tarefa_id
    sessao.commit()

    return TarefaReprocessada(
        tarefa_morta_id=tarefa_morta.id,
        tarefa_original_id=tarefa_morta.tarefa_original_id,
        nova_tarefa_id=nova_tarefa.tarefa_id,
        estado="PENDING",
    )

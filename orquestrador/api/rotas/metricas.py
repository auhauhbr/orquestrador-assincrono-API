from datetime import UTC, date, datetime, time, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from orquestrador.banco.conexao import obter_sessao
from orquestrador.esquemas.metricas import ResumoMetricas
from orquestrador.servicos.metricas import calcular_metricas

roteador = APIRouter(prefix="/metricas", tags=["métricas"])
SessaoBanco = Annotated[Session, Depends(obter_sessao)]


def _interpretar_data(valor: str, *, fim_do_dia: bool) -> datetime:
    try:
        if len(valor) == 10:
            data = date.fromisoformat(valor)
            horario = time.max if fim_do_dia else time.min
            return datetime.combine(data, horario, tzinfo=UTC)
        instante = datetime.fromisoformat(valor.replace("Z", "+00:00"))
        return instante.replace(tzinfo=instante.tzinfo or UTC).astimezone(UTC)
    except ValueError as erro:
        raise HTTPException(
            status_code=422,
            detail="Use datas no formato AAAA-MM-DD ou data/hora ISO 8601.",
        ) from erro


@roteador.get("", response_model=ResumoMetricas)
def consultar_metricas(
    sessao: SessaoBanco,
    desde: Annotated[str | None, Query(examples=["2026-06-01"])] = None,
    ate: Annotated[str | None, Query(examples=["2026-06-30"])] = None,
) -> ResumoMetricas:
    agora = datetime.now(UTC)
    fim = _interpretar_data(ate, fim_do_dia=True) if ate else agora
    inicio = (
        _interpretar_data(desde, fim_do_dia=False)
        if desde
        else fim - timedelta(hours=24)
    )
    if inicio > fim:
        raise HTTPException(
            status_code=422,
            detail="O parâmetro 'desde' não pode ser posterior a 'ate'.",
        )
    return calcular_metricas(sessao, inicio, fim)

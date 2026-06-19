from datetime import datetime
from typing import Any

from pydantic import BaseModel


class DetalhesTarefaMorta(BaseModel):
    id: int
    tarefa_original_id: str
    tipo: str
    fila: str
    parametros: dict[str, Any]
    tentativas_realizadas: int
    ultimo_erro: str
    falhou_em: datetime
    reprocessada_em: datetime | None
    nova_tarefa_id: str | None


class ListaTarefasMortas(BaseModel):
    itens: list[DetalhesTarefaMorta]
    total: int
    pagina: int
    por_pagina: int


class TarefaReprocessada(BaseModel):
    tarefa_morta_id: int
    tarefa_original_id: str
    nova_tarefa_id: str
    estado: str

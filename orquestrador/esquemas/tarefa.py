from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

Fila = Literal["high", "default", "low"]


class CriarTarefa(BaseModel):
    tipo: str = Field(examples=["enviar_email"])
    parametros: dict[str, Any] = Field(default_factory=dict)
    fila: Fila = "default"

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "tipo": "enviar_email",
                "parametros": {
                    "destinatario": "pessoa@exemplo.com",
                    "assunto": "Teste",
                    "corpo": "Olá!",
                },
                "fila": "high",
            }
        }
    )


class TarefaCriada(BaseModel):
    tarefa_id: str
    estado: str


class DetalhesTarefa(BaseModel):
    tarefa_id: str
    tipo: str
    fila: str
    estado: str
    parametros: dict[str, Any]
    resultado: Any | None = None
    erro: str | None = None
    foi_para_fila_morta: bool = False
    iniciado_em: datetime | None = None
    finalizado_em: datetime | None = None
    duracao_ms: float | None = None
    criado_em: datetime
    atualizado_em: datetime


class ListaTarefas(BaseModel):
    itens: list[DetalhesTarefa]
    total: int

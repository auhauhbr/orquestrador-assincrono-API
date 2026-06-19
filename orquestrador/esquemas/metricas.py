from datetime import datetime

from pydantic import BaseModel


class PeriodoMetricas(BaseModel):
    desde: datetime
    ate: datetime


class ResumoMetricas(BaseModel):
    periodo: PeriodoMetricas
    total_tarefas: int
    quantidade_por_estado: dict[str, int]
    taxa_sucesso_percentual: float
    duracao_media_segundos: float | None
    quantidade_por_tipo: dict[str, int]
    quantidade_por_fila: dict[str, int]

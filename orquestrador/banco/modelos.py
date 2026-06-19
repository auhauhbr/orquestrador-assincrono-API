from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from orquestrador.banco.conexao import Base


class RegistroTarefa(Base):
    __tablename__ = "tarefas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tarefa_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    tipo: Mapped[str] = mapped_column(String(100), index=True)
    fila: Mapped[str] = mapped_column(String(20), index=True)
    parametros: Mapped[dict[str, Any]] = mapped_column(JSON)
    estado: Mapped[str] = mapped_column(String(20), index=True, default="PENDING")
    resultado: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    erro: Mapped[str | None] = mapped_column(Text, nullable=True)
    foi_para_fila_morta: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        index=True,
    )
    iniciado_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    finalizado_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    duracao_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class RegistroTarefaMorta(Base):
    __tablename__ = "tarefas_mortas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tarefa_original_id: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
    )
    tipo: Mapped[str] = mapped_column(String(100), index=True)
    fila: Mapped[str] = mapped_column(String(20), index=True)
    parametros: Mapped[dict[str, Any]] = mapped_column(JSON)
    tentativas_realizadas: Mapped[int] = mapped_column(Integer)
    ultimo_erro: Mapped[str] = mapped_column(Text)
    falhou_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )
    reprocessada_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    nova_tarefa_id: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

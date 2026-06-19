from sqlalchemy import text

from orquestrador.banco.conexao import Base, motor


def preparar_banco() -> None:
    """Cria tabelas e aplica as pequenas migrações desta fase do projeto."""
    Base.metadata.create_all(bind=motor)
    comandos = (
        "ALTER TABLE tarefas ADD COLUMN IF NOT EXISTS iniciado_em TIMESTAMPTZ",
        "ALTER TABLE tarefas ADD COLUMN IF NOT EXISTS finalizado_em TIMESTAMPTZ",
        "ALTER TABLE tarefas ADD COLUMN IF NOT EXISTS duracao_ms DOUBLE PRECISION",
        (
            "ALTER TABLE tarefas ADD COLUMN IF NOT EXISTS "
            "foi_para_fila_morta BOOLEAN NOT NULL DEFAULT FALSE"
        ),
    )
    with motor.begin() as conexao:
        for comando in comandos:
            conexao.execute(text(comando))

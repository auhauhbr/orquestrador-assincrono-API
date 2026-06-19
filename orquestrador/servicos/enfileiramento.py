from uuid import uuid4

from sqlalchemy.orm import Session

from orquestrador.banco.modelos import RegistroTarefa
from orquestrador.servicos.catalogo_tarefas import criar_assinatura
from orquestrador.servicos.seguranca import mascarar_parametros


def enfileirar_tarefa(
    sessao: Session,
    *,
    tipo: str,
    parametros: dict,
    fila: str,
) -> RegistroTarefa:
    assinatura = criar_assinatura(tipo, parametros)
    tarefa_id = str(uuid4())
    registro = RegistroTarefa(
        tarefa_id=tarefa_id,
        tipo=tipo,
        fila=fila,
        parametros=parametros,
        estado="PENDING",
    )
    sessao.add(registro)
    sessao.commit()

    try:
        representacao_parametros = repr(mascarar_parametros(tipo, parametros))
        assinatura.apply_async(
            task_id=tarefa_id,
            queue=fila,
            kwargsrepr=representacao_parametros,
        )
    except Exception:
        sessao.delete(registro)
        sessao.commit()
        raise

    return registro

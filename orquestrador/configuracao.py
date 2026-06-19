from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Configuracoes(BaseSettings):
    ambiente: str = "desenvolvimento"
    nivel_log: str = "INFO"
    caminho_log: str = "/app/logs/tarefas.jsonl"
    diretorio_imagens: str = "/app/dados/imagens_processadas"
    diretorio_relatorios: str = "/app/dados/relatorios"
    agendamento_teste: bool = False
    resend_api_key: str = ""
    resend_remetente_email: str = "onboarding@resend.dev"
    resend_remetente_nome: str = "Orquestrador Assíncrono"
    redis_url: str = "redis://localhost:6379/0"
    database_url: str = (
        "postgresql+psycopg://orquestrador:troque_esta_senha"
        "@localhost:5432/orquestrador"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def obter_configuracoes() -> Configuracoes:
    return Configuracoes()

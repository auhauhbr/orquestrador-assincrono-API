# Orquestrador Assíncrono

Central de tarefas distribuídas construída com FastAPI, Celery, Redis,
PostgreSQL e Docker.

O Orquestrador Assíncrono funciona como um gerenciador de tarefas: recebe trabalhos
por uma API HTTP, registra cada solicitação no banco, envia a tarefa para uma fila
e devolve um identificador imediatamente. A execução acontece em segundo plano por
trabalhadores Celery separados por prioridade.

<p align="center">
  <img src="docs/imagens/tecnologias/python.svg" alt="Python" width="90">
  &nbsp;&nbsp;
  <img src="docs/imagens/tecnologias/fastapi.svg" alt="FastAPI" width="100">
  &nbsp;&nbsp;
  <img src="docs/imagens/tecnologias/redis.svg" alt="Redis" width="90">
  &nbsp;&nbsp;
  <img src="docs/imagens/tecnologias/postgresql.svg" alt="PostgreSQL" width="100">
  &nbsp;&nbsp;
  <img src="docs/imagens/tecnologias/docker.svg" alt="Docker" width="100">
</p>

## Sumário

1. [Arquitetura](#arquitetura)
2. [Funcionalidades](#funcionalidades)
3. [Tecnologias](#tecnologias)
4. [Visão do sistema](#visão-do-sistema)
5. [Como executar](#como-executar)
6. [Como usar](#como-usar)
7. [Tarefas disponíveis](#tarefas-disponíveis)
8. [Monitoramento e métricas](#monitoramento-e-métricas)
9. [Testes](#testes)
10. [Estrutura do projeto](#estrutura-do-projeto)

## Arquitetura

<p align="center">
  <img
    src="docs/imagens/arquitetura-orquestrador-assincrono.jpg"
    alt="Diagrama completo da arquitetura do Orquestrador Assíncrono"
    width="100%"
  >
</p>

O diagrama apresenta o fluxo completo entre os clientes HTTP, o servidor
Uvicorn, a API FastAPI, as filas no Redis, os workers Celery separados por
prioridade, o PostgreSQL, o Celery Beat, o Flower e o serviço de e-mail Resend.

Representação simplificada:

```text
                         +-------------------+
                         |    Cliente HTTP   |
                         | Swagger, curl, app|
                         +---------+---------+
                                   |
                                   v
                         +-------------------+
                         |      FastAPI      |
                         | valida e registra |
                         +----+---------+----+
                              |         |
                              v         v
                    +------------+   +------------+
                    | PostgreSQL |   |   Redis    |
                    | histórico  |   | filas e    |
                    | e métricas |   | resultados |
                    +------------+   +------+-----+
                                            |
                     +----------------------+----------------------+
                     |                      |                      |
                     v                      v                      v
            +----------------+    +-------------------+    +----------------+
            | worker high    |    | workers default   |    | worker low     |
            | fila high      |    | fila default      |    | fila low       |
            +----------------+    +-------------------+    +----------------+

            +----------------+                       +----------------+
            |  Celery Beat   |                       |     Flower     |
            | agendamentos   |                       | monitoramento  |
            +----------------+                       +----------------+
```

Fluxo de uma tarefa:

```text
POST /api/tarefas
        |
        v
Registro PENDING no PostgreSQL
        |
        v
Mensagem publicada no Redis
        |
        v
Trabalhador executa a tarefa
        |
        +---- sucesso ----> SUCCESS e resultado persistido
        |
        `---- falha ------> retry ----> FAILURE e fila morta
```

## Funcionalidades

- criação e acompanhamento de tarefas assíncronas;
- filas `high`, `default` e `low`;
- trabalhadores dedicados por prioridade;
- processamento paralelo;
- retry com backoff exponencial;
- fila de tarefas mortas e reprocessamento;
- histórico completo no PostgreSQL;
- métricas agregadas;
- logs estruturados em JSON;
- monitoramento pelo Flower;
- tarefas periódicas com Celery Beat;
- envio real de e-mail com Resend;
- redimensionamento de imagens;
- geração e download de relatórios CSV;
- cancelamento de tarefas pendentes.

## Tecnologias

| Tecnologia | Uso |
|---|---|
| FastAPI | API HTTP e Swagger |
| Celery | execução assíncrona |
| Redis | broker e resultados temporários |
| PostgreSQL | histórico, métricas e tarefas mortas |
| SQLAlchemy | acesso ao banco |
| Flower | monitoramento dos trabalhadores |
| Celery Beat | tarefas agendadas |
| Pillow | processamento de imagens |
| Resend | envio de e-mails |
| Docker Compose | execução do ambiente |
| Pytest e Ruff | testes e qualidade |

## Visão do sistema

<table>
  <tr>
    <td width="50%" align="center">
      <img src="docs/imagens/swagger-api.png" alt="Documentação interativa da API" width="100%">
      <br>
      <sub>API REST documentada e testável pelo Swagger</sub>
    </td>
    <td width="50%" align="center">
      <img src="docs/imagens/flower-monitoramento.png" alt="Monitoramento dos trabalhadores no Flower" width="100%">
      <br>
      <sub>Trabalhadores e filas acompanhados pelo Flower</sub>
    </td>
  </tr>
</table>

## Como executar

### Pré-requisitos

- Docker Desktop;
- Docker Compose;
- portas `8000` e `5555` disponíveis.

### Configuração

Crie o arquivo `.env`:

```powershell
Copy-Item .env.example .env
```

Troque as senhas de exemplo no novo arquivo.

Para habilitar e-mail real, configure:

```env
RESEND_API_KEY=
RESEND_REMETENTE_EMAIL=onboarding@resend.dev
RESEND_REMETENTE_NOME=Orquestrador Assíncrono
```

O arquivo `.env` contém segredos e não deve ser enviado ao GitHub.

### Iniciar

```powershell
docker compose up -d --build
```

### Acessos

| Serviço | Endereço |
|---|---|
| Swagger | http://localhost:8000/docs |
| Saúde da API | http://localhost:8000/saude |
| Flower | http://localhost:5555 |

### Parar

```powershell
docker compose down
```

Os dados permanecem nos volumes Docker.

## Como usar

### Criar uma tarefa

Abra `POST /api/tarefas` no Swagger ou envie:

```json
{
  "tipo": "calculo_pesado",
  "parametros": {
    "limite": 500000
  },
  "fila": "default"
}
```

Resposta:

```json
{
  "tarefa_id": "0f56f8aa-4cf8-4cf4-bd56-76e2e771cc4d",
  "estado": "PENDING"
}
```

### Consultar o resultado

```http
GET /api/tarefas/{tarefa_id}
```

Estados possíveis:

| Estado | Significado |
|---|---|
| `PENDING` | aguardando execução |
| `STARTED` | execução iniciada |
| `RETRY` | será executada novamente |
| `SUCCESS` | concluída |
| `FAILURE` | falhou definitivamente |
| `REVOKED` | cancelada |

### Outros endpoints

```text
GET    /api/tarefas
GET    /api/tarefas/{tarefa_id}
DELETE /api/tarefas/{tarefa_id}

GET    /api/metricas

GET    /api/tarefas-mortas
POST   /api/tarefas-mortas/{id}/reprocessar

GET    /api/tarefas/{tarefa_id}/download
```

## Tarefas disponíveis

### Cálculo pesado

```json
{
  "tipo": "calculo_pesado",
  "parametros": {
    "limite": 1000000
  },
  "fila": "default"
}
```

### Envio de e-mail

```json
{
  "tipo": "enviar_email",
  "parametros": {
    "destinatario": "seu-email@exemplo.com",
    "assunto": "Teste do Orquestrador Assíncrono",
    "corpo": "Mensagem enviada por uma tarefa Celery."
  },
  "fila": "high"
}
```

Sem uma chave da Resend, a tarefa funciona em modo simulado.

### Processamento de imagem

```json
{
  "tipo": "processar_imagem",
  "parametros": {
    "imagem_base64": "COLE_O_BASE64_AQUI",
    "largura_maxima": 800
  },
  "fila": "default"
}
```

Aceita PNG, JPEG e WebP. A proporção é preservada e o arquivo final é armazenado
em um volume Docker.

### Relatório CSV

```json
{
  "tipo": "gerar_relatorio_csv",
  "parametros": {
    "desde": "2026-06-01",
    "ate": "2026-06-30",
    "filtro": "tarefas_por_dia"
  },
  "fila": "default"
}
```

Filtros disponíveis:

- `tarefas_por_dia`;
- `falhas_por_tipo`.

Após a conclusão:

```http
GET /api/tarefas/{tarefa_id}/download
```

### Relatório diário

O Celery Beat executa `relatorio_diario` todos os dias às 08:00 no fuso
`America/Recife`.

## Monitoramento e métricas

O Flower mostra trabalhadores, tarefas, filas, duração e falhas:

```text
http://localhost:5555
```

As métricas das últimas 24 horas estão disponíveis em:

```http
GET /api/metricas
```

Também é possível informar um período:

```http
GET /api/metricas?desde=2026-06-01&ate=2026-06-30
```

Para acompanhar os logs:

```powershell
docker compose logs -f
```

## Testes

```powershell
docker compose --profile testes run --rm --build testes
```

Análise estática e testes:

```powershell
docker compose --profile testes run --rm --build testes `
  sh -c "ruff check orquestrador tests && python -m pytest -q"
```

Estado atual:

```text
Ruff: aprovado
Pytest: 16 testes aprovados
```

## Estrutura do projeto

```text
processador-async/
|
|-- docker-compose.yml
|-- Dockerfile
|-- .env.example
|-- requirements.txt
|
|-- orquestrador/
|   |-- api/
|   |   `-- rotas/
|   |-- banco/
|   |-- esquemas/
|   |-- observabilidade/
|   |-- servicos/
|   |-- tarefas/
|   |-- celery_aplicacao.py
|   `-- configuracao.py
|
`-- tests/
```

O projeto foi preparado para execução local. A API e o Flower são publicados
somente em `127.0.0.1`, e Redis e PostgreSQL permanecem na rede interna do Docker.

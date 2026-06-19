FROM python:3.12-slim

ARG INSTALAR_DEPENDENCIAS_DESENVOLVIMENTO=false

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    && if [ "$INSTALAR_DEPENDENCIAS_DESENVOLVIMENTO" = "true" ]; then \
         pip install --no-cache-dir -r requirements-dev.txt; \
       fi

COPY . .

RUN mkdir -p /app/logs /app/dados/imagens_processadas /app/dados/relatorios \
    && useradd --create-home --shell /usr/sbin/nologin aplicacao \
    && chown -R aplicacao:aplicacao /app

USER aplicacao

CMD ["uvicorn", "orquestrador.api.principal:aplicacao", "--host", "0.0.0.0", "--port", "8000"]

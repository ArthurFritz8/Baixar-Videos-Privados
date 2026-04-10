# Baixar Videos Privados

Fundacao tecnica em Python para um fluxo de download autorizado com arquitetura modular.

## Aviso de Uso

Este projeto deve ser usado apenas para conteudos com autorizacao legitima do titular e em conformidade com os termos da plataforma.

## Stack

- Python 3.11+
- FastAPI
- Pydantic

## Executar Localmente

1. Criar ambiente virtual.
2. Instalar dependencias: `pip install -e .[dev]`
3. Iniciar API: `uvicorn src.main:app --reload`

## Endpoint Base

- `POST /api/v1/downloads`
- `GET /api/v1/downloads/{download_id}`

## Fluxo Assincrono

1. O `POST /downloads` valida autorizacao e enfileira um job.
2. A resposta retorna `download_id` e `queue_status`.
3. O worker in-process processa o job com retry exponencial.
4. O cliente consulta `GET /downloads/{download_id}` para acompanhar o status.

## Mensagens Publicas

- Falha operacional para frontend: `Nao foi possivel baixar o video.`

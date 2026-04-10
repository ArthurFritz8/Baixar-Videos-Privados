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

### Atalho Windows (.bat)

- Executar: `start_api.bat`
- Validar ambiente sem iniciar servidor: `start_api.bat --check`

## Endpoint Base

- `POST /api/v1/downloads`
- `GET /api/v1/downloads/{download_id}`
- `POST /api/v1/downloads/{download_id}/cancel`

## Fluxo Assincrono

1. O `POST /downloads` valida autorizacao e enfileira um job.
2. A resposta retorna `download_id` e `queue_status`.
3. O worker in-process processa o job com retry exponencial.
4. O cliente consulta `GET /downloads/{download_id}` para acompanhar o status.
5. O endpoint `POST /downloads/{download_id}/cancel` suporta cancelamento cooperativo para jobs em `queued` e `processing`.

## Backend de Fila

- Padrao: `in_process` (custo zero, sem dependencia externa).
- Opcional: `redis` (open-source, configurado por variaveis de ambiente).
- Fallback automatico: se Redis nao estiver disponivel, o sistema volta para `in_process`.

## Mensagens Publicas

- Falha operacional para frontend: `Nao foi possivel baixar o video.`

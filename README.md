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
- Executar testes: `run_tests.bat`
- Executar testes com filtro: `run_tests.bat -k cancel -q`
- Validar ambiente de testes sem executar suite: `run_tests.bat --check`

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

## Download Real por URL Autorizada

- O backend suporta download real quando `video_reference` recebe uma URL HTTP/HTTPS autorizada (ex.: link assinado obtido pelo proprio usuario no provedor).
- O arquivo e salvo localmente no diretorio configurado por `DOWNLOAD_OUTPUT_DIR`.
- Opcionalmente, limite hosts permitidos com `ALLOWED_SOURCE_HOSTS` (lista separada por virgula).

Exemplo de payload:

```json
{
	"provider": "panda_video",
	"video_reference": "https://seu-link-autorizado.exemplo/video.mp4",
	"requester_id": "user-123",
	"download_id": "dl-real-001",
	"authorization": {
		"session_proof": "abcdefgh",
		"entitlement_proof": "ijklmnop"
	},
	"prefer_cached_authorization": true
}
```

## Mensagens Publicas

- Falha operacional para frontend: `Nao foi possivel baixar o video.`

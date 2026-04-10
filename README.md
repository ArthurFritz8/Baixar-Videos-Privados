# Baixar Videos Privados

API Python para download autorizado, com arquitetura modular, processamento assincrono e foco em operacao local de baixo custo.

## Aviso de Uso

Use somente para conteudos com autorizacao legitima do titular e em conformidade com os termos da plataforma.

## Stack

- Python 3.11+
- FastAPI
- Pydantic
- SQLite (padrao para estado de jobs)
- Redis (opcional para fila)

## Plataformas Aceitas

- `panda_video`
- `hotmart`
- `youtube`
- `instagram`
- `tiktok`
- `facebook`
- `x`
- `vimeo`

## Executar Localmente

1. Criar ambiente virtual.
2. Instalar dependencias: `pip install -e .[dev]`
3. Para links sociais, instalar extractor opcional: `pip install -e .[extractor]`
4. Copiar `.env.example` para `.env` e ajustar variaveis.
5. Iniciar API: `uvicorn src.main:app --reload`

### Atalhos Windows (.bat)

- Executar API: `start_api.bat`
- Validar ambiente sem iniciar servidor: `start_api.bat --check`
- Executar testes: `run_tests.bat`
- Executar testes com filtro: `run_tests.bat -k cancel -q`
- Validar ambiente de testes sem executar suite: `run_tests.bat --check`
- Pipeline local (testes + smoke + abrir docs): `publish_local.bat`
- Download por link via CMD: `download_link.bat "URL_DO_VIDEO" [provider]`

### Baixar por CMD (1 comando)

1. Inicie a API: `start_api.bat`
2. Em outro terminal, execute: `download_link.bat "https://www.youtube.com/watch?v=..."`
3. O script envia para API, acompanha status e baixa o arquivo final no diretorio atual.

Observacao:
- Tambem ha suporte via extensao para Chrome/Edge (aba ativa).

### Integracao Chrome/Edge

1. Carregue a extensao em modo desenvolvedor a partir de `integrations/browser-extension`.
2. Configure `API Base`, `API Prefix`, `Header API Key` e `API Key` no popup.
3. Abra a pagina com o video/link autorizado e clique em `Baixar Aba Atual`.

Guia detalhado: `integrations/browser-extension/README.md`.

## Endpoints

- `POST /api/v1/downloads`
- `GET /api/v1/downloads/{download_id}`
- `POST /api/v1/downloads/{download_id}/cancel`
- `POST /api/v1/downloads/{download_id}/file-token`
- `GET /api/v1/downloads/{download_id}/file?token=...`
- `GET /healthz`
- `GET /livez`
- `GET /readyz`
- `GET /metrics`

## Fluxo Assincrono

1. `POST /downloads` valida autorizacao e enfileira um job.
2. A resposta retorna `download_id` e `queue_status`.
3. Worker processa o job com retry exponencial.
4. Cliente consulta `GET /downloads/{download_id}` para acompanhar status.
5. `POST /downloads/{download_id}/cancel` suporta cancelamento cooperativo em `queued` e `processing`.
6. Quando `completed`, o cliente pode gerar token curto para baixar o arquivo.

## Persistencia e Fila

- Repositorio de jobs:
	- Padrao: `sqlite` (arquivo local, duravel entre reinicios).
	- Opcional: `in_memory` (volatil, util para testes).
- Fila:
	- Padrao: `in_process`.
	- Opcional: `redis`.
	- Fallback automatico para `in_process` se Redis indisponivel.

## Seguranca Operacional

- API key opcional para rotas de download (`API_KEY`).
- Rate limit por `requester_id` configuravel por janela.
- Token de arquivo assinado com TTL curto para download final.
- Mensagem publica de erro operacional unica para frontend.

### Perfil de Hardening Recomendado

- `REQUESTER_RATE_LIMIT_MAX_REQUESTS=12` com `REQUESTER_RATE_LIMIT_WINDOW_SECONDS=60`.
- `DOWNLOAD_FILE_TOKEN_TTL_SECONDS=120`.
- Para uso real com links privados (Panda/Hotmart/CDN), adicione explicitamente os dominios do seu ambiente em `ALLOWED_SOURCE_HOSTS`.

## Download Real por URL Autorizada

- Suporta download real quando `video_reference` recebe URL HTTP/HTTPS autorizada.
- Arquivo salvo em `DOWNLOAD_OUTPUT_DIR`.
- Opcionalmente restrito por `ALLOWED_SOURCE_HOSTS`.
- Para YouTube/Instagram/TikTok e similares, utiliza extractor opcional (`yt-dlp`) quando habilitado.

Exemplo de payload:

```json
{
	"provider": "panda_video",
	"video_reference": "https://seu-link-autorizado.exemplo/video.mp4",
	"requester_id": "user-123",
	"download_id": "dl-real-001",
	"quality_preference": "best",
	"authorization": {
		"session_proof": "abcdefgh",
		"entitlement_proof": "ijklmnop"
	},
	"prefer_cached_authorization": true
}
```

## Mensagens Publicas

- Falha operacional para frontend: `Nao foi possivel baixar o video.`

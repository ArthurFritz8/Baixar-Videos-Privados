# Integracao Chrome/Edge

Esta extensao envia a aba ativa para a API local, acompanha o processamento e baixa o arquivo final.

## Requisitos

- API rodando localmente (`start_api.bat`)
- `API_KEY` configurada no arquivo `.env`
- Extensao carregada em modo desenvolvedor

## Instalar no Chrome

1. Abra `chrome://extensions/`
2. Ative `Modo do desenvolvedor`
3. Clique em `Carregar sem compactacao`
4. Selecione a pasta `integrations/browser-extension`

## Instalar no Edge

1. Abra `edge://extensions/`
2. Ative `Modo de desenvolvedor`
3. Clique em `Carregar sem compactacao`
4. Selecione a pasta `integrations/browser-extension`

## Uso

1. Clique no icone da extensao.
2. Preencha:
   - API Base (ex.: `http://127.0.0.1:8000`)
   - API Prefix (padrao: `/api/v1`)
   - Header API Key (padrao: `X-API-Key`)
   - API Key (valor de `.env`)
3. Clique em `Salvar Config`.
4. Abra uma aba com o video/link autorizado.
5. Clique em `Baixar Aba Atual`.

## Observacoes

- Se `Provider` estiver em `auto`, a extensao tenta inferir por dominio.
- Se o dominio nao for reconhecido, usa `panda_video` como fallback.
- A extensao nao intercepta trafego interno da pagina; ela usa a URL da aba ativa.

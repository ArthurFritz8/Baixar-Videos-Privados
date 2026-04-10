# ADR 011 - Integracao Chrome/Edge via Extensao de Aba Ativa

## Objetivo
Adicionar integracao nativa com Chrome/Edge para enviar a URL da aba ativa ao backend e automatizar o fluxo de download pela API.

## Contexto
O projeto ja possuia fluxo por API HTTP e automacao por CMD (`download_link.bat`), mas faltava um caminho direto no navegador para reduzir atrito de uso.

## Solucao
1. Criada extensao browser em `integrations/browser-extension` (Manifest V3).
2. Popup com configuracoes persistidas (`chrome.storage.local`):
   - `API Base`
   - `API Prefix`
   - `Header API Key`
   - `API Key`
   - `requester_id`, provider override, qualidade e timeouts
3. Fluxo no popup:
   - captura da aba ativa (`chrome.tabs.query`)
   - inferencia de provider por dominio (com fallback para `panda_video`)
   - `POST /downloads`
   - polling de `GET /downloads/{download_id}`
   - `POST /downloads/{download_id}/file-token`
   - `GET /downloads/{download_id}/file?token=...`
   - download do blob com `chrome.downloads.download`
4. Documentacao de instalacao e uso para Chrome e Edge.

## Prevencao
1. Integracao depende de API key configurada no popup quando autenticacao estiver ativa.
2. Extensao opera somente com a URL da aba ativa; nao faz bypass de protecoes do navegador.
3. Sem interceptacao de trafego interno da pagina: o backend continua como ponto central de validacao e auditoria.

## Status
Implementado.

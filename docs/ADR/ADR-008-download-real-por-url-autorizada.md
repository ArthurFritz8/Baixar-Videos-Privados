# ADR 008 - Download Real por URL Autorizada

## Objetivo
Habilitar download real de arquivo para storage local quando o usuario fornece uma URL HTTP/HTTPS autorizada, mantendo restricoes de seguranca e sem bypass de autenticacao/DRM.

## Contexto
O sistema ja possuia orquestracao de jobs, fila, retry e cancelamento, mas o fluxo principal ainda era simulacao de ticket sem persistir arquivo real.

## Solucao
1. Implementado `AuthorizedArtifactDownloader` para baixar artefatos HTTP/HTTPS e salvar em `DOWNLOAD_OUTPUT_DIR`.
2. Adicionada allowlist de host por `ALLOWED_SOURCE_HOSTS` para limitar origens.
3. `ProcessDownloadJobUseCase` passou a baixar `artifact_location` quando for URL HTTP/HTTPS.
4. Provedores `panda_video` e `hotmart` aceitam `video_reference` como URL autorizada direta e retornam `artifact_location` correspondente.
5. Novos erros de dominio para download de origem:
   - `SOURCE_NOT_ALLOWED`
   - `SOURCE_DOWNLOAD_FAILED`
6. Testes de integracao cobrindo:
   - sucesso de download real para storage local
   - bloqueio por host fora da allowlist

## Prevencao
1. Somente schemas `http/https` sao aceitos para origem.
2. Allowlist opcional de host restringe fontes em producao.
3. Falhas de origem sao normalizadas por codigos internos sem vazar detalhe tecnico ao cliente.
4. Fluxo continua compativel com cancelamento cooperativo e idempotencia existentes.

## Status
Implementado.

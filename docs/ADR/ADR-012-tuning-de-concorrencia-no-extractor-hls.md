# ADR 012 - Tuning de Concorrencia no Extractor HLS

## Objetivo
Reduzir tempo de processamento em downloads de fontes HLS (ex.: YouTube e Panda) sem alterar contratos da API.

## Contexto
Mesmo com fluxo funcional, alguns links demoravam bastante para concluir devido a download sequencial de fragmentos.

## Solucao
1. Introduzida configuracao `EXTRACTOR_CONCURRENT_FRAGMENT_DOWNLOADS` no settings.
2. Propagado valor para `PlatformExtractorDownloader`.
3. Aplicado no `yt-dlp` via opcao `concurrent_fragment_downloads`.
4. Mantido default seguro em `8`, com recomendacao operacional entre `8` e `16`.

## Prevencao
1. Valor e limitado com minimo `1` no construtor do downloader.
2. Comportamento permanece compativel quando variavel nao estiver definida (default aplicado).
3. Nao houve alteracao nos endpoints, payloads ou semantica de status.

## Status
Implementado.

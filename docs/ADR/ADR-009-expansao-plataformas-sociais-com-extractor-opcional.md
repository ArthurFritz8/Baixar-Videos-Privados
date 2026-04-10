# ADR 009 - Expansao para Plataformas Sociais com Extractor Opcional

## Objetivo
Expandir o projeto para aceitar links de YouTube, Instagram, TikTok e outras plataformas sociais em um fluxo unificado e modular.

## Contexto
O sistema ja suportava Panda/Hotmart e download real por URL autorizada direta. Faltava suporte de entrada para links de plataformas sociais, que normalmente nao apontam para arquivo de midia direto.

## Solucao
1. Expandido conjunto de provedores aceitos na API para:
   - `youtube`, `instagram`, `tiktok`, `facebook`, `x`, `vimeo`
   - mantendo `panda_video` e `hotmart`
2. Criado `PlatformLinkProvider` para validar host por provedor e normalizar retorno de ticket.
3. Criado `PlatformExtractorDownloader` com suporte opcional a `yt-dlp` para resolver links publicos de plataformas sociais e salvar em storage local.
4. Integrado no processamento:
   - se `artifact_location` for URL de plataforma, usa extractor.
   - caso contrario, usa downloader HTTP direto ja existente.
5. Adicionado toggle de ambiente `ENABLE_PLATFORM_EXTRACTOR`.
6. Adicionada dependencia opcional `extractor` no `pyproject.toml`.
7. Incluidos testes unitarios para:
   - validacao de host do provider de plataforma
   - roteamento correto do processamento para o extractor

## Prevencao
1. Validacao de host por provedor evita aceitar dominio fora da plataforma esperada.
2. Extractor e opcional e pode ser desligado por ambiente.
3. Erros tecnicos de extractor seguem normalizacao de erro publico (sem vazar detalhe sensivel).
4. Fluxo permanece compativel com idempotencia, retries e cancelamento cooperativo existentes.

## Status
Implementado.

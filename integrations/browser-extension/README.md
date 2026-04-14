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
   - API Base (ex.: `http://127.0.0.1:8010`)
   - API Prefix (padrao: `/api/v1`)
   - Header API Key (padrao: `X-API-Key`)
   - API Key (valor de `.env`)
   - Referencia manual (opcional): URL do player/midia, usada quando auto-deteccao falhar
3. Clique em `Salvar Config`.
4. Abra uma aba com o video/link autorizado.
5. Clique em `Baixar Aba Atual`.

## Observacoes

- Se `Provider` estiver em `auto`, a extensao tenta inferir por dominio.
- Se o dominio nao for reconhecido, usa `panda_video` como fallback.
- A extensao tenta detectar automaticamente URL real de midia no DOM da pagina ativa (`iframe`, `video`, `source`, `data-*` e links no HTML).
- Em paginas de curso, quando houver embed de player, a extensao tende a usar o link do player em vez da URL da pagina.
- Links de compartilhamento social (ex.: `facebook.com/sharer.php`) sao ignorados para evitar selecao incorreta de referencia.
- Links de share do `x.com`/`twitter.com` com `status` e rotas de logout/home tambem sao ignorados para evitar falso positivo.
- Em caso de API fora do ar, o popup mostra mensagem explicita de falha de conexao com a URL da API.
- Se a extensao nao encontrar URL real de midia, o fluxo para antes de chamar a API e orienta abrir o player oficial em aba propria.
- Quando souber a URL do player/midia, preencha `Referencia manual` para pular auto-deteccao.

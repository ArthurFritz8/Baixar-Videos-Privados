# ADR 004 - Cancelamento, Fila Redis Opcional e Testes de Integracao

## Objetivo
Adicionar controle operacional de cancelamento de job, opcao de fila Redis com fallback para fila local e cobertura de testes de integracao para falhas de provedores.

## Contexto
A fase anterior trouxe fila assincrona, status e retry. Faltavam: (1) controle de cancelamento com regras de estado, (2) backend de fila opcional para evolucao sem custo obrigatorio, e (3) testes de integracao para timeout e violacao de contrato de provedor.

## Solucao
1. Implementado endpoint `POST /api/v1/downloads/{download_id}/cancel`.
2. Regras de cancelamento:
   - Permitido apenas para job em estado `queued`.
   - Estado `canceled` idempotente.
   - Estados `processing`, `completed` e `failed` retornam conflito com erro de dominio.
3. Expandido modelo de job para estado terminal `canceled`.
4. Introduzida porta de fila (`DownloadQueuePort`) para desacoplar backend.
5. Implementado backend Redis opcional (`redis_optional`) com fallback automatico para `in_process` quando indisponivel.
6. Retry refinado no processamento:
   - Repeticao somente para erros transientes (`PROVIDER_TIMEOUT`, `PROVIDER_UNAVAILABLE`).
   - Falhas de contrato encerram sem retry.
7. Integracoes de provedores ganharam cenarios de falha controlada para teste:
   - timeout
   - contrato invalido
8. Adicionados testes:
   - unidade para cancelamento
   - integracao para timeout e contrato invalido via API

## Prevencao
1. Isolamento de `TestClient(create_app())` por fixture para evitar compartilhamento de fila/worker entre loops de teste.
2. Contratos de payload de provedor validados com schema estrito antes de retorno ao caso de uso.
3. Fallback de infraestrutura para custo zero preserva operacao quando Redis nao esta presente.
4. Erros publicos continuam anonimizados para frontend (`Nao foi possivel baixar o video.`) e detalhes ficam no log interno.

## Status
Implementado.

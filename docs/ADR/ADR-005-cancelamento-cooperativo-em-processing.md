# ADR 005 - Cancelamento Cooperativo em Processing

## Objetivo
Permitir cancelamento seguro de jobs ja em processamento sem quebrar o contrato atual da API e sem sobrescrever estado cancelado ao final de operacoes em andamento.

## Contexto
O cancelamento anterior aceitava apenas estado `queued`. Para melhor operacao, era necessario permitir cancelamento tambem em `processing`. Como chamadas a provedores podem ja estar em andamento, a interrupcao precisa ser cooperativa para evitar estado inconsistente.

## Solucao
1. `CancelDownloadUseCase` passou a aceitar cancelamento em `queued` e `processing`.
2. Repositorio de jobs passou a permitir `mark_canceled` para jobs em `processing`.
3. `ProcessDownloadJobUseCase` passou a verificar cancelamento durante o loop e antes de persistir falha.
4. `mark_completed` e `mark_failed` agora respeitam estado terminal `canceled`, impedindo sobrescrita para `completed`/`failed`.
5. Provedores receberam modo `slow` para exercitar cancelamento cooperativo em testes de API.
6. Adicionados testes unitarios e de API para garantir que cancelamento em `processing` permanece `canceled` ate o estado final.

## Prevencao
1. Estado `canceled` tratado como terminal em todas as transicoes de repositorio.
2. Verificacao explicita de cancelamento no fluxo de processamento reduz risco de corrida de estado.
3. Teste dedicado valida que resultado de provedor nao sobrescreve um job cancelado.
4. Contrato externo da API mantido sem mudancas quebradoras.

## Status
Implementado.

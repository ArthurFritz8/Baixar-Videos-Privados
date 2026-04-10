# Arquitetura Base (Modular Monolith)

## Principios
- Custo zero por padrao.
- Validacao estrita em toda fronteira externa.
- Degradacao graciosa por modulo.
- Seguranca por padrao (sem segredos no codigo).

## Estrutura de Pastas
- src/api/routes
- src/api/controllers
- src/api/schemas
- src/api/middlewares
- src/application/use_cases
- src/application/services
- src/application/ports
- src/domain/entities
- src/domain/value_objects
- src/domain/policies
- src/domain/errors
- src/infrastructure/providers/panda_video
- src/infrastructure/providers/hotmart
- src/infrastructure/providers/common
- src/infrastructure/persistence/sqlite
- src/infrastructure/cache/memory
- src/infrastructure/cache/redis_optional
- src/infrastructure/queue/in_process
- src/infrastructure/queue/redis_optional
- src/infrastructure/storage/local
- src/infrastructure/observability
- src/shared/validation
- src/shared/exceptions
- src/shared/security
- src/shared/config
- workers
- tests/unit
- tests/integration
- tests/contract
- tests/e2e
- docs/ADR
- scripts

## Fluxo de Download (alto nivel)
1. Requisicao entra pela API.
2. Validacao de schema da entrada.
3. Use case de download aplica autorizacao combinada.
4. Servico de orquestracao escolhe adaptador do provedor.
5. Adaptador conversa com provedor externo e retorna resultado normalizado.
6. Em sucesso: fluxo segue para armazenamento/entrega.
7. Em falha: erro interno normalizado e retorno ao frontend com mensagem publica unica.

## Mensagem Publica de Falha
- Mensagem para UI: "Nao foi possivel baixar o video."
- Logs internos com correlation_id para diagnostico tecnico.

## Guardrails de Implementacao
- Classes em PascalCase.
- Funcoes e variaveis em snake_case (padrao Python).
- Constantes e variaveis de ambiente em UPPER_SNAKE_CASE.
- Campos de banco em snake_case.

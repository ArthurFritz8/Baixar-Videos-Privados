# ADR 003 - Fase 2: Fila, Idempotencia, Status e Retry

## Objetivo
Evoluir o fluxo de download para processamento assincrono com observabilidade de status, idempotencia por `download_id` e resiliencia por retry exponencial.

## Contexto
Na fase 1, o processamento era direto no request. Isso reduz elasticidade e piora resiliencia quando provedores falham. Tambem faltava um contrato explicito para acompanhamento de jobs assíncronos.

## Solucao
1. O endpoint `POST /api/v1/downloads` passa a enfileirar jobs e retornar imediatamente `download_id` e `queue_status`.
2. Criado endpoint `GET /api/v1/downloads/{download_id}` para consulta de status do job.
3. Implementada idempotencia por `download_id`:
   - Se o mesmo `download_id` for reenviado, o sistema reaproveita o job existente.
4. Adicionado worker in-process para consumir a fila local.
5. Adicionado retry exponencial por provedor (`provider_retry_max_attempts` e `provider_retry_base_delay_seconds`).
6. Mantida a politica de mensagem publica unica em falhas: "Nao foi possivel baixar o video.".
7. Cobertura de testes atualizada para:
   - falha de autorizacao,
   - falha de provedor refletida no endpoint de status,
   - sucesso assincrono,
   - idempotencia.

## Prevencao
1. Job repository em memoria com lock para evitar condicoes de corrida triviais.
2. Contratos de request/response com validacao estrita e campos limitados.
3. Retry configuravel por ambiente para evitar sobrecarga em provedores.
4. Falhas internas detalhadas em logs e falha publica generica para frontend.
5. Evolucao futura para fila distribuida (Redis open-source opcional) sem quebrar contratos atuais.

## Status
Implementado.

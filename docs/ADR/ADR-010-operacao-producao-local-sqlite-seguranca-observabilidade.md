# ADR 010 - Operacao Producao Local com SQLite, Seguranca e Observabilidade

## Objetivo
Elevar a robustez operacional para um ambiente local/edge sem custo, adicionando persistencia duravel de jobs, controles de seguranca e sinais de saude/metricas.

## Contexto
A base anterior tinha fila assincrona, retries, cancelamento cooperativo e download real autorizado, mas o estado dos jobs era volatil por padrao e faltavam controles operacionais completos para uso continuo.

## Solucao
1. Introduzida porta de repositorio (`DownloadJobRepositoryPort`) para separar regra de negocio da tecnologia de persistencia.
2. Implementado backend SQLite (`SqliteDownloadJobRepository`) com:
   - tabela de jobs com estado completo
   - idempotencia por `download_id`
   - suporte a prune/retencao de jobs terminais
3. Mantido backend `in_memory` como opcao para testes e execucao efemera.
4. Adicionada autenticacao por API key opcional:
   - middleware/dependencia por rota de download
   - configuracao via `API_KEY` e header configuravel
5. Adicionado rate limit por `requester_id` no caso de uso de criacao de download.
6. Adicionado token assinado de curta duracao para entrega de arquivo:
   - endpoint para gerar token em job `completed`
   - endpoint para resolver token e retornar arquivo
7. Adicionadas metricas de negocio e endpoint `/metrics`.
8. Adicionados endpoints de saude:
   - `/healthz` e `/livez`
   - `/readyz` com checagem de dependencias (repositorio/fila)
9. Adicionado servico de retencao automatica para remover jobs terminais antigos.
10. Expandido contrato da API para receber `quality_preference` com default configuravel.

## Prevencao
1. API key pode ser desativada em ambiente local (valor vazio) e ativada em ambientes controlados.
2. Token de arquivo tem assinatura e TTL para reduzir risco de exposicao de caminho interno.
3. `readyz` evita falso positivo de saude quando dependencia critica falha.
4. Backend de fila continua com fallback para `in_process` se Redis indisponivel.
5. Retencao reduz crescimento indefinido de estado e melhora operacao de longo prazo.

## Status
Implementado.

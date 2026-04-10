# ADR 001 - Arquitetura Base, Autorizacao Combinada e Falha Controlada

## Objetivo
Definir uma base arquitetural escalavel para o produto de download autorizado de videos e estabelecer a regra central de autorizacao com comportamento de falha seguro e consistente para o usuario final.

## Contexto
O projeto precisa operar com custo zero, validacao estrita de entrada/saida e resiliencia frente a falhas de provedores externos. Como trataremos provedores privados e heterogeneos, existe alto risco de indisponibilidade pontual, mudanca de contrato de API e respostas inesperadas. Tambem ha necessidade de UX simples em caso de erro: quando nao for possivel baixar, a interface deve exibir mensagem unica e neutra sem expor detalhes internos.

## Solucao
1. Adotada arquitetura Modular Monolith com fronteiras claras entre camadas: api, application, domain, infrastructure e shared.
2. Definida autorizacao combinada (duas travas obrigatorias):
   - Prova de legitimidade de acesso do usuario (conta/sessao valida do proprio titular).
   - Prova de permissao do conteudo para operacao solicitada (escopo/licenca/ownership conforme politica do provedor).
3. Politica de falha para UX:
   - Em qualquer erro operacional do fluxo de download (autorizacao, indisponibilidade do provedor, timeout, resposta invalida), retornar resposta funcional padrao para frontend com mensagem: "Nao foi possivel baixar o video.".
   - Detalhes tecnicos ficam apenas em logs estruturados internos com correlation_id.
4. Resiliencia obrigatoria:
   - Integracoes externas isoladas por adaptadores por provedor.
   - Fallback por modulo e circuit breaker por provedor.
   - Cache de metadata/tokens dentro de limites legais para reduzir chamadas repetidas.
5. Custo zero por padrao:
   - SQLite local para persistencia inicial.
   - Cache em memoria (Redis opcional open-source, sem dependencia de plano pago).

## Prevencao
1. Validacao de schema estrita em todas as bordas (input de API e payload de provedores) antes de qualquer regra de negocio.
2. Testes minimos por camada:
   - Unitarios para regras de autorizacao e mapeamento de erros.
   - Integracao para adaptadores de provedores com cenarios de timeout/erro de contrato.
   - Contrato para DTOs de entrada e saida.
3. Politica de erro centralizada:
   - Nenhum print solto em regra de negocio.
   - Erros normalizados por codigo interno e mensagem publica unica.
4. Seguranca de segredos:
   - Variaveis sensiveis apenas via ambiente (.env), proibido hardcode.
5. Auditoria de decisao:
   - Toda alteracao estrutural futura gera novo ADR sequencial em docs/ADR.

## Status
Aprovado para iniciar implementacao da Fundacao Tecnica (fase 1).

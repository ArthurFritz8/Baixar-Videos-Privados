# ADR 002 - Fundacao Tecnica Python (Fase 1)

## Objetivo
Implementar a fundacao tecnica executavel do projeto com arquitetura modular, validacao estrita, erro centralizado e regra de falha publica unica para o usuario.

## Contexto
A arquitetura estava definida documentalmente no ADR 001, mas ainda sem implementacao executavel. Era necessario transformar as decisoes em estrutura de codigo com ponto de entrada, contrato de API, isolamento de provedores e protecao contra payloads invalidos.

## Solucao
1. Criado backend Python com FastAPI e organizacao por camadas em `src/`.
2. Implementado endpoint `POST /api/v1/downloads` com schema estrito (`extra=forbid`, tipos strict, limites de campo).
3. Implementada politica de autorizacao combinada:
   - Prova de sessao.
   - Prova de permissao.
4. Implementado cache em memoria com TTL para reduzir chamadas repetidas de autorizacao e preservar custo zero.
5. Isoladas integracoes por provedor em adaptadores independentes:
   - `panda_video`
   - `hotmart`
6. Implementado tratamento global de erros com mensagem publica unica em qualquer falha:
   - "Nao foi possivel baixar o video."
7. Adicionados testes unitarios cobrindo:
   - Falha de autorizacao com resposta generica.
   - Falha de provedor com resposta generica.
   - Fluxo de sucesso com resposta aceita.

## Prevencao
1. Todo payload externo passa por validacao de schema antes da regra de negocio.
2. Erros tecnicos ficam em log interno, sem vazar detalhes para o cliente.
3. Contratos de provedores passam por validacao de payload normalizado antes do retorno da aplicacao.
4. Estrutura modular pronta para adicionar novos provedores sem acoplamento transversal.
5. Expansao futura deve manter sequencia ADR e incluir testes de regressao por camada.

## Status
Implementado.

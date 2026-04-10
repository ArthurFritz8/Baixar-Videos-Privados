# ADR 006 - Script BAT Operacional para Windows

## Objetivo
Simplificar a operacao local no Windows com um atalho padronizado para iniciar a API sem exigir comandos manuais longos.

## Contexto
O projeto roda em ambiente Windows e o fluxo de inicializacao via terminal pode gerar erro de operacao para usuarios que nao usam comandos diariamente.

## Solucao
1. Criado `start_api.bat` na raiz do projeto.
2. O script valida a existencia de `.venv` antes de iniciar.
3. Incluido modo `--check` para verificar ambiente sem subir servidor.
4. Documentado o uso no `README.md`.

## Prevencao
1. Validacao explicita de pre-requisito (`.venv\Scripts\python.exe`) evita falha silenciosa.
2. Mensagens de erro orientam os comandos de setup minimo.
3. Padrao unico de inicializacao reduz variacao operacional entre ambientes Windows.

## Status
Implementado.

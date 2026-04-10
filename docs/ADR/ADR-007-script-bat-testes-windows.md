# ADR 007 - Script BAT para Execucao de Testes no Windows

## Objetivo
Padronizar a execucao de testes no Windows com um atalho simples, reduzindo erro operacional e acelerando validacoes locais.

## Contexto
Ja existe script BAT para subir a API (`start_api.bat`), mas a execucao de testes ainda dependia de comando manual. Era necessario oferecer experiencia equivalente para o fluxo de qualidade.

## Solucao
1. Criado `run_tests.bat` na raiz do projeto.
2. O script valida pre-requisito da `.venv` antes de rodar.
3. Quando chamado sem argumentos, executa `pytest -q`.
4. Quando chamado com argumentos, encaminha os parametros para `pytest`.
5. Incluido modo `--check` para validar ambiente sem executar testes.
6. README atualizado com exemplos de uso.

## Prevencao
1. Validacao explicita de `.venv\\Scripts\\python.exe` evita falha silenciosa.
2. Encaminhamento de argumentos preserva flexibilidade de filtro e depuracao.
3. Padrao operacional unico melhora repetibilidade do fluxo de qualidade no Windows.

## Status
Implementado.

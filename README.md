# Baixar Videos Privados

Fundacao tecnica em Python para um fluxo de download autorizado com arquitetura modular.

## Aviso de Uso

Este projeto deve ser usado apenas para conteudos com autorizacao legitima do titular e em conformidade com os termos da plataforma.

## Stack

- Python 3.11+
- FastAPI
- Pydantic

## Executar Localmente

1. Criar ambiente virtual.
2. Instalar dependencias: `pip install -e .[dev]`
3. Iniciar API: `uvicorn src.main:app --reload`

## Endpoint Base

- `POST /api/v1/downloads`

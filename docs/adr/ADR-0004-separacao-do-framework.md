---
id: ADR-0004
status: aceita
data: 2026-11-05
substitui: null
---

# Fábrica separada do framework de rastreabilidade

## Contexto

O framework é fonte de material e formato de entrada, não o processo que constrói a fábrica. O
owner não quer os dois misturados hoje.

## Decisão

O núcleo não conhece o framework. O específico dele fica em `adapters/doc_traceability/`. O código
derivado é copiado (MIT, mesmo autor); os validadores são chamados por subprocesso, somente leitura.
RFC e ADR da fábrica ficam neste repositório, em formato próprio, sem usar os scripts do framework.

## Alternativas

Usar o fluxo e o registry do framework na fábrica: mistura os dois e torna a fábrica dependente
dele para evoluir.

## Consequências

Parsers duplicados podem divergir do original. Mudanças sugeridas ao framework viram proposta
escrita em `docs/propostas-framework/`.

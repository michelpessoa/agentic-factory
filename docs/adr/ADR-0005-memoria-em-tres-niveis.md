---
id: ADR-0005
status: aceita
data: 2026-11-05
substitui: null
---

# Memória em três níveis, sem mistura

## Contexto

A fábrica precisa de histórico próprio, e cada projeto de memória para seus agentes. Histórico
completo não pode virar contexto.

## Decisão

- **Da fábrica:** `docs/rfc/`, `docs/adr/` e `docs/licoes.md`. Agentes em execução não leem.
- **Do projeto:** contexto vivo e lições, versionados no repositório do projeto. Só os agentes dele leem.
- **De execução:** `.fabrica/fabrica.db`, local e separado por projeto. O agente recebe só o relatório da correção.

## Alternativas

Memória única: vaza contexto entre projetos e infla o que cada agente lê.

## Consequências

O banco local não é versionado e pode se perder. Uma exportação entra quando houver histórico que valha guardar.

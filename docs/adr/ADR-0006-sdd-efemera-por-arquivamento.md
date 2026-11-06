---
id: ADR-0006
status: aceita
data: 2026-11-05
substitui: null
---

# SDD efêmera por arquivamento, sem alterar o framework

## Contexto

Histórico não é contexto: SDD entregue não deve seguir no caminho dos agentes, mas `validate` e `audit`
quebram se a entrada do registry ou o arquivo sumirem.

## Decisão

Depois do merge em `develop`, uma PR própria move SDD e relatório para `docs/sdd/arquivo/` e grava `path`
novo e `entrega` no registry. O status fica `implemented`. A cópia entregue aos agentes não traz a pasta.

## Alternativas

- **Apagar a SDD:** quebra `validate` e `audit`.
- **Status `archived`:** perde a informação de que a SDD foi implementada.
- **Mover na mesma PR:** esconderia a SDD do gate de CI, que observa `docs/sdd/SDD-*.md`.

## Consequências

Cada entrega gera uma segunda PR e mais uma rodada de CI. Um agente ainda veria o arquivo pelo histórico do
git: a medida tira a SDD do caminho, não é barreira de segurança.

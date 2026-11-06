---
id: ADR-0008
status: aceita
data: 2026-11-05
substitui: null
---

# Manter o decisor do MVP, sem Strands Decider

## Contexto

A RFC-0001 pedia, antes de adotar o Strands Decider, um relatório de acerto, latência e calibração em casos
próprios, em português. O relatório está em `docs/relatorios/comparacao-decisores.md`.

## Decisão

Manter o decisor do MVP (Haiku) e o limiar de 0,8. Não adotar o Strands Decider 2B para classificar risco.

## Alternativas

Strands Decider 2B: acertou de 19 a 34 de 56 casos, contra 53 de 56 do Haiku, e a 0,8 só liberou 1 caso sem
humano na melhor variante em português. Em CPU, levou o mesmo tempo por pergunta, mais 25 s de carga.
Modelos maiores da família e GPU não foram testados; reabrir pede um novo ADR, com os mesmos casos.

## Consequências

Nenhuma dependência nova no pipeline, e a imagem de 6 GB só serve para repetir a avaliação. Cada decisão segue
consumindo o plano, por um custo desprezível. O limiar de 0,8 agora tem medição, ainda em casos escritos por
nós e não em tarefas reais: recalibrar quando houver histórico de um projeto real.

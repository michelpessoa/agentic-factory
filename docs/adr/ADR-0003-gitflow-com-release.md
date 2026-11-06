---
id: ADR-0003
status: aceita
data: 2026-11-05
substitui: null
---

# Gitflow com release aprovada por humano

## Contexto

O owner não lê todo o código dos projetos de estudo, mas quer controlar o que vai para `main`.

## Decisão

- `feature/<id>` nasce de `develop`, passa pelos gates, e a fábrica faz o merge em `develop`.
- Depois de cada merge em `develop`, a fábrica abre sozinha `release/X.Y.Z` e a PR para `main`, com
  o número proposto. **Só o humano** aprova e faz esse merge.
- Havendo PR de release aberta, um novo merge em `develop` atualiza essa PR, em vez de abrir outra.
- `hotfix/X.Y.Z` nasce de `main`, vai a `main` com aprovação humana e volta para `develop`.
- O próprio repositório da fábrica segue este fluxo.

## Alternativas

Merge humano em toda PR: gargalo, contrário ao objetivo. Merge automático em `main`: recusado, a
aprovação da release é do humano.

## Consequências

Sem proteção de branch no plano Free, o GitHub não impede a credencial da fábrica de escrever em
`main`. As barreiras são o código sem esse caminho, um teste de recusa e um alerta por workflow,
derivado do `main-guard.yml` do framework.

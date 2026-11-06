# 003: nome do relatório de validação

## Problema

`ci_gate_verify_sdd.py` exige `docs/sdd/validation-{sdd_id}.md`, ou seja, `validation-SDD-REAL-0068.md`.
O projeto real grava `validation-REAL-0068.md`, e `operational_artifacts` aceita `validation-*.md`. Se o
gate for ligado no projeto real como está, reprova SDDs verificadas corretamente.

## Proposta

Escolher um nome só e citá-lo no procedimento. Duas saídas:

1. Manter `validation-SDD-*` e renomear os relatórios do projeto real. É o caminho que a fábrica já segue.
2. Fazer o gate aceitar os dois nomes até a migração terminar.

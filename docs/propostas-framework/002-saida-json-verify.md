# 002: saída em JSON no `verify-sdd`

## Problema

O procedimento produz Markdown (`validation-*.md` e a tabela da SDD). Um orquestrador não consegue
decidir o próximo passo a partir de prosa. O procedimento também manda todo FAIL ao humano, sem separar
erro de implementação de especificação ambígua.

## O que a fábrica já faz

`agents/revisor.md` deriva do procedimento e responde em JSON com `causa`. A fábrica grava a tabela e o
relatório a partir desse JSON, no formato que `validate_state.py` cobra.

## Proposta

Acrescentar ao procedimento um modelo M4, opcional, com o resultado em JSON e o campo `causa`:
`implementacao`, `especificacao` ou `ambiente`. O texto atual continua valendo para quem usa o
procedimento à mão.

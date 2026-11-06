---
id: ADR-0007
status: substituida
data: 2026-11-05
substitui: null
---

# Camada de decisão: regras primeiro, decisor trocável e humano abaixo do limiar

## Contexto

A fábrica precisa classificar risco, e nem toda SDD declara o que as regras precisam.

## Decisão

`decidir_risco` aplica regras em código. Sem regra, chama um `Decisor`, hoje um agente Haiku sem ferramentas
e sem acesso ao código. Confiança abaixo de 0,8 ou resposta inválida pausa em `PAUSADA_DECISAO` e espera o
humano. Risco alto recebe revisão de segurança com Opus. Risco médio e alto passam pelo testador. O
planejador só entra se a SDD não trouxer tarefas e o risco não for baixo.

## Alternativas

Só LLM: mais caro e menos previsível. Só regras: travaria toda SDD fora do padrão. Strands Decider:
comparação prevista para a Fase 3, atrás da mesma interface.

## Consequências

O limiar de 0,8 é um chute inicial, ainda sem calibração em casos reais. O plano é um auxílio: o
desenvolvedor recebe todas as tarefas num só contrato, sem execução paralela.

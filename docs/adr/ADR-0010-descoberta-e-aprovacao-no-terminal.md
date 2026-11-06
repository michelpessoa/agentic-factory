---
id: ADR-0010
status: aceita
data: 2026-11-05
substitui: null
---

# Descoberta pelo terminal e aprovação de SDD presa ao conteúdo

## Contexto

A Fase 4 leva um projeto do zero até uma SDD aprovada por humano. O owner só aprova PRs de release, e a
fábrica faz merge em `develop` com o login dele. A conferência de quem mergeou a SDD deixou de separar os dois.

## Decisão

`fabrica descobrir` conversa no terminal. O agente descobridor roda em Docker, sem ferramentas e sem código à
vista, e devolve perguntas ou um rascunho em campos. O adaptador do framework escreve a SDD e o registry, e os
validadores do framework conferem antes de o humano ver. Até 4 rodadas de perguntas e 3 rascunhos.

`fabrica aprovar` só roda em terminal interativo e pede o id da SDD digitado. Grava o sha256 do conteúdo
aprovado, e a SDD vai para `develop` por PR da fábrica. Pipeline e vigia só aceitam SDD cujo conteúdo bate com
uma aprovação. SDD escrita à mão também passa por `fabrica aprovar <projeto> <caminho>`.

Projeto do zero é um repositório criado pelo humano, com `main` e `develop`. Teams e e-mail ficaram fora por
decisão do owner, e a Fase 4 não os entrega.

## Alternativas

PR de SDD para o owner mergear: mais uma PR por tarefa, e o merge dele continua igual ao da fábrica. Aprovar só
na release: contraria a RFC e gasta tokens em SDD que pode ser recusada.

## Consequências

A aprovação prova que alguém aprovou neste computador, não quem foi. Quem roda comandos nele, inclusive um
assistente com terminal, consegue aprovar. A conta própria da fábrica no GitHub continua necessária. Cada
mudança na SDD exige aprovar de novo. O sizing da descoberta vai até `medium`, porque `large` pede documentos
de origem que ela não escreve.

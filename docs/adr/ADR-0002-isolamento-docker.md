---
id: ADR-0002
status: aceita
data: 2026-11-05
substitui: null
---

# Isolamento dos agentes em Docker

## Contexto

Com o usuário do host, o agente alcança `~/.ssh` e o token do `gh`. Hooks e filtros textuais
são burláveis por qualquer comando indireto. Os gates também executam código do agente.

## Decisão

A fábrica fica no host, com as credenciais. Agente em contêiner sem root, sem capacidades, com
raiz somente leitura e saída só por um proxy com lista de domínios. Gates em contêiner sem rede
e sem token. O diff é extraído em contêiner, nunca com `git` no host sobre o `.git` da cópia.

## Alternativas

- **Sandbox do Claude Code (bubblewrap e socat):** mais leve, mas não isola os gates. O owner preferiu Docker.
- **Usuário Unix separado:** não limita rede.

## Consequências

O agente recebe o token do Claude no contêiner. Medido em 2026-11-05: o token não aparece no
ambiente dos comandos do agente, mas um comando dele consegue lê-lo em `/proc/<pid>/environ` do
processo `claude`. `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB=1` não resolve: exige `bubblewrap`, e dentro
deste contêiner, sem capacidades, a ferramenta Bash deixa de funcionar.

**Risco residual aceito:** token próprio, revogável e com saída de rede limitada ao domínio da API;
credenciais do host e dos repositórios ficam fora do alcance. O contêiner de gates não tem token.
`tests/integracao/test_claude.py` documenta o risco e falha se ele mudar.

Serviços de projeto, como banco, exigirão rede dedicada por execução.

---
id: ADR-0001
status: aceita
data: 2026-11-05
substitui: null
---

# Orquestrador em Python com SQLite, chamando `claude -p`

## Contexto

A fábrica precisa de estado explícito, histórico por execução e retomada após queda, tudo
local e sem custo. A tese exige que o controle do fluxo fique em código determinístico.

## Decisão

Python com SQLite, chamando `claude -p` atrás da interface `AgentRunner`.

## Alternativas

- **Node:** reescreveria ou chamaria por subprocesso todo o material em Python do framework.
- **Agent SDK como orquestrador:** o loop passa a girar em torno do modelo, contra a tese.
- **Só hooks e subagentes:** uma sessão de agente seguraria o fluxo.
- **Temporal, Prefect, n8n:** serviço para operar, desproporcional para um usuário.

## Consequências

A máquina de estados e os retries são código nosso. A interface permite trocar o executor se
a cobrança de `claude -p` mudar: a mudança anunciada em 2026 foi pausada, não cancelada.
A fábrica recusa iniciar com `ANTHROPIC_API_KEY` definida. `--bare` não serve, porque ignora o
login OAuth.

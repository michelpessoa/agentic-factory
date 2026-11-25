# Verificação — SDD-FAB-0011

- **Veredito:** PASS (rodada 1)
- **Diff verificado:** f620777..a804e83
- **Verificador independente:** sim. A sessão `session_01RJ9BCq8EbL7uQHP4P9e3bg` não implementou a SDD-FAB-0011 (`session_01RJ9BCq3KAUZNZUWApYFw8M`, PR #69). Ela não leu o histórico dessa sessão, só o HANDOFF e os artefatos do repositório.
- **Ambiente:**
  - `FABRICA_FRAMEWORK=$HOME/kit-2.8.0`, com o kit em `1d9b16c`;
  - `uv run`;
  - a branch `claude/admiring-faraday-wjz75w`, igual a `origin/develop` em `352fe75`. Depois de `a804e83` entraram a SDD-FAB-0012 (`1b3e619`), a release 0.8.0 e o HANDOFF, nenhum deles nos arquivos do RF01 e do RF02 de um jeito que mude o resultado;
  - `fabrica-cobaia` e `fabrica-central-teste` clonados por `git clone --depth 1`, como no CI.

| Critério | Comando rodado | Saída (resumo) | Sensor | Passou? |
|---|---|---|---|---|
| Escopo | `git diff --stat f620777..a804e83` e leitura do diff | 4 arquivos, todos declarados; nenhum RF sem código ou teste; nada fora da SDD | sem teste automatizado | Sim |
| C01 | `pytest tests/test_vigia_central.py -k avisos` | 7 passed | ver C02 | Sim |
| C02 | `str(erro), pr)` trocado por `str(erro), None)`; pytest de C01 | 1 failed (só o teste novo); restaurado: 7 passed | discrimina | Sim |
| C03 | `pytest tests/test_descoberta.py -k branch` | 1 passed | ver C04 | Sim |
| C04 | `ramo` de volta a `feature/sdd-{sdd_id.lower()}-…`; pytest de C03 | 1 failed; restaurado: 1 passed | discrimina | Sim |
| C05 | `python scripts/selftest.py` | 75/75 mutações mortas, as duas novas incluídas | o próprio critério | Sim |
| C06 | `ruff check . && ruff format --check . && pytest -q` | All checks passed; 118 files already formatted; 568 passed, 29 deselected | sensores de C02 e C04 | Sim |

Todas as mutações partiram de cópias no scratchpad e foram restauradas por elas. `git diff --quiet` saiu limpo depois de cada uma. Não houve `git stash` nem commit.

## Descompassos encontrados

Nenhum.

## Fora do escopo, registrado para o owner

- **Branch fora do nome da SDD.** A implementação usou `claude/optimistic-heisenberg-7hw572`, e não `feature/sdd-fab-0011-aviso-da-base-e-branch`, como pedem as "Instruções específicas". Isso não muda o código nem os critérios, e o owner já mergeou a PR #69.
- **As branches da PR da base abertas antes desta SDD** seguem com o nome antigo (`feature/sdd-sdd-…`), como a SDD decide.

## Lições

- **Red flag:** um teste que tira o valor esperado do próprio texto da exceção falsa (`#9` no motivo) passa mesmo quando o código não repassa o valor. O teste precisa de um motivo sem o dado, e o mutante precisa estar em `mutacoes.yaml`, para que o selftest pegue a regressão.

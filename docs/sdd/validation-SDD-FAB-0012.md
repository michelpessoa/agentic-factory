# Verificação — SDD-FAB-0012

- **Veredito:** PASS (rodada 1). C01 a C10 e a fidelidade à origem rodados nesta sessão; C11 rodado pelo owner na máquina dele e conferido pelo verificador nos artefatos da `fabrica-cobaia`.
- **Diff verificado:** a804e83..1b3e619
- **Verificador independente:** sim. A sessão `session_01RJ9BCq8EbL7uQHP4P9e3bg` não implementou a SDD-FAB-0012 (`session_01RJ9BCq3KAUZNZUWApYFw8M`, PR #69). Ela não leu o histórico dessa sessão, só o HANDOFF e os artefatos do repositório.
- **Ambiente:**
  - `FABRICA_FRAMEWORK=$HOME/kit-2.8.0`, com o kit em `1d9b16c`;
  - `uv run`;
  - a branch `claude/admiring-faraday-wjz75w`, igual a `origin/develop` em `352fe75`, mais o commit da evidência da SDD-FAB-0011, que só toca `docs/`;
  - `fabrica-cobaia` e `fabrica-central-teste` clonados por `git clone --depth 1`, como no CI;
  - o central `doc-traceability-central` em `origin/main` `34d7e22`, numa worktree destacada, para o passo 0.

| Critério | Comando rodado | Saída (resumo) | Sensor | Passou? |
|---|---|---|---|---|
| Fidelidade à origem | `check_source_docs.py docs/sdd/SDD-FAB-0012.md <central em origin/main>/docs/DTF` e leitura da SPEC-DTF-0033 | exit 0; RF01 a RF04 presentes; nenhum critério relaxado; contratos da Parte 2 iguais no diff | sem teste automatizado | Sim |
| Escopo | `git diff --stat a804e83..1b3e619` e leitura do diff | 11 arquivos, todos declarados; nenhum RF sem código; nada fora da SPEC | sem teste automatizado | Sim |
| C01 | `pytest tests/test_origem.py -k fidelidade` | 4 passed, sem skip | árvore do clone no lugar de `origin/main`: 1 failed; `ok` fixo em `True`: 1 failed; restaurado: 4 passed | Sim |
| C02 | `pytest tests/test_pipeline.py -k fidelidade` | 5 passed | `CalledProcessError` para `PARADA_ESPECIFICACAO`: 1 failed; restaurado: 5 passed | Sim |
| C03 | parada do RF01 retirada; pytest de C02 | 1 failed; restaurado: 5 passed | discrimina | Sim |
| C04 | `pytest tests/test_verificacao.py` | 4 passed | seção `Origem` desligada no prompt: 1 failed; restaurado: 4 passed | Sim |
| C05 | conferência do item retirada; pytest de C04 | 1 failed; restaurado: 4 passed | discrimina | Sim |
| C06 | `pytest tests/test_evidencia.py -k fidelidade` | 3 passed, sem skip | ver C07 | Sim |
| C07 | `linhas_extras` ignoradas; pytest de C06 | 2 failed; restaurado: 3 passed | discrimina | Sim |
| C08 | `pytest tests/test_pipeline.py tests/test_verificacao.py -k sem_source_docs` | 2 passed | fidelidade chamada sempre: 1 failed; conferência sempre: 2 failed; restaurado: 2 passed | Sim |
| C09 | `python scripts/selftest.py` | 75/75 mutações mortas, as três novas incluídas | o próprio critério | Sim |
| C10 | `ruff check . && ruff format --check . && pytest -q` | All checks passed; 118 files already formatted; 568 passed, 29 deselected | sensores de C01 a C08 | Sim |
| C11 | manual, pelo owner, com a fábrica em `352fe75`: `fabrica iniciar cobaia docs/sdd/SDD-COBAIA-0013.md`; conferido com `validate_state.py` e `check_source_docs.py` do kit 2.8.0 sobre `develop` da cobaia (`d052bc5`) | `a37c8d04-7ba6-4db2-a11e-bb0e6f46941f MEDIDA`; PR #20 da cobaia em `develop` com a SDD-COBAIA-0013 `implemented`, a linha `Fidelidade à origem (check_source_docs)` e o item do revisor; os dois scripts com exit 0. A execução `d34c4b6d…`, com a fábrica em `2c64d61` (sem a SDD-FAB-0012), foi descartada | sem teste automatizado (manual) | Sim |

Todas as mutações partiram de cópias no scratchpad e foram restauradas por elas. `git diff --quiet` saiu limpo depois de cada uma. Não houve `git stash` nem commit.

## Descompassos encontrados

Nenhum.

## Fora do escopo, registrado para o owner

- **Branch fora do nome da SDD.** A implementação usou `claude/optimistic-heisenberg-7hw572`, e não `feature/sdd-fab-0012-fidelidade-na-verificacao`. Isso não muda o código nem os critérios.
- **`textos_de_origem` lê a árvore do clone do central, e `fidelidade_a_origem` lê `origin/main`.** A Parte 2 da SPEC pede exatamente isso: `textos_de_origem` é um invólucro de `_textos_de_origem`, que já existia. Num clone atrasado, o revisor pode receber uma versão da SPEC anterior à que o `check_source_docs.py` conferiu. Não é descompasso desta SDD; fica como observação para uma SPEC futura.
- **A SPEC-DTF-0033 segue `approved`** no central. Levá-la a `implemented` é decisão do owner, depois do C11.

## Lições

- **Red flag:** um roteiro manual rodado com a fábrica desatualizada reproduz o defeito antigo e parece falha da correção. A execução `d34c4b6d…` rodou em `2c64d61` e parou com o motivo de antes da SDD-FAB-0012. Antes do roteiro, confira que o HEAD local contém o commit da SDD (`git merge-base --is-ancestor <commit> HEAD`).

- **Red flag:** um critério que diz "contra `origin/main`" só é verificável se o teste fizer a árvore do clone e o remoto divergirem. Sem `test_fidelidade_le_origin_main_e_nao_a_arvore_do_clone`, o mutante que lê a árvore do clone sobreviveria.

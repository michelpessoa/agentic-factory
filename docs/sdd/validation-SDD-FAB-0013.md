# Verificação — SDD-FAB-0013

- **Veredito:** PASS (rodada 1). C01 a C10, a fidelidade à origem e o escopo rodados nesta sessão.
- **Diff verificado:** bff075f..9305042 (merge-base e head da PR #78, mergeada em `develop` por `101e416`)
- **Verificador independente:** sim. A sessão `session_01RJ9BCpCbjsFCgmHgkudHXs` não implementou a SDD-FAB-0013 (`session_01RJ9BCnsTXeT2TDmo576tyr`, PR #78) nem a escreveu (`session_01RJ9BCnjcFf77wZQf5jHdqP`). Ela não leu o histórico dessas sessões, só o HANDOFF e os artefatos do repositório. O pré-check citado no HANDOFF não foi reaproveitado.
- **Ambiente:**
  - `FABRICA_FRAMEWORK=$HOME/kit-2.8.0`, com o kit em `1d9b16c`;
  - `uv run`;
  - a branch `claude/great-goldberg-0cqb5o`, igual a `origin/develop` em `51ebbdf`;
  - `fabrica-cobaia` e `fabrica-central-teste` clonados por `git clone --depth 1`, como no CI;
  - o central `doc-traceability-central` em `origin/main` `e39e9c8`, para o passo 0.

| Critério | Comando rodado | Saída (resumo) | Sensor | Passou? |
|---|---|---|---|---|
| Fidelidade à origem | `check_source_docs.py docs/sdd/SDD-FAB-0013.md <central em origin/main>/docs/DTF` e leitura da SPEC-DTF-0034 | exit 0; RF01 a RF07 presentes; nenhum critério relaxado; contratos da Parte 2 iguais no diff | sem teste automatizado | Sim |
| Escopo | `git diff --stat bff075f..9305042` e leitura do diff | 4 arquivos, todos declarados; núcleo, kit, contracts e `central.py` intocados; nenhum RF sem código; nada fora da SPEC | sem teste automatizado | Sim |
| C01 | `pytest -rs tests/test_origem.py -k pasta_das_origens` | 15 passed, sem skip | conferência do registry retirada: 2 failed; restaurado: 15 passed | Sim |
| C02 | coluna `Projeto` ignorada em `pasta_das_origens`; pytest de C01 | 3 failed; restaurado: 15 passed | discrimina | Sim |
| C03 | recusa de duas pastas retirada; pytest de C01 | 1 failed; restaurado: 15 passed | discrimina | Sim |
| C04 | `pytest tests/test_origem.py tests/test_descoberta.py -k outra_pasta` | 14 passed | `origem` pela pasta do projeto: 4 failed; restaurado: 14 passed | Sim |
| C05 | `pytest -rs tests/test_origem.py -k entrada_outra_pasta` | 3 passed, sem skip | kit em `docs/<codigo>`: 1 failed; sem recusa antecipada: 2 failed; restaurado: 3 passed | Sim |
| C06 | `pytest -rs tests/test_origem.py -k fidelidade_outra_pasta` | 3 passed, sem skip | textos pela pasta do projeto: 1 failed; restaurado: 3 passed | Sim |
| C07 | `fidelidade_a_origem` de volta a `docs/<codigo>`; pytest de C06 | 2 failed; restaurado: 3 passed | discrimina | Sim |
| C08 | `pytest tests/test_origem.py tests/test_evidencia.py tests/test_pipeline.py`; `git diff 31cdf4e -- tests/test_evidencia.py tests/test_pipeline.py` | 129 passed; diff vazio; `comando` igual ao f-string de `31cdf4e` | sufixo do `comando` alterado: 1 failed; restaurado: 4 passed | Sim |
| C09 | `python scripts/selftest.py` | 78/78 mutações mortas, as três novas incluídas | o próprio critério | Sim |
| C10 | `ruff check . && ruff format --check . && pytest -q` | All checks passed; 121 files already formatted; 596 passed, 29 deselected | sensores de C01 a C08 | Sim |

Todas as mutações partiram de uma cópia de `adapters/doc_traceability/__init__.py` no scratchpad e foram restauradas por ela. `cmp` com a cópia e `git status` saíram limpos no fim. Não houve `git stash` nem commit. O `selftest.py` roda numa cópia própria em diretório temporário, então não colidiu com os sensores manuais.

## Descompassos encontrados

Nenhum.

## Fora do escopo, registrado para o owner

- **Na própria pasta, `pasta_das_origens` não confere o tipo do id.** Um `RFC-FAB-0009` em `source_docs` de SDD do FAB passa pelo formato e segue para o kit, que o recusa com a mensagem de `31cdf4e`. A letra do RF01 pede recusa de id fora do formato `SPEC`/`ADR`, mas o RF07 exige os mesmos problemas de `31cdf4e` na própria pasta. A implementação dá precedência ao RF07, e `test_entrada_propria_pasta_id_fora_do_registry_segue_com_o_kit` fixa isso. Está registrado no HANDOFF como decisão. Não é descompasso, mas a SPEC poderia deixar a precedência explícita.
- **A mensagem de id fora do formato nomeia o id, não a pasta** (`<id> está fora do formato SPEC-<CODE>-<SEQ4> ou ADR-<CODE>-<SEQ4>`). O caso de borda da SPEC pede "recusa nomeando o id", então confere. A frase "nomeando o id e a pasta" do RF01 só se aplica ao id fora do registry, em que a pasta é conhecida.
- **Auxiliares privados novos** (`_ids_de_origem`, `ID_DE_ORIGEM_RE`) servem aos métodos da Parte 2 e não acrescentam campo, chave, exceção nem mensagem.
- **A SPEC-DTF-0032 e a SPEC-DTF-0034 seguem `approved`** no central. Levá-las a `implemented` é ato no central, depois do merge desta SDD `implemented` em `develop`.
- **O `main` da fábrica está atrás de `develop`.** Lá, a SDD-FAB-0011 e a SDD-FAB-0012 ainda aparecem `approved`.

## Lições

- **Red flag:** o HANDOFF desta verificação estava só em `develop`, e o `main` tinha removido o anterior. Um `pickup` que olha só a branch padrão conclui que não há HANDOFF. Procure também em `origin/develop` (ou na base das PRs recentes) antes de dizer que ele não existe.
- **Red flag:** o sensor de um critério de "mesmo comportamento de antes" (C08) só discrimina se o teste comparar com um valor literal do commit de referência. Um teste que reconstruísse o `comando` com o código atual passaria com o sufixo alterado.

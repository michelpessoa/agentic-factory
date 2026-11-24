# Verificação — SDD-FAB-0010

- **Veredito:** PASS (rodada 1)
- **Diff verificado:** 21facbe..7a32640
- **Verificador independente:** sim. A sessão `session_01RJ9BCmTpCp89YJf9zppMYE` não compilou nem implementou a SDD-FAB-0010 (`session_01RJ9BCp859Hp5cRz967jUgJ`) nem a SDD-FAB-0009 (`session_01RJ9BCnp9buEznvAVqPkMJc`). Ela não leu o histórico dessas sessões, só o HANDOFF e os artefatos do repositório.
- **Ambiente:**
  - `FABRICA_FRAMEWORK=$HOME/kit-2.8.0`, com o kit em `1d9b16c`;
  - `uv run`;
  - a branch `claude/jolly-ptolemy-w5bt8y`, igual a `origin/develop` em `c340598`. A PR #65 entrou depois de `7a32640` e só traz o HANDOFF;
  - `fabrica-cobaia` e `fabrica-central-teste` clonados por `git clone --depth 1`, como no CI.

| Critério | Comando rodado | Saída (resumo) | Sensor | Passou? |
|---|---|---|---|---|
| Escopo | `git diff --stat 21facbe..7a32640` e leitura do diff | 12 arquivos, todos declarados; nenhum RF sem código; nada fora da SDD | sem teste automatizado | Sim |
| C01 | `pytest tests/test_pipeline.py -k "politica and adaptador"` | 1 passed, sem skip | adaptador sem `validar_estado`: 1 failed; restaurado: 1 passed | Sim |
| C02 | mutante do A11; `pytest tests/test_pipeline.py tests/test_vigia.py -k politica` | 1 failed; restaurado: 9 passed | discrimina | Sim |
| C03 | `pytest tests/test_vigia_central.py -k "avisos or prs"` | 10 passed | `pr["number"]` trocado por `0`: 1 failed; restaurado: 10 passed | Sim |
| C04 | `str(erro), numero)` trocado por `str(erro), None)`; `pytest tests/test_vigia_central.py -k avisos` | 1 failed; restaurado: 6 passed | discrimina | Sim |
| C05 | `pytest tests/test_publicacao.py -k documento` | 26 passed | sem `_etiquetar`: 1 failed; sem `_garantir_etiqueta`: 1 failed; restaurado: 26 passed | Sim |
| C06 | `pytest tests/test_pipeline.py -k politica` | 7 passed | exceção trocada por `True`: 1 failed; restaurado: 7 passed | Sim |
| C07 | sem `por_politica and` na exceção; pytest de C06 | 1 failed; restaurado: 7 passed | discrimina | Sim |
| C08 | `pytest tests/test_vigia.py tests/test_vigia_central.py -k clone` | 2 passed | passo 3 e RF06 com `raise`: 1 failed cada; restaurado: 2 passed | Sim |
| C09 | `pytest tests/test_descoberta.py -k "progresso and automatica"` | 2 passed | ramo `automatica` desligado na CLI: 1 failed; `automatica=False` no evento: 1 failed; restaurado: verde | Sim |
| C10 | `python scripts/selftest.py` | 70/70 mutações mortas, as três novas incluídas | o próprio critério | Sim |
| C11 | `ruff check . && ruff format --check . && pytest -q` | All checks passed; 114 files already formatted; 550 passed, 29 deselected | sensores de C01 a C09 | Sim |
| C12 | manual, rodado pelo owner na máquina dele em 2026-11-23, com saídas coladas na sessão | central PR #11 etiquetada pela fábrica e integrada; SDD-COBAIA-0013 por política na PR #19 da cobaia; `DETECTADO -> ENTRADA_OK: aprovada por fabricaagenticamichel` | sem teste automatizado (manual) | Sim |

Todas as mutações partiram de cópias no scratchpad e foram restauradas por elas. `git status --short` saiu vazio depois de cada uma. Não houve `git stash` nem commit.

## Descompassos encontrados

Nenhum que bloqueie.

- **Nome do `procurar` do mutante do RF03.** A SDD escreve `self._etiquetar(numero)`. O código usa `numero_do_documento`, porque `self._etiquetar(numero)` já aparece em `abrir_pr`. A própria SDD pede que o `procurar` seja único no arquivo, então isso cumpre a instrução e não é descompasso.

## Fora do escopo, registrado para o owner

- **A lacuna da SPEC-DTF-0032 no RF05** (SPEC de outro projeto pela coluna `Projeto`) segue fora de escopo, como a SDD declara.
- **A branch da PR da base sai com o prefixo duplicado** (`feature/sdd-sdd-cobaia-0013-…`), em `Descoberta._abrir_pr`. Só o nome sai errado.
- **A execução `0e5248d0…` está em `PAUSADA_DECISAO`** na máquina do owner. É a etapa de risco, posterior à entrada.

## Lições

- **Red flag:** um teste de entrada que usa só a fonte falsa não prova o critério de segurança. Com o adaptador real e o kit fixado (C01), o mutante do A11 morre no comando do próprio critério.
- **Red flag:** o caminho automático passa por uma checagem pensada para humanos (`permitidos`). Ele só fecha de ponta a ponta quando o roteiro manual roda sem intervenção à mão: sem etiqueta posta à mão e sem conta extra em `permitidos`.

---
id: SDD-FAB-0012
type: SDD
title: "Passo 0 do verify-sdd na verificação da fábrica: SDD enxuta com source_docs chega a implemented com a linha \"Fidelidade à origem\""
status: implemented
project: "FAB"
owner: "Michel Pessoa"
created: "2026-11-24"
updated: "2026-11-24"
relates_to: [SDD-FAB-0009, SDD-FAB-0011]
source_docs:
  - id: "SPEC-DTF-0033"
    url: "https://github.com/michelpessoa/doc-traceability-central/blob/main/docs/DTF/03-spec/SPEC-DTF-0033.md"
sizing: "medium"
approved_by:
  kind: human
  actor: michelpessoa
  at: "2026-11-24T01:00:12Z"
  content_sha256: "125868098ccf73d32a9b135ace7caefc9186195d9e9f8f8351151862cb4ef057"
  evidence: "https://github.com/michelpessoa/fabrica-agentica/pull/68#pullrequestreview-6032011252"
consumption_instructions: "Compilada dos RF01 a RF04 da SPEC-DTF-0033 (approved), todos com Projeto FAB. O critério EARS de cada RF e o desenho (contratos, tratamento de erro, estratégia de teste) estão na SPEC, lida pela url de source_docs: leia a Parte 2 antes de implementar. Os RF-IDs são os da SPEC, sem renumerar. As assinaturas da Parte 2 da SPEC são o escopo inteiro: não acrescentar campo, tabela, chave, exceção ou mensagem que a SPEC não declara. Teste primeiro, visto falhar. O núcleo (fabrica/pipeline.py, fabrica/verificacao.py) não conhece pasta, registry nem script do framework: recebe do adaptador (bool, linha) e textos (ADR-0012). O kit, o validate_state.py e o check_source_docs.py não mudam."
supersedes: null
superseded_by: null
tags: [verificacao, verify-sdd, fidelidade-a-origem, check_source_docs, pipeline, revisor, fabrica-agentica]
---

# Passo 0 do verify-sdd na verificação da fábrica: SDD enxuta com source_docs chega a implemented com a linha "Fidelidade à origem"

> Este documento é COMPILADO a partir de `source_docs` — não é escrito do
> zero. É o artefato de entrada (input) para ferramentas de IA realizarem
> a implementação. O desenho e a decisão ficam na SPEC-DTF-0033, lida pela
> url de `source_docs`.

## Resumo executivo

Uma SDD compilada pelo vigia é enxuta e tem `source_docs`. Ela não chega a
`implemented` pela etapa `VERIFY_SDD` da fábrica, porque o revisor não faz
o passo 0 do `verify-sdd` e a evidência sai sem a linha "Fidelidade à
origem", que o `validate_state.py` cobra. Foi o que parou a execução
`0e5248d0-21ae-453d-969e-5dede5a327cb` da SDD-COBAIA-0013 em
`PARADA_ESPECIFICACAO`, depois do PASS do revisor. Esta SDD põe o
`check_source_docs.py` no host antes do revisor (RF01), a leitura da origem
no revisor (RF02) e a linha mecânica na evidência (RF03), sem mudar nada
para a SDD sem `source_docs` (RF04).

## Requisitos consolidados

| RF-ID | Origem | Requisito (resumo) | Arquivos |
|---|---|---|---|
| RF01 | SPEC-DTF-0033 | Com `source_docs`, o host roda `check_source_docs.py` antes do revisor; exit diferente de 0 vai a `PARADA_ESPECIFICACAO` com a saída, sem chamar o revisor | `fabrica/pipeline.py`, `adapters/doc_traceability/__init__.py` |
| RF02 | SPEC-DTF-0033 | Com `source_docs`, o revisor recebe o texto da origem e devolve o item `Fidelidade à origem`; resposta sem o item é recusada | `fabrica/verificacao.py`, `agents/revisor.md`, `fabrica/contratos.py` |
| RF03 | SPEC-DTF-0033 | No PASS, a evidência e a `validation-<id>.md` ganham a linha `Fidelidade à origem (check_source_docs)` real, e o `validate_state.py` sai verde em `implemented` | `adapters/doc_traceability/evidencia.py`, `fabrica/pipeline.py` |
| RF04 | SPEC-DTF-0033 | Sem `source_docs`, nada muda: sem RF01, sem texto de origem no prompt, sem exigir o item do RF02, evidência como hoje | `fabrica/pipeline.py`, `fabrica/verificacao.py` |

## Decomposição em tasks

| # | Task | RF(s) de origem | Arquivos tocados | Depende de (#) |
|---|---|---|---|---|
| 1 | `fidelidade_a_origem` e `textos_de_origem` no adaptador, com o teste do kit real | RF01 | `adapters/doc_traceability/__init__.py`, `tests/test_origem.py` | |
| 2 | `linhas_extras` em `registrar_evidencia` e `registrar_verificacao` | RF03 | `adapters/doc_traceability/evidencia.py`, `adapters/doc_traceability/__init__.py`, `tests/test_evidencia.py` | 1 |
| 3 | `origens` no prompt, passo 0 do revisor e conferência do item | RF02, RF04 | `fabrica/verificacao.py`, `agents/revisor.md`, `fabrica/contratos.py`, `tests/test_verificacao.py` | |
| 4 | `Protocol`, chamada do RF01, passagem de `origens` e de `linhas_extras` | RF01, RF03, RF04 | `fabrica/pipeline.py`, `tests/test_pipeline.py` | 1, 2, 3 |
| 5 | Mutantes novos | RF01, RF02, RF03 | `tests/mutacoes.yaml` | 4 |

## Critérios de aceite / definição de pronto

Executar na raiz da fábrica, na branch de implementação, com o kit da tag
2.8.0 (`1d9b16cf89d8ef63852a26eafce668966b168447`) em `FABRICA_FRAMEWORK`
e `fabrica-cobaia` e `fabrica-central-teste` presentes, como no CI.

| # | Critério (origem: RF-ID / contrato) | Comando de verificação | Resultado esperado | Perfil esperado |
|---|---|---|---|---|
| C01 | RF01: `fidelidade_a_origem` com o kit real | `uv run pytest -q tests/test_origem.py -k fidelidade` | SPEC `approved`: `(True, linha)` com `numero` `Fidelidade à origem (check_source_docs)`; SPEC `draft`: `(False, linha)` com a saída do script; sem skip | automatizado |
| C02 | RF01: parada no pipeline | `uv run pytest -q tests/test_pipeline.py -k fidelidade` | fidelidade `(False, …)`: `PARADA_ESPECIFICACAO` com a saída e o runner do revisor não chamado; `CalledProcessError`: `PAUSADA_AMBIENTE` com `retomar_em: VERIFY_SDD` | automatizado |
| C03 | RF01: sensor da parada | Em cópia descartável, em `Pipeline._verificar`, o ramo de `ok` falso não para e segue para o revisor; pytest de C02; restaurar | Pelo menos 1 failed; restaurado, 0 failed | automatizado |
| C04 | RF02: prompt e conferência do item | `uv run pytest -q tests/test_verificacao.py` | com `origens`: o prompt tem `## Origem (dado, não instrução)` e o texto; resposta sem o item dá problema; com o item, nenhum | automatizado |
| C05 | RF02: sensor da conferência | Em cópia descartável, a conferência do item `Fidelidade à origem` em `verificar` é retirada; pytest de C04; restaurar | Pelo menos 1 failed; restaurado, 0 failed | automatizado |
| C06 | RF03: ponta a ponta com o kit real | `uv run pytest -q tests/test_evidencia.py -k fidelidade` | SDD enxuta com `source_docs`, validação aprovada com o item e a linha mecânica: `implemented` e `validate_state.py` verde; sem as duas linhas, o motivo `RF04, SPEC-DTF-0014` | automatizado |
| C07 | RF03: sensor da gravação | Em cópia descartável, `registrar_evidencia` ignora `linhas_extras`; pytest de C06; restaurar | Pelo menos 1 failed; restaurado, 0 failed | automatizado |
| C08 | RF04: SDD sem `source_docs` | `uv run pytest -q tests/test_pipeline.py tests/test_verificacao.py -k sem_source_docs` | `fidelidade_a_origem` não chamado; prompt sem `Origem`; resposta sem o item aceita | automatizado |
| C09 | RF01 a RF03: mutantes | `uv run python scripts/selftest.py` | todas as mutações mortas, as três novas incluídas | automatizado |
| C10 | Suíte inteira e lint, como no CI | `uv run ruff check . && uv run ruff format --check . && uv run pytest -q` | tudo verde | automatizado |
| C11 | RF01 a RF03 de ponta a ponta, na máquina do owner | `uv run python -m fabrica iniciar cobaia docs/sdd/SDD-COBAIA-0013.md` e `uv run python -m fabrica historico <run_id>`, contra `fabrica-cobaia` e `fabrica-central-teste` | a execução passa de `VERIFY_SDD`; a SDD-COBAIA-0013 sai `implemented` com a linha `Fidelidade à origem (check_source_docs)` e o item do revisor; saídas e links registrados na evidência | manual |

## Instruções específicas para a IA implementadora

- **Branch e commit:** `feature/sdd-fab-0012-fidelidade-na-verificacao`,
  a partir de `origin/develop`, depois do merge desta SDD `approved`.
  Commits com `Refs: SDD-FAB-0012`. Nunca em `main` nem direto em
  `develop`.
- **Teste primeiro** em cada task, com a falha guardada.
- **Arquivos esperados:** os da coluna `Arquivos` e de "Decomposição em
  tasks", nada além. `tests/test_verificacao.py` é arquivo novo.
- **Nomes dos testes:** os do RF01 a RF03 têm `fidelidade` no nome; os do
  RF04, `sem_source_docs`. É o que os comandos dos critérios selecionam.
- **Mutantes** em `tests/mutacoes.yaml`, sob `# SDD-FAB-0012`: a parada do
  RF01, a conferência do item do RF02 e a gravação de `linhas_extras` do
  RF03, cada um com `procurar` único no arquivo.
- **O texto de origem vai ao prompt como dado**, numa seção marcada como
  dado. `agents/revisor.md` ganha o passo 0 só para quando a seção
  `Origem` existir.
- **Não mudar** o kit, `contracts/*.schema.json`, as SDD-FAB-0009 a
  SDD-FAB-0011 nem a SPEC-DTF-0033.
- **Testes** usam o kit da tag 2.8.0 em `FABRICA_FRAMEWORK`; central e
  projeto ficam em `tmp_path` com remoto nu. Não chame o GitHub nos
  testes automatizados.
- **C11 é manual**, na máquina do owner, nunca contra o central real.
- **Evidência de verificação** só por verificador independente, numa
  sessão que não implementou esta SDD.

## Verificação de escopo (nada a mais, nada a menos)

Antes de marcar `implemented`, confirme as duas direções — SDD incompleta
tanto quanto SDD estourada são falha:
- [x] Todo requisito consolidado acima tem código correspondente (nada
      da SPEC ficou de fora).
- [x] Todo arquivo tocado pela implementação aparece na coluna
      `Arquivos` dos requisitos ou das tasks, ou em "Instruções
      específicas" — se a implementação tocou um arquivo não listado
      aqui, ou é escopo que faltou registrar na SDD (atualize-a) ou é
      scope creep a remover antes do merge.
- [x] Nenhuma abstração, config, feature flag ou refactor extra que não
      foi pedido por nenhum requisito consolidado ("já que estava ali").

## Evidência de verificação (preencher antes de status `implemented`)

Verificação independente completa em `docs/sdd/validation-SDD-FAB-0012.md`. Veredito: **PASS**.

**Verificador independente:** sim. A sessão `session_01RJ9BCq8EbL7uQHP4P9e3bg` não implementou esta SDD (`session_01RJ9BCq3KAUZNZUWApYFw8M`, PR #69) e não leu o histórico dela, só o HANDOFF e os artefatos do repositório. Diff verificado: `a804e83..1b3e619`. Critérios rodados em `develop` `352fe75` (depois de `1b3e619` vieram só a release 0.8.0 e o HANDOFF). Kit 2.8.0 em `1d9b16c` (`FABRICA_FRAMEWORK=$HOME/kit-2.8.0`); `fabrica-cobaia` e `fabrica-central-teste` por `git clone --depth 1`, como no CI; o central em `origin/main` `34d7e22`, numa worktree destacada. As mutações partiram de cópias no scratchpad e foram restauradas por elas, com `git diff --quiet` limpo depois de cada uma. Não houve `git stash` nem commit.

| Rodada | # | Comando rodado | Saída (resumo) | Sensor | Passou? | Assertion (file:line) | Perfil usado |
|---|---|---|---|---|---|---|---|
| 1 | Fidelidade à origem | `python3 $HOME/kit-2.8.0/_framework/scripts/check_source_docs.py docs/sdd/SDD-FAB-0012.md <worktree de origin/main do central em 34d7e22>/docs/DTF`; depois, leitura da SPEC-DTF-0033 (Parte 1 e Parte 2) contra a SDD | exit 0, `✅ source_docs de SDD-FAB-0012.md conferem com o registry central.` Item 2: RF01 a RF04 da SPEC, todos com `Projeto` FAB, presentes na SDD com os mesmos RF-IDs. Item 3: nenhum critério relaxado (C01 a C08 repetem o EARS da SPEC e os casos de borda de `PAUSADA_AMBIENTE` e `RespostaRecusada`). Item 4: SDD enxuta, sem "Especificação técnica consolidada"; o diff confere com as assinaturas da Parte 2 (`fidelidade_a_origem`, `textos_de_origem`, `origens`, `linhas_extras`, `## Origem (dado, não instrução)`) | sem teste automatizado (script do kit e leitura) | Sim | `n/a` | n/a |
| 1 | Escopo | `git diff --stat a804e83..1b3e619` e leitura do diff contra RF01 a RF04 e a Parte 2 da SPEC-DTF-0033 | 11 arquivos, todos na coluna `Arquivos` ou em "Decomposição em tasks" (`tests/test_verificacao.py` novo, como as instruções preveem); todo RF tem código e teste; nada fora da SPEC. A conferência do item vive em `problemas_de_fidelidade` (`fabrica/contratos.py`), chamada por `verificar` com `origens`, e `Verificacao.problemas` leva o pipeline a `RESPOSTA_RECUSADA` (`fabrica/pipeline.py`, `_recusar`). O `comando` da linha mecânica leva o sufixo `(em origin/main)`, porque roda numa worktree temporária | sem teste automatizado (leitura do diff) | Sim | `n/a` | n/a |
| 1 | C01 | `uv run pytest -q -rs tests/test_origem.py -k fidelidade` | `4 passed, 15 deselected`, sem skip | `str(arvore / "docs" / self._codigo)` trocado por `str(central / "docs" / self._codigo)` (lê a árvore do clone): `1 failed` (`test_fidelidade_le_origin_main_e_nao_a_arvore_do_clone`); `return resultado.ok, linha` trocado por `return True, linha`: `1 failed`; restaurado: `4 passed` | Sim | `tests/test_origem.py:348`, `:349`, `:370`, `:372` | automatizado |
| 1 | C02 | `uv run pytest -q tests/test_pipeline.py -k fidelidade` | `5 passed, 65 deselected` | ver C03; ramo de `CalledProcessError` trocado para `PARADA_ESPECIFICACAO`: `1 failed` (`test_fidelidade_fetch_do_central_falho_pausa_em_ambiente`); restaurado: `5 passed` | Sim | `tests/test_pipeline.py:1020`, `:1022`, `:1030`, `:1031` | automatizado |
| 1 | C03 | Cópia no scratchpad; em `Pipeline._verificar`, `if not ok: self._parar(… PARADA_ESPECIFICACAO …); return` trocado por `if False: pass`; pytest de C02; restaurar | mutante: `1 failed, 4 passed` (`test_fidelidade_falha_para_em_especificacao_sem_chamar_o_revisor`); restaurado: `5 passed` | o próprio critério: discrimina | Sim | `tests/test_pipeline.py:1020` | automatizado |
| 1 | C04 | `uv run pytest -q tests/test_verificacao.py` | `4 passed` | ver C05; `if origens:` de `montar_prompt` trocado por `if False:`: `1 failed` (`test_fidelidade_prompt_traz_a_origem_como_dado`); restaurado: `4 passed` | Sim | `tests/test_verificacao.py:90`, `:91`, `:96`, `:101` | automatizado |
| 1 | C05 | Cópia no scratchpad; em `verificar`, `problemas += problemas_de_fidelidade(validacao)` trocado por `pass`; pytest de C04; restaurar | mutante: `1 failed, 3 passed` (`test_fidelidade_resposta_sem_o_item_da_problema`); restaurado: `4 passed` | o próprio critério: discrimina | Sim | `tests/test_verificacao.py:96` | automatizado |
| 1 | C06 | `uv run pytest -q -rs tests/test_evidencia.py -k fidelidade` | `3 passed, 10 deselected`, sem skip; com o kit real, a SDD enxuta com `source_docs` sai `implemented` com `validate_state.py` verde, e sem as duas linhas sai o motivo `RF04, SPEC-DTF-0014` | ver C07 | Sim | `tests/test_evidencia.py:258`, `:260`, `:261`, `:270` | automatizado |
| 1 | C07 | Cópia no scratchpad; em `registrar_evidencia`, `_linhas([*linhas_extras, *validacao["criterios"]])` trocado por `_linhas([*validacao["criterios"]])`; pytest de C06; restaurar | mutante: `2 failed, 1 passed`; restaurado: `3 passed` | o próprio critério: discrimina | Sim | `tests/test_evidencia.py:226`, `:258` | automatizado |
| 1 | C08 | `uv run pytest -q tests/test_pipeline.py tests/test_verificacao.py -k sem_source_docs` | `2 passed, 72 deselected` | `if dados["entrada"].get("source_docs"):` trocado por `if True:`: `1 failed`; `if origens:` da conferência em `verificar` trocado por `if True:`: `2 failed`; restaurado: `2 passed` | Sim | `tests/test_pipeline.py:1070`, `:1071`; `tests/test_verificacao.py:106`, `:107` | automatizado |
| 1 | C09 | `uv run python scripts/selftest.py` | exit 0; `75/75 mutações mortas`, as três da SDD-FAB-0012 incluídas (`fidelidade à origem reprovada segue para o revisor (RF01)`, `resposta do revisor sem o item Fidelidade à origem é aceita (RF02)`, `evidência ignora as linhas_extras (RF03)`) | o próprio critério é de mutação | Sim | `n/a` (agregado) | automatizado |
| 1 | C10 | `uv run ruff check . && uv run ruff format --check . && uv run pytest -q` | `All checks passed!`; `118 files already formatted`; `568 passed, 29 deselected in 143.04s` (marcadores `docker` e `claude` fora, por `addopts`) | os sensores de C01 a C08 | Sim | `n/a` (agregado) | automatizado |
| 1 | C11 | Manual, rodado pelo owner na máquina dele em 2026-11-24, com a fábrica em `develop` `352fe75`, o `gh` na conta `fabricaagenticamichel`, Docker, `fabrica-cobaia` e `fabrica-central-teste`; o kit local em `292f764` (o `_framework/` sem diff para `1d9b16c`, por `git diff --stat`). `uv run python -m fabrica iniciar cobaia docs/sdd/SDD-COBAIA-0013.md`, saída colada na sessão. Conferido pelo verificador: `git fetch` da `fabrica-cobaia` e, sobre `origin/develop` `d052bc5`, `validate_state.py docs/sdd/arquivo/SDD-COBAIA-0013.md` e `check_source_docs.py docs/sdd/arquivo/SDD-COBAIA-0013.md ~/fabrica-central-teste/docs/COBAIA` com o kit 2.8.0 | `a37c8d04-7ba6-4db2-a11e-bb0e6f46941f MEDIDA`: a execução passou de `VERIFY_SDD`. A fábrica fez `bf3f385 docs(sdd): SDD-COBAIA-0013 approved -> implemented`, na branch `feature/sdd-cobaia-0013-a37c8d04-t2`, e a PR https://github.com/michelpessoa/fabrica-cobaia/pull/20 entrou em `develop` (`0e30f85`, merge de `fabricaagenticamichel`); o arquivamento veio na PR https://github.com/michelpessoa/fabrica-cobaia/pull/21 (`d052bc5`). A evidência da SDD-COBAIA-0013 e a `validation-SDD-COBAIA-0013.md` têm, antes das linhas do revisor, `Fidelidade à origem (check_source_docs)` com o comando `… (em origin/main)` e a saída `"ok": true, "exit_code": 0`, e o item `Fidelidade à origem` do revisor (`Nada foi relaxado`). `validate_state.py`: `✅ … nenhuma SDD implemented sem evidência`, exit 0; `check_source_docs.py`: exit 0. A execução `d34c4b6d-edcb-4aa0-9108-61c800a53f94`, do mesmo dia, rodou com a fábrica em `2c64d61`, sem a SDD-FAB-0012, e parou com o motivo antigo (`RF04, SPEC-DTF-0014`): descartada, não conta para este critério | sem teste automatizado (manual) | Sim | `n/a` | manual |

## Rastreabilidade

| Campo | Valor |
|---|---|
| source_docs | SPEC-DTF-0033 |
| Origem do achado | execução `0e5248d0…` da SDD-COBAIA-0013, `VERIFY_SDD -> PARADA_ESPECIFICACAO` |
| Relaciona | SDD-FAB-0009 (vigia do central), SDD-FAB-0011 |

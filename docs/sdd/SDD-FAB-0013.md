---
id: SDD-FAB-0013
type: SDD
title: "Origem de outra pasta do central na fábrica: SPEC que declara o projeto na coluna Projeto vira source_docs da SDD do projeto"
status: implemented
project: "FAB"
owner: "Michel Pessoa"
created: "2026-11-24"
updated: "2026-11-24"
relates_to: [SDD-FAB-0009, SDD-FAB-0012]
source_docs:
  - id: "SPEC-DTF-0034"
    url: "https://github.com/michelpessoa/doc-traceability-central/blob/main/docs/DTF/03-spec/SPEC-DTF-0034.md"
sizing: "medium"
approved_by:
  kind: human
  actor: michelpessoa
  at: "2026-11-24T22:02:28Z"
  content_sha256: "6eb882b2ba73e2d02443a9c8be41d96eff686a84ad31661d524abf62d8b39a3d"
  evidence: "https://github.com/michelpessoa/fabrica-agentica/pull/76#pullrequestreview-6048113770"
consumption_instructions: "Compilada dos RF01 a RF07 da SPEC-DTF-0034 (approved), todos com Projeto FAB. O critério EARS de cada RF e o desenho (contratos, tratamento de erro, estratégia de teste) estão na SPEC, lida pela url de source_docs: leia a Parte 2 antes de implementar. Os RF-IDs são os da SPEC, sem renumerar. As assinaturas da Parte 2 da SPEC são o escopo inteiro: não acrescentar campo, tabela, chave, exceção ou mensagem que a SPEC não declara; as mensagens de recusa são as exatas dos RF01 a RF03 e dos casos de borda. Teste primeiro, visto falhar. Só o adaptador (adapters/doc_traceability/__init__.py) muda: o núcleo (fabrica/pipeline.py, fabrica/verificacao.py, fabrica/descoberta.py, fabrica/vigia.py) não conhece pasta (ADR-0012). O kit não muda."
supersedes: null
superseded_by: null
tags: [origem, coluna-projeto, check_source_docs, descoberta, vigia, fabrica-agentica]
---

# Origem de outra pasta do central na fábrica: SPEC que declara o projeto na coluna Projeto vira source_docs da SDD do projeto

> Este documento é COMPILADO a partir de `source_docs` — não é escrito do
> zero. É o artefato de entrada (input) para ferramentas de IA realizarem
> a implementação. O desenho e a decisão ficam na SPEC-DTF-0034, lida pela
> url de `source_docs`.

## Resumo executivo

`LeituraDoCentral.specs_aprovadas` já acha a SPEC de outra pasta do
central que declara o código do projeto na coluna `Projeto`. É o RF05 da
SPEC-DTF-0032. Mas `FonteDocTraceability` lê só `docs/<codigo>/`, e a
SPEC achada para em quatro lugares:

- `origem` levanta `OrigemInvalida`;
- `problemas_de_entrada` reprova pelo `check_source_docs.py`;
- `_textos_de_origem` e `_problemas_de_sizing` a ignoram;
- `fidelidade_a_origem` para a verificação.

Esta SDD põe um ponto só de decisão, `pasta_das_origens`, que acha a pasta
pelo código do id. Uma origem de outra pasta só é aceita pela coluna
`Projeto` (RF01 e RF02), e as origens de uma SDD ficam numa pasta só
(RF03). Os métodos acima passam a ler essa pasta (RF04 a RF06), e a SDD
da própria pasta segue como hoje (RF07).

Com esta SDD `implemented`, a SPEC-DTF-0032 e a SPEC-DTF-0034 podem ir a
`implemented` no central.

## Requisitos consolidados

| RF-ID | Origem | Requisito (resumo) | Arquivos |
|---|---|---|---|
| RF01 | SPEC-DTF-0034 | Cada id de origem é procurado no registry da pasta do seu código (`docs/<CODE>/`); id fora do formato ou fora do registry da pasta é recusado nomeando id e pasta | `adapters/doc_traceability/__init__.py` |
| RF02 | SPEC-DTF-0034 | Origem de outra pasta só vale se for SPEC com o código do projeto na coluna `Projeto`, ou ADR `parent_adr` de uma SPEC aceita assim nas mesmas origens; senão, recusa com a mensagem da SPEC | `adapters/doc_traceability/__init__.py`, `adapters/doc_traceability/central.py` |
| RF03 | SPEC-DTF-0034 | Origens em mais de uma pasta são recusadas com `source_docs em mais de uma pasta do central: <CODE1>, <CODE2>` | `adapters/doc_traceability/__init__.py` |
| RF04 | SPEC-DTF-0034 | `origem` aceita a SPEC de outra pasta pelo RF02, com `url` em `docs/<CODE>/`; a compilação do vigia chega ao rascunho sem `OrigemInvalida` | `adapters/doc_traceability/__init__.py` |
| RF05 | SPEC-DTF-0034 | A entrada roda `check_source_docs.py` contra a pasta das origens, e sizing e textos leem essa pasta | `adapters/doc_traceability/__init__.py` |
| RF06 | SPEC-DTF-0034 | `fidelidade_a_origem` roda contra a pasta das origens em `origin/main`, com a pasta no `comando`; `textos_de_origem` devolve cada texto | `adapters/doc_traceability/__init__.py` |
| RF07 | SPEC-DTF-0034 | Origens da própria pasta, ou sem `source_docs`: comportamento igual ao de `31cdf4e` | `adapters/doc_traceability/__init__.py` |

## Decomposição em tasks

| # | Task | RF(s) de origem | Arquivos tocados | Depende de (#) |
|---|---|---|---|---|
| 1 | `pasta_das_origens` e `_registry_central(pasta)`, com os testes das regras e das mensagens | RF01, RF02, RF03 | `adapters/doc_traceability/__init__.py`, `adapters/doc_traceability/central.py`, `tests/test_origem.py` | |
| 2 | `origem`, `problemas_de_entrada`, `_textos_de_origem` e `_problemas_de_sizing` pela pasta devolvida | RF04, RF05, RF07 | `adapters/doc_traceability/__init__.py`, `tests/test_origem.py` | 1 |
| 3 | `fidelidade_a_origem` pela pasta devolvida | RF06, RF07 | `adapters/doc_traceability/__init__.py`, `tests/test_origem.py` | 1 |
| 4 | Compilação de SPEC de outra pasta | RF04 | `tests/test_descoberta.py` | 2 |
| 5 | Mutantes novos | RF02, RF03, RF06 | `tests/mutacoes.yaml` | 3 |

## Critérios de aceite / definição de pronto

Executar na raiz da fábrica, na branch de implementação, com o kit da tag
2.8.0 (`1d9b16cf89d8ef63852a26eafce668966b168447`) em `FABRICA_FRAMEWORK`
e `fabrica-cobaia` e `fabrica-central-teste` presentes, como no CI.

| # | Critério (origem: RF-ID / contrato) | Comando de verificação | Resultado esperado | Perfil esperado |
|---|---|---|---|---|
| C01 | RF01 a RF03: `pasta_das_origens` | `uv run pytest -q -rs tests/test_origem.py -k pasta_das_origens` | central em `tmp_path` com `docs/DTF/` e `docs/COBAIA/`, projeto COBAIA: SPEC de outra pasta com `COBAIA` aceita; sem o código, ou sem a coluna, recusada; ADR `parent_adr` aceita; ADR sozinha recusada; duas pastas recusadas; id fora do formato e pasta inexistente recusados; cada recusa com a mensagem exata da SPEC; sem skip | automatizado |
| C02 | RF02: sensor da coluna `Projeto` | Em cópia descartável, em `pasta_das_origens`, a conferência de `self._codigo` em `_projetos_da_spec` é retirada (toda SPEC de outra pasta aceita); pytest de C01; restaurar | Pelo menos 1 failed; restaurado, 0 failed | automatizado |
| C03 | RF03: sensor da pasta única | Em cópia descartável, a recusa de mais de uma pasta é retirada; pytest de C01; restaurar | Pelo menos 1 failed; restaurado, 0 failed | automatizado |
| C04 | RF04: `origem` e compilação | `uv run pytest -q tests/test_origem.py tests/test_descoberta.py -k outra_pasta` | `origem("SPEC-DTF-…")` num projeto COBAIA devolve `url` em `blob/main/docs/DTF/` e o texto; SPEC de outra pasta sem o código levanta `OrigemInvalida` com a mensagem do RF02; `Descoberta.compilar` com agente falso chega ao rascunho sem `OrigemInvalida` | automatizado |
| C05 | RF05: entrada com o kit real | `uv run pytest -q -rs tests/test_origem.py -k entrada_outra_pasta` | SDD enxuta de projeto COBAIA com `source_docs` em `docs/DTF/` sai sem problema de entrada; com SPEC sem `COBAIA` na coluna, sai o problema do RF02 e o kit não roda; sem skip | automatizado |
| C06 | RF06: verificação com o kit real | `uv run pytest -q -rs tests/test_origem.py -k fidelidade_outra_pasta` | `fidelidade_a_origem` dá `(True, linha)` com `docs/DTF` no `comando`; SPEC de outra pasta em `draft` em `origin/main` dá `(False, linha)`; `textos_de_origem` devolve o texto; sem skip | automatizado |
| C07 | RF06: sensor da pasta na verificação | Em cópia descartável, `fidelidade_a_origem` volta a passar `docs/<self._codigo>` ao `check_source_docs.py`; pytest de C06; restaurar | Pelo menos 1 failed; restaurado, 0 failed | automatizado |
| C08 | RF07: origem da própria pasta | `uv run pytest -q tests/test_origem.py tests/test_evidencia.py tests/test_pipeline.py` | os testes de hoje verdes, sem mudança de asserção (`git diff 31cdf4e -- tests/test_evidencia.py tests/test_pipeline.py` vazio); o teste novo com `propria_pasta` no nome confere o `comando` idêntico ao de `31cdf4e` | automatizado |
| C09 | RF02, RF03, RF06: mutantes | `uv run python scripts/selftest.py` | todas as mutações mortas, as três novas incluídas | automatizado |
| C10 | Suíte inteira e lint, como no CI | `uv run ruff check . && uv run ruff format --check . && uv run pytest -q` | tudo verde | automatizado |

## Instruções específicas para a IA implementadora

- **Branch e commit:** `feature/sdd-fab-0013-origem-de-outra-pasta`,
  a partir de `origin/develop`, depois do merge desta SDD `approved`.
  Commits com `Refs: SDD-FAB-0013`. Nunca em `main` nem direto em
  `develop`.
- **Teste primeiro** em cada task, com a falha guardada.
- **Arquivos esperados:** só os da coluna `Arquivos` e de "Decomposição em
  tasks". Em `adapters/doc_traceability/central.py`, só o necessário para
  importar `_projetos_da_spec`, sem mudar o comportamento de
  `LeituraDoCentral`.
- **Nomes dos testes:**
  - os do RF01 ao RF03 têm `pasta_das_origens` no nome;
  - os do RF04 ao RF06 têm `outra_pasta`, com `entrada_outra_pasta` no
    RF05 e `fidelidade_outra_pasta` no RF06;
  - o do RF07 tem `propria_pasta`.

  É o que os comandos dos critérios selecionam.
- **Mutantes** em `tests/mutacoes.yaml`, sob `# SDD-FAB-0013`. São três:
  a regra da coluna `Projeto` do RF02, a recusa de duas pastas do RF03 e
  a pasta de `fidelidade_a_origem` do RF06. Cada um tem `procurar` único
  no arquivo.
- **Os testes existentes** de `tests/test_evidencia.py` e
  `tests/test_pipeline.py` não mudam. Em `tests/test_origem.py`, só se
  acrescenta.
- **Não mudar:**
  - o kit e `contracts/*.schema.json`;
  - o núcleo (`fabrica/*.py`);
  - `LeituraDoCentral.specs_aprovadas`;
  - as SDD-FAB-0009 a SDD-FAB-0012 e a SPEC-DTF-0034.
- **Testes** usam o kit da tag 2.8.0 em `FABRICA_FRAMEWORK`. Central e
  projeto ficam em `tmp_path`, com remoto nu onde houver `git fetch`. Não
  chame o GitHub nos testes.
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

Verificação independente completa em `docs/sdd/validation-SDD-FAB-0013.md`. Veredito: **PASS**.

**Verificador independente:** sim. A sessão `session_01RJ9BCpCbjsFCgmHgkudHXs` não implementou esta SDD (`session_01RJ9BCnsTXeT2TDmo576tyr`, PR #78) nem a escreveu (`session_01RJ9BCnjcFf77wZQf5jHdqP`), e não leu o histórico delas, só o HANDOFF e os artefatos do repositório. O pré-check do HANDOFF não foi reaproveitado: todo comando foi rodado de novo. Diff verificado: `bff075f..9305042` (merge-base e head da PR #78). Critérios rodados em `develop` `51ebbdf` (depois de `101e416` veio só o HANDOFF). Kit 2.8.0 em `1d9b16c` (`FABRICA_FRAMEWORK=$HOME/kit-2.8.0`); `fabrica-cobaia` e `fabrica-central-teste` por `git clone --depth 1`, como no CI; o central `doc-traceability-central` em `origin/main` `e39e9c8`. As mutações partiram de uma cópia de `adapters/doc_traceability/__init__.py` no scratchpad e foram restauradas por ela, com `git status` limpo no fim. Não houve `git stash` nem commit.

| Rodada | # | Comando rodado | Saída (resumo) | Sensor | Passou? | Assertion (file:line) | Perfil usado |
|---|---|---|---|---|---|---|---|
| 1 | Fidelidade à origem | `python3 $HOME/kit-2.8.0/_framework/scripts/check_source_docs.py docs/sdd/SDD-FAB-0013.md <central em origin/main e39e9c8>/docs/DTF`; depois, leitura da SPEC-DTF-0034 (Parte 1 e Parte 2) contra a SDD | exit 0, `✅ source_docs de SDD-FAB-0013.md conferem com o registry central.` Item 2: RF01 a RF07 da SPEC, todos com `Projeto` FAB, presentes na SDD com os mesmos RF-IDs. Item 3: nenhum critério relaxado (C01 a C08 repetem o EARS, as mensagens exatas e os casos de borda da SPEC; C02, C03, C07 e C09 são os sensores da estratégia de teste). Item 4: SDD enxuta; o diff confere com as assinaturas da Parte 2 (`pasta_das_origens(self, ids: list[str]) -> tuple[str, list[str]]`, regras na ordem formato → pasta única → registry → RF02; `_registry_central(self, pasta: str \| None = None)`; `origem`, `fidelidade_a_origem` e os demais com a mesma assinatura; `comando` `… <central>/docs/<pasta> (em origin/main)`) | sem teste automatizado (script do kit e leitura) | Sim | `n/a` | n/a |
| 1 | Escopo | `git diff --stat bff075f..9305042` e leitura do diff contra RF01 a RF07 e a Parte 2 da SPEC-DTF-0034 | 4 arquivos (`adapters/doc_traceability/__init__.py`, `tests/test_origem.py`, `tests/test_descoberta.py`, `tests/mutacoes.yaml`), todos na coluna `Arquivos` ou em "Decomposição em tasks"; `central.py` não mudou (só importado); núcleo `fabrica/*.py`, kit e `contracts/` intocados; 0 linhas removidas dos três arquivos de teste. Todo RF tem código e teste. Fora das assinaturas da SPEC, só auxiliares privados (`_ids_de_origem`, `ID_DE_ORIGEM_RE`), sem campo, chave, exceção ou mensagem nova | sem teste automatizado (leitura do diff) | Sim | `n/a` | n/a |
| 1 | C01 | `uv run pytest -q -rs tests/test_origem.py -k pasta_das_origens` | `15 passed, 31 deselected`, sem skip | ver C02 e C03; além disso, `if doc_id not in registry` trocado por `if False`: `2 failed, 13 passed`; restaurado: `15 passed` | Sim | `tests/test_origem.py:447`, `:451`, `:458`, `:466`, `:474`, `:485`, `:495`, `:502`, `:509`, `:516`, `:524` | automatizado |
| 1 | C02 | Cópia no scratchpad; em `pasta_das_origens`, `if self._codigo in _projetos_da_spec(texto):` trocado por `… or True:` (toda SPEC de outra pasta aceita); pytest de C01; restaurar | mutante: `3 failed, 12 passed`; restaurado: `15 passed` | o próprio critério: discrimina | Sim | `tests/test_origem.py:451`, `:458`, `:485` | automatizado |
| 1 | C03 | Cópia no scratchpad; o bloco `if len(pastas) > 1: return "", [...]` retirado; pytest de C01; restaurar | mutante: `1 failed, 14 passed`; restaurado: `15 passed` | o próprio critério: discrimina | Sim | `tests/test_origem.py:495` | automatizado |
| 1 | C04 | `uv run pytest -q tests/test_origem.py tests/test_descoberta.py -k outra_pasta` | `14 passed, 120 deselected` | em `origem`, `pasta_das_origens([doc_id])` trocado por `self._codigo, []`: `4 failed, 10 passed`; restaurado: `14 passed` | Sim | `tests/test_origem.py:536`, `:540`, `:543`; `tests/test_descoberta.py:1240`, `:1243` | automatizado |
| 1 | C05 | `uv run pytest -q -rs tests/test_origem.py -k entrada_outra_pasta` | `3 passed, 43 deselected`, sem skip | `docs_central` de `problemas_de_entrada` trocado para `docs/<self._codigo>`: `1 failed, 2 passed`; recusa antecipada (`if problemas_de_pasta and pasta != self._codigo`) trocada por `if False`: `2 failed, 1 passed`; restaurado: `3 passed` | Sim | `tests/test_origem.py:597`, `:607`, `:610`, `:628`, `:631` | automatizado |
| 1 | C06 | `uv run pytest -q -rs tests/test_origem.py -k fidelidade_outra_pasta` | `3 passed, 43 deselected`, sem skip | ver C07; registry de `_textos_de_origem` trocado para `self._codigo`: `1 failed, 2 passed`; restaurado: `3 passed` | Sim | `tests/test_origem.py:670`, `:672`, `:673`, `:690`, `:693`, `:713` | automatizado |
| 1 | C07 | Cópia no scratchpad; em `fidelidade_a_origem`, `str(arvore / "docs" / pasta),` trocado por `str(arvore / "docs" / self._codigo),`; pytest de C06; restaurar | mutante: `2 failed, 1 passed`; restaurado: `3 passed` | o próprio critério: discrimina | Sim | `tests/test_origem.py:670`, `:690` | automatizado |
| 1 | C08 | `uv run pytest -q tests/test_origem.py tests/test_evidencia.py tests/test_pipeline.py`; `git diff --stat 31cdf4e -- tests/test_evidencia.py tests/test_pipeline.py` | `129 passed`; diff vazio (0 linhas). O `comando` esperado em `test_fidelidade_propria_pasta_comando_igual_ao_de_31cdf4e` confere com o f-string de `31cdf4e` (`adapters/doc_traceability/__init__.py:113`) | sufixo `"(em origin/main)"` trocado por `"(origin/main)"`: `1 failed, 3 passed` (`-k propria_pasta`); restaurado: `4 passed` | Sim | `tests/test_origem.py:724` | automatizado |
| 1 | C09 | `uv run python scripts/selftest.py` | exit 0; `78/78 mutações mortas`, as três da SDD-FAB-0013 incluídas (`SPEC de outra pasta aceita sem o código do projeto na coluna Projeto (RF02)`, `origens em mais de uma pasta do central aceitas (RF03)`, `fidelidade à origem volta a conferir docs/<codigo> (RF06)`) | o próprio critério é de mutação | Sim | `n/a` (agregado) | automatizado |
| 1 | C10 | `uv run ruff check . && uv run ruff format --check . && uv run pytest -q` | `All checks passed!`; `121 files already formatted`; `596 passed, 29 deselected in 161.87s` (marcadores `docker` e `claude` fora, por `addopts`) | os sensores de C01 a C08 | Sim | `n/a` (agregado) | automatizado |

## Rastreabilidade

| Campo | Valor |
|---|---|
| source_docs | SPEC-DTF-0034 |
| Origem do achado | lacuna do RF05 da SPEC-DTF-0032, declarada fora de escopo na SDD-FAB-0010 e na SPEC-DTF-0033 |
| Relaciona | SDD-FAB-0009 (vigia do central), SDD-FAB-0012 (`fidelidade_a_origem`) |

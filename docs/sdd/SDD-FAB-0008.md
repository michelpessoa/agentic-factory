---
id: SDD-FAB-0008
type: SDD
title: "Registry do projeto com documents em fluxo: a redação passa o documents para bloco antes de acrescentar a SDD nova, para o registry seguir YAML válido"
status: implemented
project: "FAB"
owner: "Michel Pessoa"
created: "2026-11-21"
updated: "2026-11-21"
relates_to: [SDD-FAB-0005]
source_docs: []
sizing: "small"
approved_by:
  kind: human
  actor: michelpessoa
  at: "2026-11-21T12:47:18Z"
  content_sha256: "69aa147af589f7ca02c68b081a5cc4db82f14dda0ca66e509ba22e934d218fda"
  evidence: "https://github.com/michelpessoa/fabrica-agentica/pull/55#pullrequestreview-6005275104"
consumption_instructions: "SDD small, sem SPEC de origem: o requisito e o desenho estão aqui. Nasce da observação sobre documents: [] nas rodadas 3 e 4 da verificação independente da SDD-FAB-0005 (docs/sdd/validation-SDD-FAB-0005.md, seção Descompassos encontrados). Os requisitos RF01 a RF03 abaixo são o escopo inteiro: não acrescentar campo, chave, exceção ou mensagem que esta SDD não declara. Teste primeiro, visto falhar. Só a função registrar de adapters/doc_traceability/redacao.py muda; o núcleo (fabrica/descoberta.py) e o kit não mudam."
supersedes: null
superseded_by: null
tags: [descoberta, registry, redacao, yaml, fabrica-agentica]
---

# Registry do projeto com documents em fluxo: a redação passa o documents para bloco antes de acrescentar a SDD nova, para o registry seguir YAML válido

## Resumo executivo

A `registrar` de `adapters/doc_traceability/redacao.py` acrescenta a SDD
nova ao `docs/sdd/registry.yaml` do projeto por append de texto: soma
`  - id: SDD-…` e os demais campos ao fim do arquivo. Isso só dá YAML
válido quando o registry termina em `documents:` vazio ou em `documents:`
em bloco com itens. Com `documents: []`, o resultado é:

```yaml
documents: []
  - id: SDD-ZERO-0001
```

O `yaml.safe_load` do resultado falha com `ParserError`
(`expected <block end>, but found '<block sequence start>'`). O mesmo vale
para `documents:` em fluxo com itens (`documents: [{id: …}]`). O
`validate_doc.py` e o `registry_tools.py` do kit falham igual, e a
descoberta recusa as três tentativas e para em `PARADA`.

Os testes do kit usam `documents: []`, então um projeto que nasce nesse
formato quebra na primeira descoberta. Os testes da fábrica só usam
`documents:` vazio, e por isso o defeito passou. Foi visto nas rodadas 3
e 4 da verificação da SDD-FAB-0005 e reproduzido nesta sessão chamando
`registrar` direto sobre os três formatos: `documents:` dá
`['SDD-ZERO-0002']`; `documents: []` e `documents: [{id: SDD-ZERO-0001, type: SDD}]`
dão `ParserError while parsing a block mapping`.

Esta SDD faz a `registrar` passar `documents` para o formato em bloco,
só quando ele está em fluxo, antes de acrescentar a SDD nova. Nos formatos
que já funcionam, o arquivo segue preservado byte a byte, com o mesmo
texto acrescentado.

## Decisão(ões) de arquitetura aplicável(is)

- **ADR-0012 (fábrica, aceita):** o núcleo não conhece o framework. A
  correção fica no adaptador, em `adapters/doc_traceability/redacao.py`.
  `fabrica/descoberta.py` não muda.
- **Decisões nesta SDD:**
  - **Só normaliza o formato em fluxo.** O registry em bloco não é
    reformatado: comentários, aspas e ordem das chaves dos registries
    existentes ficam como estão. É o mesmo comportamento de hoje.
  - **A troca é localizada pelo próprio parser.** O `yaml.compose` dá o nó
    do valor de `documents` com `flow_style` e as posições de início e fim
    no texto. Só o trecho da chave `documents` até o fim do valor é
    trocado; o resto do arquivo não muda. Expressão regular sobre o texto
    não é usada, porque o fluxo pode ocupar várias linhas.
  - **Os itens já existentes no fluxo são reescritos em bloco** pelo
    `yaml.safe_dump`, na mesma ordem, e a SDD nova entra logo depois
    deles. Comentários dentro do fluxo se perdem nessa troca; é o custo
    aceito, porque o formato em fluxo é o de registry recém-criado.
  - **Fora de escopo:** `documents` ausente, nulo (`documents: ~`) ou com
    outro tipo de valor, e `documents` em bloco que não seja a última chave
    do arquivo. Nenhum deles foi visto, e o comportamento atual nesses
    casos não muda.
  - **O kit não muda.**

## Requisitos consolidados

| RF-ID | Requisito | Critério de aceite (EARS) | Arquivos |
|---|---|---|---|
| RF01 | `documents: []` vira bloco | Quando o registry do projeto tiver `documents: []`, a `registrar` deve gravar um registry que o `yaml.safe_load` lê, com a SDD nova como único item de `documents`, e o validador real do kit deve aceitar a SDD na descoberta. | `adapters/doc_traceability/redacao.py`, `tests/test_redacao.py`, `tests/test_descoberta.py` |
| RF02 | `documents` em fluxo com itens vira bloco | Quando o registry do projeto tiver `documents` em fluxo com itens, a `registrar` deve gravar um registry que o `yaml.safe_load` lê, com os itens existentes na mesma ordem e a SDD nova depois deles. | `adapters/doc_traceability/redacao.py`, `tests/test_redacao.py` |
| RF03 | Formatos em bloco seguem byte a byte | Quando o registry do projeto tiver `documents:` vazio, `documents:` em bloco com itens, ou não existir, a `registrar` deve gravar o mesmo texto de antes desta SDD: o arquivo anterior intacto e a entrada da SDD nova acrescentada no fim. | `adapters/doc_traceability/redacao.py`, `tests/test_redacao.py` |

## Especificação técnica consolidada

**`adapters/doc_traceability/redacao.py` (RF01 a RF03).**

- Função nova do módulo, `_documents_em_bloco(texto: str) -> str`:
  - faz `yaml.compose(texto)`; se a raiz não for `yaml.MappingNode`,
    devolve `texto`;
  - acha o par cuja chave é o escalar `documents`; sem ele, devolve
    `texto`;
  - se o valor não for `yaml.SequenceNode` ou não tiver
    `flow_style` verdadeiro, devolve `texto` (formato em bloco, nulo ou
    outro tipo: nada muda);
  - senão, troca `texto[chave.start_mark.index:valor.end_mark.index]` por
    `"documents:"`, seguido, quando a lista carregada por
    `yaml.safe_load(texto)["documents"]` não for vazia, de `"\n"` e do
    `yaml.safe_dump(lista, allow_unicode=True, sort_keys=False, default_flow_style=False)`
    com cada linha prefixada por dois espaços e sem a quebra de linha
    final, e devolve o texto resultante.
- `registrar`: depois da checagem de id repetido e antes do
  `if not texto.endswith("\n")`, faz `texto = _documents_em_bloco(texto)`.
  A assinatura, a mensagem de `ValueError` e o texto acrescentado não
  mudam.

**`tests/test_redacao.py` (RF01 a RF03).** Testes novos, todos com
`registry` no nome, chamando `escrever_sdd` com `COMPLETO` sobre um
`docs/sdd/registry.yaml` escrito pelo teste:

- `documents: []`: o `yaml.safe_load` do registry gravado lê, e os ids de
  `documents` são só o da SDD nova;
- `documents: [{id: SDD-ZERO-0001, type: SDD, status: draft}]`: lê, e os
  ids são `SDD-ZERO-0001` e a SDD nova, nessa ordem, com o item antigo
  igual ao de antes;
- `documents:` vazio, `documents:` em bloco com um item e registry
  inexistente: o registry gravado começa pelo texto anterior inteiro (para
  o inexistente, pelo cabeçalho de hoje) e o que vem depois é exatamente a
  entrada da SDD nova no formato de hoje.

**`tests/test_descoberta.py` (RF01).** Um teste novo, com `registry` no
nome e o mesmo `skipif` de framework ausente do
`test_rascunho_vira_sdd_que_passa_nos_validadores_reais_num_repo_vazio`:
o `remoto` ganha um commit com `docs/sdd/registry.yaml` em
`project: "ZERO"`, `framework_version: "2.7.0"` e `documents: []`; com
`RunnerFila(rascunho())` e `FonteDocTraceability()`, a descoberta chega a
`AGUARDANDO_APROVACAO` e a `tentativa` da sessão é 1.

## Critérios de aceite / definição de pronto

| # | Critério (origem: RF-ID / contrato) | Comando de verificação | Resultado esperado | Perfil esperado |
|---|---|---|---|---|
| 1 | RF01 e RF02: registry em fluxo vira bloco válido | `uv run pytest -q tests/test_redacao.py -k "registry and fluxo"` | `documents: []` e `documents` em fluxo com um item: YAML válido, ids na ordem da especificação | automatizado |
| 2 | RF03: formatos em bloco seguem byte a byte | `uv run pytest -q tests/test_redacao.py -k "registry and bloco"` | `documents:` vazio, em bloco com item e registry inexistente: texto anterior intacto e entrada de hoje no fim | automatizado |
| 3 | RF01: descoberta com `documents: []` passa nos validadores reais na tentativa 1 | `uv run pytest -q tests/test_descoberta.py -k registry` com `FABRICA_FRAMEWORK` no kit `4293d7a` | `AGUARDANDO_APROVACAO`, `tentativa` 1 | automatizado |
| 4 | Regressão: suíte inteira e lint, como no CI | `uv run ruff check . && uv run ruff format --check . && uv run pytest -q` com o kit em `4293d7a`, `fabrica-cobaia` e o central de teste presentes | tudo verde | automatizado |

## Instruções específicas para a IA implementadora

- Teste primeiro: cada critério acima tem teste visto falhar antes do
  código. Os do critério 2 passam já antes da correção (são de regressão);
  confira que falham com uma correção que reformata sempre.
- Nomes dos testes: os de fluxo com `fluxo` no nome, os de bloco e
  inexistente com `bloco` no nome, para os filtros dos critérios.
- Arquivos esperados: `adapters/doc_traceability/redacao.py`,
  `tests/test_redacao.py` e `tests/test_descoberta.py`, nada além.
- Não altere `fabrica/descoberta.py`, `contracts/*.schema.json`, o
  `docs/sdd/registry.yaml` da fábrica nem o kit.
- Os testes não escrevem em `~/fabrica-central-teste` nem chamam o GitHub.

## Verificação de escopo (nada a mais, nada a menos)

- [x] Todo requisito consolidado acima tem código correspondente.
- [x] Todo arquivo tocado aparece na coluna `Arquivos` dos requisitos.
- [x] Nenhuma abstração, config, feature flag ou refactor extra que não
      foi pedido por nenhum requisito consolidado.

## Evidência de verificação (preencher antes de status `implemented`)

Verificação independente completa em `docs/sdd/validation-SDD-FAB-0008.md`. Veredito: **PASS** (rodada 1).

**Verificador independente:** sim (sessão separada da que implementou, `session_01RJ9BCpfVWSsMkVFRFoFeQr`, sem o histórico dela; diff `f434300..b9b02d5`, os pais do merge `b9b02d5` da PR #56, que entrou sobre `develop` depois do merge `f434300` da PR #55)

| Rodada | # | Comando rodado | Saída (resumo) | Sensor | Passou? | Assertion (file:line) | Perfil usado |
|---|---|---|---|---|---|---|---|
| 1 | Fidelidade à origem | não se aplica: `source_docs: []`, sizing `small` | sem SPEC nem ADR de origem; o requisito e o desenho estão nesta SDD | sem teste automatizado (não se aplica) | Sim | `n/a` | n/a |
| 1 | Escopo | `git diff --stat f434300..b9b02d5`; `git diff --stat f434300..b9b02d5 -- fabrica/descoberta.py contracts/ docs/sdd/registry.yaml` | três arquivos: `adapters/doc_traceability/redacao.py` (+21), `tests/test_descoberta.py` (+14), `tests/test_redacao.py` (+62), todos na coluna `Arquivos`; o segundo comando sai vazio. `_documents_em_bloco` segue a especificação passo a passo (`yaml.compose`, `MappingNode`, chave `documents`, `SequenceNode` com `flow_style`, troca de `chave.start_mark.index` a `valor.end_mark.index`, `safe_dump` com os mesmos argumentos e dois espaços); em `registrar`, só a linha `texto = _documents_em_bloco(texto)` entre a checagem de id e o `endswith("\n")`. Sem função, chave ou mensagem além disso | sem teste automatizado (leitura do diff) | Sim | `n/a` | n/a |
| 1 | 1 | `uv run pytest -q tests/test_redacao.py -k "registry and fluxo"` | `2 passed, 14 deselected` (`test_registry_em_fluxo_vazio_recebe_a_sdd_nova`, `test_registry_em_fluxo_com_item_mantem_a_ordem`) | `redacao.py` de `f434300`: `2 failed` (`ParserError: while parsing a block mapping`); `_documents_em_bloco` devolvendo `texto`: `2 failed`; chamada tirada de `registrar`: `2 failed`; itens do fluxo descartados (`if lista` → `if False`): `1 failed` (`..._com_item_mantem_a_ordem`); restaurado: `2 passed` | Sim | `tests/test_redacao.py:209`, `:217`, `:218` | automatizado |
| 1 | 2 | `uv run pytest -q tests/test_redacao.py -k "registry and bloco"` | `3 passed, 13 deselected` (`..._byte_a_byte[vazio]`, `[com-item]`, `..._inexistente_nasce_em_bloco_como_hoje`) | correção que reformata sempre (checagem de `SequenceNode`/`flow_style` removida): `1 failed` (`[com-item]`: `type: 'SDD'` vira `type: SDD`); `redacao.py` de `f434300`: `3 passed`, como a SDD prevê para testes de regressão; restaurado: `3 passed` | Sim | `tests/test_redacao.py:232`, `:237` | automatizado |
| 1 | 3 | `FABRICA_FRAMEWORK=~/doc-traceability-framework uv run pytest -q tests/test_descoberta.py -k registry` (kit em `4293d7a`) | `3 passed, 73 deselected`; o filtro pega também os dois `test_formato_com_redator_real_le_o_registry_da_base` já existentes; o do critério é `test_registry_em_documents_vazio_em_fluxo_passa_nos_validadores_na_tentativa_1`, sem skip | `redacao.py` de `f434300`: `1 failed` (tentativa 1 recusada, `RunnerFila` sem segunda resposta: `IndexError: pop from empty list`); `_documents_em_bloco` devolvendo `texto`: `1 failed`; chamada tirada de `registrar`: `1 failed`; restaurado: `1 passed` | Sim | `tests/test_descoberta.py:338`, `:339` | automatizado |
| 1 | 4 | `uv run ruff check . && uv run ruff format --check . && uv run pytest -q` (kit em `4293d7a`, `fabrica-cobaia` em `d4e8cf1`, central de teste em `844800d`) | `All checks passed!`; `109 files already formatted`; `499 passed, 29 deselected in 114.98s` | coberto pelos sensores 1 a 3 | Sim | `n/a` (suíte) | automatizado |

## Rastreabilidade

| Campo | Valor |
|---|---|
| source_docs | nenhum (sizing `small`) |
| Origem do achado | SDD-FAB-0005, verificação independente, rodadas 3 e 4, "Descompassos encontrados" (`docs/sdd/validation-SDD-FAB-0005.md`) |
| Relaciona | SDD-FAB-0005 (redação da SDD sob 2.7.0) |

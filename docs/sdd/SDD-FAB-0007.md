---
id: SDD-FAB-0007
type: SDD
title: "Tabela de Requisitos funcionais da SPEC com o cabeçalho do template, para o EARS do kit ler o critério na 3ª coluna"
status: implemented
project: "FAB"
owner: "Michel Pessoa"
created: "2026-11-20"
updated: "2026-11-21"
relates_to: [SDD-FAB-0003, SDD-FAB-0006]
source_docs: []
sizing: "small"
approved_by:
  kind: human
  actor: michelpessoa
  at: "2026-11-20T22:51:06Z"
  content_sha256: "6e69c5be8de1c318f6271cdf0a9635ac7961d2f0aecb9ddc40195e9cb329fb13"
  evidence: "https://github.com/michelpessoa/fabrica-agentica/pull/48#pullrequestreview-6000437218"
consumption_instructions: "SDD small, sem SPEC de origem: o requisito e o desenho estão aqui. Nasce do critério 5 da verificação independente da SDD-FAB-0006 (rodada 2, docs/sdd/validation-SDD-FAB-0006.md). Os requisitos RF01 e RF02 abaixo são o escopo inteiro: não acrescentar campo, chave, exceção ou mensagem que esta SDD não declara. Teste primeiro, visto falhar. O núcleo (fabrica/descoberta.py) não muda: a checagem fica no adaptador, ao lado da das partes (SDD-FAB-0006)."
supersedes: null
superseded_by: null
tags: [descoberta, central, spec, ears, fabrica-agentica]
---

# Tabela de Requisitos funcionais da SPEC com o cabeçalho do template, para o EARS do kit ler o critério na 3ª coluna

## Resumo executivo

O critério 5 da SDD-FAB-0006 é a descoberta real até a PR da SPEC no
central de teste. O owner rodou esse critério (rodada 2 da verificação),
e a descoberta parou na etapa 3. As 3 tentativas foram recusadas com
`critério de RF0N não está em EARS — falta o verbo de obrigação ('deve')`,
e o trecho citado em cada problema era uma lista de caminhos de arquivo.

O `check_ears` do `validate_doc.py` do kit lê o critério sempre na 3ª
coluna da tabela de Requisitos funcionais (`cells[2]`). O template do kit
tem `| RF-ID | Requisito | Critério de aceite (EARS) | Arquivos |`. O
`agents/descobridor.md` pede só "tabela com RF-ID, critério de aceite em
EARS e coluna Arquivos". O agente escreveu a tabela sem a coluna
`Requisito`, e o kit leu `Arquivos` como critério. A mensagem do kit não
diz isso, e o agente repetiu a tabela nas 3 tentativas.

Esta SDD faz duas coisas:

- o descobridor passa a dar o cabeçalho exato da tabela;
- a escrita no central passa a recusar a SPEC cuja tabela tenha outro
  cabeçalho, com uma mensagem que diz qual é o certo. A recusa volta ao
  agente como os outros problemas do documento.

## Decisão(ões) de arquitetura aplicável(is)

- **ADR-0012 (fábrica, aceita):** o núcleo não conhece o framework. A
  checagem fica em `adapters/doc_traceability/central.py`, no
  `EscritaNoCentral.problemas`, ao lado de `_problemas_das_partes`.
  `fabrica/descoberta.py` não muda.
- **Decisões nesta SDD:**
  - **O cabeçalho é o do template do kit, exato:**
    `| RF-ID | Requisito | Critério de aceite (EARS) | Arquivos |`. A
    SPEC-ZERO-0001 e a SPEC-ZERO-0002 já o usam.
  - **Só a primeira tabela da seção `## Requisitos funcionais`.** A seção é
    lida pelo `secao` do compilador, que já ignora cercas de código. Seção
    ausente não ganha problema aqui: o `validate_doc.py` já acusa.
  - **Só SPEC.** RFC não tem essa tabela.
  - **O kit não muda.** Ler o critério pelo nome da coluna, e não pela
    posição, é decisão do kit, para uma versão futura.

## Requisitos consolidados

| RF-ID | Requisito | Critério de aceite (EARS) | Arquivos |
|---|---|---|---|
| RF01 | Descobridor dá o cabeçalho da tabela | Quando o agente entregar `documento` do tipo SPEC, o `agents/descobridor.md` deve pedir a tabela de Requisitos funcionais com o cabeçalho exato `\| RF-ID \| Requisito \| Critério de aceite (EARS) \| Arquivos \|`. | `agents/descobridor.md`, `tests/test_central_escrita.py` |
| RF02 | Escrita no central recusa tabela fora do template | Se o documento for SPEC e a primeira tabela da seção `## Requisitos funcionais` tiver cabeçalho diferente de `\| RF-ID \| Requisito \| Critério de aceite (EARS) \| Arquivos \|`, então `EscritaNoCentral.problemas` deve devolver o motivo, junto dos problemas do `validate_doc.py` e das partes, e a descoberta não abre a PR. RFC não é conferida. | `adapters/doc_traceability/central.py`, `tests/test_central_escrita.py` |

## Especificação técnica consolidada

**`agents/descobridor.md` (RF01).** No item que começa por "`corpo` é o
documento em Markdown", o trecho
`Requisitos funcionais (tabela com RF-ID, critério de aceite em EARS e coluna Arquivos)`
passa a ser:

```
Requisitos funcionais (tabela com o cabeçalho exato `| RF-ID | Requisito | Critério de aceite (EARS) | Arquivos |`, nessa ordem: o validador lê o critério na 3ª coluna)
```

O resto do item e do arquivo não muda.

**`adapters/doc_traceability/central.py` (RF02).**

- Constante do módulo:
  `CABECALHO_RF = "| RF-ID | Requisito | Critério de aceite (EARS) | Arquivos |"`.
- `_problemas_da_tabela_rf(texto: str) -> list[str]`, função do módulo:
  - lê `secao(texto, "Requisitos funcionais")`, importado de
    `adapters.doc_traceability.compilador`; com `None`, devolve `[]`;
  - pega a primeira linha da seção que começa por `|`; sem nenhuma,
    devolve `[]`;
  - compara as células dessa linha (cada uma sem espaços nas pontas) com
    as de `CABECALHO_RF`; diferentes, devolve
    `[f"SPEC com a tabela de Requisitos funcionais fora do template: o cabeçalho deve ser '{CABECALHO_RF}', com o critério EARS na 3ª coluna"]`;
  - iguais, `[]`.
- `EscritaNoCentral.problemas(texto)`: com `dados["type"] == "SPEC"`,
  acrescenta `_problemas_da_tabela_rf(texto)` depois de
  `_problemas_das_partes(texto)`. A assinatura e o resto do método não
  mudam.

**`tests/test_central_escrita.py` (RF01, RF02).**

- O cabeçalho da tabela de `CORPO_SPEC` passa a ser `CABECALHO_RF`. O teste
  `test_montar_corpo_completo_nao_tem_problemas` segue sem edição.
- Testes novos, todos com `cabecalho` no nome:
  - SPEC com a tabela sem a coluna `Requisito`
    (`| RF-ID | Critério de aceite (EARS) | Arquivos |`) devolve a mensagem
    da especificação;
  - SPEC com `Requisito` e `Critério de aceite (EARS)` trocados de lugar
    devolve a mensagem;
  - SPEC com o cabeçalho do template não ganha o problema;
  - RFC não ganha o problema;
  - o `agents/descobridor.md` contém `CABECALHO_RF`.

## Critérios de aceite / definição de pronto

| # | Critério (origem: RF-ID / contrato) | Comando de verificação | Resultado esperado | Perfil esperado |
|---|---|---|---|---|
| 1 | RF01: descobridor dá o cabeçalho | `uv run pytest -q tests/test_central_escrita.py -k "cabecalho and descobridor"` | o teste acha `CABECALHO_RF` em `agents/descobridor.md` | automatizado |
| 2 | RF02: escrita recusa tabela fora do template | `uv run pytest -q tests/test_central_escrita.py -k "cabecalho and not descobridor"` | sem `Requisito` e com colunas trocadas: a mensagem da especificação; cabeçalho do template e RFC: nenhum problema de cabeçalho | automatizado |
| 3 | Regressão: suíte inteira e lint, como no CI | `uv run ruff check . && uv run ruff format --check . && uv run pytest -q` com o kit em `4293d7a`, `fabrica-cobaia` e o central de teste presentes | tudo verde | automatizado |
| 4 | RF01 e RF02 de ponta a ponta, junto com o critério 5 da SDD-FAB-0006 | Roteiro, pelo owner, com o agente real: `uv run python -m fabrica descobrir zero "<ideia medium>"` contra `~/fabrica-central-teste`, com `FABRICA_FRAMEWORK` no kit `4293d7a`, até a PR da SPEC no central de teste | SPEC-ZERO-0003 (ou a seguinte) em `in_review`, com as duas linhas `# Parte` e a tabela de Requisitos funcionais com `CABECALHO_RF` | manual |

## Instruções específicas para a IA implementadora

- Teste primeiro: cada critério automatizado acima tem teste visto
  falhar antes do código.
- Arquivos esperados: `agents/descobridor.md`,
  `adapters/doc_traceability/central.py` e `tests/test_central_escrita.py`,
  nada além.
- Não altere `fabrica/descoberta.py`, `adapters/doc_traceability/compilador.py`,
  `contracts/*.schema.json` nem o kit.
- Não mude `_problemas_das_partes` nem as mensagens da SDD-FAB-0006.
- Não edite a SPEC-ZERO-0001 nem a SPEC-ZERO-0002 no
  `fabrica-central-teste`. Os testes não escrevem em
  `~/fabrica-central-teste` nem chamam o GitHub.

## Verificação de escopo (nada a mais, nada a menos)

- [x] Todo requisito consolidado acima tem código correspondente.
- [x] Todo arquivo tocado aparece na coluna `Arquivos` dos requisitos.
- [x] Nenhuma abstração, config, feature flag ou refactor extra que não
      foi pedido por nenhum requisito consolidado.

## Evidência de verificação (preencher antes de status `implemented`)

Verificação independente completa em `docs/sdd/validation-SDD-FAB-0007.md`. Veredito: **PASS** (rodada 1).

**Verificador independente:** sim (sessão separada da que implementou, `session_01RJ9BCnZLNghyGFghYWc4jC`; diff `a2da298..c1d42ca`, os pais do merge `af2db69` da PR #49)

| Rodada | # | Comando rodado | Saída (resumo) | Sensor | Passou? | Assertion (file:line) | Perfil usado |
|---|---|---|---|---|---|---|---|
| 1 | Fidelidade à origem | não se aplica: `source_docs: []`, sizing `small` | sem SPEC nem ADR de origem; o requisito e o desenho estão nesta SDD | sem teste automatizado (não se aplica) | Sim | `n/a` | n/a |
| 1 | Escopo | `git diff --stat a2da298 c1d42ca`; `git diff --stat a2da298 af2db69 -- fabrica/descoberta.py adapters/doc_traceability/compilador.py contracts/ docs/sdd/SDD-FAB-0006.md` | três arquivos: `adapters/doc_traceability/central.py` (+17 −1), `agents/descobridor.md` (+1 −1), `tests/test_central_escrita.py` (+44 −1), todos na coluna `Arquivos`; o segundo comando sai vazio. `CABECALHO_RF`, `_problemas_da_tabela_rf`, a mensagem e a ordem depois de `_problemas_das_partes` iguais à especificação; texto da SDD contido em `agents/descobridor.md`: `True`. A comparação usa o `_celulas` que já existe no compilador, sem função nova | sem teste automatizado (leitura do diff) | Sim | `n/a` | n/a |
| 1 | 1 | `uv run pytest -q tests/test_central_escrita.py -k "cabecalho and descobridor"` | `1 passed, 51 deselected` | descobridor com o texto antigo ("tabela com RF-ID, critério…"): `1 failed`; cabeçalho com `Requisito` e `Critério` trocados: `1 failed`; restaurado: passa | Sim | `tests/test_central_escrita.py:388` | automatizado |
| 1 | 2 | `uv run pytest -q tests/test_central_escrita.py -k "cabecalho and not descobridor"` | `4 passed, 48 deselected` (sem `Requisito`, colunas trocadas, cabeçalho do template, RFC) | `_problemas_da_tabela_rf` não chamada: `2 failed`; comparando só a quantidade de colunas: `1 failed`; problema devolvido sempre: `1 failed`; conferindo também RFC: `1 failed`; restaurado: `14 passed` em `-k "cabecalho or partes"` | Sim | `tests/test_central_escrita.py:364`, `:371`, `:375`, `:383` | automatizado |
| 1 | 3 | `uv run ruff check . && uv run ruff format --check . && uv run pytest -q` (kit em `4293d7a`, `fabrica-cobaia` e central de teste em `main`, `PYTHONDONTWRITEBYTECODE=1`) | `All checks passed!`; `107 files already formatted`; `490 passed, 29 deselected in 124.74s` | coberto pelos sensores 1 e 2 | Sim | `n/a` (suíte) | automatizado |
| 1 | 4 | `uv run python -m fabrica descobrir zero "<ideia medium>"`, rodado pelo owner na máquina dele, sessão `e3a45134-47ee-4d05-85f9-f13957bb5b92` criada em 2026-11-21T01:32:20Z, 12 s depois do `pull --ff-only` de `develop` para `af2db69` (reflog do owner; `git diff af2db69 -- agents/descobridor.md adapters/doc_traceability/central.py` vazio), kit `4293d7a`. Conferido aqui num clone próprio do central de teste: `git fetch origin pull/8/head`, `grep` no front-matter e nas linhas, `validate_doc.py` do `_framework/` do central (2.7.0), `_problemas_das_partes`, `_problemas_da_tabela_rf` e `compilador._parte_2` sobre o texto da PR | PR michelpessoa/fabrica-central-teste#8, um commit só sobre `main` (`d9d4c86`, autor "Fábrica Agêntica", 2026-11-21T01:36:17Z): SPEC-ZERO-0004 com `status: in_review`, `sizing: "medium"`, `# Parte 1 — Requisito (o QUÊ)` na linha 25, `\| RF-ID \| Requisito \| Critério de aceite (EARS) \| Arquivos \|` na linha 29 (RF01 a RF05), `# Parte 2 — Desenho (o COMO e o ONDE)` na linha 56; aprovada pelos validadores na tentativa 1 de 3 (relato do owner); `validate_doc.py`: `✅ 1 documento(s) passaram`; partes `[]`, tabela `[]`; `_parte_2` começa por `# Parte 2 — Desenho (o COMO e o ONDE)`. Ressalva: o agente acertou o cabeçalho na tentativa 1, então a recusa do RF02 não aconteceu nesta rodada real; ela fica coberta pelo critério 2. Uma descoberta anterior (sessão `ef10e0ac-…`, SPEC-ZERO-0003) rodou sobre `0b05469`, sem esta SDD, e não conta | sem teste automatizado (roteiro manual) | Sim | `n/a` | manual |

## Rastreabilidade

| Campo | Valor |
|---|---|
| source_docs | nenhum (sizing `small`) |
| Origem do achado | SDD-FAB-0006, verificação independente, rodada 2, critério 5 (`docs/sdd/validation-SDD-FAB-0006.md`) |
| Relaciona | SDD-FAB-0003 (escrita no central), SDD-FAB-0006 (partes da SPEC) |

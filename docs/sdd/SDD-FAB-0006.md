---
id: SDD-FAB-0006
type: SDD
title: "SPEC da descoberta com as linhas '# Parte 1' e '# Parte 2' do template, para o compilador da SDD enxuta ler o desenho"
status: implemented
project: "FAB"
owner: "Michel Pessoa"
created: "2026-11-20"
updated: "2026-11-21"
relates_to: [SDD-FAB-0003, SDD-FAB-0005]
source_docs: []
sizing: "small"
approved_by:
  kind: human
  actor: michelpessoa
  at: "2026-11-20T22:04:42Z"
  content_sha256: "2b6cf1977d61160af6f2fbf3c9c2491718559f726e43f339892f5a6599abd6d4"
  evidence: "https://github.com/michelpessoa/fabrica-agentica/pull/45#pullrequestreview-6000002029"
consumption_instructions: "SDD small, sem SPEC de origem: o requisito e o desenho estão aqui. Nasce do critério 9 da verificação independente da SDD-FAB-0005 (rodada 2, docs/sdd/validation-SDD-FAB-0005.md). Os requisitos RF01 a RF03 abaixo são o escopo inteiro: não acrescentar campo, chave, exceção ou mensagem que esta SDD não declara. Teste primeiro, visto falhar. O núcleo (fabrica/descoberta.py) não muda: a checagem fica no adaptador, como as demais do documento do central."
supersedes: null
superseded_by: null
tags: [descoberta, central, spec, documentacao-enxuta, compilador, fabrica-agentica]
---

# SPEC da descoberta com as linhas '# Parte 1' e '# Parte 2' do template, para o compilador da SDD enxuta ler o desenho

## Resumo executivo

A SDD-FAB-0005 ensinou o compilador a resolver a SDD enxuta: o
`especificacao` do contrato é a SPEC de origem da linha `# Parte 2` até o
fim, e a SPEC sem essa linha levanta `SddInvalida`
(`SPEC-<id> sem '# Parte 2'`), como a SPEC-DTF-0031 pede. A verificação
independente dela (rodada 2, critério 9) mostrou que a própria fábrica
escreve SPECs sem a linha. A descoberta sem `--origem`, em sizing
`medium`, abre a SPEC no central (SDD-FAB-0003), e o
`agents/descobridor.md` lista as seções da SPEC sem `# Parte 1` e sem
`# Parte 2`. O `validate_doc.py` do kit aceita a SPEC assim. As duas
SPECs `approved` do `fabrica-central-teste` (SPEC-ZERO-0001 e
SPEC-ZERO-0002) saíram desse caminho. Com origem nelas, a descoberta
enxuta recusa as três tentativas e para em `PARADA`.

Esta SDD faz a SPEC da descoberta seguir o template do kit nesse ponto:

- o descobridor passa a pedir as duas linhas, na posição do template;
- a escrita no central passa a recusar a SPEC sem elas, antes de abrir a
  PR. A recusa volta ao agente como os outros problemas do documento.

## Decisão(ões) de arquitetura aplicável(is)

- **ADR-0012 (fábrica, aceita):** o núcleo não conhece o framework. A
  checagem fica em `adapters/doc_traceability/central.py`, no
  `EscritaNoCentral.problemas`, que a descoberta já chama e cujos motivos
  já voltam ao agente. `fabrica/descoberta.py` não muda.
- **SPEC-DTF-0031 (approved), RF16:** o compilador lê a Parte 2 a partir
  da linha `# Parte 2`. Esta SDD não muda o compilador nem o contrato da
  SPEC. Ela corrige quem produz a SPEC.
- **Decisões nesta SDD:**
  - **A linha é reconhecida como o compilador a reconhece.** Início de
    linha `# Parte 1` ou `# Parte 2`, fora de cercas de código, pelo
    mesmo `_sem_cercas_de_codigo` do compilador. O descobridor é
    instruído com o texto exato do template:
    `# Parte 1 — Requisito (o QUÊ)` e
    `# Parte 2 — Desenho (o COMO e o ONDE)`.
  - **Só SPEC.** RFC não tem Parte 1 nem Parte 2 no template e não é
    origem de SDD enxuta.
  - **SPECs existentes ficam como estão.** SPEC-ZERO-0001 e
    SPEC-ZERO-0002 não são editadas. O critério 9 da SDD-FAB-0005 passa
    a rodar contra uma SPEC nova, escrita pela descoberta com esta SDD.
  - **O kit não muda aqui.** Exigir as duas linhas no `validate_doc.py`
    é decisão do kit, para uma versão futura. Esta SDD não depende dela.

## Requisitos consolidados

| RF-ID | Requisito | Critério de aceite (EARS) | Arquivos |
|---|---|---|---|
| RF01 | Descobridor pede as partes do template | Quando o agente entregar `documento` do tipo SPEC, o `agents/descobridor.md` deve pedir o corpo na ordem `# <titulo>`, Objetivo, a linha `# Parte 1 — Requisito (o QUÊ)`, Requisitos funcionais, Requisitos transversais (sweep), Fora de escopo, a linha `# Parte 2 — Desenho (o COMO e o ONDE)`, Contratos técnicos e Estratégia de teste. | `agents/descobridor.md`, `tests/test_central_escrita.py` |
| RF02 | Escrita no central recusa SPEC sem as partes | Se o documento for SPEC e não tiver, em início de linha e fora de cerca de código, `# Parte 1` ou `# Parte 2`, ou tiver `# Parte 2` antes de `# Parte 1`, então `EscritaNoCentral.problemas` deve devolver o motivo, junto dos problemas do `validate_doc.py`, e a descoberta não abre a PR. RFC não é conferida. | `adapters/doc_traceability/central.py`, `tests/test_central_escrita.py` |
| RF03 | SPEC escrita é lida pelo compilador | Quando a escrita no central montar uma SPEC sem problemas, o `_parte_2` do compilador deve devolver o texto a partir de `# Parte 2`, sem `None`. | `tests/test_central_escrita.py` |

## Especificação técnica consolidada

**`agents/descobridor.md` (RF01).** O item que começa por "`corpo` é o
documento em Markdown" passa a dizer, para a SPEC:

```
Na SPEC: Objetivo; a linha `# Parte 1 — Requisito (o QUÊ)`; Requisitos funcionais (tabela com RF-ID, critério de aceite em EARS e coluna Arquivos), Requisitos transversais (sweep) e Fora de escopo; a linha `# Parte 2 — Desenho (o COMO e o ONDE)`; Contratos técnicos e Estratégia de teste. As duas linhas `# Parte` são obrigatórias: a SDD enxuta lê o desenho a partir de `# Parte 2`.
```

O resto do item (a RFC) e o resto do arquivo não mudam.

**`adapters/doc_traceability/central.py` (RF02).**

- Constantes do módulo:
  `PARTE_1 = "# Parte 1 — Requisito (o QUÊ)"` e
  `PARTE_2 = "# Parte 2 — Desenho (o COMO e o ONDE)"`.
- `_problemas_das_partes(texto: str) -> list[str]`, função do módulo:
  - sobre `_sem_cercas_de_codigo(texto)`, importado de
    `adapters.doc_traceability.compilador`, procura
    `re.search(r"^# Parte 1\b", ..., re.MULTILINE)` e o mesmo com
    `Parte 2`;
  - para cada linha ausente, o problema
    `f"SPEC sem a linha '{PARTE_1}' do template"` ou
    `f"SPEC sem a linha '{PARTE_2}' do template: a SDD enxuta lê o desenho a partir dela"`;
  - com as duas presentes e `# Parte 2` antes de `# Parte 1`, o problema
    `"SPEC com '# Parte 2' antes de '# Parte 1'"`;
  - senão, `[]`.
- `EscritaNoCentral.problemas(texto)`: guarda a lista do
  `validar_documento` como hoje e, com `dados["type"] == "SPEC"`,
  acrescenta `_problemas_das_partes(texto)` ao fim. A assinatura e o
  resto do método não mudam.

**`tests/test_central_escrita.py` (RF01 a RF03).**

- `CORPO_SPEC` ganha as duas linhas na posição do RF01. O teste
  `test_montar_corpo_completo_nao_tem_problemas` segue sem edição.
- Testes novos, todos com `partes` no nome:
  - SPEC sem `# Parte 2`, sem `# Parte 1` e com a ordem invertida: cada
    uma devolve a mensagem da especificação;
  - `# Parte 2` só dentro de uma cerca de código conta como ausente;
  - RFC sem as linhas não ganha esse problema;
  - a SPEC montada com `CORPO_SPEC`, sem problemas, dá
    `compilador._parte_2(texto)` começando por `PARTE_2`;
  - o `agents/descobridor.md` contém `PARTE_1` e `PARTE_2`, nessa ordem.

## Critérios de aceite / definição de pronto

| # | Critério (origem: RF-ID / contrato) | Comando de verificação | Resultado esperado | Perfil esperado |
|---|---|---|---|---|
| 1 | RF01: descobridor pede as duas linhas na ordem | `uv run pytest -q tests/test_central_escrita.py -k "partes and descobridor"` | o teste acha `PARTE_1` antes de `PARTE_2` em `agents/descobridor.md` | automatizado |
| 2 | RF02: escrita recusa SPEC sem as partes | `uv run pytest -q tests/test_central_escrita.py -k "partes and not descobridor and not compilador"` | sem `# Parte 2`, sem `# Parte 1`, com a ordem invertida e com `# Parte 2` só em cerca: a mensagem da especificação; RFC sem as linhas: nenhum problema de parte | automatizado |
| 3 | RF03: SPEC escrita é lida pelo compilador | `uv run pytest -q tests/test_central_escrita.py -k "partes and compilador"` | `_parte_2` da SPEC montada começa por `# Parte 2 — Desenho (o COMO e o ONDE)` | automatizado |
| 4 | Regressão: suíte inteira e lint, como no CI | `uv run ruff check . && uv run ruff format --check . && uv run pytest -q` com o kit em `4293d7a`, `fabrica-cobaia` e o central de teste presentes | tudo verde | automatizado |
| 5 | RF01 a RF03 de ponta a ponta | Roteiro, pelo owner, com o agente real: `uv run python -m fabrica descobrir zero "<ideia medium>"` contra `~/fabrica-central-teste`, até a PR da SPEC no central de teste | SPEC-ZERO-0003 (ou a seguinte) em `in_review` com as duas linhas `# Parte`; depois de `approved` pela review, ela serve de origem para o critério 9 da SDD-FAB-0005 | manual |

## Instruções específicas para a IA implementadora

- Teste primeiro: cada critério automatizado acima tem teste visto
  falhar antes do código.
- Arquivos esperados: `agents/descobridor.md`,
  `adapters/doc_traceability/central.py` e `tests/test_central_escrita.py`,
  nada além.
- Não altere `fabrica/descoberta.py`, `adapters/doc_traceability/compilador.py`,
  `contracts/*.schema.json` nem o kit.
- Não edite a SPEC-ZERO-0001 nem a SPEC-ZERO-0002 no
  `fabrica-central-teste`. Os testes não escrevem em
  `~/fabrica-central-teste` nem chamam o GitHub.

## Verificação de escopo (nada a mais, nada a menos)

- [x] Todo requisito consolidado acima tem código correspondente.
- [x] Todo arquivo tocado aparece na coluna `Arquivos` dos requisitos.
- [x] Nenhuma abstração, config, feature flag ou refactor extra que não
      foi pedido por nenhum requisito consolidado.

## Evidência de verificação (preencher antes de status `implemented`)

Verificação independente completa em `docs/sdd/validation-SDD-FAB-0006.md`. Veredito da rodada 1: **pendente**. Os critérios 1 a 4 passam, com sensor, e o código cobre RF01 a RF03 sem nada a mais. O critério 5 é manual, do owner, e não foi rodado. A SDD segue `approved` até o owner rodar o critério 5 e o resultado entrar nesta tabela. Rodada 2: **FAIL** no critério 5, por causa na especificação. A descoberta parou na etapa 3 sem abrir a PR: o agente escreveu a tabela de Requisitos funcionais com três colunas, o `validate_doc.py` leu `Arquivos` como critério e recusou as 3 tentativas. O texto do `descobridor.md` (o desta SDD) não dá o cabeçalho da tabela. Por decisão do owner, a correção vai para a SDD-FAB-0007. Rodada 3: **PASS**. Com a SDD-FAB-0007 em `develop` (`af2db69`), a descoberta real do owner abriu a SPEC-ZERO-0004 em `in_review` com as duas linhas `# Parte` e o `_parte_2` do compilador lê o desenho dela. A SDD passa a `implemented`.

**Verificador independente:** sim (sessão separada, sem o histórico da que implementou; diff `b736c77..d1d4320`, o primeiro pai e o segundo pai do merge `84fa72c` da PR #46)

| Rodada | # | Comando rodado | Saída (resumo) | Sensor | Passou? | Assertion (file:line) | Perfil usado |
|---|---|---|---|---|---|---|---|
| 1 | Fidelidade à origem | não se aplica: `source_docs: []`, sizing `small` | sem SPEC nem ADR de origem; o requisito e o desenho estão nesta SDD | sem teste automatizado (não se aplica) | Sim | `n/a` | n/a |
| 1 | Escopo | `git diff --stat b736c77 d1d4320`; `git diff --stat b736c77 84fa72c -- fabrica/descoberta.py adapters/doc_traceability/compilador.py contracts/` | três arquivos: `adapters/doc_traceability/central.py` (+24 −2), `agents/descobridor.md` (+1 −1), `tests/test_central_escrita.py` (+89 −3), todos na coluna `Arquivos`; o segundo comando sai vazio. O kit é outro repositório e a PR não tem arquivo dele. Constantes, `_problemas_das_partes`, mensagens e o texto do descobridor iguais à especificação (texto da SDD contido em `agents/descobridor.md`: `True`) | sem teste automatizado (leitura do diff) | Sim | `n/a` | n/a |
| 1 | 1 | `uv run pytest -q tests/test_central_escrita.py -k "partes and descobridor"` | `1 passed, 46 deselected` | linha `# Parte 2` tirada do `descobridor.md`: `1 failed`; linha `# Parte 1` tirada (fica só a 2): `1 failed`; restaurado: passa | Sim | `tests/test_central_escrita.py:345` | automatizado |
| 1 | 2 | `uv run pytest -q tests/test_central_escrita.py -k "partes and not descobridor and not compilador"` | `7 passed, 40 deselected` (sem `# Parte 2`, sem `# Parte 1`, sem as duas, ordem invertida, `# Parte 2` só em cerca, `# Parte 2` fora do início da linha, RFC) | sem o problema de `# Parte 2`: `4 failed`; sem o de `# Parte 1`: `2 failed`; sem a ordem: `1 failed`; sem tirar as cercas: `1 failed`; regex sem `^` e sem `MULTILINE`: `1 failed`; conferindo também RFC: `1 failed`; `_problemas_das_partes` não chamada em `problemas`: `6 failed`; restaurado: `7 passed` | Sim | `tests/test_central_escrita.py:289`, `:295`, `:302`, `:312`, `:318`, `:328` | automatizado |
| 1 | 3 | `uv run pytest -q tests/test_central_escrita.py -k "partes and compilador"` | `1 passed, 46 deselected` | `PARTE_2` diferente do template: `1 failed`; `compilador._parte_2` devolvendo `None` (mutação local, restaurada): `1 failed`; restaurado: passa | Sim | `tests/test_central_escrita.py:339` | automatizado |
| 1 | 4 | `uv run ruff check . && uv run ruff format --check . && uv run pytest -q` (kit em `4293d7a`, `fabrica-cobaia` em `d4e8cf1`, central de teste em `f745c8a`) | `All checks passed!`; `105 files already formatted`; `485 passed, 29 deselected in 106.75s`; central de teste sem mudança (`git status --porcelain` vazio) | coberto pelos sensores 1 a 3 | Sim | `n/a` (suíte) | automatizado |
| 1 | 5 | sem execução na rodada 1: roteiro manual do owner com o agente real, até a SPEC-ZERO-0003 em `in_review` no central de teste (executado nas rodadas 2 e 3, linhas abaixo) | pendente do owner na rodada 1 | sem teste automatizado (roteiro manual) | Pendente na rodada 1 | `n/a` | manual |
| 2 | 5 | `uv run python -m fabrica descobrir zero "Avisar o responsável por e-mail quando um cadastro mudar, com histórico das mudanças"`, rodado pelo owner na máquina dele em 2026-11-20 sobre `develop` em `0b05469`, com `FABRICA_FRAMEWORK` no kit `4293d7a` e o central de teste em `main` atualizado (sessão `222bb219-8bf5-4ea1-9d46-f9eaa3c48b10`); saída colada pelo owner, conferida aqui contra o `check_ears` do `validate_doc.py` do kit | 4 rodadas de perguntas; "O agente entregou um rascunho de SPEC, tamanho medium"; tentativas 1, 2 e 3 recusadas com os mesmos 7 problemas, `SPEC-ZERO-0003: critério de RF0N não está em EARS — falta o verbo de obrigação ('deve')`, de RF01 a RF07, cada um citando caminhos de arquivo (`'cmd/zero/main.go, internal/cliente/servico.go, …'`); "Parada na etapa 3/6 Validar … Nada foi gravado na base nem no central". Nenhum problema de `# Parte` na última tentativa. Causa: o `check_ears` lê o critério na 3ª coluna (`cells[2]`, `validate_doc.py:440`, template `\| RF-ID \| Requisito \| Critério de aceite (EARS) \| Arquivos \|`); o agente omitiu `Requisito`, e a 3ª coluna virou `Arquivos`. O `agents/descobridor.md:9` pede só "tabela com RF-ID, critério de aceite em EARS e coluna Arquivos", texto que vem da SDD-FAB-0003 e que esta SDD manteve | sem teste automatizado (roteiro manual) | Não | `n/a` | manual |
| 3 | 5 | `uv run python -m fabrica descobrir zero "<ideia medium>"`, rodado pelo owner na máquina dele, sessão `e3a45134-47ee-4d05-85f9-f13957bb5b92` criada em 2026-11-21T01:32:20Z, 12 s depois do `pull --ff-only` de `develop` para `af2db69` (reflog do owner; `git diff af2db69 -- agents/descobridor.md adapters/doc_traceability/central.py` vazio), kit `4293d7a`. Conferido aqui num clone próprio do central de teste: `git fetch origin pull/8/head`, `grep` no front-matter e nas linhas, `validate_doc.py` do `_framework/` do central (2.7.0), `_problemas_das_partes`, `_problemas_da_tabela_rf` e `compilador._parte_2` sobre o texto da PR. O código desta SDD é o mesmo desde `84fa72c` | PR michelpessoa/fabrica-central-teste#8, um commit só sobre `main` (`d9d4c86`, autor "Fábrica Agêntica", 2026-11-21T01:36:17Z): SPEC-ZERO-0004 com `status: in_review`, `sizing: "medium"`, `# Parte 1 — Requisito (o QUÊ)` na linha 25, `\| RF-ID \| Requisito \| Critério de aceite (EARS) \| Arquivos \|` na linha 29 (RF01 a RF05), `# Parte 2 — Desenho (o COMO e o ONDE)` na linha 56; aprovada pelos validadores na tentativa 1 de 3 (relato do owner); `validate_doc.py`: `✅ 1 documento(s) passaram`; partes `[]`, tabela `[]`; `_parte_2` começa por `# Parte 2 — Desenho (o COMO e o ONDE)`. A SPEC-ZERO-0003 (sessão `ef10e0ac-…`, sobre `0b05469`) também saiu com as duas linhas, mas o owner a descartou como evidência | sem teste automatizado (roteiro manual) | Sim | `n/a` | manual |

## Rastreabilidade

| Campo | Valor |
|---|---|
| source_docs | nenhum (sizing `small`) |
| Origem do achado | SDD-FAB-0005, verificação independente, rodada 2, critério 9 (`docs/sdd/validation-SDD-FAB-0005.md`) |
| Relaciona | SDD-FAB-0003 (escrita no central), SDD-FAB-0005 (compilador da SDD enxuta) |

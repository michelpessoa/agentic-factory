---
id: SDD-FAB-0011
type: SDD
title: "Correções pequenas do vigia e da descoberta: número da PR da base no aviso com teste que discrimina e branch da PR da base sem o prefixo duplicado"
status: approved
project: "FAB"
owner: "Michel Pessoa"
created: "2026-11-24"
updated: "2026-11-24"
relates_to: [SDD-FAB-0009, SDD-FAB-0010]
source_docs: []
sizing: "small"
approved_by:
  kind: human
  actor: michelpessoa
  at: "2026-11-24T00:50:40Z"
  content_sha256: "c4002ff639ad5e5ba4ecd755fbd2873f0709d0212f3e911c5597ec90db488772"
  evidence: "https://github.com/michelpessoa/fabrica-agentica/pull/67#pullrequestreview-6031932233"
consumption_instructions: "SDD small, sem SPEC de origem: o requisito e o desenho estão aqui. Nasce da ressalva do A08 da verificação rodada 2 da SDD-FAB-0009 e do nome da branch visto no C12 da SDD-FAB-0010 (docs/sdd/validation-SDD-FAB-0009.md e docs/sdd/validation-SDD-FAB-0010.md). Os requisitos RF01 e RF02 e as mudanças de 'Especificação técnica consolidada' são o escopo inteiro: não acrescentar campo, tabela, chave, exceção ou mensagem que esta SDD não declara. Teste primeiro, visto falhar. O passo 0 'Fidelidade à origem' na verificação da fábrica NÃO é escopo desta SDD: ele tem SPEC própria no central."
supersedes: null
superseded_by: null
tags: [vigia, descoberta, avisos, publicacao, verificacao, fabrica-agentica]
---

# Correções pequenas do vigia e da descoberta: número da PR da base no aviso com teste que discrimina e branch da PR da base sem o prefixo duplicado

## Resumo executivo

Duas pendências pequenas ficaram depois das SDD-FAB-0009 e SDD-FAB-0010, as
duas já `implemented`:

- **O número da PR da base no aviso não tem teste que o discrimine.** Na
  rodada 2 da verificação da SDD-FAB-0009 (A08), o mutante que troca o
  `pr` por `None` na chamada de `_avisar` de `Vigia._compilar` sobreviveu.
  O código passa o número (`fabrica/vigia.py:204`), mas o único teste
  (`test_avisos_publicacao_recusada_avisa_com_a_pr`) usa uma exceção falsa
  com `#9` no próprio texto. O RF10 da SPEC-DTF-0032 pede o número da PR
  quando houver.
- **A branch da PR da base sai com o prefixo duplicado.** No C12 da
  SDD-FAB-0010, a SDD-COBAIA-0013 entrou pela branch
  `feature/sdd-sdd-cobaia-0013-…`. `Descoberta._abrir_pr` monta
  `feature/sdd-{sdd_id.lower()}-…`, e o `sdd_id` já começa com `SDD-`. O
  pipeline monta `feature/{sdd_id.lower()}-…`
  (`fabrica/pipeline.py:509`), sem a duplicação.

Esta SDD acrescenta o teste e o mutante do primeiro caso e corrige o nome
da branch do segundo.

## Decisão(ões) de arquitetura aplicável(is)

- **ADR-0012 (fábrica, aceita):** o núcleo não conhece o framework. Nada
  aqui muda isso.
- **Decisões nesta SDD:**
  - **RF01 só muda testes.** O código de `Vigia._compilar` já passa o
    número. Falta o teste com motivo sem `#` e o mutante em
    `tests/mutacoes.yaml`.
  - **RF02 segue a convenção do pipeline:** `feature/<sdd_id minúsculo>-…`,
    como em `Pipeline._ramo`. As branches já abertas com o nome antigo não
    são renomeadas.
- **Fora de escopo:**
  - **O passo 0 "Fidelidade à origem" na etapa `VERIFY_SDD`.** É o que
    levou a execução `0e5248d0…` da SDD-COBAIA-0013 a
    `PARADA_ESPECIFICACAO`. Toca o pipeline, o adaptador, o revisor e a
    gravação da evidência, e muda o comportamento externo do pipeline.
    Pelo critério de sizing, é `medium` e tem SPEC própria no central.
  - **A lacuna do RF05 da SPEC-DTF-0032** (SPEC de outro projeto pela
    coluna `Projeto`).

## Requisitos consolidados

| RF-ID | Origem | Requisito (resumo) | Arquivos |
|---|---|---|---|
| RF01 | — | Se a publicação por política de uma SDD compilada falhar e a sessão tiver o número da PR, então o vigia deve avisar com `(PR #<número>)`, mesmo quando o texto do motivo não o traz; um teste com motivo sem `#` deve falhar se o número não chegar ao aviso. | `tests/test_vigia_central.py`, `tests/mutacoes.yaml` |
| RF02 | — | Quando a descoberta abrir a PR da SDD na base, a branch deve ser `feature/<sdd_id em minúsculas>-<8 primeiros caracteres da sessão>`, sem `sdd-` repetido. | `fabrica/descoberta.py`, `tests/test_descoberta.py`, `tests/mutacoes.yaml` |

## Especificação técnica consolidada

**`fabrica/descoberta.py` (RF02).** Em `Descoberta._abrir_pr`, a linha
`ramo = f"feature/sdd-{sdd_id.lower()}-{sessao[:8]}"` passa a
`ramo = f"feature/{sdd_id.lower()}-{sessao[:8]}"`. Nada mais em
`_abrir_pr` muda: commit, push, título e corpo da PR.

**Testes.**

- `tests/test_vigia_central.py` (RF01):
  `test_avisos_publicacao_recusada_sem_numero_no_motivo_avisa_com_a_pr`.
  `DescobertaFalsa(erro_publicar=DescobertaInvalida("checks vermelhos"))`,
  cuja sessão já devolve `pr: 9` em `dados`. O aviso contém
  `SPEC-ZERO-0001 (PR #9): checks vermelhos`.
- `tests/test_descoberta.py` (RF02):
  `test_branch_da_pr_da_base_sem_prefixo_duplicado`. Depois de
  `d.aprovar(sessao)`, `github.prs[0]` começa com
  `feature/sdd-zero-0001-` e não contém `sdd-sdd-`.
- `tests/mutacoes.yaml`, duas entradas novas sob `# SDD-FAB-0011`:
  - `fabrica/vigia.py`: `self._avisar(notificador, spec_id, str(erro), pr)`
    trocado por `self._avisar(notificador, spec_id, str(erro), None)`,
    teste `tests/test_vigia_central.py`;
  - `fabrica/descoberta.py`: `ramo = f"feature/{sdd_id.lower()}-{sessao[:8]}"`
    trocado por `ramo = f"feature/sdd-{sdd_id.lower()}-{sessao[:8]}"`,
    teste `tests/test_descoberta.py`.

## Decomposição em tasks

| # | Task | RF(s) de origem | Arquivos tocados | Depende de (#) |
|---|---|---|---|---|
| 1 | Teste do número da PR da base no aviso | RF01 | `tests/test_vigia_central.py` | |
| 2 | Branch da PR da base sem prefixo duplicado | RF02 | `fabrica/descoberta.py`, `tests/test_descoberta.py` | |
| 3 | Mutantes novos | RF01, RF02 | `tests/mutacoes.yaml` | 1, 2 |

## Critérios de aceite / definição de pronto

Executar na raiz da fábrica, na branch de implementação, com o kit da tag
2.8.0 (`1d9b16cf89d8ef63852a26eafce668966b168447`) em `FABRICA_FRAMEWORK`
e `fabrica-cobaia` e `fabrica-central-teste` presentes, como no CI.

| # | Critério (origem: RF-ID / contrato) | Comando de verificação | Resultado esperado | Perfil esperado |
|---|---|---|---|---|
| C01 | RF01: número da PR da base no aviso | `uv run pytest -q tests/test_vigia_central.py -k avisos` | aviso `SPEC-ZERO-0001 (PR #9): checks vermelhos` com motivo sem `#`; 0 failed | automatizado |
| C02 | RF01: sensor do número | Em cópia descartável, `str(erro), pr)` trocado por `str(erro), None)` em `Vigia._compilar`; pytest de C01; restaurar | Pelo menos 1 failed; restaurado, 0 failed | automatizado |
| C03 | RF02: nome da branch | `uv run pytest -q tests/test_descoberta.py -k branch` | branch começa com `feature/sdd-zero-0001-`, sem `sdd-sdd-`; 0 failed | automatizado |
| C04 | RF02: sensor do nome | Em cópia descartável, a linha do `ramo` volta a `feature/sdd-{sdd_id.lower()}-…`; pytest de C03; restaurar | Pelo menos 1 failed; restaurado, 0 failed | automatizado |
| C05 | RF01, RF02: mutantes | `uv run python scripts/selftest.py` | todas as mutações mortas, as duas novas incluídas | automatizado |
| C06 | Suíte inteira e lint, como no CI | `uv run ruff check . && uv run ruff format --check . && uv run pytest -q` | tudo verde | automatizado |

## Instruções específicas para a IA implementadora

- **Branch e commit:** `feature/sdd-fab-0011-aviso-da-base-e-branch`, a
  partir de `origin/develop`, depois do merge desta SDD `approved`.
  Commits com `Refs: SDD-FAB-0011`. Nunca em `main` nem direto em
  `develop`.
- **Teste primeiro** em cada task, com a falha guardada. O teste do RF01
  passa já com o código de hoje; a falha que conta é a do mutante (C02).
- **Arquivos esperados:** os da coluna `Arquivos`, nada além.
- **Não acrescentar** tabela, coluna, chave, exceção ou mensagem que esta
  SDD não declara.
- **Testes** usam o kit da tag 2.8.0 em `FABRICA_FRAMEWORK`. Não chame o
  GitHub nos testes automatizados.
- **Evidência de verificação** só por verificador independente, numa
  sessão que não implementou esta SDD.

## Verificação de escopo (nada a mais, nada a menos)

Antes de marcar `implemented`, confirme as duas direções — SDD incompleta
tanto quanto SDD estourada são falha:
- [ ] Todo requisito consolidado acima tem código ou teste correspondente.
- [ ] Todo arquivo tocado aparece na coluna `Arquivos` dos requisitos ou
      das tasks.
- [ ] Nenhuma abstração, config, feature flag ou refactor extra que não
      foi pedido por nenhum requisito consolidado.

## Evidência de verificação (preencher antes de status `implemented`)

Preenchida pela skill `verify-sdd`, em sessão separada da que implementou.

**Verificador independente:** {sim | não — mesma sessão que implementou}

| # | Comando rodado | Saída (resumo) | Sensor | Passou? | Assertion (file:line) | Perfil usado |
|---|---|---|---|---|---|---|

## Rastreabilidade

| Campo | Valor |
|---|---|
| source_docs | nenhum (sizing `small`) |
| Origem dos achados | SDD-FAB-0009, verificação rodada 2 (A08); SDD-FAB-0010, C12 (nome da branch) |
| Relaciona | SDD-FAB-0009, SDD-FAB-0010 |

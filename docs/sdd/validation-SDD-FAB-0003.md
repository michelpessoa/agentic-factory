# Verificação — SDD-FAB-0003

- **Veredito:** PASS (rodada 2; a rodada 1 reprovou só o passo 0, Fidelidade à origem)
- **Diff verificado:** 6f259ad..506ecda (fábrica, branch `sdd/SDD-FAB-0003-impl`, PR michelpessoa/fabrica-agentica#39). O código é o mesmo de `460b4cb`: `git diff --stat 460b4cb 506ecda` mostra só `docs/sdd/SDD-FAB-0003.md`.
- **Verificador independente:** sim (subagente separado, sem ler o histórico da sessão que implementou)
- **Ambiente:** kit em efe1c71e96bf72d5627a69f21fa8655c8c810425 (2.6.0) via `FABRICA_FRAMEWORK`; `~/projetos/fabrica-cobaia`; `~/fabrica-central-teste` em 658cecd; `doc-traceability-central` em 81538f7; 2026-11-19.

| Rodada | Critério | Comando rodado | Saída (resumo) | Sensor | Passou? |
|---|---|---|---|---|---|
| 2 | Fidelidade à origem (SPEC-DTF-0030, ADR-DTF-0008) | `check_source_docs.py docs/sdd/SDD-FAB-0003.md ~/doc-traceability-central/docs/DTF`; leitura da SPEC e da ADR | exit 0; RF08 a RF13 e o passo 6 do kit representados; nada relaxado; divergências de contrato declaradas em "Decisões nesta compilação"; `approval_hash.py` = `db205eb8…` = `approved_by` | sem teste automatizado (script e leitura) | Sim |
| 1 | 1 (RF01) | grep em `projetos/*.yaml` e no CI; `framework_check.py --auto` e grep de `approvers` no central de teste | três `2.6.0`; `efe1c71…`; framework_check verde; `approvers: [michelpessoa]` nos dois | `zero.yaml` em 2.5.0: `test_framework_versao` 1 failed; central com documento divergente: exit 1 | Sim |
| 1 | 2 (RF02) | `uv run pytest -q tests/test_regras.py -k central` | 2 passed | 3 mutações: 2 failed cada | Sim |
| 1 | 3 (RF02) | `uv run pytest -q tests/test_descoberta.py -k documento` | 13 passed | 9 mutações (8 em `descoberta.py`, 1 no `descobridor.md`): 1 a 3 failed cada | Sim |
| 1 | 4 (RF03) | `uv run pytest -q tests/test_central_escrita.py -k montar` | 6 passed | 5 mutações: 1 a 3 failed cada | Sim |
| 1 | 5 (RF04) | `uv run pytest -q tests/test_central_escrita.py -k abrir` | 4 passed | 6 mutações: 1 failed cada | Sim |
| 1 | 6 (RF05) | `uv run pytest -q tests/test_central_escrita.py -k conferir` | 12 passed | 5 mutações: 1 a 3 failed cada | Sim |
| 1 | 7 (RF06) | `uv run pytest -q tests/test_central_escrita.py -k integrar` | 10 passed | 9 mutações, inclusive a reversão do `460b4cb`: 1 a 7 failed cada | Sim |
| 1 | 8 (RF07) | `uv run pytest -q tests/test_central_escrita.py -k executor` | 2 passed | 4 mutações: 1 a 2 failed cada | Sim |
| 1 | 9 (RF04-RF06) | `uv run pytest -q tests/test_publicacao.py -k documento` | 25 passed | 7 mutações: 1 a 16 failed cada | Sim |
| 1 | 10 (RF02, RF05) | `uv run pytest -q tests/test_central_escrita.py -k cli` | 7 passed | 4 mutações: 1 failed cada | Sim |
| 1 | 11 (RF02-RF07, manual) | roteiro do owner sobre `42f1caf`; commits e front-matter conferidos no git do central de teste | PR #5, review 00:17:36Z, aprovação `5447cb8` 00:18:05Z, run `success` 00:19:23Z (registro do owner), merge `658cecd` 00:19:27Z | sem teste automatizado (manual) | Sim |
| 1 | 12 | `uv run ruff check . && uv run ruff format --check . && uv run pytest -q` | All checks passed; 98 files formatted; 412 passed, 29 deselected | espera do head anulada: suíte falha; `import os`: F401; formato: 1 file would be reformatted | Sim |

A tabela completa, com assertion e perfil, está na SDD, em "Evidência de verificação".

## Rodada 1 (reprovada no passo 0)

Os critérios 1 a 12 passaram e os sensores discriminaram. O passo 0, item 4, reprovou: duas assinaturas da SPEC-DTF-0030, Parte 2, estavam diferentes na SDD e sem registro.

- `EscritaNoCentral.__init__(..., framework: Path, ...)` na SPEC; `framework: Framework` na SDD e no código.
- `conferir` devolve a saída do `review_approval.py` na SPEC; na retomada, a SDD e o código devolvem um dict `dtf.review-approval/1` montado do front-matter.

Veredito: FAIL, com causa na especificação. O `1713343` registra as duas em "Decisões nesta compilação", o `506ecda` grava a nova aprovação do owner, e o código não muda.

## Requisito e código, nas duas direções

- RF01: `projetos/{cobaia,zero,exemplo}.yaml` e `.github/workflows/ci.yml`; central de teste com `_framework/` do kit em `efe1c71` e `approvers` em ZERO e COBAIA.
- RF02: `Regras.tipo_do_central`, `repositorio` e `pasta`; `Descoberta._rodada` e `_receber_documento`, com as mensagens literais; `documento` no schema; as três regras no `descobridor.md`.
- RF03: `EscritaNoCentral.proximo_id`, `montar` e `problemas`; `Framework.validar_documento`.
- RF04: `EscritaNoCentral.abrir_pr` (ordem, mensagens, `finally`); `enviar_ramo_documento`; `Github.abrir_pr_documento`; `Framework.gerar_registry_md` e `validar_registry`.
- RF05: `EscritaNoCentral.conferir`; `Framework.decidir_review`; `fabrica central conferir` em `__main__`.
- RF06: `EscritaNoCentral.integrar`, `_esperar_head`, `_aprovar_texto` e `_aprovar_no_registry`; `Github.fazer_merge_de_documento`.
- RF07: `_exigir_executor_fora_de_approvers` no início de `abrir_pr` e de `conferir`.
- Arquivos: os do diff estão em "Decomposição em tasks", mais `HANDOFF.md` (artefato operacional) e a própria SDD. `compilador.py`, `evidencia.py`, `arquivo.py`, `redacao.py`, `gates.py`, `roteamento.py`, `pipeline.py`, `fazer_merge_em_develop` e `RAMO_PUBLICAVEL` não foram tocados.

## Descompassos encontrados

- Rodada 1, bloqueante, corrigido na SDD: as duas divergências de contrato acima.

Não bloqueantes, registrados para o humano:

- `tests/test_central_escrita.py:377` e `:390` conferem só que `motivos` não está vazio, não o texto do motivo do kit.
- `abrir_pr_documento` recusa com a mensagem "push recusado para o ramo …", porque reusa `exigir_ramo_documento` (`fabrica/publicacao.py:77`).
- Extras pequenos sem requisito próprio: a função pública `exigir_ramo_documento` e o `_executar` separado de `_rodar` em `validadores.py`, que o `gerar_registry_md` sem `--json` usa.
- Na retomada, o `conferir` confia no `approved_by` que está no head da PR, sem rodar o `review_approval.py`. O CI do central confere de novo o `actor` contra `approvers` e o hash, no `validate_state.py`.
- A `SPEC-ZERO-0002` no central de teste tem `updated` anterior a `created`, do defeito corrigido em `460b4cb`. Ficou como está, por decisão do owner.
- Os horários do run do critério 11 vêm do registro do owner. A API do GitHub não estava acessível ao verificador.

## Lições

- Red flag: decisão de compilação que muda uma assinatura da Parte 2 da SPEC, até o tipo de um parâmetro, sem uma linha em "Decisões nesta compilação". O passo 0 reprova, mesmo com o comportamento igual.
- Red flag: SPEC que pede ao mesmo tempo "devolve a saída do script" e "retoma de onde parou", quando o script recusa o estado da retomada. A SDD precisa dizer qual das duas prevalece.

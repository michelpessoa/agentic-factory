# Verificação — SDD-FAB-0002

- **Veredito:** PASS (rodada 2; a rodada 1 reprovou o sensor do critério 6)
- **Diff verificado:** 193ea4a..b20b01c (fábrica, branch feature/SDD-FAB-0002-regras-e-origem: 2b83055 task 1, b1b20d8 task 2, b20b01c correção de testes após a rodada 1)
- **Verificador independente:** sim (subagente separado, sem ler o histórico da sessão que implementou)
- **Ambiente:** kit em 012ff479f83c09b1c754145506b3a21f929f1b1f (2.5.0) via `FABRICA_FRAMEWORK`; `~/projetos/fabrica-cobaia`; `~/fabrica-central-teste` em ec9e286; `doc-traceability-central` em 5add677; 2026-11-17.

| Rodada | Critério | Comando rodado | Saída (resumo) | Sensor | Passou? | Assertion (file:line) | Perfil usado |
|---|---|---|---|---|---|---|---|
| 2 | Fidelidade à origem (RFC-DTF-0009, ADR-DTF-0008) | `python3 $FABRICA_FRAMEWORK/_framework/scripts/check_source_docs.py docs/sdd/SDD-FAB-0002.md ~/doc-traceability-central/docs/DTF` (central em 5add677) | "✅ source_docs de SDD-FAB-0002.md conferem com o registry central.", exit 0; itens 2-4 não se aplicam (source_docs são RFC e ADR, sem SPEC); leitura da P3 coberta, escrita fora de escopo (fase 4) | sem teste automatizado (script mecânico e leitura) | Sim | n/a | manual |
| 2 | 1 (RF01) | `uv run pytest -q tests/test_regras.py -k regras` | 12 passed | `niveis()` fixo: 1 failed; filtro `(opcional)` removido: 2 failed; `transicao_permitida` invertida: 4 failed; restaurado: 12 passed | Sim | `tests/test_regras.py:36` | automatizado |
| 2 | 2 (RF02) | `uv run pytest -q tests/test_regras.py -k sizing` | 4 passed, 8 deselected | `if sizing not in niveis` → `if False`: 1 failed; `large` fora do enum do schema: 1 failed; restaurado: 4 passed | Sim | `tests/test_regras.py:118` | automatizado |
| 2 | 3 (RF03) | `uv run pytest -q tests/test_regras.py -k spec` | 6 passed, 6 deselected | SPEC não exigida, sizing divergente aceito, `parent_adr` ignorado, SPEC fora do registry vira problema, small exige SPEC: 1 failed cada; restaurado: 6 passed | Sim | `tests/test_regras.py:129` | automatizado |
| 2 | 4 (RF04) | `uv run pytest -q tests/test_origem.py` | 8 passed | troca ssh→https removida: 1 failed (`test_origem_adr_approved_com_remote_ssh`, com a config global isolada); `.git` mantido: 2 failed; status e tipo não conferidos: 1 failed cada; sizing fixo `None`: 1 failed; restaurado: 8 passed | Sim | `tests/test_origem.py:88` | automatizado |
| 2 | 5 (RF04) | `uv run pytest -q tests/test_origem.py -k cli` | 3 passed, 5 deselected | checagem de `--retomar` removida: 1 failed; origem não conferida: 2 failed; sessão criada antes da conferência: 1 failed; restaurado: 3 passed | Sim | `tests/test_origem.py:123` | automatizado |
| 2 | 6 (RF05) | `uv run pytest -q tests/test_descoberta.py -k origem` | 5 passed, 16 deselected | sem repasse de `origens` em `FonteDocTraceability.escrever_sdd`: 1 failed (`test_sdd_com_origem_passa_no_validate_doc_real`); entrada sem origens, `criar` sem guardar, aprovar sem repassar, decisão sem "Origem:", saída sem origem alterada (hash): 1 failed cada; `source_docs` ignorado e Rastreabilidade sem ids: 2 failed cada; restaurado: 5 passed | Sim | `tests/test_descoberta.py:381` | automatizado |
| 2 | 7 (RF06) | `uv run pytest -q tests/test_regras.py -k transicao` | 2 passed, 10 deselected | checagem de transição → `if False`: 1 failed; status lido forçado a approved: 1 failed; restaurado: 2 passed | Sim | `tests/test_regras.py:168` | automatizado |
| 2 | 8 (RF01-RF06) | `uv run ruff check . && uv run ruff format --check . && uv run pytest -q` com kit, fabrica-cobaia e central de teste | "All checks passed!", "94 files already formatted", "333 passed, 29 deselected" (docker e claude, como no CI; nenhum skip) | mutação do repasse de origens na suíte inteira: 1 failed, 332 passed; `import os` sem uso: ruff 1 erro; restaurado: verde | Sim | `tests/test_descoberta.py:381` | automatizado |

## Rodada 1 (reprovada)

A rodada 1, no diff 193ea4a..b1b20d8, rodou os mesmos critérios com os mesmos comandos. Todos passaram, mas dois sensores falharam:

- **Critério 6 (RF05), bloqueante:** tirar o repasse de `origens` em `FonteDocTraceability.escrever_sdd` não derrubava nenhum teste. Passavam os 5 de `-k origem` e os 333 da suíte inteira.
- **Critério 4 (RF04), ressalva:** tirar a troca ssh→https também não derrubava nenhum teste. O ambiente reescreve a url por `GIT_CONFIG_*`, então o teste não exercitava a troca.

Veredito: FAIL, com causa na implementação (cobertura de teste). O b20b01c mexe só em testes e cobre os dois pontos.

## Requisito e código, nas duas direções

- RF01: `adapters/doc_traceability/regras.py` (`Regras.niveis`, `documentos` sem `(opcional)` e `()` para nível desconhecido, `transicao_permitida` False para `de` desconhecido).
- RF02: `FonteDocTraceability._problemas_de_sizing`, chamado depois dos validadores e antes de `compilar_sdd`, com a mensagem literal; enum de `contracts/resposta-descoberta.schema.json` com os quatro níveis.
- RF03: SPEC exigida quando `documentos(sizing)` contém SPEC; sizing divergente e `parent_adr` ausente, com as mensagens literais; SPEC fora do registry fica para o `check_source_docs.py`; leitura pelo `path` do registry do central.
- RF04: `FonteDocTraceability.origem` (três mensagens literais; url de `git remote get-url origin` com ssh→https, sem `.git`, mais `/blob/main/<path>`); `OrigemInvalida` em `__all__`; `--origem` (append, default [], metavar ID), conferido antes de `criar`, saída 2; `--origem` com `--retomar` sai com 2.
- RF05: `Descoberta.criar(ideia, origens)`, `_rodada` com as cinco chaves, as três chamadas a `escrever_sdd` com `origens=`; `montar_sdd`/`escrever_sdd` com `origens` por último; sem origens, saída idêntica (sha256 reconferido contra develop); regra nova em `agents/descobridor.md` com o texto literal.
- RF06: `registrar_verificacao` lê o status e recusa antes de `registrar_evidencia`.
- Arquivos: os 10 do diff estão na tabela "Decomposição em tasks". `compilador.py`, `evidencia.py`, `arquivo.py`, `gates.py` e `roteamento.py` não foram tocados. Código sem requisito: nenhum.

## Descompassos encontrados

- **Rodada 1, bloqueante (corrigido):** tirar o repasse de `origens` em `FonteDocTraceability.escrever_sdd` deixava a SDD real com `source_docs: []` e nenhum teste falhava. No b20b01c, `test_sdd_com_origem_passa_no_validate_doc_real` passou a conferir `source_docs` e a Rastreabilidade, e o teste do remote ssh isola a config global do git. Na rodada 2, as duas mutações são detectadas.

Não bloqueantes, registrados para o humano:

- A CLI imprime `erro: <mensagem>` para `OrigemInvalida`; a SDD diz "imprime a mensagem". A mensagem aparece inteira, no estilo do resto da CLI.
- `__main__` usa `descoberta.redator.origem(...)`, que é o mesmo objeto de `montar_fonte(projeto)`; o Protocol `Redator` não declara `origem` (lacuna só de tipo).
- O comando do critério 1 (`-k regras`) casa com o nome do módulo e roda o arquivo inteiro; discrimina do mesmo jeito.
- O texto da SDD diz que a RFC-DTF-0010 está `in_review`; no central em 5add677 ela está `approved`, e há a ADR-DTF-0009 approved sobre origem local. Não afeta a implementação.

## Lições

- Red flag: "o teste da camada de cima usa um redator falso e o da camada de baixo chama a função pura". O repasse de um parâmetro novo com default `()` na fronteira do adaptador some em silêncio. Para cada parâmetro novo com default, um teste atravessa a fronteira real e confere o efeito.
- Red flag: teste de url com remote ssh num ambiente com `url.<https>.insteadOf git@github.com:` (via `GIT_CONFIG_*`). O `git remote get-url` já devolve https e a conversão não é exercida; isole a config no teste.
- Red flag: `-k <palavra>` que é parte do nome do módulo seleciona o arquivo inteiro, e o comando do critério deixa de isolar o que diz verificar.

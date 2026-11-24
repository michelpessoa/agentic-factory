---
id: SDD-FAB-0001
type: SDD
title: "Leitura do central: framework fixado em 2.5.0, caminho do central por projeto e validadores lidos pelo --json do executor_contract"
status: implemented
project: "FAB"
owner: "Michel Pessoa"
created: "2026-11-17"
updated: "2026-11-17"
relates_to: []
source_docs:
  - id: "ADR-0012"
    url: "https://github.com/michelpessoa/fabrica-agentica/blob/develop/docs/adr/ADR-0012-executora-do-fluxo-do-framework.md"
  - id: "RFC-DTF-0009"
    url: "https://github.com/michelpessoa/doc-traceability-central/blob/main/docs/DTF/01-rfc/RFC-DTF-0009.md"
sizing: "large"
approved_by:
  kind: human
  actor: michelpessoa
  at: "2026-11-17T01:22:17Z"
  content_sha256: "9ae355f960ab55fc4402ee26158ddaf2156a62e934ace7a76fdac41db2d6fb24"
  evidence: "https://github.com/michelpessoa/fabrica-agentica/pull/29#pullrequestreview-5931026541"
consumption_instructions: "Compilada da ADR-0012 da fábrica (aceita) e da RFC-DTF-0009 (approved), fase 3, parte de leitura. Sem SPEC por decisão da RFC-DTF-0009 (tabela 'Plano'). Os requisitos RF01 a RF06 abaixo são o escopo inteiro: não acrescentar campo, chave, exceção ou mensagem que esta SDD não declara. Teste primeiro, visto falhar. O núcleo (`fabrica/pipeline.py`, `fabrica/descoberta.py`) segue sem conhecer o framework: tudo que lê o framework ou o central fica em `adapters/doc_traceability/`. O central de teste muda por branch e PR próprios no `fabrica-central-teste`."
supersedes: null
superseded_by: null
tags: [integracao, executor, central, framework-fixado, executor-contract]
---

# Leitura do central: framework fixado em 2.5.0, caminho do central por projeto e validadores lidos pelo --json do executor_contract

> Este documento é COMPILADO a partir de `source_docs` — não é escrito do
> zero. É o artefato de entrada (input) para ferramentas de IA realizarem
> a implementação. Vive no repositório de CÓDIGO deste projeto (não no
> repositório central do framework) porque é o único documento pensado
> para ser lido pela IA no momento de implementar.

## Resumo executivo

Primeira SDD da fase 3 da RFC-DTF-0009: a fábrica passa a ler do central.
Hoje ela fixa o framework 2.3.2, lê os scripts de um clone sem saber onde
está o central do projeto, lê a saída dos validadores como texto livre e
nunca roda `check_source_docs.py`, porque chama `validar_entrada` sem
`docs_central`. Esta SDD sobe a versão fixada para 2.5.0 (a que tem
`executor_contract` e `--json`), faz cada projeto declarar o caminho do
central e exige que o `_framework/` desse central esteja na mesma versão.
Também passa a ler os validadores pelo `--json` declarado em
`executor_contract.machine_outputs` e roda `check_source_docs.py` na
entrada. O central de teste sobe para 2.5.0 junto. A leitura de sizing,
gates e ciclo de status do `workflow-rules.yaml`, e a entrada de SPEC e
ADR `approved` como `source_docs` na descoberta, ficam para a SDD
seguinte da fase 3.

## Decisão(ões) de arquitetura aplicável(is)

- **ADR-0012 (fábrica, aceita):** versão do framework fixada por projeto,
  com `projetos/<nome>.yaml` declarando a versão e o caminho do central; a
  fábrica recusa iniciar se a versão do clone não for a declarada; o CI faz
  checkout do kit nessa versão. O adaptador conhece o `executor_contract` e
  o central, o núcleo não. `check_source_docs.py` roda na entrada.
- **RFC-DTF-0009 (approved), tabela "Plano":** a fase 3 é ADR-0012 e SDDs
  na fábrica, sem SPEC nova no DTF. Pelas decisões do owner sobre o plano,
  as fases 3 e 4 rodam contra um central de teste
  (`michelpessoa/fabrica-central-teste`), e o caminho do central é
  configurável por projeto.
- **`executor_contract` (framework 2.5.0, seção 20):** os scripts com
  `--json` e o schema `_framework/schemas/resultado-validador.schema.json`
  (`schema: dtf.resultado-validador/1`) que esta SDD consome.

## Requisitos consolidados

- **RF01 — Versão fixada 2.5.0.** `projetos/cobaia.yaml`,
  `projetos/zero.yaml` e `projetos/exemplo.yaml` declaram
  `framework: "2.5.0"`. O CI faz checkout do kit no commit
  `012ff479f83c09b1c754145506b3a21f929f1b1f` (merge da SDD-DTF-0054,
  `framework.version: "2.5.0"`). Origem: ADR-0012, "Versão do framework
  fixada por projeto".
- **RF02 — Caminho do central por projeto.** `projetos/<nome>.yaml` ganha
  o campo `central`: caminho local da raiz do repositório central, com `~`
  expandido. `Projeto` ganha `central: str = ""`. Sem `central`, a fábrica
  recusa iniciar. Origem: ADR-0012 e RFC-DTF-0009 ("o caminho do central é
  configurável por projeto").
- **RF03 — Central na versão declarada.** Ao iniciar, além do clone do
  framework, a fábrica confere a versão do `_framework/` do central
  declarado e recusa iniciar se não for a do projeto. Central inexistente
  ou sem `_framework/` também recusa. Origem: ADR-0012 ("sizing, gates e
  ciclo de status vêm do `workflow-rules.yaml` na versão fixada").
- **RF04 — Validadores pelo `--json`.** `validate_doc.py`,
  `registry_tools.py validate`, `check_source_docs.py` e
  `validate_state.py` são chamados com `--json`, nos argumentos de
  `executor_contract.machine_outputs`. A fábrica decide pelo campo `ok` e
  monta as mensagens a partir de `problemas[].mensagem`, não do texto da
  saída. Saída que não é JSON, ou que não traz
  `schema: dtf.resultado-validador/1`, é problema, nunca aprovação. Origem:
  ADR-0012, "O adaptador passa a conhecer o contrato do executor".
- **RF05 — `check_source_docs.py` na entrada.** `problemas_de_entrada`
  roda `check_source_docs.py <sdd> <central>/docs/<codigo> --json` junto
  com `validate_doc.py` e `registry_tools.py validate`. SDD com
  `source_docs` que não está `approved` no registry do central é recusada
  na entrada. SDD com `source_docs: []` passa, como já faz o framework.
  Origem: ADR-0012, "Leitura do central".
- **RF06 — Central de teste em 2.5.0 e no CI.** O `fabrica-central-teste`
  recebe o `_framework/` do kit no mesmo commit do RF01, por branch e PR
  próprios. Os registries de `docs/ZERO/` e `docs/COBAIA/` mantêm
  `framework_version: "2.3.2"` (não retroativo). Os projetos declaram
  `central: "~/fabrica-central-teste"`, e o CI clona o central de teste
  nesse caminho. Origem: RFC-DTF-0009, decisão do owner "Onde o executor
  escreve nos testes: híbrido"; decisão do owner nesta sessão
  (2026-11-17) de subir o central de teste junto.

**Fora de escopo, para a SDD seguinte da fase 3:** sizing, gates e ciclo
de status lidos do `workflow-rules.yaml`; SPEC e ADR `approved` do central
entrando como `source_docs` nas SDDs da descoberta. **Fase 4:** qualquer
escrita no central e `approved_by` com `kind: policy`.

## Especificação técnica consolidada

**`projetos/*.yaml` (RF01, RF02, RF06).** Em `cobaia.yaml` e `zero.yaml`:
`framework: "2.5.0"` e `central: "~/fabrica-central-teste"`. Em
`exemplo.yaml`: `framework: "2.5.0"` e
`central: "~/doc-traceability-central"`, com comentário na mesma linha:
`# raiz do repositório central; a fábrica confere a versão do _framework/ dele`.

**`fabrica/pipeline.py`, `Projeto` (RF02).** Novo campo, logo depois de
`framework`: `central: str = ""`, com o comentário
`# Raiz do repositório central do projeto. Vazia: a fábrica recusa iniciar.`
Nenhuma outra mudança no núcleo.

**`adapters/doc_traceability/validadores.py` (RF03, RF04, RF05).**

- `ResultadoValidador` ganha `problemas: tuple[str, ...] = ()`, as
  mensagens de `problemas[].mensagem` na ordem do JSON. `saida` continua
  com stdout mais stderr, para log.
- `_rodar` passa a acrescentar `--json` aos argumentos e a ler o stdout
  como JSON. `ok` é `True` só quando o JSON é um objeto com
  `schema == "dtf.resultado-validador/1"` e `ok is True`. Se o stdout não
  for JSON, ou o `schema` for outro, `ok` é `False` e `problemas` é
  `(f"saída fora do contrato dtf.resultado-validador/1: {trecho}",)`, onde
  `trecho` é o final de stdout mais stderr, no máximo 300 caracteres.
- `exigir_central(central: Path, exigida: str) -> None`: com `central`
  vazio (`Path("")`) ou sem `_framework/scripts`, levanta
  `VersaoDivergente("o projeto não declara o caminho do central: preencha `central` em projetos/<nome>.yaml")`
  ou `VersaoDivergente(f"central não encontrado em {central}")`,
  respectivamente. Com versão do `_framework/` do central diferente de
  `exigida`, levanta
  `VersaoDivergente(f"o projeto exige o framework {exigida}, e o central em {central} está na {atual}")`.
  Reusa `Framework(central).versao()`.
- `validar_entrada(repo, sdd, docs_central)`: `docs_central` deixa de ser
  opcional; `check_source_docs.py` roda sempre.
- `validar_estado` continua com a mesma assinatura e passa a usar `--json`
  via `_rodar`.

**`adapters/doc_traceability/__init__.py` (RF02 a RF05).**
`FonteDocTraceability.__init__(self, framework=None, central: Path | None = None, codigo: str = "")`.
`exigir_versao(exigida)` chama `self._framework.exigir_versao(exigida)` e
depois `self._framework.exigir_central(self._central or Path(""), exigida)`.
`problemas_de_entrada` passa `self._central / "docs" / self._codigo` a
`validar_entrada` e monta cada problema como `f"{r.nome}: {mensagem}"`, uma
linha por mensagem de `r.problemas`. `registrar_verificacao` devolve
`list(resultado.problemas)` quando `validate_state` não passa.

**`fabrica/__main__.py`, `montar_fonte` (RF02).**
`FonteDocTraceability(central=Path(projeto.central).expanduser() if projeto.central else None, codigo=projeto.codigo)`.
A captura de `VersaoDivergente` que já existe cobre a recusa.

**`.github/workflows/ci.yml` (RF01, RF06).** `FRAMEWORK_SHA:
012ff479f83c09b1c754145506b3a21f929f1b1f  # framework 2.5.0`. Novo passo,
depois do clone do `fabrica-cobaia`:
`git clone --depth 1 https://github.com/michelpessoa/fabrica-central-teste "$HOME/fabrica-central-teste"`.
Ele só passa depois que a PR do RF06 no central de teste for mergeada em
`main`.

**`fabrica-central-teste` (RF06).** Branch
`sdd/SDD-FAB-0001-framework-2.5.0`. `_framework/` substituído
integralmente pelo `_framework/` do kit no commit do RF01. Depois rodar,
no próprio central, `python3 _framework/scripts/render_prompts.py` e
`python3 _framework/scripts/generate_registry_md.py` para `docs/ZERO` e
`docs/COBAIA`. Nada é editado à mão em arquivo gerado.

**Riscos conhecidos.** Com o framework 2.5.0, a SDD `approved` criada desde
2026-11-17 num registry que declara `framework_version: "2.5.0"` é cobrada
por `approved_by`. A descoberta grava a versão do framework só ao criar um
registry novo. Num projeto sem `docs/sdd/registry.yaml`, a primeira SDD
aprovada passa a ser recusada por `validate_state.py` até a fase 4 escrever
`approved_by` com `kind: policy`. Projetos com registry em 2.3.2 não são
afetados. Isto não é corrigido aqui: a correção é escrita, fora do escopo.
Só fica registrado para não ir à release antes da fase 4.

## Decomposição em tasks

| # | Task | RF(s) de origem | Arquivos tocados | Depende de (#) |
|---|---|---|---|---|
| 1 | Central de teste em 2.5.0 (repo `fabrica-central-teste`) | RF06 | `_framework/`, `AGENTS.md`, `CHANGELOG.md`, `QUICKSTART.md`, `docs/ZERO/registry.md`, `docs/COBAIA/registry.md` | — |
| 2 | Versão fixada e caminho do central nos projetos e no CI | RF01, RF02, RF06 | `projetos/cobaia.yaml`, `projetos/zero.yaml`, `projetos/exemplo.yaml`, `fabrica/pipeline.py`, `.github/workflows/ci.yml`, `tests/test_framework_versao.py` | 1 |
| 3 | Validadores pelo `--json`, central conferido e `check_source_docs` na entrada | RF03, RF04, RF05 | `adapters/doc_traceability/validadores.py`, `adapters/doc_traceability/__init__.py`, `fabrica/__main__.py`, `tests/test_validadores_framework.py`, `tests/test_framework_versao.py`, `tests/test_evidencia.py` | 2 |

## Critérios de aceite / definição de pronto

| # | Critério (origem: RF-ID / contrato) | Comando de verificação | Resultado esperado | Perfil esperado |
|---|---|---|---|---|
| 1 | RF01: todo projeto declara 2.5.0 e o clone do CI é a 2.5.0 | `FABRICA_FRAMEWORK=~/doc-traceability-framework uv run pytest -q tests/test_framework_versao.py` com o kit no commit do RF01 | passa, incluindo `test_clone_do_framework_e_a_versao_dos_projetos` (não pulado) | automatizado |
| 2 | RF02: projeto sem `central` é recusado | `uv run pytest -q tests/test_framework_versao.py -k central` | teste com `central` vazio levanta `VersaoDivergente` com "não declara o caminho do central" | automatizado |
| 3 | RF03: central em versão diferente, ou inexistente, é recusado | `uv run pytest -q tests/test_framework_versao.py -k central` | central falso em 2.3.2 com projeto em 2.5.0 levanta "o central em … está na 2.3.2"; caminho inexistente levanta "central não encontrado" | automatizado |
| 4 | RF04: decisão pelo `ok` do JSON, mensagens de `problemas[].mensagem` | `uv run pytest -q tests/test_validadores_framework.py` com framework e `fabrica-cobaia` presentes | `SDD-COBAIA-0003` recusada com a mensagem do marcador de ambiguidade pendente, vinda do JSON; `SDD-COBAIA-0001` aceita | automatizado |
| 5 | RF04: saída fora do contrato é problema | `uv run pytest -q tests/test_validadores_framework.py -k contrato` | script falso que imprime texto não JSON dá `ok False` e problema "saída fora do contrato dtf.resultado-validador/1" | automatizado |
| 6 | RF05: `check_source_docs` roda na entrada e recusa origem não aprovada | `uv run pytest -q tests/test_validadores_framework.py -k source_docs` | central temporário com SPEC `draft` citada em `source_docs`: problema de `check_source_docs.py`; com a SPEC `approved`, sem problema; `source_docs: []`, sem problema | automatizado |
| 7 | RF06: central de teste em 2.5.0, registries em 2.3.2 | `python3 -c "import yaml;print(yaml.safe_load(open('$HOME/fabrica-central-teste/_framework/rules/workflow-rules.yaml'))['framework']['version'])"` e `grep framework_version ~/fabrica-central-teste/docs/*/registry.yaml` | `2.5.0`; os dois registries em `"2.3.2"` | automatizado |
| 8 | RF06: gerados do central de teste batem com o `_framework/` | `cd ~/fabrica-central-teste && python3 _framework/scripts/check_renderings.py` | sai 0 | automatizado |
| 9 | Suíte inteira e lint, como no CI | `uv run ruff check . && uv run ruff format --check . && uv run pytest -q` com kit, `fabrica-cobaia` e central de teste presentes | tudo verde | automatizado |

## Instruções específicas para a IA implementadora

- Teste primeiro: cada critério acima tem teste visto falhar antes do
  código.
- Arquivos esperados: os de "Decomposição em tasks", nada além. O núcleo só
  muda em `Projeto` (um campo).
- Os testes que usam scripts reais seguem com `skipif` quando o framework,
  o `fabrica-cobaia` ou o central de teste não existem; no CI os três
  existem e nenhum é pulado.
- Para os testes de `check_source_docs`, monte o central temporário em
  `tmp_path` com `docs/<CODIGO>/registry.yaml` e o documento citado; não
  escreva em `~/fabrica-central-teste`.
- Não altere `adapters/doc_traceability/compilador.py`, `redacao.py`,
  `evidencia.py` nem `arquivo.py`.
- Não mude a versão gravada pela descoberta em registry novo (ver "Riscos
  conhecidos").
- No `fabrica-central-teste`, não toque `docs/ZERO/registry.yaml` nem
  `docs/COBAIA/registry.yaml`.

## Verificação de escopo (nada a mais, nada a menos)
Antes de marcar `implemented`, confirme as duas direções — SDD incompleta
tanto quanto SDD estourada são falha:
- [x] Todo requisito consolidado acima tem código correspondente (nada
      da SPEC ficou de fora).
- [x] Todo arquivo tocado pela implementação aparece em "Especificação
      técnica consolidada" ou "Instruções específicas" — se a
      implementação tocou um arquivo não listado aqui, ou é escopo que
      faltou registrar na SDD (atualize-a) ou é scope creep a remover
      antes do merge.
- [x] Nenhuma abstração, config, feature flag ou refactor extra que não
      foi pedido por nenhum requisito consolidado ("já que estava ali").

Nota da verificação: na fábrica, os 11 arquivos do diff estão na
tabela "Decomposição em tasks". No `fabrica-central-teste`, três itens
ficam fora da lista da task 1 e foram aceitos como escopo registrado
aqui, não como scope creep: `docs/especificacao.md` (gerado por
`render_prompts.py`, que esta SDD manda rodar), `requirements.txt` com
`jsonschema==4.26.0` (o mesmo pin do kit 2.5.0, que os testes de
`_framework/` importam) e a PR #1 (`.claude/`, `docs/guias/guia-tecnico.md`,
`.github/workflows/framework-check.yml`), sem a qual o critério 8 sai 1
(`.claude/settings.json` é artefato mecanizado que `check_renderings.py`
cobra). Detalhe em `docs/sdd/validation-SDD-FAB-0001.md`.

## Evidência de verificação (preencher antes de status `implemented`)
Preenchida pela skill `verify-sdd`, em sessão separada da que implementou.

Verificação independente completa em `docs/sdd/validation-SDD-FAB-0001.md`. Veredito: **PASS**.
Diff verificado: `5487928..a8774d2` (fábrica, PR #31) e `5258d5c..ec9e286` (`fabrica-central-teste`, PRs #1 e #2). Kit em `012ff479f83c09b1c754145506b3a21f929f1b1f` (2.5.0), em 2026-11-17.

**Verificador independente:** sim

| Rodada | # | Comando rodado | Saída (resumo) | Sensor | Passou? | Assertion (file:line) | Perfil usado |
|---|---|---|---|---|---|---|---|
| 1 | Fidelidade à origem | `python3 $FABRICA_FRAMEWORK/_framework/scripts/check_source_docs.py docs/sdd/SDD-FAB-0001.md ~/doc-traceability-central/docs/DTF` (central em 41a9f52) | exit 1, um problema só: "source_docs 'ADR-0012' não encontrado no registry central". RFC-DTF-0009 passa (approved, url = path). ADR-0012 é da fábrica (ADR-0004), exceção declarada na Rastreabilidade desta SDD aprovada; conferida à mão: `docs/adr/ADR-0012-executora-do-fluxo-do-framework.md` existe, `status: aceita`, url aponta para o mesmo arquivo. Sem SPEC (decisão da RFC-DTF-0009, Plano): RF01-RF06 cobrem as decisões da ADR-0012 para a leitura (versão fixada, central por projeto, executor_contract, check_source_docs na entrada) e a decisão do owner na RFC-DTF-0009 (central de teste, caminho configurável); nada relaxado | sem teste automatizado (leitura de documento; a parte mecanizada é o check_source_docs acima) | Sim | n/a | manual |
| 1 | 1 | `FABRICA_FRAMEWORK=/home/user/doc-traceability-framework uv run pytest tests/test_framework_versao.py -vv -rs` (kit em 012ff47) | 17 passed, 0 skipped; `test_clone_do_framework_e_a_versao_dos_projetos PASSED` | `projetos/zero.yaml` com `framework: "2.3.2"`: 1 failed (test_clone_do_framework_e_a_versao_dos_projetos); restaurado: 17 passed | Sim | `tests/test_framework_versao.py:61` | automatizado |
| 1 | 2 | `uv run pytest -q tests/test_framework_versao.py -k central` | 10 passed, 7 deselected; inclui test_central_vazio_recusa, test_fonte_sem_central_recusa, test_montar_fonte_sem_central_recusa | `if central == Path("")` trocado por `if False` em `exigir_central`: 3 failed; `exigir_central` removido de `FonteDocTraceability.exigir_versao`: 3 failed (test_fonte_sem_central_recusa, test_fonte_confere_o_central_do_projeto, test_montar_fonte_sem_central_recusa); restaurado: 10 passed | Sim | `tests/test_framework_versao.py:71` | automatizado |
| 1 | 3 | `uv run pytest -q tests/test_framework_versao.py -k central` | 10 passed, 7 deselected; test_central_em_outra_versao_recusa e test_central_inexistente_recusa passam | `atual != exigida` invertido para `==`: 3 failed; checagem de `_framework/scripts` trocada por `if False`: 1 failed (test_central_inexistente_recusa); restaurado: 10 passed | Sim | `tests/test_framework_versao.py:79`, `tests/test_framework_versao.py:85` | automatizado |
| 1 | 4 | `uv run pytest tests/test_validadores_framework.py -vv -rs` com kit e `~/projetos/fabrica-cobaia` | 11 passed, 0 skipped; test_sdd_valida_passa (os três validadores, ok e sem problemas) e test_needs_clarification_e_recusado (mensagem vinda de `problemas`) | `ok` fixo `True` em `_rodar`: 3 failed (test_needs_clarification_e_recusado, test_contrato_decide_pelo_ok_do_json_e_pede_json, test_source_docs_nao_aprovado_e_recusado); `problemas = ()`: os mesmos 3 failed; restaurado: 11 passed | Sim | `tests/test_validadores_framework.py:42`, `tests/test_validadores_framework.py:33` | automatizado |
| 1 | 5 | `uv run pytest -q tests/test_validadores_framework.py -k contrato` | 5 passed, 6 deselected | checagem de `schema` removida: 1 failed (test_json_de_outro_schema_fica_fora_do_contrato); saída fora do contrato com `ok True`: 2 failed; restaurado: 5 passed | Sim | `tests/test_validadores_framework.py:57`, `tests/test_validadores_framework.py:66` | automatizado |
| 1 | 6 | `uv run pytest -q tests/test_validadores_framework.py -k source_docs` | 3 passed, 8 deselected | `check_source_docs.py` tirado de `validar_entrada`: 3 failed; `check_source_docs.py` sempre `ok`: 1 failed (test_source_docs_nao_aprovado_e_recusado); `problemas_de_entrada` montando com `r.saida` em vez de `r.problemas`: 1 failed em tests/test_evidencia.py (test_entrada_real_da_uma_linha_por_problema_do_json); restaurado: tudo passa | Sim | `tests/test_validadores_framework.py:128`, `tests/test_validadores_framework.py:135`, `tests/test_validadores_framework.py:141` | automatizado |
| 1 | 7 | `python3 -c "import yaml;print(yaml.safe_load(open('$HOME/fabrica-central-teste/_framework/rules/workflow-rules.yaml'))['framework']['version'])"` e `grep framework_version ~/fabrica-central-teste/docs/*/registry.yaml` (central em ec9e286) | `2.5.0`; `docs/COBAIA/registry.yaml:framework_version: "2.3.2"`, `docs/ZERO/registry.yaml:framework_version: "2.3.2"`. `diff -rq _framework` contra o kit em 012ff47: sem diferença | `framework.version` trocado para 2.3.2 no workflow-rules.yaml do central: o comando imprime `2.3.2`; restaurado: `2.5.0` (git status limpo) | Sim | n/a (comando de leitura, sem arquivo de teste) | automatizado |
| 1 | 8 | `cd ~/fabrica-central-teste && python3 _framework/scripts/check_renderings.py` | "5 renderização(ões) concordam com workflow-rules.yaml (8 tipos ativos, 6 Iron Laws, 4 níveis)", exit 0 | Iron Law alterada em AGENTS.md: exit 1; `.claude/settings.json` ausente: exit 1 ("artefato mecanizado ausente"); restaurado: exit 0 (git status limpo). Trocar só o título "v2.5.0" de AGENTS.md não é detectado (o script compara fatos, não texto) | Sim | `_framework/scripts/check_renderings.py` (exit do script) | automatizado |
| 1 | 9 | `uv run ruff check . && uv run ruff format --check . && uv run pytest -q` com kit, fabrica-cobaia e central de teste | "All checks passed!", "89 files already formatted", "308 passed, 29 deselected" (docker e claude, como no CI), exit 0 | `import re` sem uso em validadores.py: ruff exit 1 (F401); `SCHEMA_RESULTADO` trocado para `/2`: 11 failed; restaurado: ruff limpo e suíte verde | Sim | n/a (agregado; asserções nas linhas 1-8) | automatizado |

## Rastreabilidade
| Campo | Valor |
|---|---|
| source_docs | ADR-0012, RFC-DTF-0009 |
| fase | RFC-DTF-0009, fase 3 (leitura) |
| aprovação | human, por review "Aprovado" na PR. A ADR-0012 vive na fábrica (ADR-0004), não no registry do central: `check_source_docs.py` contra `docs/DTF` acusa só ela, e a política de SDD (`approval_policy`) não se aplica |

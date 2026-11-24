---
id: SDD-FAB-0002
type: SDD
title: "Regras do framework na entrada e origem do central na descoberta: sizing, documentos por nível, ciclo de status e --origem"
status: implemented
project: "FAB"
owner: "Michel Pessoa"
created: "2026-11-17"
updated: "2026-11-17"
relates_to: [SDD-FAB-0001]
source_docs:
  - id: "RFC-DTF-0009"
    url: "https://github.com/michelpessoa/doc-traceability-central/blob/main/docs/DTF/01-rfc/RFC-DTF-0009.md"
  - id: "ADR-DTF-0008"
    url: "https://github.com/michelpessoa/doc-traceability-central/blob/main/docs/DTF/02-adr/ADR-DTF-0008.md"
sizing: "large"
approved_by:
  kind: human
  actor: michelpessoa
  at: "2026-11-17T11:45:08Z"
  content_sha256: "c5cc4fb7ef33817b65e95927935bd9812483392da60d1ae17bf8c3d01ed8d2ad"
  evidence: "https://github.com/michelpessoa/fabrica-agentica/pull/33#pullrequestreview-5937803935"
consumption_instructions: "Compilada da RFC-DTF-0009 (approved, fase 3, parte de leitura) e da ADR-DTF-0008 (approved), com a ADR-0012 da fábrica (aceita) citada no corpo e fora de source_docs (RFC-DTF-0010, alternativa A, decisão do owner de 2026-11-17). Os requisitos RF01 a RF06 abaixo são o escopo inteiro: não acrescentar campo, chave, exceção ou mensagem que esta SDD não declara. Teste primeiro, visto falhar. O núcleo (`fabrica/pipeline.py`, `fabrica/descoberta.py`) segue sem conhecer o framework: em `descoberta.py` a origem é um dicionário opaco repassado ao agente e ao redator."
supersedes: null
superseded_by: null
tags: [integracao, executor, central, sizing, status-lifecycle, origem, descoberta]
---

# Regras do framework na entrada e origem do central na descoberta: sizing, documentos por nível, ciclo de status e --origem

> Este documento é COMPILADO a partir de `source_docs` — não é escrito do
> zero. É o artefato de entrada (input) para ferramentas de IA realizarem
> a implementação. Vive no repositório de CÓDIGO deste projeto (não no
> repositório central do framework) porque é o único documento pensado
> para ser lido pela IA no momento de implementar.

## Resumo executivo

Segunda e última SDD da fase 3 da RFC-DTF-0009, parte de leitura. A
SDD-FAB-0001 fixou o framework em 2.5.0, deu a cada projeto o caminho do
central e passou a ler os validadores pelo `--json`. Falta o que a
ADR-0012 da fábrica chama de "leitura do central": sizing, documentos
exigidos e ciclo de status vindos do `workflow-rules.yaml` na versão
fixada, e SPEC e ADR `approved` do central entrando como `source_docs`
nas SDDs da descoberta.

Esta SDD faz a fábrica ler, do `workflow-rules.yaml` do clone fixado, os
níveis de sizing, os documentos exigidos por nível e as transições de
status permitidas. Com isso:

- a entrada recusa sizing que não é nível do framework;
- a entrada recusa SDD `medium` ou maior sem SPEC em `source_docs`;
- a fábrica só passa uma SDD a `implemented` quando o framework permite
  essa transição.

A descoberta ganha `--origem`. O owner nomeia a SPEC ou a ADR `approved`
do central, a fábrica confere o registry, entrega o texto ao agente e
grava `{id, url}` em `source_docs`.

Os limites numéricos da descoberta (3 requisitos e 4 arquivos em
`small`) e o piso de risco da ADR-0009 continuam como estão, por cima do
framework, porque o `workflow-rules.yaml` descreve o sizing em prosa.

## Decisão(ões) de arquitetura aplicável(is)

- **ADR-0012 (fábrica, aceita), "Leitura do central":** sizing, gates e
  ciclo de status vêm do `workflow-rules.yaml` na versão fixada; SPEC e
  ADR `approved` entram como `source_docs`; as regras de risco da
  ADR-0009 continuam por cima, como piso. A ADR-0012 vive na fábrica e
  fica fora de `source_docs`: a RFC-DTF-0010 (`in_review`) trata a origem
  local, e até a versão nova do kit as SDDs da fábrica citam só o
  central (decisão do owner, 2026-11-17).
- **RFC-DTF-0009 (approved), P3 e tabela "Plano":** a fase 3 é ADR-0012 e
  SDDs na fábrica, sem SPEC nova no DTF.
- **ADR-DTF-0008 (approved):** `executor_contract.reads` declara
  `sizing`, `decision_gates`, `status_lifecycle`, `repository_topology`,
  `frontmatter_schema`, `registry` e `approval_policy` como o que o
  executor pode ler. Esta SDD lê `sizing`, `status_lifecycle` e
  `registry`.
- **Decisões do owner nesta sessão (2026-11-17):** a origem entra por
  `--origem` explícito, nunca escolhida pelo agente; a fábrica lê os
  níveis e os documentos por nível, e os limites numéricos ficam como
  piso da ADR-0009.

## Requisitos consolidados

- **RF01 — Regras lidas do framework fixado.** Um leitor novo,
  `Regras(raiz)`, lê `<raiz>/_framework/rules/workflow-rules.yaml`, onde
  `raiz` é a raiz do clone do framework já conferido pela SDD-FAB-0001.
  Ele devolve os níveis de sizing (`sizing.levels[].id`), os documentos
  obrigatórios de um nível (`sizing.levels[].documents`, sem as entradas
  que terminam em `(opcional)`) e se uma transição de status está em
  `status_lifecycle.allowed_transitions`. Origem: ADR-0012, "Leitura do
  central"; ADR-DTF-0008, `executor_contract.reads`.
- **RF02 — Sizing é nível do framework.** `problemas_de_entrada` recusa a
  SDD cujo `sizing` não está entre os níveis do framework. O schema da
  resposta da descoberta passa a aceitar os quatro níveis. Origem:
  ADR-0012.
- **RF03 — Documentos exigidos pelo nível.** Quando os documentos do
  nível da SDD incluem SPEC, `problemas_de_entrada` exige ao menos uma
  entrada `SPEC-` em `source_docs`. Para cada SPEC citada que está no
  registry do central:
  - o `sizing` da SDD é o da SPEC;
  - se a SPEC tem `parent_adr`, essa ADR está em `source_docs`.

  SPEC citada que não está no registry fica para `check_source_docs.py`,
  sem problema repetido aqui. Origem: ADR-0012; `sizing.levels` e
  `decision_gates.spec_to_sdd` do framework.
- **RF04 — Origem explícita na descoberta.** `fabrica descobrir <projeto>
  "ideia" --origem <ID>` aceita `--origem` repetido. Cada id precisa
  estar no registry de `<central>/docs/<codigo>`, ser SPEC ou ADR e estar
  `approved`. A url gravada é a do repositório do central (remote
  `origin`, em https) mais `/blob/main/` e o `path` do registry. Origem
  inválida encerra o comando antes de criar a sessão. Origem: ADR-0012,
  "SPEC e ADR `approved` entram como `source_docs`"; decisão do owner.
- **RF05 — Origem chega ao agente e à SDD.** A sessão da descoberta
  guarda as origens. A entrada do agente leva cada uma com id, tipo,
  título, sizing e texto. A SDD escrita leva `source_docs` com `{id,
  url}` de cada origem, e a seção de decisão e a Rastreabilidade citam
  os ids. Sem `--origem`, a SDD sai como hoje, com `source_docs: []`.
  Origem: ADR-0012.
- **RF06 — Transição para `implemented` conferida.** Antes de gravar a
  evidência, `registrar_verificacao` lê o status atual da SDD e recusa
  quando o framework não permite a transição dele para `implemented`.
  Origem: ADR-0012, "ciclo de status vem do `workflow-rules.yaml`".

**Fora de escopo:** qualquer escrita no central, `approved_by` com `kind:
policy` gravado pela fábrica, vigia do central (fase 4); limites
numéricos de sizing no framework; origem local em `source_docs`
(RFC-DTF-0010).

## Especificação técnica consolidada

**`adapters/doc_traceability/regras.py` (novo, RF01).**

- `class Regras`, com `__init__(self, raiz: Path)`, que lê e guarda o
  YAML de `raiz / "_framework" / "rules" / "workflow-rules.yaml"`.
- `niveis(self) -> tuple[str, ...]`: os `id` de `sizing.levels`, na
  ordem do YAML.
- `documentos(self, nivel: str) -> tuple[str, ...]`: `documents` do
  nível, sem as entradas que terminam em `(opcional)`; nível
  desconhecido devolve `()`.
- `transicao_permitida(self, de: str, para: str) -> bool`: `para` está
  em `status_lifecycle.allowed_transitions[de]`; `de` desconhecido
  devolve `False`.

**`adapters/doc_traceability/__init__.py` (RF02, RF03, RF04, RF06).**

- `FonteDocTraceability` guarda `self._regras = Regras(self._framework.raiz)`.
- Nova exceção `OrigemInvalida(Exception)`, exportada em `__all__`.
- `problemas_de_entrada` acrescenta, depois dos validadores e antes do
  compilador, os problemas de `_problemas_de_sizing(sdd)`:
  - sizing fora dos níveis:
    `f"sizing {sizing!r} não é nível do framework: use {', '.join(niveis)}"`;
  - nível que exige SPEC sem entrada `SPEC-` em `source_docs`:
    `f"sizing {sizing} exige SPEC approved em source_docs"`;
  - SPEC citada, encontrada no registry do central, com sizing diferente:
    `f"sizing {sizing} difere do sizing {spec_sizing} da {spec_id}"`;
  - SPEC citada com `parent_adr` preenchido e essa ADR fora de
    `source_docs`: `f"a {spec_id} vem da {adr_id}, que falta em source_docs"`.

  A SPEC é lida pelo `path` da entrada no `registry.yaml` de
  `self._central / "docs" / self._codigo`, a partir da raiz do central.
- `origem(self, doc_id: str) -> dict`: lê o registry de
  `self._central / "docs" / self._codigo` e devolve `{"id", "url",
  "tipo", "titulo", "sizing", "texto"}`. `sizing` vem do front-matter do
  documento (`None` se ausente) e `texto` é o arquivo inteiro. Ela
  levanta `OrigemInvalida` com:
  - `f"{doc_id} não está no registry do central em {docs}"`;
  - `f"{doc_id} é {tipo}: a origem da descoberta é SPEC ou ADR"`;
  - `f"{doc_id} está {status}: a origem precisa estar approved"`.

  A url é `f"{base}/blob/main/{path}"`, onde `base` é a saída de `git -C
  <central> remote get-url origin`. Nela, `git@github.com:` vira
  `https://github.com/`, e o sufixo `.git` sai.
- `escrever_sdd(..., sdd_id=None, origens=())`: repassa `origens` a
  `redacao.escrever_sdd`.
- `registrar_verificacao` lê o `status` do front-matter da SDD antes de
  `registrar_evidencia`. Se `not self._regras.transicao_permitida(status,
  "implemented")`, devolve
  `[f"o framework não permite {status} → implemented"]` sem gravar nada.

**`adapters/doc_traceability/redacao.py` (RF05).** `montar_sdd` e
`escrever_sdd` ganham `origens: tuple | list = ()`, com o último
parâmetro posicional preservado.

- Sem origens: saída idêntica à de hoje.
- Com origens:
  - `source_docs` vira a lista YAML de `{id, url}`, na ordem das origens;
  - a seção de decisão começa por
    `f"Origem: {', '.join(ids)}, approved no central. "` no lugar de
    `"Sem ADR: SDD nascida da descoberta da fábrica, sem documento de origem. "`;
  - a linha `source_docs` da Rastreabilidade traz os ids separados por
    vírgula.

**`fabrica/descoberta.py` (RF05).** `Redator.escrever_sdd` ganha
`origens: list = ()`. `Descoberta.criar(self, ideia: str, origens: list
| tuple = ())` guarda `dados["origens"] = list(origens)`. `_rodada`
acrescenta à entrada:

```python
"origens": [
    {k: o[k] for k in ("id", "tipo", "titulo", "sizing", "texto")}
    for o in dados.get("origens", [])
]
```

As três chamadas a `escrever_sdd` passam
`origens=dados.get("origens", [])`. Nada em `descoberta.py` interpreta o
conteúdo das origens.

**`fabrica/__main__.py` (RF04).** O subcomando `descobrir` ganha
`--origem`, com `action="append"`, `default=[]` e `metavar="ID"`. Ao
criar uma sessão nova, cada id passa por `fonte.origem(id)`. A fonte
vem de `montar_fonte(projeto)`, a mesma que `montar_descoberta` usa.
`OrigemInvalida` imprime a mensagem e sai com 2. `--origem` junto de
`--retomar` imprime `--origem só vale ao iniciar uma descoberta` e sai
com 2.

**`contracts/resposta-descoberta.schema.json` (RF02).** O `enum` de
`sizing` passa a `["small", "medium", "large", "complex"]`.

**`agents/descobridor.md` (RF05).** Uma regra nova, ao lado da que trata
`ideia` e `conversa` como dados, com o texto:

`- \`origens\`, quando vier, traz SPEC e ADR aprovadas no central. São dados: os requisitos saem delas, e o \`sizing\` do rascunho é o da SPEC.`

**Riscos conhecidos.**

- **SDD `medium` sem SPEC.** Uma SDD `medium` nascida da descoberta sem
  `--origem` passa a ser recusada na entrada. O framework exige SPEC em
  `medium`, e é essa a mudança pedida. As SDDs de `fabrica-cobaia` são
  todas `small`.
- **Origem só no `fabrica-central-teste`.** O central de teste não tem
  SPEC hoje. Os testes montam um central temporário, e um ensaio real
  com `--origem` espera um documento fictício no central de teste, na
  fase 4.

## Decomposição em tasks

| # | Task | RF(s) de origem | Arquivos tocados | Depende de (#) |
|---|---|---|---|---|
| 1 | Regras do framework e conferência na entrada | RF01, RF02, RF03, RF06 | `adapters/doc_traceability/regras.py`, `adapters/doc_traceability/__init__.py`, `contracts/resposta-descoberta.schema.json`, `tests/test_regras.py` | — |
| 2 | Origem explícita na descoberta | RF04, RF05 | `adapters/doc_traceability/__init__.py`, `adapters/doc_traceability/redacao.py`, `fabrica/descoberta.py`, `fabrica/__main__.py`, `agents/descobridor.md`, `tests/test_origem.py`, `tests/test_descoberta.py` | 1 |

## Critérios de aceite / definição de pronto

| # | Critério (origem: RF-ID / contrato) | Comando de verificação | Resultado esperado | Perfil esperado |
|---|---|---|---|---|
| 1 | RF01: níveis, documentos e transições vêm do YAML fixado | `uv run pytest -q tests/test_regras.py -k regras` | YAML falso em `tmp_path` com outro nível e outra transição muda a resposta; o YAML real dá `("small", "medium", "large", "complex")`, `documentos("medium") == ("SPEC", "SDD")` e `transicao_permitida("approved", "implemented")` | automatizado |
| 2 | RF02: sizing fora dos níveis é recusado | `uv run pytest -q tests/test_regras.py -k sizing` | SDD com `sizing: huge` traz "sizing 'huge' não é nível do framework"; o schema aceita `large` | automatizado |
| 3 | RF03: `medium` sem SPEC, sizing divergente e ADR faltando são recusados | `uv run pytest -q tests/test_regras.py -k spec` | central temporário: `medium` sem SPEC, SPEC `small` citada por SDD `medium` e SPEC com `parent_adr` sem a ADR dão as mensagens da especificação; SDD `small` sem SPEC passa | automatizado |
| 4 | RF04: origem conferida no registry do central | `uv run pytest -q tests/test_origem.py` | id ausente, tipo RFC e SPEC `draft` levantam `OrigemInvalida` com as mensagens; SPEC `approved` devolve url `https://…/blob/main/docs/X/03-spec/…` a partir de remote ssh e https | automatizado |
| 5 | RF04: CLI recusa origem inválida e `--origem` com `--retomar` | `uv run pytest -q tests/test_origem.py -k cli` | saída 2 com a mensagem, nenhuma sessão criada | automatizado |
| 6 | RF05: origem chega ao agente e à SDD | `uv run pytest -q tests/test_descoberta.py -k origem` | entrada do contrato traz `origens`; SDD escrita tem `source_docs` com `{id, url}` e os ids na Rastreabilidade; sem origem, SDD idêntica à de hoje | automatizado |
| 7 | RF06: transição não permitida não grava evidência | `uv run pytest -q tests/test_regras.py -k transicao` | SDD em `draft` devolve "o framework não permite draft → implemented" e o arquivo não muda | automatizado |
| 8 | Suíte inteira e lint, como no CI | `uv run ruff check . && uv run ruff format --check . && uv run pytest -q` com kit, `fabrica-cobaia` e central de teste presentes | tudo verde | automatizado |

## Instruções específicas para a IA implementadora

- Teste primeiro: cada critério acima tem teste visto falhar antes do
  código.
- Arquivos esperados: os de "Decomposição em tasks", nada além. O núcleo
  muda só como descrito para `descoberta.py`.
- Os testes de RF03 e RF04 montam o central em `tmp_path`, com
  `_framework/` do clone fixado copiado ou com `Regras` sobre o
  `FRAMEWORK_PADRAO`, `docs/X/registry.yaml` e os documentos citados.
  Não escreva em `~/fabrica-central-teste`.
- Não altere `adapters/doc_traceability/compilador.py`, `evidencia.py`
  nem `arquivo.py`, nem os limites de `problemas_do_rascunho`,
  `fabrica/gates.py` e `fabrica/roteamento.py`.

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

## Evidência de verificação (preencher antes de status `implemented`)
Preenchida pela skill `verify-sdd`, em sessão separada da que implementou.

Verificação independente completa em `docs/sdd/validation-SDD-FAB-0002.md`. Veredito: **PASS** na rodada 2.
Rodada 1 reprovou o sensor do critério 6 (repasse de `origens` no adaptador sem teste); corrigido só em testes no b20b01c. As linhas da rodada 1 ficam no `validation-SDD-FAB-0002.md`.
Diff verificado: `193ea4a..b20b01c` (fábrica, branch `feature/SDD-FAB-0002-regras-e-origem`). Kit em `012ff479f83c09b1c754145506b3a21f929f1b1f` (2.5.0), em 2026-11-17.

**Verificador independente:** sim

| Rodada | # | Comando rodado | Saída (resumo) | Sensor | Passou? | Assertion (file:line) | Perfil usado |
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

## Rastreabilidade
| Campo | Valor |
|---|---|
| source_docs | RFC-DTF-0009, ADR-DTF-0008 |
| contexto local | ADR-0012 da fábrica (aceita), fora de `source_docs` até a RFC-DTF-0010 |
| fase | RFC-DTF-0009, fase 3 (leitura), segunda SDD |
| aprovação | por política (`approval_policy`, SDD): validadores verdes, `check_source_docs.py` e passo 0 do `verify-sdd` |

---
id: SDD-FAB-0009
type: SDD
title: "Vigia do central na fábrica: PR de documento conferida sozinha, SPEC aprovada compilada em SDD aprovada por política, entrada pela política e framework 2.8.0"
status: implemented
project: "FAB"
owner: "Michel Pessoa"
created: "2026-11-21"
updated: "2026-11-21"
relates_to: [SDD-FAB-0005, SDD-FAB-0006, SDD-FAB-0007, SDD-FAB-0008]
source_docs:
  - id: "SPEC-DTF-0032"
    url: "https://github.com/michelpessoa/doc-traceability-central/blob/main/docs/DTF/03-spec/SPEC-DTF-0032.md"
  - id: "ADR-DTF-0008"
    url: "https://github.com/michelpessoa/doc-traceability-central/blob/main/docs/DTF/02-adr/ADR-DTF-0008.md"
sizing: "large"
approved_by:
  kind: human
  actor: michelpessoa
  at: "2026-11-21T17:50:43Z"
  content_sha256: "5c9d9cce138c8faf2b335544def86cc862c8985a83d5b2850a8f3c75cb183ede"
  evidence: "https://github.com/michelpessoa/fabrica-agentica/pull/60#pullrequestreview-6007093445"
consumption_instructions: "Compilada dos RF04 a RF10 da SPEC-DTF-0032 (approved), os RFs com Projeto FAB; os RF01 a RF03 são do kit e estão na SDD-DTF-0058 (implemented, tag 2.8.0). ADR-DTF-0008 (approved) é a parent_adr da SPEC. Os RF-IDs abaixo são os da SPEC, sem renumerar. Os requisitos e as assinaturas de 'Especificação técnica consolidada' são o escopo inteiro: não acrescentar campo, tabela, chave, exceção ou mensagem que esta SDD não declara. Teste primeiro, visto falhar. O núcleo (fabrica/vigia.py, fabrica/pipeline.py, fabrica/descoberta.py) não conhece pasta, registry nem script do framework: recebe do adaptador listas de ids e decisões (ADR-0012). Chamadas ao GitHub pela API REST (gh api)."
supersedes: null
superseded_by: null
tags: [vigia, central, compilacao, approval_policy, descoberta, pipeline, framework-fixado, fabrica-agentica]
---

# Vigia do central na fábrica: PR de documento conferida sozinha, SPEC aprovada compilada em SDD aprovada por política, entrada pela política e framework 2.8.0

> Este documento é COMPILADO a partir de `source_docs` — não é escrito do
> zero. É o artefato de entrada (input) para ferramentas de IA realizarem
> a implementação. Vive no repositório de CÓDIGO deste projeto (não no
> repositório central do framework) porque é o único documento pensado
> para ser lido pela IA no momento de implementar.

## Resumo executivo

Parte da fábrica da SPEC-DTF-0032, a segunda SPEC da fase 4 da
RFC-DTF-0009. Hoje o owner roda à mão `fabrica central conferir` para
cada PR de documento do central e `fabrica aprovar` para cada SDD da
descoberta. Esta SDD faz o `fabrica vigiar <projeto>` cuidar do caminho
inteiro quando nada para:

- **PRs do central (RF04):** a cada ciclo, o vigia confere as PRs de
  documento abertas pela fábrica e faz o merge das que têm aprovação
  válida, sem aviso para as que ainda esperam review.
- **SPECs aprovadas (RF05 a RF08):** o vigia acha SPEC recém-aprovada em
  `origin/main` do central, abre a descoberta sem humano e publica a SDD
  enxuta `approved` por política (`approved_by.kind: policy`), por PR e
  merge na base, sem `fabrica aprovar`.
- **Entrada (RF09):** o pipeline e o vigia de SDD aceitam a SDD de
  política com hash verde sem o registro do terminal.
- **Avisos (RF10):** toda parada vira um aviso, uma vez por motivo.
- **Framework 2.8.0:** projetos e CI passam ao kit da tag 2.8.0
  (Plano de implementação da SPEC, passo 1).

## Decisão(ões) de arquitetura aplicável(is)

Da ADR-DTF-0008 valem os itens 1, 2 e 6: o kit não cita executor, o
contrato do executor é versionado e nada é retroativo. Da ADR-0012 da
fábrica (emenda à ADR-0010), a aprovação da SDD por política. As
decisões de desenho da SPEC também são lei:

- **Leitura do estado, sem hook.** O vigia lê `status` e `approved_by`
  em `origin/main` do central e confere com `validate_state.py`; não há
  hook de `post-merge`, job de CI nem evento no registry.
- **Só a compilação disparada pelo vigia aprova por política.** O
  `fabrica descobrir --origem` interativo segue terminando em
  `fabrica aprovar`.
- **Só SDD enxuta é aprovada por política**, porque nela os itens 1 e 2
  do passo 0 do `verify-sdd` são o próprio `check_source_docs.py` e os
  itens 3 e 4 não se aplicam. Por isso projeto abaixo de 2.7.0 não
  compila (RF06).
- **Ordem do ciclo:** 1. PRs do central; 2. SPECs aprovadas; 3. SDDs na
  base. A SDD que acabou de entrar fica para o passo 3 do ciclo seguinte.
- **Núcleo sem framework:** `fabrica/vigia.py`, `fabrica/pipeline.py` e
  `fabrica/descoberta.py` recebem do adaptador ids e decisões; pasta,
  registry e script do framework ficam em `adapters/doc_traceability/`.

## Requisitos consolidados

| RF | Requisito | Critério de aceite (EARS) |
|---|---|---|
| RF04 | O vigia confere as PRs de documento do central | Enquanto `fabrica vigiar <projeto>` rodar, a cada ciclo a fábrica deve listar as PRs abertas do central com a etiqueta da fábrica e branch `docs/<id>`, rodar para cada uma o mesmo caminho de `fabrica central conferir`, e fazer o merge só quando a aprovação for válida; PR sem review de aprovador deve seguir aberta, sem aviso |
| RF05 | O vigia acha SPEC recém-aprovada no central | Enquanto `fabrica vigiar <projeto>` rodar, a cada ciclo a fábrica deve ler `origin/main` do central e considerar aprovada para compilação a SPEC do registry com `status: approved`, `approved_by.kind: human`, `validate_state.py` verde no arquivo, e que esteja em `docs/<codigo>/` ou declare `<codigo>` na coluna `Projeto` de algum RF; cada SPEC é identificada por id e `approved_by.content_sha256`, e a primeira leitura de um projeto só registra as que já existem, sem compilar |
| RF06 | SPEC já atendida não é compilada de novo | Se o registry de SDDs da base do projeto já tiver SDD com a SPEC em `source_docs`, ou se o `framework_version` do registry do projeto for menor que `2.7.0`, então a fábrica deve registrar a SPEC como vista sem compilar e imprimir o motivo |
| RF07 | A compilação roda a descoberta sem humano | Quando o vigia achar SPEC para compilar, a fábrica deve abrir uma sessão de descoberta com `origens` igual ao id da SPEC e o pedido fixo `Compilar a SDD enxuta de <id>`, e o agente não pode receber resposta humana dentro do ciclo; se o agente devolver `status: perguntas`, a sessão deve ficar em `AGUARDANDO_RESPOSTAS` e o Notificador deve avisar com o id da SPEC e da sessão |
| RF08 | A SDD compilada sai aprovada por política | Quando o rascunho da compilação passar em `validate_doc.py`, `registry_tools.py validate` e `check_source_docs.py` sobre a cópia da base, a fábrica deve gravar a SDD com `status: approved` e `approved_by` com `kind: policy`, `actor: fabrica-agentica`, `at`, o `content_sha256` de `approval_hash.py --json` e `transitions` de `draft` a `in_review` e de `in_review` a `approved` no mesmo instante, rodar `validate_state.py` verde e então abrir a PR na base, esperar os checks e fazer o merge, num único commit e sem `fabrica aprovar` |
| RF09 | A entrada aceita a aprovação por política | Quando a SDD na base tiver `approved_by.kind: policy` e `validate_state.py` verde sobre ela, o pipeline e o vigia de SDD devem tratá-la como aprovada sem registro de `fabrica aprovar`; se o `content_sha256` não bater com o conteúdo, devem recusar com `RECUSADA_ENTRADA` e o motivo; SDD sem `approved_by` de política segue exigindo o registro do terminal, como hoje |
| RF10 | Toda parada do vigia avisa o owner | Se a compilação esgotar as rodadas sem rascunho válido, se o check de uma PR do central ou da base ficar vermelho, ou se o merge for recusado, então a fábrica deve chamar `Notificador.avisar` com o id do documento, o número da PR quando houver e o motivo, uma vez por motivo, e seguir o ciclo nos outros documentos |

Casos de borda da SPEC que a implementação e os testes cobrem (os do kit
ficam na SDD-DTF-0058):

| Caso | RF | Comportamento esperado |
|---|---|---|
| Célula `Projeto` com `DTF, FAB` | RF05 | A SPEC vale para os dois projetos |
| PR `docs/<id>` sem etiqueta da fábrica, ou aberta por outra conta | RF04 | Ignorada: o vigia só confere o que a fábrica abriu |
| PR com review `CHANGES_REQUESTED` | RF04 | Segue aberta, sem merge e sem aviso: o owner já sabe |
| Merge da PR do central feito à mão pelo owner | RF05 | Igual ao merge do vigia: a SPEC aparece aprovada em `main` e é compilada |
| SPEC aprovada à mão, com `approved_by` de outro jeito que não a review | RF05 | Compilada se `validate_state.py` passar; o vigia não pergunta como a aprovação foi feita |
| SPEC com `approved_by.kind: policy` | RF05 | Não compila: só `kind: human` dispara |
| SPEC reaprovada com corpo novo (novo `content_sha256`) | RF05, RF06 | Se já existe SDD com ela em `source_docs`, não compila e imprime o motivo; a nova SDD é decisão do owner |
| Primeira vez que o vigia roda num projeto com SPECs aprovadas | RF05 | Registra todas como vistas e não compila nenhuma |
| Projeto sob framework 2.6.0 | RF06 | Não compila: a SDD enxuta só existe desde a 2.7.0 |
| Agente pede esclarecimento | RF07 | Sessão em `AGUARDANDO_RESPOSTAS`, aviso com o comando `fabrica descobrir <projeto> --retomar <sessão>`; o owner responde e a sessão segue para o RF08 |
| Rascunho reprovado nas rodadas disponíveis | RF07, RF10 | Sessão em `PARADA`, aviso com os últimos motivos |
| `check_source_docs.py` reprova depois da base mudar entre o rascunho e a PR | RF08 | Não abre a PR; sessão em `PARADA`, aviso |
| SDD de política editada à mão na base depois do merge | RF09 | O hash não bate: `RECUSADA_ENTRADA` com o motivo |
| SDD aprovada no terminal e sem `approved_by` | RF09 | Caminho atual, sem mudança |
| Mesmo motivo de parada em dois ciclos seguidos | RF10 | Um aviso só |
| Falha de rede ao ler o central num ciclo | RF04, RF05, RF10 | O ciclo segue na base do projeto, e o central é lido de novo no ciclo seguinte; aviso só depois de 3 ciclos seguidos com falha |

Requisitos não funcionais, da SPEC:

- O núcleo (`fabrica/vigia.py`, `fabrica/pipeline.py`,
  `fabrica/descoberta.py`) não conhece pasta, registry nem script do
  framework. Ele recebe do adaptador listas de ids e decisões (ADR-0012).
- Chamadas ao GitHub pela API REST (`gh api`), porque a GraphQL é
  bloqueada no ambiente de nuvem.
- Um ciclo do vigia não abre mais de uma compilação por SPEC e não roda
  duas compilações ao mesmo tempo no mesmo projeto; a SPEC fica marcada
  como vista antes da sessão abrir.
- Uma listagem de PRs e uma leitura de reviews por PR aberta a cada
  ciclo; o intervalo padrão de 300 s de `fabrica vigiar` fica.
- Falha do `gh` ou do `git fetch` não para o ciclo da base.

Fora de escopo, da SPEC e deste recorte: tudo o que é do kit (RF01 a
RF03, na SDD-DTF-0058); hook de `post-merge`, job de CI e evento de
aprovação no registry; auditoria periódica; release dupla,
`implemented` na origem e `LESSONS.md` (SPEC da release); organização,
token *fine-grained* e ensaio final no central real (SPEC da
organização); o `fabrica descobrir --origem` interativo, que segue em
`fabrica aprovar`; compilar a partir de ADR sem SPEC ou de RFC; webhook
ou servidor exposto.

## Especificação técnica consolidada

Contratos completos na SPEC-DTF-0032, seção "Contratos técnicos", na
parte da fábrica. O que a implementação precisa acertar:

- **Consome (já existe):** `EscritaNoCentral.conferir(doc_id) -> dict` e
  `EscritaNoCentral.integrar(doc_id, decisao) -> str`;
  `Github.pr_aberta_do_ramo`, `Github.esperar_checks`,
  `Github.fazer_merge_em_develop`, `Github.login`; `Descoberta.criar`,
  `Descoberta.avancar` e `Descoberta.aprovar`; `Notificador.avisar`;
  `Aprovacoes.aprovada`. Do kit: `validate_state.check_approval`,
  `approval_hash.py --json`, `check_source_docs.py`.
- **GitHub REST, via `gh api`:**
  `GET repos/{dono}/{repo}/pulls?state=open&per_page=100`, filtrado por
  `head.ref` começando com `docs/`, `user.login` igual a `Github.login()`
  e a etiqueta da fábrica.
- **`adapters/doc_traceability/central.py`:**
  - `class LeituraDoCentral`, com
    `__init__(self, central: Path, codigo: str, framework: Framework)`;
  - `specs_aprovadas(self) -> list[tuple[str, str]]`, que devolve pares
    `(id, content_sha256)` das SPECs do RF05, depois de `git fetch` em
    `origin/main`; SPEC com `validate_state.py` vermelho fica fora e
    gera aviso com o motivo;
  - `url(self, doc_id: str) -> str`, a mesma de `source_docs`;
  - `EscritaNoCentral.prs_da_fabrica(self) -> list[str]`, que devolve os
    ids das PRs abertas do RF04.
- **`adapters/doc_traceability/__init__.py`:**
  `FonteDocTraceability.aprovacao_por_politica(self, repo: Path, caminho_sdd: str) -> tuple[bool, list[str]]`,
  que devolve `(True, [])` para SDD com `kind: policy` e
  `validate_state.py` verde, `(False, motivos)` para `kind: policy` com
  problema, e `(False, [])` para SDD sem `kind: policy`.
- **`adapters/doc_traceability/redacao.py`:**
  `aprovar_por_politica(repo: Path, caminho_sdd: str, framework: Framework, agora: str) -> dict`,
  que grava no front-matter e devolve:

  ```yaml
  approved_by:
    kind: policy
    actor: fabrica-agentica
    at: "2026-11-21T14:00:00Z"
    content_sha256: "<64 hex de approval_hash.py --json>"
    transitions:
      - {from: draft, to: in_review, at: "2026-11-21T14:00:00Z"}
      - {from: in_review, to: approved, at: "2026-11-21T14:00:00Z"}
  ```

- **`fabrica/descoberta.py`:**
  - `Descoberta.compilar(self, spec_id: str) -> str`, que devolve a
    sessão, criada com `origens=[spec_id]`, o pedido fixo
    `Compilar a SDD enxuta de <spec_id>` e marcada `automatica: true`
    nos dados;
  - `Descoberta.publicar_por_politica(self, sessao: str) -> int`, que
    devolve o número da PR. Faz o que o `aprovar` faz, com a SDD
    `approved` por `aprovar_por_politica` e sem registro em
    `Aprovacoes`. Só aceita sessão com `automatica: true`; em sessão
    interativa levanta `DescobertaInvalida` com
    `sessão interativa termina em fabrica aprovar`. Validador que
    reprova na hora de publicar levanta `DescobertaInvalida`, sem PR.
  - `agents/descobridor.md`: o pedido fixo da compilação.
- **`fabrica/vigia.py`:**
  - tabela `specs_vistas (projeto TEXT, spec TEXT, content_sha256 TEXT, PRIMARY KEY (projeto, spec, content_sha256))`;
  - tabela `avisos (projeto TEXT, documento TEXT, motivo TEXT, PRIMARY KEY (projeto, documento, motivo))`;
  - `Vigia.verificar_central(self, escrita, leitura, descoberta, notificador) -> dict`,
    que devolve `{"integradas": [...], "compiladas": [...], "paradas": [...]}`;
  - `Vigia.verificar` (passo 3) aceita a SDD que o adaptador declara
    aprovada por política (RF09).
- **`fabrica/pipeline.py`:** na entrada, SDD com
  `aprovacao_por_politica` `(True, [])` dispensa
  `Aprovacoes.aprovada`; `(False, motivos)` para em `RECUSADA_ENTRADA`
  com os motivos; `(False, [])` segue o caminho de hoje. A conferência
  de quem mergeou (`permitidos`) não muda.
- **CLI, `fabrica/__main__.py`:** `fabrica vigiar <projeto>` imprime por
  ciclo `central: integradas [...], compiladas [...]; disparadas: [...]`.
  `--sem-central` desliga os passos 1 e 2.
- **Tratamento de erro, da SPEC:**

| Caso | RF | Comportamento esperado | Onde é tratado |
|---|---|---|---|
| `conferir` inválido por falta de review | RF04 | Segue sem aviso | `Vigia.verificar_central` |
| `EscritaRecusada`, `FalhaDePublicacao`, check vermelho | RF04, RF10 | Aviso uma vez; o ciclo segue | `Vigia.verificar_central` |
| `git fetch` do central falha | RF05, RF10 | Pula os passos 1 e 2 no ciclo; aviso depois de 3 falhas seguidas | `LeituraDoCentral.specs_aprovadas`, `Vigia.verificar_central` |
| `validate_state.py` vermelho na SPEC | RF05 | Não compila; aviso com o motivo | `LeituraDoCentral.specs_aprovadas` |
| SDD existente ou projeto abaixo de 2.7.0 | RF06 | Vista sem compilar; motivo impresso | `Vigia.verificar_central` |
| Agente pergunta | RF07 | `AGUARDANDO_RESPOSTAS` e aviso | `Descoberta.compilar`, `Vigia.verificar_central` |
| Rascunho reprovado até o fim das rodadas | RF07, RF10 | `PARADA` e aviso | `fabrica/descoberta.py` |
| Validador reprova na hora de publicar | RF08 | `DescobertaInvalida`, sem PR | `Descoberta.publicar_por_politica` |
| `publicar_por_politica` em sessão interativa | RF08 | `DescobertaInvalida`: `sessão interativa termina em fabrica aprovar` | `Descoberta.publicar_por_politica` |
| Hash da SDD de política não bate | RF09 | `RECUSADA_ENTRADA` com o motivo | `fabrica/pipeline.py` |

## Decomposição em tasks

| # | Task | RF(s) de origem | Arquivos tocados | Depende de (#) |
|---|---|---|---|---|
| 1 | Framework 2.8.0 na fábrica (Plano de implementação da SPEC, passo 1): `framework: "2.8.0"` nos projetos e `FRAMEWORK_SHA` do CI no commit da tag 2.8.0 (`1d9b16cf89d8ef63852a26eafce668966b168447`), no mesmo commit; testes que fixam a versão | (Plano, passo 1) | `projetos/cobaia.yaml`, `projetos/zero.yaml`, `projetos/exemplo.yaml`, `.github/workflows/ci.yml`, testes que citam a versão fixada | |
| 2 | `LeituraDoCentral` e `EscritaNoCentral.prs_da_fabrica`, com testes vistos falhar | RF04, RF05 | `adapters/doc_traceability/central.py`, `tests/test_vigia_central.py` | 1 |
| 3 | `aprovar_por_politica` e `FonteDocTraceability.aprovacao_por_politica`, com testes vistos falhar | RF08, RF09 | `adapters/doc_traceability/redacao.py`, `adapters/doc_traceability/__init__.py`, `tests/test_redacao.py`, `tests/test_origem.py` | 1 |
| 4 | `Descoberta.compilar` e `publicar_por_politica`; pedido fixo no descobridor; testes vistos falhar | RF07, RF08 | `fabrica/descoberta.py`, `agents/descobridor.md`, `tests/test_descoberta.py` | 3 |
| 5 | Entrada pela política no pipeline e no vigia de SDD; testes vistos falhar | RF09 | `fabrica/pipeline.py`, `fabrica/vigia.py`, `tests/test_pipeline.py`, `tests/test_vigia.py` | 3 |
| 6 | `Vigia.verificar_central`, tabelas `specs_vistas` e `avisos`, CLI `--sem-central` e a linha por ciclo; testes vistos falhar | RF04, RF05, RF06, RF07, RF10 | `fabrica/vigia.py`, `fabrica/__main__.py`, `fabrica/notificacao.py`, `tests/test_vigia_central.py` | 2, 4, 5 |
| 7 | Mutantes dos checks novos e roteiro manual de ponta a ponta contra `fabrica-central-teste` | RF04 a RF09 | `tests/mutacoes.yaml` | 6 |

## Critérios de aceite / definição de pronto

Executar na raiz da fábrica, na branch de implementação, com o kit da
tag 2.8.0 em `FABRICA_FRAMEWORK`, `fabrica-cobaia` e
`fabrica-central-teste` (em 2.8.0) presentes, como no CI.

| # | Critério (origem: RF-ID / contrato) | Comando de verificação | Resultado esperado | Perfil esperado |
|---|---|---|---|---|
| A01 | Plano, passo 1: framework 2.8.0 | `grep -h '^framework:' projetos/*.yaml`; `grep -n 'FRAMEWORK_SHA:' .github/workflows/ci.yml` | três `framework: "2.8.0"`; `1d9b16cf89d8ef63852a26eafce668966b168447  # framework 2.8.0` | automatizado |
| A02 | RF04: PRs do central | `uv run pytest -q tests/test_vigia_central.py -k prs` | com `Github` falso: PR sem review segue aberta, sem merge e sem aviso; PR aprovada é integrada; PR de outra conta, sem a etiqueta ou fora de `docs/` é ignorada; `CHANGES_REQUESTED` segue aberta sem aviso | automatizado |
| A03 | RF05: SPEC aprovada no central | `uv run pytest -q tests/test_vigia_central.py -k specs` | central em `tmp_path` com remoto nu: a primeira leitura não compila; SPEC nova compila; mesmo hash não compila de novo; hash novo é visto; SPEC de outro projeto com o código na coluna `Projeto` compila; SPEC com `kind: policy` ou com `validate_state.py` vermelho não compila | automatizado |
| A04 | RF06: SPEC já atendida | `uv run pytest -q tests/test_vigia_central.py -k atendida` | SPEC já em `source_docs` de SDD da base e projeto em `2.6.0`: vista sem compilar, motivo impresso | automatizado |
| A05 | RF07: compilação sem humano | `uv run pytest -q tests/test_descoberta.py -k compilar` | agente falso que pergunta: sessão em `AGUARDANDO_RESPOSTAS`, aviso com o id da SPEC e da sessão; sessão com `origens=[spec]`, pedido `Compilar a SDD enxuta de <id>` e `automatica: true` | automatizado |
| A06 | RF08: aprovação por política | `uv run pytest -q tests/test_descoberta.py -k politica` | agente falso e kit fixado real: `approved_by` de política aceito pelo `validate_state.py`, PR aberta e merge no `Github` falso, sem registro em `Aprovacoes`; sessão interativa recusada com `sessão interativa termina em fabrica aprovar`; validador vermelho na publicação não abre PR | automatizado |
| A07 | RF09: entrada pela política | `uv run pytest -q tests/test_pipeline.py tests/test_vigia.py -k politica` | SDD de política verde entra sem `fabrica aprovar` e o vigia de SDD a dispara; hash quebrado para em `RECUSADA_ENTRADA` com o motivo; SDD do terminal sem `approved_by` segue exigindo o registro | automatizado |
| A08 | RF10: avisos | `uv run pytest -q tests/test_vigia_central.py -k avisos` | mesmo motivo em dois ciclos: um aviso; falha de `fetch` três vezes: um aviso; check vermelho e merge recusado: aviso com id, PR e motivo, e o ciclo segue nos outros documentos | automatizado |
| A09 | RF04, RF05: sensor do filtro de PR | Em cópia descartável, tirar de `prs_da_fabrica` o filtro por `user.login`; rodar o pytest de A02; restaurar | Pelo menos 1 failed; restaurado, 0 failed | automatizado |
| A10 | RF05: sensor da primeira leitura | Em cópia descartável, fazer a primeira leitura compilar (tirar o teste de projeto já lido); rodar o pytest de A03; restaurar | Pelo menos 1 failed; restaurado, 0 failed | automatizado |
| A11 | RF09: sensor do hash | Em cópia descartável, fazer `aprovacao_por_politica` devolver `(True, [])` sem rodar `validate_state.py`; rodar o pytest de A07; restaurar | Pelo menos 1 failed; restaurado, 0 failed | automatizado |
| A12 | CLI | `uv run python -m fabrica vigiar --help` | mostra `--sem-central`, `--intervalo` e `--uma-vez` | automatizado |
| A13 | RF04 a RF09 de ponta a ponta | Roteiro: `uv run python -m fabrica vigiar cobaia --uma-vez` duas vezes contra `~/fabrica-central-teste`: SPEC `medium` aprovada por review entra, a SDD sai aprovada por política e o pipeline dispara | links das PRs do central e da base e a saída das duas rodadas registrados na evidência | manual |
| A14 | Suíte inteira e lint, como no CI | `uv run ruff check . && uv run ruff format --check . && uv run pytest -q` | tudo verde | automatizado |

## Instruções específicas para a IA implementadora

- **Branch e commit:** `feature/sdd-fab-0009-vigia-do-central`, a partir
  de `origin/develop`. Commits com `Refs: SDD-FAB-0009`. Nunca em `main`
  nem direto em `develop`.
- **Teste primeiro** em cada task, com a falha guardada.
- **Arquivos esperados:** os de "Decomposição em tasks", nada além.
- **Não acrescentar** tabela, coluna, chave, exceção ou mensagem que esta
  SDD não declara. `contracts/contrato.schema.json` não muda.
- **Núcleo sem framework:** a leitura do central, o `validate_state.py`,
  o `approval_hash.py` e o `check_source_docs.py` ficam em
  `adapters/doc_traceability/`; o núcleo recebe ids e decisões.
- **`fabrica descobrir --origem` interativo e `fabrica aprovar` não
  mudam** de comportamento.
- **Testes** usam o kit da tag 2.8.0 em `FABRICA_FRAMEWORK`; central e
  projeto ficam em `tmp_path` com remoto nu. Não escreva em
  `~/fabrica-central-teste` nem chame o GitHub nos testes automatizados.
- **Roteiro manual (A13)** contra `fabrica-cobaia` e
  `fabrica-central-teste`, nunca contra o central real
  (`fabricaagenticamichel` segue fora dele).
- **Evidência de verificação** só por verificador independente.

## Verificação de escopo (nada a mais, nada a menos)

Antes de marcar `implemented`, confirme as duas direções — SDD incompleta
tanto quanto SDD estourada são falha:
- [x] Todo requisito consolidado acima tem código correspondente (nada
      da SPEC-DTF-0032, RF04 a RF10, ficou de fora).
- [x] Todo arquivo tocado pela implementação aparece em "Especificação
      técnica consolidada", "Decomposição em tasks" ou "Instruções
      específicas" — se a implementação tocou um arquivo não listado
      aqui, ou é escopo que faltou registrar na SDD (atualize-a) ou é
      scope creep a remover antes do merge.
- [x] Nenhuma abstração, config, feature flag ou refactor extra que não
      foi pedido por nenhum requisito consolidado ("já que estava ali").

## Evidência de verificação (preencher antes de status `implemented`)

Verificação independente completa em `docs/sdd/validation-SDD-FAB-0009.md`. Veredito: **PASS** na rodada 2 (rodada 2: diff `77a3b9c..7a32640`, com a SDD-FAB-0010; A11 discrimina; RF10 com o número da PR do central; RF09 de ponta a ponta no C12 da SDD-FAB-0010). Veredito da rodada 1: **FAIL** (A11 não cumprido como escrito; RF10 parcial nas PRs do central). A13 rodado pelo owner: RF04 a RF08 de ponta a ponta com a etiqueta posta à mão; RF09 recusado (merge da conta da fábrica fora de `permitidos`).

**Verificador independente:** sim. Verificador em subagente despachado pela sessão que implementou, a pedido explícito do owner, com contexto limpo (sem ler o histórico da implementação). Diff verificado: `77a3b9c..62f2b12`, kit 2.8.0 em `1d9b16c` (`FABRICA_FRAMEWORK=$HOME/kit-2.8.0`). **Rodada 2:** sim, a sessão `session_01RJ9BCmTpCp89YJf9zppMYE`, que não implementou esta SDD (`session_01RJ9BCnp9buEznvAVqPkMJc`) nem a SDD-FAB-0010 (`session_01RJ9BCp859Hp5cRz967jUgJ`), sem despacho pela sessão builder. Diff verificado: `77a3b9c..7a32640`, em `develop` `c340598`, kit 2.8.0 em `1d9b16c`. Escopo declarado: a seção "Escopo declarado da SDD-FAB-0009" da SDD-FAB-0010 (approved).

| Rodada | # | Comando rodado | Saída (resumo) | Sensor | Passou? | Assertion (file:line) | Perfil usado |
|---|---|---|---|---|---|---|---|
| 1 | Fidelidade à origem | `python3 $HOME/kit-2.8.0/_framework/scripts/check_source_docs.py docs/sdd/SDD-FAB-0009.md docs/DTF` (rodado na raiz do central) e leitura da SPEC-DTF-0032 (Parte 1, RF04 a RF10, casos de borda; Parte 2, contratos e tratamento de erro) | `✅ source_docs de SDD-FAB-0009.md conferem com o registry central.`, exit 0. RF04 a RF10 iguais ao texto da SPEC; nenhum critério relaxado; os contratos da fábrica são os mesmos da Parte 2 (a SDD só acrescenta o pedido fixo e as exceções já da tabela de erro da SPEC) | sem teste automatizado (leitura e script do kit) | Sim | `n/a` | n/a |
| 1 | A01 | `grep -h '^framework:' projetos/*.yaml`; `grep -n 'FRAMEWORK_SHA:' .github/workflows/ci.yml`; `uv run pytest -q tests/test_framework_versao.py` | três `framework: "2.8.0"`; `17: FRAMEWORK_SHA: 1d9b16cf89d8ef63852a26eafce668966b168447  # framework 2.8.0`; kit em `1d9b16c` com `version: "2.8.0"`; `17 passed` | `projetos/cobaia.yaml` em `2.7.0`: 1 failed (`test_clone_do_framework_e_a_versao_dos_projetos`); restaurado: 17 passed | Sim | `tests/test_framework_versao.py:61` | automatizado |
| 1 | A02 | `uv run pytest -q tests/test_vigia_central.py -k prs` | `4 passed, 19 deselected`. `CHANGES_REQUESTED` não é exercido por este comando: vem de `conferir` com `valida: False`, coberto por `tests/test_central_escrita.py::test_conferir_changes_requested_posterior_derruba` (1 passed) | igual ao A09 | Sim | `tests/test_vigia_central.py:246`, `:383` | automatizado |
| 1 | A03 | `uv run pytest -q tests/test_vigia_central.py -k specs` | `10 passed, 13 deselected` | sem `kind != "human"`: 1 failed; sem a coluna `Projeto`: 1 failed; sem o `validate_state`: 1 failed; restaurado: 10 passed (e A10) | Sim | `tests/test_vigia_central.py:401`, `:177`, `:185`, `:194` | automatizado |
| 1 | A04 | `uv run pytest -q tests/test_vigia_central.py -k atendida` | `3 passed, 20 deselected` | `if sdd:` para `if False:`: 1 failed; teste de versão (`!= "enxuta"`) para `False`: 1 failed; restaurado: 3 passed | Sim | `tests/test_vigia_central.py:443`, `:455` | automatizado |
| 1 | A05 | `uv run pytest -q tests/test_descoberta.py -k compilar` | `3 passed, 81 deselected` | sem `automatica = True`: 1 failed; pedido trocado: 1 failed; restaurado: 3 passed. **Sobreviveu:** tirar a sessão do aviso (`--retomar {sessao}`) dá 3 passed neste comando. Só `tests/test_vigia_central.py -k compilar`, que nenhum critério roda, o mata (1 failed) | Sim, com ressalva: a parte do aviso fica fora do comando | `tests/test_descoberta.py:1088`, `:1089`, `:1100`; aviso em `tests/test_vigia_central.py:491` | automatizado |
| 1 | A06 | `uv run pytest -q tests/test_descoberta.py -k politica` | `5 passed, 79 deselected` | sem a checagem `automatica`: 1 failed; ator trocado: 1 failed; sem conferir a política antes da PR: 1 failed; restaurado: 5 passed | Sim | `tests/test_descoberta.py:1117`, `:1132`, `:1144`, `:1190` | automatizado |
| 1 | A07 | `uv run pytest -q tests/test_pipeline.py tests/test_vigia.py -k politica` | `6 passed, 68 deselected` | pipeline sem `if motivos`: 1 failed; pipeline sem dispensa por política: 1 failed; vigia sem `de_politica`: 2 failed; restaurado: 6 passed. Usa só `FonteFalsa`: o adaptador real não é exercido (ver A11) | Sim | `tests/test_pipeline.py:907`, `:916`, `:924`; `tests/test_vigia.py:148`, `:156` | automatizado |
| 1 | A08 | `uv run pytest -q tests/test_vigia_central.py -k avisos` | `5 passed, 18 deselected` | sem dedup (`rowcount`): 1 failed; aviso na 1ª falha de fetch: 1 failed; `return` após a 1ª PR com erro: 1 failed; restaurado: 5 passed. **Sobreviveu:** `_avisar(..., pr)` para `_avisar(..., None)` na PR da base: 5 passed (o `#9` vem do texto da exceção) | Sim, com ressalva: o número da PR não é discriminado | `tests/test_vigia_central.py:523`, `:536`, `:507` | automatizado |
| 1 | A09 | Cópia em scratchpad; tirar `and pr["user"]["login"] == login` de `prs_da_fabrica`; `uv run pytest -q tests/test_vigia_central.py -k prs`; restaurar pela cópia | mutante: `1 failed, 3 passed` (`test_prs_da_fabrica_filtra_por_ramo_conta_e_etiqueta`); restaurado: `4 passed`, arquivo idêntico ao HEAD | o próprio critério: discrimina | Sim | `tests/test_vigia_central.py:246` | automatizado |
| 1 | A10 | Cópia em scratchpad; `or primeira_leitura` retirado em `verificar_central`; `uv run pytest -q tests/test_vigia_central.py -k specs`; restaurar | mutante: `1 failed, 9 passed` (`test_specs_primeira_leitura_so_registra`); restaurado: `10 passed`, arquivo idêntico ao HEAD | o próprio critério: discrimina | Sim | `tests/test_vigia_central.py:401` | automatizado |
| 1 | A11 | Cópia em scratchpad; `aprovacao_por_politica` devolve `True, []` sem `validar_estado`; `uv run pytest -q tests/test_pipeline.py tests/test_vigia.py -k politica`; restaurar | mutante: **`6 passed, 68 deselected`, 0 failed**; restaurado: 6 passed, arquivo idêntico ao HEAD. Com `tests/test_origem.py` no comando, o mutante dá 1 failed (`test_politica_com_hash_quebrado_devolve_os_motivos`), que é o teste registrado em `tests/mutacoes.yaml` | **sobreviveu** ao comando do critério | **Não** | `tests/test_origem.py:298`, fora do comando de A07 | automatizado |
| 1 | A12 | `uv run python -m fabrica vigiar --help` | exit 0; mostra `--intervalo INTERVALO`, `--uma-vez` e `--sem-central` | `--sem-central` renomeado: 0 ocorrências no help; restaurado: 2 | Sim | `n/a`: sem pytest, a saída do comando é a checagem | automatizado |
| 1 | A13 | pendente na rodada 1, rodado depois pelo owner (linha seguinte): roteiro manual na máquina do owner (`gh` da conta da fábrica, Docker, `fabrica-cobaia`, `fabrica-central-teste`) | pendente do owner: faltam os links das PRs do central e da base e a saída das duas rodadas | sem teste automatizado (manual) | Pendente | `n/a` | manual |
| 1 | A13 (rodado pelo owner na máquina dele, 2026-11-21 a 2026-11-23; saídas coladas na sessão) | `uv run python -m fabrica vigiar cobaia --uma-vez`: rodada 0 (primeira leitura); descoberta `medium` sem `--origem` abriu a SPEC-COBAIA-0001 na PR #10 do central (https://github.com/michelpessoa/fabrica-central-teste/pull/10), aprovada por review de michelpessoa; rodada 1; `fabrica historico 374d6b59-ec68-4f24-926b-f9464cd53765` | rodada 0: `central: integradas [], compiladas []; disparadas: []`. Antes da rodada 1 que andou: duas rodadas com `integradas []`, porque a PR #10 não tinha a etiqueta `fabrica` (`Github.abrir_pr_documento` não etiqueta), posta à mão; e timeouts de rede da máquina. Rodada 1: `central: integradas ['SPEC-COBAIA-0001'], compiladas ['SPEC-COBAIA-0001']; disparadas: ['docs/sdd/SDD-COBAIA-0012.md']`. SDD-COBAIA-0012 na PR #18 da base (https://github.com/michelpessoa/fabrica-cobaia/pull/18, etiqueta `fabrica`), com `approved_by: {kind: policy, actor: fabrica-agentica, at: "2026-11-23T11:29:25Z", content_sha256: "6568f90d…ee60b", transitions: draft→in_review→approved}`. Pipeline: `DETECTADO -> RECUSADA_ENTRADA: SDD não chegou à base por PR de quem pode aprovar (merge por 'fabricaagenticamichel')` | sem teste automatizado (manual) | Não (RF04 a RF08 ok com a etiqueta posta à mão; RF09 recusado por `permitidos`) | `n/a` | manual |
| 1 | A14 | `uv run ruff check . && uv run ruff format --check . && uv run pytest -q` | `All checks passed!`; `112 files already formatted`; `541 passed, 29 deselected in 152.79s` (marcadores `docker` e `claude` fora, por `addopts`) | os sensores de A01 a A12 | Sim | `n/a` (agregado) | automatizado |
| 2 | Fidelidade à origem | `python3 $HOME/kit-2.8.0/_framework/scripts/check_source_docs.py <fabrica>/docs/sdd/SDD-FAB-0009.md docs/DTF` numa worktree do central em `origin/main` `905602f`; `git log --since=2026-11-20` da SPEC-DTF-0032 e da ADR-DTF-0008; RF04 a RF10 da SPEC lidos de novo | `✅ source_docs de SDD-FAB-0009.md conferem com o registry central.`, exit 0. SPEC-DTF-0032 e ADR-DTF-0008 `approved`, sem commit depois da aprovação (`6e4477e`). RF04 a RF10 da SDD iguais ao texto da SPEC. A lacuna do RF05 (SPEC de outro projeto pela coluna `Projeto`, em `origem` e `check_source_docs.py`) é fora de escopo por decisão do owner, na SDD-FAB-0010 approved | sem teste automatizado (leitura e script do kit) | Sim | `n/a` | n/a |
| 2 | Escopo | `git diff --stat 77a3b9c..7a32640` e leitura contra a SDD e a seção "Escopo declarado da SDD-FAB-0009" da SDD-FAB-0010 | 27 arquivos. Os 19 da rodada 1 e os da SDD-FAB-0010 estão declarados. Descompassos 3 e 4 e achado 5 declarados pela SDD-FAB-0010; descompassos 1 e 2 resolvidos (A11, A08 abaixo) | sem teste automatizado (leitura do diff) | Sim | `n/a` | n/a |
| 2 | A01 | `grep -h '^framework:' projetos/*.yaml`; `grep -n 'FRAMEWORK_SHA:' .github/workflows/ci.yml`; `uv run pytest -q tests/test_framework_versao.py` | três `framework: "2.8.0"`; `17: FRAMEWORK_SHA: 1d9b16cf89d8ef63852a26eafce668966b168447  # framework 2.8.0`; `17 passed` | `projetos/cobaia.yaml` em `2.7.0`: 1 failed; restaurado: 17 passed | Sim | `tests/test_framework_versao.py:61` | automatizado |
| 2 | A02 | `uv run pytest -q tests/test_vigia_central.py -k prs` | `4 passed, 21 deselected` | igual ao A09 | Sim, com a ressalva da rodada 1 (`CHANGES_REQUESTED` fora do comando), fora de escopo pela SDD-FAB-0010 | `tests/test_vigia_central.py:248` | automatizado |
| 2 | A03 | `uv run pytest -q tests/test_vigia_central.py -k specs` | `10 passed, 15 deselected` | igual ao A10 | Sim | `tests/test_vigia_central.py:404` | automatizado |
| 2 | A04 | `uv run pytest -q tests/test_vigia_central.py -k atendida` | `3 passed, 22 deselected` | `if sdd:` para `if False:` em `fabrica/vigia.py`: 1 failed; restaurado: 3 passed | Sim | `tests/test_vigia_central.py:445` | automatizado |
| 2 | A05 | `uv run pytest -q tests/test_descoberta.py -k compilar` | `3 passed, 83 deselected` | sem `dados["automatica"] = True`: 1 failed; restaurado: 3 passed | Sim, com a ressalva da rodada 1 (aviso fora do comando), fora de escopo pela SDD-FAB-0010 | `tests/test_descoberta.py:1092` | automatizado |
| 2 | A06 | `uv run pytest -q tests/test_descoberta.py -k politica` | `5 passed, 81 deselected` | `"actor": ATOR_DA_POLITICA` trocado por `"outro"` em `redacao.py`: 1 failed; restaurado: 5 passed | Sim | `tests/test_descoberta.py:1192` | automatizado |
| 2 | A07 | `uv run pytest -q tests/test_pipeline.py tests/test_vigia.py -k politica` | `9 passed, 69 deselected`, com o teste do adaptador real (`test_politica_adaptador_real_hash_quebrado_para_em_recusada_entrada`) | pipeline sem `if motivos`: 2 failed; vigia sem `and not de_politica`: 2 failed; restaurado: 9 passed | Sim | `tests/test_pipeline.py:955`, `:956`; `tests/test_vigia.py:156` | automatizado |
| 2 | A08 | `uv run pytest -q tests/test_vigia_central.py -k avisos` | `6 passed, 19 deselected`, com `test_avisos_pr_do_central_sem_numero_no_motivo_avisa_com_a_pr` | dedup (`rowcount`) tirado: 1 failed; número da PR do central trocado por `None`: 1 failed; restaurado: 6 passed. **Sobreviveu:** o `pr` da PR da base (`fabrica/vigia.py:204`) trocado por `None`: 6 passed, porque o número vem no texto da exceção falsa. O código passa o `pr` | Sim, com ressalva: o número da PR da base segue sem teste que o discrimine | `tests/test_vigia_central.py:544`, `:545` | automatizado |
| 2 | A09 | Cópia no scratchpad; tirar `and pr["user"]["login"] == login` de `prs_da_fabrica`; `uv run pytest -q tests/test_vigia_central.py -k prs`; restaurar | mutante: `1 failed, 3 passed`; restaurado: `4 passed` | o próprio critério: discrimina | Sim | `tests/test_vigia_central.py:248` | automatizado |
| 2 | A10 | Cópia no scratchpad; `or primeira_leitura` retirado em `verificar_central`; `uv run pytest -q tests/test_vigia_central.py -k specs`; restaurar | mutante: `1 failed, 9 passed`; restaurado: `10 passed` | o próprio critério: discrimina | Sim | `tests/test_vigia_central.py:404` | automatizado |
| 2 | A11 | Cópia no scratchpad; `aprovacao_por_politica` devolve `True, []` sem `validar_estado`; `uv run pytest -q tests/test_pipeline.py tests/test_vigia.py -k politica`; restaurar | mutante: **`1 failed, 8 passed, 69 deselected`** (`test_politica_adaptador_real_hash_quebrado_para_em_recusada_entrada`); restaurado: `9 passed` | o próprio critério: discrimina | Sim | `tests/test_pipeline.py:956` | automatizado |
| 2 | A12 | `uv run python -m fabrica vigiar --help` | exit 0; `usage: fabrica vigiar [-h] [--intervalo INTERVALO] [--uma-vez] [--sem-central]` | `"--sem-central"` renomeado em `fabrica/__main__.py`: 0 ocorrências no help; restaurado: 1 | Sim | `n/a`: sem pytest, a saída do comando é a checagem | automatizado |
| 2 | A13 | Manual, rodado pelo owner fora do container: o C12 da SDD-FAB-0010, rodado pelo owner na máquina dele em 2026-11-23 (kit em `292f764`, `_framework/` igual a `1d9b16c`), saídas coladas na sessão. A rodada 0, de primeira leitura, é a da rodada 1. `uv run python -m fabrica vigiar cobaia --uma-vez` e `fabrica historico 0e5248d0-21ae-453d-969e-5dede5a327cb` | SPEC-COBAIA-0002 `medium`, aprovada por review, na PR https://github.com/michelpessoa/fabrica-central-teste/pull/11, com a etiqueta `fabrica` da própria fábrica. Ciclo: `central: integradas ['SPEC-COBAIA-0002'], compiladas ['SPEC-COBAIA-0002']; disparadas: ['docs/sdd/SDD-COBAIA-0013.md']`. SDD-COBAIA-0013 por política na PR https://github.com/michelpessoa/fabrica-cobaia/pull/19 (etiqueta `fabrica`, merge por `fabricaagenticamichel`). Pipeline: `DETECTADO -> ENTRADA_OK: aprovada por fabricaagenticamichel`, depois `PAUSADA_DECISAO` na etapa de risco, fora do escopo | sem teste automatizado (manual) | Sim | `n/a` | manual |
| 2 | A14 | `uv run ruff check . && uv run ruff format --check . && uv run pytest -q` | `All checks passed!`; `114 files already formatted`; `550 passed, 29 deselected in 134.73s`; `scripts/selftest.py`: `70/70 mutações mortas` | os sensores de A01 a A12 | Sim | `n/a` (agregado) | automatizado |

## Rastreabilidade

| Campo | Valor |
|---|---|
| source_docs | SPEC-DTF-0032, ADR-DTF-0008 |
| parent RFC | RFC-DTF-0009 |
| SDD irmã | SDD-DTF-0058 (kit, RF01 a RF03, implemented) |

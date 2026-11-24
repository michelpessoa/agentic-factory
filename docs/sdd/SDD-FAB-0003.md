---
id: SDD-FAB-0003
type: SDD
title: "Escrita no central: rascunho de SPEC ou RFC por PR na descoberta e aprovação pela review, com approved_by gravado antes do merge"
status: implemented
project: "FAB"
owner: "Michel Pessoa"
created: "2026-11-18"
updated: "2026-11-19"
relates_to: [SDD-FAB-0001, SDD-FAB-0002]
source_docs:
  - id: "SPEC-DTF-0030"
    url: "https://github.com/michelpessoa/doc-traceability-central/blob/main/docs/DTF/03-spec/SPEC-DTF-0030.md"
  - id: "ADR-DTF-0008"
    url: "https://github.com/michelpessoa/doc-traceability-central/blob/main/docs/DTF/02-adr/ADR-DTF-0008.md"
sizing: "large"
approved_by:
  kind: human
  actor: michelpessoa
  at: "2026-11-19T01:01:52Z"
  content_sha256: "db205eb884f02faa71ba0389f88f63f6ce911d77eaf66892ec4237668e0095a4"
  evidence: "https://github.com/michelpessoa/fabrica-agentica/pull/39#pullrequestreview-5967735753"
consumption_instructions: "Compilada dos RF08 a RF13 da SPEC-DTF-0030 (approved) e do passo 6 do plano do kit nela, que a SDD-DTF-0055 deixou de fora; ADR-DTF-0008 (approved) é a parent_adr da SPEC. A ADR-0012 da fábrica (aceita) é citada no corpo e fica fora de source_docs, como na SDD-FAB-0002. Os requisitos RF01 a RF07 abaixo são o escopo inteiro: não acrescentar campo, chave, exceção ou mensagem que esta SDD não declara. Teste primeiro, visto falhar. O núcleo (`fabrica/descoberta.py`, `fabrica/pipeline.py`) segue sem conhecer o framework: em `descoberta.py` o documento do central é um dicionário opaco entregue ao escritor. O central de teste muda por branch e PR próprios no `fabrica-central-teste`."
supersedes: null
superseded_by: null
tags: [integracao, executor, central, escrita, aprovacao, review, approved_by, descoberta]
---

# Escrita no central: rascunho de SPEC ou RFC por PR na descoberta e aprovação pela review, com approved_by gravado antes do merge

> Este documento é COMPILADO a partir de `source_docs` — não é escrito do
> zero. É o artefato de entrada (input) para ferramentas de IA realizarem
> a implementação. Vive no repositório de CÓDIGO deste projeto (não no
> repositório central do framework) porque é o único documento pensado
> para ser lido pela IA no momento de implementar.

## Resumo executivo

Parte da fábrica da SPEC-DTF-0030, a primeira SPEC da fase 4 da
RFC-DTF-0009. O kit já tem a sua parte, na 2.6.0 (SDD-DTF-0055, tag
`2.6.0` em `efe1c71`):

- `review_approval.py` decide, sem rede, se as reviews aprovam;
- `approvers` no registry central;
- o `executor_contract` permite PR `docs/<id>` em `in_review` e
  `approved_by` humano gravado antes do merge.

Hoje a fábrica só lê o central (SDD-FAB-0001 e SDD-FAB-0002). Esta SDD a
faz escrever:

- **Na descoberta.** Uma descoberta sem `--origem` com sizing `medium` ou
  maior deixa de terminar num rascunho de SDD que a entrada recusa. Ela
  entrega um rascunho de SPEC (`medium`) ou de RFC (`large`, `complex`),
  que a fábrica valida com o `validate_doc.py` do kit e abre por PR no
  central, em `in_review`.
- **No comando novo `fabrica central conferir <projeto> <id>`.** O
  comando lê a PR e as reviews pela API REST e entrega as reviews ao
  `review_approval.py`. Se a aprovação valer, grava `approved_by` na
  mesma PR, espera os checks e faz o merge em `main` do central.

A fábrica sobe para o framework 2.6.0, e o `fabrica-central-teste`
recebe o `_framework/` 2.6.0 e `approvers: [michelpessoa]` em
`docs/ZERO/` e `docs/COBAIA/`. Esse é o passo 6 do plano do kit na
SPEC, que a SDD-DTF-0055 deixou fora do escopo dela.

## Decisão(ões) de arquitetura aplicável(is)

- **SPEC-DTF-0030 (approved), RF08 a RF13 e "Plano de implementação",
  parte da fábrica:** origem dos requisitos desta SDD. O passo 6 da parte
  do kit (central de teste em 2.6.0 com `approvers`) entra aqui, porque a
  SDD-DTF-0055 o deixou fora e a fábrica não sobe de versão sem ele: a
  SDD-FAB-0001 recusa central em versão diferente da do projeto.
- **ADR-DTF-0008 (approved), decisões 4 e 5:** aprovação humana pela
  review sobre o head da PR, e escrita do executor só por PR, nunca por
  push em `main`. O merge em `main` do central é o da PR `docs/<id>`,
  feito pela API depois da review válida.
- **ADR-0012 (fábrica, aceita):** a escrita no central fica atrás do
  adaptador, numa interface nova ao lado de `FonteDeContrato`, e a
  fábrica faz o merge da PR do central depois de conferir o login do
  revisor e o commit revisado. Fica fora de `source_docs` pelo mesmo
  motivo da SDD-FAB-0002: a origem local é tema da RFC-DTF-0010 e da
  ADR-DTF-0009, ainda sem SPEC.
- **ADR-0003 (fábrica):** continua valendo para o repositório do
  projeto. O merge em `main` que esta SDD abre vale só para PR de branch
  `docs/<id>` com destino `main` no central. A guarda de
  `fazer_merge_em_develop` não muda.
- **Decisões nesta compilação:**
  - **Onde o RF13 é conferido.** A SPEC põe a conferência do login em
    `EscritaNoCentral.__init__`. Esta SDD a põe no início de `abrir_pr` e
    de `conferir`. Feita no construtor, ela chamaria o GitHub e exigiria
    `approvers` em toda descoberta, inclusive em `small` e em projeto sem
    `approvers`, e a SPEC só pede que a fábrica não abra PR nesse
    projeto. O comportamento pedido pelo RF13 e pelos casos de borda é o
    mesmo.
  - **Id livre.** O "id seguinte livre" do RF09 olha o registry em
    `origin/main` e também as branches `docs/<tipo>-<codigo>-*` do
    remoto. Assim, duas PRs abertas não reservam o mesmo id, o que já
    aconteceu no kit com a SDD-DTF-0055.
  - **`framework: Framework` no construtor.** A SPEC declara
    `EscritaNoCentral.__init__(..., framework: Path, ...)`. Esta SDD recebe
    o objeto `Framework` de `adapters/doc_traceability/validadores.py`, que
    já roda os scripts do clone fixado e expõe a raiz em `framework.raiz`.
    O caminho continua sendo o do kit fixado, só chega embrulhado no
    objeto que os outros métodos usam. Nenhum comportamento da SPEC muda.
  - **Retorno do `conferir` na retomada.** A SPEC diz que `conferir`
    devolve a saída JSON do `review_approval.py`, que o kit dá como
    inválida para documento fora de `in_review`. A mesma SPEC pede que um
    `conferir` repetido siga de onde parou. Quando o documento no head da
    PR já está `approved` com `approved_by`, esta SDD não roda o script e
    devolve um dict no mesmo contrato `dtf.review-approval/1` (passo 4 de
    `conferir`), com o `approved_by` do front-matter. Prevalece a
    retomada, porque esse `approved_by` foi gravado depois de uma
    decisão válida do próprio `review_approval.py`.

## Requisitos consolidados

- **RF01 — Framework 2.6.0 na fábrica e no central de teste.** A fábrica
  declara `framework: "2.6.0"` nos projetos e fixa o kit em `efe1c71`
  (tag `2.6.0`) no CI. O `fabrica-central-teste` recebe `_framework/` do
  kit nesse commit, e `docs/ZERO/registry.yaml` e
  `docs/COBAIA/registry.yaml` passam a `framework_version: "2.6.0"` com
  `approvers: [michelpessoa]`. Origem: SPEC-DTF-0030, plano da fábrica,
  passo 1, e plano do kit, passo 6.
- **RF02 — Descoberta sem origem acima de `small` produz documento do
  central.** Enquanto a sessão não tiver origens e o sizing for `medium`,
  `large` ou `complex`, a descoberta só aceita `status: documento`, com
  `documento.tipo` igual ao primeiro tipo do central que
  `Regras.documentos(sizing)` exige (`SPEC` em `medium`, `RFC` em
  `large` e `complex`). O rascunho de SDD nesse estado é recusado com
  motivo. Com origem, ou em `small`, o caminho da fase 3 não muda.
  Origem: SPEC-DTF-0030, RF08.
- **RF03 — Rascunho vira documento válido do framework.** A fábrica
  monta o front-matter (id seguinte livre, `status: in_review`,
  `project`, `owner`, `created`, `updated`, `sizing`, e `parent_rfc:
  null` e `parent_adr: null` na SPEC) sobre o corpo do agente. Ela só
  segue se o `validate_doc.py --json` do kit fixado aprovar. Se reprovar,
  os motivos voltam ao agente na mesma sessão. Origem: SPEC-DTF-0030,
  RF09.
- **RF04 — Documento entra no central por PR.** No clone do central, a
  fábrica:
  - cria a branch `docs/<id em minúsculas>` a partir de `origin/main`;
  - grava o documento na pasta do tipo e acrescenta a entrada ao
    `registry.yaml`;
  - regenera o `registry.md` e roda `registry_tools.py validate`;
  - faz commit e push da branch e abre a PR para `main`.

  A descoberta termina com o número da PR e não gera SDD. Origem:
  SPEC-DTF-0030, RF10.
- **RF05 — `fabrica central conferir` confere a review.** O comando acha
  a PR aberta da branch `docs/<id>` e lê o head e as reviews pela API
  REST. Grava as reviews num arquivo temporário e roda
  `review_approval.py --json` sobre o documento no head. Se a aprovação
  for inválida, imprime os motivos, sai com 1 e não altera nada. Origem:
  SPEC-DTF-0030, RF11.
- **RF06 — Aprovação gravada na mesma PR antes do merge.** Com a
  aprovação válida, a fábrica, na branch da PR:
  - muda no documento só `status` para `approved`, `updated` e o
    `approved_by` devolvido;
  - muda o status no `registry.yaml` e regenera o `registry.md`;
  - roda `validate_state.py` e `registry_tools.py validate`;
  - faz commit e push;
  - espera o GitHub reportar o commit enviado como head da PR;
  - espera os checks verdes sobre esse head e só então faz o merge em
    `main` pela API.

  Um `conferir` repetido retoma de onde parou, sem outro commit. Origem:
  SPEC-DTF-0030, RF12.
- **RF07 — O executor não aprova o que escreveu.** Se o login do token
  (`gh api user`) estiver em `approvers` do registry central do projeto,
  a fábrica recusa abrir a PR e recusa o `conferir`. Também recusa os
  dois quando o projeto não declara `approvers`. Origem: SPEC-DTF-0030,
  RF13 e caso de borda "Registry central sem `approvers`".

**Fora de escopo** (SPEC-DTF-0030, "Fora de escopo"):

- compilação da SDD a partir da SPEC aprovada e aprovação da SDD por
  política;
- consulta periódica das PRs, disparo automático do `conferir` e hook de
  `post-merge` (SPEC do vigia);
- release dupla e `LESSONS.md`;
- organização, token *fine-grained* e ensaio no central real;
- rascunho de ADR e de STRAT, e a continuação depois da RFC aprovada;
- merge de PR que não seja de branch `docs/<id>`;
- mudar documentos existentes do central e declarar `approvers` em
  central real.

## Especificação técnica consolidada

Contratos completos na SPEC-DTF-0030, "Contratos técnicos". O que a
implementação precisa acertar:

**`projetos/*.yaml` e `.github/workflows/ci.yml` (RF01).**
`projetos/cobaia.yaml`, `projetos/zero.yaml` e `projetos/exemplo.yaml`
passam a `framework: "2.6.0"`. No CI, `FRAMEWORK_SHA` vira
`efe1c71e96bf72d5627a69f21fa8655c8c810425`, com o comentário
`# framework 2.6.0`, no mesmo commit, como o próprio CI pede.

**`fabrica-central-teste` (RF01), por branch e PR no próprio
repositório.**

- `_framework/` vira cópia do `_framework/` do kit em `efe1c71`.
- `docs/ZERO/registry.yaml` e `docs/COBAIA/registry.yaml` passam a ter
  `framework_version: "2.6.0"` e, logo abaixo, `approvers:
  [michelpessoa]`.
- `registry.md` é regenerado com `generate_registry_md.py`, e o
  `framework_check.py --auto` desse repositório tem que passar.

Sem esse merge, o CI da fábrica com `framework: "2.6.0"` recusa o central
pela regra da SDD-FAB-0001.

**`adapters/doc_traceability/regras.py` (RF02, RF03, RF04).** Três
métodos novos em `Regras`, lidos de `document_types` do YAML:

- `repositorio(self, tipo: str) -> str | None`: o `repo` do tipo, ou
  `None` se o tipo não existe.
- `pasta(self, tipo: str, codigo: str) -> str`: o `folder` do tipo com
  `{PROJECT_CODE}` trocado por `codigo`.
- `tipo_do_central(self, sizing: str) -> str | None`: o primeiro de
  `documentos(sizing)` cujo `repositorio` é `central`, ou `None` (é o
  caso de `small`).

**`adapters/doc_traceability/validadores.py` (RF03, RF04, RF05, RF06).**
Métodos novos em `Framework`, todos rodando o script do clone fixado,
como `_rodar`:

- `validar_documento(self, cwd: Path, documento: Path) -> ResultadoValidador`:
  `validate_doc.py <documento> --json`.
- `validar_registry(self, cwd: Path, docs: Path) -> ResultadoValidador`:
  `registry_tools.py validate <docs> --json`.
- `gerar_registry_md(self, docs: Path) -> None`:
  `generate_registry_md.py <docs>`, sem `--json`, porque o script não
  está em `machine_outputs`. Saída diferente de 0 levanta
  `RuntimeError` com o stderr. Nenhum chamador a captura, porque é falha
  do kit.
- `decidir_review(self, documento: Path, reviews: Path, head: str, pr_url: str) -> dict`:
  `review_approval.py <documento> --reviews <reviews> --head <head> --pr-url <pr_url> --json`.
  Devolve o JSON quando `schema` for `dtf.review-approval/1`, com
  qualquer código de saída. Fora disso, devolve
  `{"valida": False, "motivos": [f"saída fora do contrato dtf.review-approval/1: {saida[-300:]}"], "approved_by": None}`.

**`adapters/doc_traceability/central.py` (novo; RF03 a RF07).**

- `class EscritaRecusada(Exception)`.
- `repositorio_do_central(central: Path) -> str`: `dono/repo` a partir
  de `git -C <central> remote get-url origin`, tirando
  `git@github.com:` ou `https://github.com/` e o sufixo `.git`. Remote
  de outro host levanta
  `EscritaRecusada(f"remote origin de {central} não é do GitHub: {url}")`.
- `class EscritaNoCentral`, com `__init__(self, central: Path, codigo: str, framework: Framework, github: Github)`.
  Guarda os argumentos e `Regras(framework.raiz)`, sem rede.
- `tipo_do_central(self, sizing: str) -> str | None`: repassa a `Regras`.
- `_exigir_executor_fora_de_approvers(self) -> None` (RF07). Lê
  `approvers` de `docs/<codigo>/registry.yaml` em `origin/main`. Levanta:
  - sem `approvers`:
    `EscritaRecusada(f"approvers não declarado no registry de docs/{codigo}: a fábrica não abre PR nesse projeto")`;
  - com `github.login()` na lista:
    `EscritaRecusada(f"a conta do executor {login} está em approvers de docs/{codigo}: o executor não pode ser aprovador")`.
- `proximo_id(self, tipo: str) -> str` (RF03). Roda `git fetch -q origin
  main` e lê `git show origin/main:docs/<codigo>/registry.yaml`. O maior
  número entre os ids `^{tipo}-{codigo}-(\d{4})$` do registry e as
  branches de `git ls-remote --heads origin "docs/{tipo minúsculo}-{codigo minúsculo}-*"`,
  mais 1, com 4 dígitos. Sem nenhum, `0001`.
- `montar(self, documento: dict, owner: str, hoje: str) -> tuple[str, str]`
  (RF03). Devolve o id e o texto: front-matter nesta ordem, com os
  textos entre aspas por `redacao._texto`, e depois uma linha em branco e
  `documento["corpo"]`, terminado em `\n`:
  - `id`, `type`, `title`, `status: in_review`, `project`, `owner`,
    `created`, `updated` e `relates_to: []`;
  - só na SPEC, `parent_rfc: null` e `parent_adr: null`;
  - `sizing`, `supersedes: null`, `superseded_by: null` e
    `tags: [fabrica-descoberta]`, que é `redacao.TAG`.
- `problemas(self, texto: str) -> list[str]` (RF03). Grava num diretório
  temporário `docs/<codigo>/registry.yaml` (o de `origin/main`) e o
  documento em `<pasta do tipo>/<id>.md`. Roda `validar_documento` com
  `cwd` nesse diretório e devolve os `problemas`. Lista vazia é
  aprovação.
- `abrir_pr(self, doc_id: str, tipo: str, texto: str, titulo: str) -> int`
  (RF04, RF07). Na ordem:
  1. `_exigir_executor_fora_de_approvers()`.
  2. Clone com `git status --porcelain` não vazio:
     `EscritaRecusada(f"clone do central em {central} tem mudança local")`.
     Branch atual diferente de `main`:
     `EscritaRecusada(f"clone do central em {central} está em {ramo}, não em main")`.
  3. `git fetch -q origin main`. Se `docs/<id minúsculo>` existir em
     `git ls-remote --heads origin`:
     `EscritaRecusada(f"{ramo} já existe no central: retome a descoberta para pegar o id seguinte")`.
  4. `git switch -q -C <ramo> origin/main`. Grava o documento na pasta
     do tipo e acrescenta ao `registry.yaml` uma entrada no formato de
     `redacao.registrar`: `id`, `type`, `title`, `status: in_review`,
     `owner`, `created`, `updated`, `relates_to: []`, `path` e
     `tags: [fabrica-descoberta]`.
  5. `framework.gerar_registry_md(docs)`. Roda `framework.validar_registry`;
     se reprovar,
     `EscritaRecusada(f"registry_tools validate: {'; '.join(problemas)}")`.
  6. `publicacao.commit` com
     `f"docs({codigo}): {doc_id} em in_review, da descoberta da fábrica"`.
     Push por `publicacao.enviar_ramo_documento` para a url do `origin`.
  7. `github.abrir_pr_documento(ramo, f"docs({codigo}): {doc_id} — {titulo}", corpo)`,
     com o corpo abaixo, e devolve o número.
  8. Num `finally`: `git switch -q main`.

  Corpo da PR:

  ```
  Rascunho {doc_id}, da descoberta da fábrica, em in_review.

  Para aprovar: review "Approve", ou review de comentário com o texto exato `Aprovado`, sobre o último commit desta PR. Mudança depois da review pede nova review.

  Depois da review: `uv run python -m fabrica central conferir <projeto> {doc_id}`.
  ```

  O corpo termina com `publicacao.RODAPE_PR`.
- `conferir(self, doc_id: str) -> dict` (RF05, RF07). Na ordem:
  1. `_exigir_executor_fora_de_approvers()`.
  2. `pr = github.pr_aberta_do_ramo(ramo)`. Sem PR:
     `EscritaRecusada(f"nenhuma PR aberta para {ramo}")`.
  3. `head = pr["head"]["sha"]`. Roda `git fetch -q origin <ramo>` e
     `git worktree add --detach <temporário> <head>`. O documento é o
     `path` da entrada `doc_id` no `registry.yaml` desse head.
  4. Se o documento no head já estiver `approved` com `approved_by`, é
     retomada. Devolve
     `{"schema": "dtf.review-approval/1", "documento": doc_id, "valida": True, "motivos": [], "head": head, "approved_by": <o do front-matter>}`,
     sem ler reviews.
  5. Senão, grava `github.reviews(pr["number"])` num arquivo JSON
     temporário e devolve
     `framework.decidir_review(documento, arquivo, head, pr["html_url"])`.
  6. Num `finally`: `git worktree remove --force <temporário>`.
- `ESPERA_DO_HEAD_SEGUNDOS = 5` e `LIMITE_DO_HEAD_SEGUNDOS = 120`,
  constantes do módulo.
- `integrar(self, doc_id: str, decisao: dict, dormir=time.sleep) -> str`
  (RF06). Com
  `decisao["valida"]` falso, levanta `EscritaRecusada("aprovação inválida")`.
  Depois, na ordem:
  1. Mesma checagem de clone limpo e em `main` do `abrir_pr`.
     `git fetch -q origin <ramo>` e `git switch -q -C <ramo> origin/<ramo>`.
  2. Documento em `in_review`:
     - `HEAD` diferente de `decisao["head"]` levanta
       `EscritaRecusada(f"head de {ramo} mudou para {sha}: rode conferir de novo")`;
     - no front-matter, só o texto muda: `status: in_review` vira
       `status: approved`, `updated` vira hoje, e o bloco `approved_by:`
       (`kind`, `actor`, `at`, `content_sha256`, `evidence`, com 2
       espaços de recuo, valores de texto entre aspas) entra logo depois
       da linha `sizing:`;
     - na entrada `doc_id` do `registry.yaml`, `status: in_review` vira
       `approved` e `updated` vira hoje, por regex como
       `evidencia._atualizar_registry`;
     - `framework.gerar_registry_md(docs)`, `framework.validar_estado(central, documento)`
       e `framework.validar_registry(central, docs)`. Se algum reprovar:
       `git reset -q --hard origin/<ramo>` e
       `EscritaRecusada(f"validação antes do push: {'; '.join(problemas)}")`;
     - `publicacao.commit` com
       `f"docs({codigo}): {doc_id} approved por review de {actor}"` e
       `enviar_ramo_documento`.
  3. Documento já em `approved` (retomada): nenhum commit.
  4. Espera do head, depois do push e também na retomada. `enviado` é o
     `git rev-parse HEAD` da branch local. Em laço: `pr =
     github.pr_aberta_do_ramo(ramo)`; sem PR,
     `EscritaRecusada(f"nenhuma PR aberta para {ramo}")`; com
     `pr["head"]["sha"] == enviado`, segue; senão, `dormir(ESPERA_DO_HEAD_SEGUNDOS)`
     e lê de novo. Passado `LIMITE_DO_HEAD_SEGUNDOS` de espera somada sem
     igualar, levanta
     `EscritaRecusada(f"head da PR #{numero} segue em {pr['head']['sha']}, não em {enviado}, depois de {LIMITE_DO_HEAD_SEGUNDOS}s: rode conferir de novo")`,
     sem ler checks e sem merge. Só depois do head igual os checks são
     lidos, porque `esperar_checks` lê o `statusCheckRollup` do head que
     o GitHub conhece no momento, e logo após o push esse head ainda é o
     commit anterior, com os checks dele.
  5. `situacao, detalhe = github.esperar_checks(numero)`. Situação fora
     de `{"passou", "sem_checks"}`:
     `EscritaRecusada(f"checks da PR #{numero}: {situacao} {detalhe}")`,
     sem merge.
  6. `sha = github.fazer_merge_de_documento(numero)`.
  7. `git switch -q main` e `git pull -q --ff-only origin main` só
     depois do merge; em erro, `git switch -q main` num `finally`.
     Devolve `sha`.

**`adapters/doc_traceability/__init__.py`.** Reexporta
`EscritaNoCentral`, `EscritaRecusada` e `repositorio_do_central` em
`__all__`. `FonteDocTraceability` não muda.

**`fabrica/publicacao.py` (RF04, RF05, RF06, RF07).**

- `RAMO_DOCUMENTO = re.compile(r"^docs/(spec|rfc)-[a-z0-9]+-[0-9]{4}$")`
  e `BASE_DE_DOCUMENTO = "main"`. A docstring do módulo passa a dizer:
  push também em `docs/<id>` de documento do central; merge em `main`
  só de PR `docs/<id>` do central (ADR-0012).
- `enviar_ramo_documento(repo: Path, url: str, ramo: str) -> None`:
  ramo fora de `RAMO_DOCUMENTO` levanta
  `PublicacaoRecusada(f"push recusado para o ramo {ramo!r}")`. Push de
  `HEAD:refs/heads/<ramo>`, sem `--force`.
- Em `Github`, tudo por `gh api` (REST):
  - `login(self) -> str`: `GET user` e devolve `login`.
  - `pr_aberta_do_ramo(self, ramo: str) -> dict | None`:
    `GET repos/{repo}/pulls?head={dono}:{ramo}&state=open` e devolve a
    primeira, ou `None`.
  - `reviews(self, numero: int) -> list[dict]`:
    `GET repos/{repo}/pulls/{numero}/reviews?per_page=100`.
  - `abrir_pr_documento(self, ramo: str, titulo: str, corpo: str) -> int`:
    ramo fora de `RAMO_DOCUMENTO` levanta `PublicacaoRecusada`. `POST
    repos/{repo}/pulls` com `head`, `base=main`, `title` e `body`, e
    devolve `number`.
  - `fazer_merge_de_documento(self, numero: int) -> str`: `GET
    repos/{repo}/pulls/{numero}`. Base diferente de `main`, ou head fora
    de `RAMO_DOCUMENTO`, levanta
    `PublicacaoRecusada(f"merge recusado: {head} → {base}")`. Já
    mergeada, devolve `merge_commit_sha`. Senão, `PUT
    repos/{repo}/pulls/{numero}/merge` com `merge_method=merge` e
    `sha=<head.sha>`, e devolve o `sha` da resposta.
- `esperar_checks` e `fazer_merge_em_develop` não mudam.

**`contracts/resposta-descoberta.schema.json` (RF02).**

- `status` aceita `"documento"`.
- `documento` entra em `required`, com tipo `["object", "null"]`,
  `additionalProperties: false` e `required` `tipo`, `titulo`, `sizing`
  e `corpo`:
  - `tipo`: enum `["SPEC", "RFC"]`;
  - `titulo`: como o `titulo` do rascunho (`pattern` `^[^|\n]+$`, de 1 a
    400);
  - `sizing`: enum dos quatro níveis;
  - `corpo`: string com `minLength: 1`.
- As descrições de `rascunho` e `perguntas` passam a valer também para
  `status: documento` (`rascunho` null e `perguntas` vazia).

**`agents/descobridor.md` (RF02, RF03).** Três regras novas, logo
depois da regra de `origens`:

- `- Sem \`origens\` e com sizing \`medium\` ou maior, entregue \`status: documento\` e \`rascunho\` null: \`tipo\` \`SPEC\` em \`medium\`, \`RFC\` em \`large\` e \`complex\`. Em \`small\`, ou com \`origens\`, entregue \`rascunho\` e \`documento\` null.`
- `- \`corpo\` é o documento em Markdown, sem front-matter, começando por \`# <titulo>\`. Na SPEC: Objetivo, Requisitos funcionais (tabela com RF-ID, critério de aceite em EARS e coluna Arquivos), Requisitos transversais (sweep), Contratos técnicos, Estratégia de teste e Fora de escopo. Na RFC: Contexto, Problema, Objetivos, Alternativas, Proposta e Riscos.`
- `- Na SPEC, \`Requisitos transversais (sweep)\` é a tabela \`| Categoria | Destino (RF-ID ou n/a) | Motivo (obrigatório se n/a) |\` com uma linha para cada categoria, com estes nomes exatos: Autorização / permissão, Concorrência, Idempotência, Observabilidade, Falha de dependência externa, Validação de entrada, Limite de volume / rate. \`Destino\` é o RF-ID que cobre a categoria ou \`n/a\`; com \`n/a\`, \`Motivo\` é obrigatório.`

**`fabrica/descoberta.py` (RF02, RF03, RF04).**

- Estado novo `NO_CENTRAL = "NO_CENTRAL"`.
- Protocolo novo `Escritor`, com:
  - `tipo_do_central(self, sizing: str) -> str | None`;
  - `montar(self, documento: dict, owner: str, hoje: str) -> tuple[str, str]`;
  - `problemas(self, texto: str) -> list[str]`;
  - `abrir_pr(self, doc_id: str, tipo: str, texto: str, titulo: str) -> int`.
- `Descoberta.__init__` ganha o último parâmetro `escritor=None`.
- Em `_rodada`, depois do ramo de `perguntas`:
  - com `status: documento`, chama `_receber_documento` e retorna;
  - com rascunho, sem origens, com `escritor` e com
    `escritor.tipo_do_central(rascunho["sizing"])` não nulo, recusa com
    `f"sizing {sizing} sem --origem pede rascunho de {esperado} no central, não de SDD"`.
- `_receber_documento(self, sessao, dados, documento)` recusa, por
  `_recusar`, na ordem:
  - documento `None`: `"status documento sem documento"`;
  - sessão com origens:
    `"com --origem a descoberta entrega rascunho de SDD, não documento do central"`;
  - sem `escritor`: `"documento do central sem escrita no central configurada"`;
  - `tipo_do_central(sizing)` nulo:
    `f"sizing {sizing} gera rascunho de SDD, não documento do central"`;
  - tipo diferente do esperado: `f"sizing {sizing} pede {esperado}, não {tipo}"`.

  Depois, chama `montar` e `problemas`. Com problemas, recusa com eles,
  e a tentativa seguinte os leva ao agente. Sem problemas, chama
  `abrir_pr`, guarda `dados |= {"documento": documento, "doc_id": doc_id, "pr": pr, "problemas": []}`
  e salva em `NO_CENTRAL`. Uma exceção de `abrir_pr` sai de `avancar`
  sem salvar, e a sessão continua em `PERGUNTANDO`.

**`fabrica/__main__.py` (RF04, RF05, RF06).**

- `montar_escrita(projeto) -> EscritaNoCentral`: o central de
  `projeto.central`,
  `Github(repositorio_do_central(central))` e `Framework()`.
- `montar_descoberta` passa `escritor=montar_escrita(projeto)`.
- `conversar` trata `NO_CENTRAL` imprimindo
  `f"\nRascunho {doc_id} na PR #{pr} do central, em in_review."` e
  `f"Aprove por review na PR e depois: uv run python -m fabrica central conferir <projeto> {doc_id}"`,
  e sai com 0.
- Grupo novo `central`, com o subcomando `conferir <projeto> <id>`:
  - `montar_fonte(projeto)`, que confere a versão;
  - `decisao = escrita.conferir(id)`. Inválida: imprime `- <motivo>` por
    motivo e sai com 1;
  - `sha = escrita.integrar(id, decisao)` e imprime
    `f"{id} approved e em main do central pelo merge {sha}"`; saída 0;
  - `EscritaRecusada`, `FalhaDePublicacao` e `PublicacaoRecusada`:
    imprime `f"erro: {erro}"` e sai com 1.
- `descobrir` passa a capturar também `EscritaRecusada` e
  `FalhaDePublicacao`, com saída 1, como `DescobertaInvalida`.

**Riscos conhecidos.**

- **Placeholder em `in_review`.** O `validate_doc.py` do kit trata
  placeholder e marcador de ambiguidade pendente como aviso em `in_review` e como
  problema em `approved`. O rascunho pode entrar na PR com aviso. A
  review humana é a primeira barreira. A segunda é o CI do central sobre
  o commit de aprovação, e o `conferir` não faz o merge com check
  vermelho. Esta SDD não endurece o validador do kit.
- **Conta do token.** Enquanto o `gh` da máquina estiver logado como
  `michelpessoa`, que é o aprovador, o `conferir` e a abertura de PR
  recusam, pelo RF07. O ensaio precisa do token da
  `fabricaagenticamichel`, colaboradora do `fabrica-central-teste`
  (SPEC-DTF-0030, "Dependências").
- **`esperar_checks` usa `gh pr view`, que é GraphQL.** A SPEC manda
  reusá-lo. Ele roda na máquina do owner, como hoje, e não em sessão de
  nuvem.
- **Head da PR atrasado depois do push.** No critério 11 de 2026-11-18,
  logo após o push do commit de aprovação (`40f825b`), o GitHub ainda
  reportava o commit anterior como head da PR, com checks verdes, e o
  merge (`5111fcd`) saiu no mesmo segundo em que o run do CI sobre
  `40f825b` foi criado. A espera do head (passo 4 de `integrar`) fecha
  essa corrida sem mudar `esperar_checks`. Com o head igual, um CI ainda
  não criado aparece como `sem_checks`, e `esperar_checks` já espera
  120 s nesse caso antes de aceitar.

## Decomposição em tasks

| # | Task | RF(s) de origem | Arquivos tocados | Depende de (#) |
|---|---|---|---|---|
| 1 | Framework 2.6.0 na fábrica e no central de teste | RF01 | `projetos/cobaia.yaml`, `projetos/zero.yaml`, `projetos/exemplo.yaml`, `.github/workflows/ci.yml`; no `fabrica-central-teste`: `_framework/`, `docs/ZERO/registry.yaml`, `docs/COBAIA/registry.yaml`, `docs/ZERO/registry.md`, `docs/COBAIA/registry.md` | — |
| 2 | Regras, validadores e publicação para documento do central | RF03, RF04, RF06, RF07 | `adapters/doc_traceability/regras.py`, `adapters/doc_traceability/validadores.py`, `fabrica/publicacao.py`, `tests/test_regras.py`, `tests/test_publicacao.py` | 1 |
| 3 | Escrita no central e conferência da review | RF03, RF04, RF05, RF06, RF07 | `adapters/doc_traceability/central.py`, `adapters/doc_traceability/__init__.py`, `tests/test_central_escrita.py` | 2 |
| 4 | Descoberta produz documento do central e comando `central conferir` | RF02, RF04, RF05 | `contracts/resposta-descoberta.schema.json`, `agents/descobridor.md`, `fabrica/descoberta.py`, `fabrica/__main__.py`, `tests/test_descoberta.py`, `tests/test_central_escrita.py` | 3 |

## Critérios de aceite / definição de pronto

| # | Critério (origem: RF-ID / contrato) | Comando de verificação | Resultado esperado | Perfil esperado |
|---|---|---|---|---|
| 1 | RF01: fábrica e central de teste em 2.6.0 | `grep -h '^framework:' projetos/*.yaml && grep -n 'FRAMEWORK_SHA:' .github/workflows/ci.yml`; no `fabrica-central-teste` em `main`, `python3 _framework/scripts/framework_check.py --auto` e `grep -n 'approvers' docs/ZERO/registry.yaml docs/COBAIA/registry.yaml` | três `framework: "2.6.0"`; `efe1c71e96bf72d5627a69f21fa8655c8c810425`; `framework_check` verde; `approvers: [michelpessoa]` nos dois | automatizado |
| 2 | RF02: tipo do central por sizing | `uv run pytest -q tests/test_regras.py -k central` | YAML real: `tipo_do_central("medium") == "SPEC"`, `"large"` e `"complex"` dão `"RFC"`, `"small"` dá `None`; YAML falso em `tmp_path` com outro tipo muda a resposta; `pasta("RFC", "ZERO") == "docs/ZERO/01-rfc"` | automatizado |
| 3 | RF02: descoberta sem origem em `medium` ou maior | `uv run pytest -q tests/test_descoberta.py -k documento` | agente falso: SPEC em `medium` e RFC em `large` chegam a `NO_CENTRAL` com o número da PR; RFC em `medium`, SPEC em `large`, documento em `small`, documento com origem e rascunho de SDD `medium` sem origem são recusados com as mensagens da especificação; com origem, o rascunho de SDD `medium` segue o caminho da fase 3; `agents/descobridor.md` traz as categorias do sweep com os nomes de `SWEEP_CATEGORIES` do `validate_doc.py` do kit fixado | automatizado |
| 4 | RF03: front-matter, id livre e `validate_doc.py` real | `uv run pytest -q tests/test_central_escrita.py -k montar` | central em `tmp_path` com remoto nu local: `montar` dá o front-matter da especificação, a SPEC com `parent_rfc: null` e `parent_adr: null`; o id pula o maior do registry e o de uma branch `docs/` remota; corpo sem seção obrigatória dá o problema do `validate_doc.py` do kit fixado; corpo completo dá `[]` | automatizado |
| 5 | RF04: documento entra no central por PR | `uv run pytest -q tests/test_central_escrita.py -k abrir` | branch `docs/<id>` no remoto nu, com o documento na pasta do tipo, a entrada no `registry.yaml` em `in_review` e o `registry.md` regenerado; `Github` falso recebe a PR para `main`; clone sujo, clone fora de `main` e branch já existente levantam `EscritaRecusada` sem push; o clone volta a `main` | automatizado |
| 6 | RF05: `conferir` | `uv run pytest -q tests/test_central_escrita.py -k conferir` | reviews falsas: `APPROVED` do aprovador sobre o head dá `valida: true` com `approved_by.evidence` em `#pullrequestreview-<id>`; review sobre commit anterior e `CHANGES_REQUESTED` posterior dão `valida: false` com o motivo do kit; sem PR aberta, `EscritaRecusada` com "nenhuma PR aberta para docs/<id>"; nada muda no remoto | automatizado |
| 7 | RF06: aprovação na mesma PR antes do merge, sem duplicar | `uv run pytest -q tests/test_central_escrita.py -k integrar` | commit de aprovação muda só `status`, `updated` e `approved_by` no documento e o status no registry; `validate_state.py` real verde; merge só depois de checks `passou`; check `falhou` sai sem merge com o nome do check; segundo `conferir`/`integrar` não cria commit e faz o merge; head mudado depois da decisão levanta `EscritaRecusada`; `Github` falso com head atrasado (devolve o commit anterior nas primeiras leituras de `pr_aberta_do_ramo`) só chama `esperar_checks` depois de devolver o commit enviado, com `dormir` falso chamado com `ESPERA_DO_HEAD_SEGUNDOS`; head que nunca chega ao commit enviado levanta `EscritaRecusada` com "depois de 120s", sem chamar `esperar_checks` nem `fazer_merge_de_documento`; na retomada a espera do head também roda | automatizado |
| 8 | RF07: executor não aprova o que escreveu | `uv run pytest -q tests/test_central_escrita.py -k executor` | login do `Github` falso em `approvers` recusa `abrir_pr` e `conferir` com a mensagem da especificação; registry sem `approvers` recusa os dois; nenhum push | automatizado |
| 9 | RF04, RF05, RF06: limites da publicação | `uv run pytest -q tests/test_publicacao.py -k documento` | `enviar_ramo_documento` e `abrir_pr_documento` recusam ramo fora de `docs/(spec\|rfc)-<código>-NNNN`; `fazer_merge_de_documento` recusa base que não é `main` e head que não é `docs/<id>`; `fazer_merge_em_develop` segue recusando `main` | automatizado |
| 10 | RF02, RF05: CLI | `uv run pytest -q tests/test_central_escrita.py -k cli` | `central conferir` com aprovação inválida sai com 1 e imprime os motivos; com `EscritaRecusada` sai com 1 e `erro: ...`; `conversar` em `NO_CENTRAL` imprime a PR e o comando `central conferir` | automatizado |
| 11 | RF02 a RF07 de ponta a ponta | Roteiro: `uv run python -m fabrica descobrir zero "<ideia medium>"` contra `~/fabrica-central-teste`, com o token da `fabricaagenticamichel`; review `Aprovado` do owner na PR; `uv run python -m fabrica central conferir zero <id>` | PR `docs/spec-zero-<NNNN>` aberta em `in_review` (`0002` no ensaio repetido, porque a `SPEC-ZERO-0001` já está em `main`); `conferir` grava `approved_by` com `actor: michelpessoa`, espera o CI e faz o merge; o merge é posterior ao fim, com `success`, do job `validate` sobre o commit de aprovação (horários de `gh run view` e do merge); links da PR, do run e do merge registrados na evidência | manual |
| 12 | Suíte inteira e lint, como no CI | `uv run ruff check . && uv run ruff format --check . && uv run pytest -q` com o kit em `efe1c71`, `fabrica-cobaia` e o central de teste presentes | tudo verde | automatizado |

## Instruções específicas para a IA implementadora

- Teste primeiro: cada critério automatizado acima tem teste visto
  falhar antes do código.
- Arquivos esperados: os de "Decomposição em tasks", nada além. O núcleo
  muda só como descrito para `descoberta.py` e `__main__.py`.
- Os testes de `central.py` montam o central em `tmp_path`: um
  repositório nu como `origin`, um clone com `_framework/` do kit fixado
  (ou só `docs/<codigo>/registry.yaml`, com `Framework` sobre o
  `FRAMEWORK_PADRAO`) e um `Github` falso que registra as chamadas. Não
  escreva em `~/fabrica-central-teste` nem chame o GitHub nos testes.
- Reviews de teste seguem o formato da API REST: `id`, `user.login`,
  `state`, `body`, `commit_id` e `submitted_at`. A regra de qual review
  vale é do `review_approval.py` do kit. Não a reimplemente na fábrica.
- Não altere `adapters/doc_traceability/compilador.py`, `evidencia.py`,
  `arquivo.py` nem `redacao.py` (só importe `_texto` e `TAG`), nem
  `fazer_merge_em_develop`, `RAMO_PUBLICAVEL`, `fabrica/gates.py` e
  `fabrica/roteamento.py`.
- A task 1 tem uma parte no `fabrica-central-teste`, com branch e PR
  próprios, mergeada antes do merge desta SDD em `develop`. O CI da
  fábrica clona o central de teste em `main`.

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

Verificação independente completa em `docs/sdd/validation-SDD-FAB-0003.md`. Veredito: **PASS** (rodada 2; a rodada 1 reprovou só o passo 0, por duas diferenças de contrato da SPEC-DTF-0030 sem registro, corrigidas na SDD em `1713343` e reaprovadas em `506ecda`, sem mudança de código).

**Verificador independente:** sim

Diff verificado: `6f259ad..506ecda` (código igual ao de `460b4cb`); kit em `efe1c71e96bf72d5627a69f21fa8655c8c810425` (2.6.0) via `FABRICA_FRAMEWORK`; `fabrica-central-teste` em `658cecd`; `doc-traceability-central` em `81538f7`; 2026-11-19.

| # | Comando rodado | Saída (resumo) | Sensor | Passou? | Assertion (file:line) | Perfil usado |
|---|---|---|---|---|---|---|
| Fidelidade à origem (SPEC-DTF-0030, ADR-DTF-0008) | `python3 $FABRICA_FRAMEWORK/_framework/scripts/check_source_docs.py docs/sdd/SDD-FAB-0003.md ~/doc-traceability-central/docs/DTF` (central em `81538f7`); leitura da SPEC-DTF-0030 (RF08 a RF13, casos de borda, Parte 2, plano do kit passo 6) e da ADR-DTF-0008 (decisões 4 e 5) | "✅ source_docs de SDD-FAB-0003.md conferem com o registry central.", exit 0; RF08→RF02, RF09→RF03, RF10→RF04, RF11→RF05, RF12→RF06, RF13→RF07, passo 6 do kit→RF01; nenhum critério relaxado; contratos da Parte 2 iguais, com as divergências declaradas em "Decisões nesta compilação" (RF13 em `abrir_pr`/`conferir`, `framework: Framework`, retorno do `conferir` na retomada) e no ajuste do passo 4 de `integrar` (`dormir` com default); `approval_hash.py` dá `db205eb8…`, igual ao `approved_by` | sem teste automatizado (script mecânico e leitura) | Sim | n/a | manual |
| 1 | `grep -h '^framework:' projetos/*.yaml && grep -n 'FRAMEWORK_SHA:' .github/workflows/ci.yml`; no `fabrica-central-teste` em `origin/main` (`658cecd`): `python3 _framework/scripts/framework_check.py --auto` e `grep -n approvers docs/ZERO/registry.yaml docs/COBAIA/registry.yaml` | três `framework: "2.6.0"`; `FRAMEWORK_SHA: efe1c71e96bf72d5627a69f21fa8655c8c810425  # framework 2.6.0`; "✅ Todas as verificações do framework passaram." exit 0; `approvers: [michelpessoa]` na linha 3 dos dois, abaixo de `framework_version: "2.6.0"`; `_framework/` idêntico ao do kit (`diff -r -x __pycache__`) | `projetos/zero.yaml` em `2.5.0`: grep mostra `2.5.0` e `tests/test_framework_versao.py` 1 failed; cópia do central com documento divergente do registry: `framework_check` exit 1; `exigir_central(central, "2.5.0")`: `VersaoDivergente`; restaurado: 17 passed | Sim | `tests/test_framework_versao.py:61` | automatizado |
| 2 | `uv run pytest -q tests/test_regras.py -k central` | 2 passed, 12 deselected | `== "central"` → `!=`: 2 failed; `pasta` sem trocar `{PROJECT_CODE}`: 2 failed; `repositorio` fixo em `"central"`: 2 failed; restaurado: 2 passed | Sim | `tests/test_regras.py:77` | automatizado |
| 3 | `uv run pytest -q tests/test_descoberta.py -k documento` | 13 passed, 21 deselected | `tipo != esperado` → `False`: 2 failed; recusa do rascunho de SDD `medium` sem origem anulada: 1 failed; recusa com origem anulada: 1 failed; `esperado is None` anulado: 1 failed; `NO_CENTRAL` → `PARADA`: 3 failed; problemas do validador ignorados: 1 failed; guarda `not origens` removida: 1 failed; "Concorrencia" no `descobridor.md`: 1 failed; restaurado: 13 passed | Sim | `tests/test_descoberta.py:474` | automatizado |
| 4 | `uv run pytest -q tests/test_central_escrita.py -k montar` | 6 passed, 32 deselected | branches remotas ignoradas no id: 1 failed; id sem +1: 3 failed; SPEC sem `parent_rfc`/`parent_adr`: 1 failed; `problemas` devolve `[]`: 1 failed; `status: draft`: 1 failed; restaurado: 6 passed | Sim | `tests/test_central_escrita.py:201` | automatizado |
| 5 | `uv run pytest -q tests/test_central_escrita.py -k abrir` | 4 passed, 34 deselected | sem checar clone sujo, sem checar `main`, sem checar branch existente, sem `gerar_registry_md`, sem `switch main` no `finally`, entrada em `draft`: 1 failed cada; restaurado: 4 passed | Sim | `tests/test_central_escrita.py:278` | automatizado |
| 6 | `uv run pytest -q tests/test_central_escrita.py -k conferir` | 12 passed, 26 deselected | retomada forçada (`if True`): 3 failed; `pr_url` trocado: 1 failed; mensagem sem PR trocada: 1 failed; JSON aceito sem `schema`: 1 failed; worktree não removido: 1 failed; restaurado: 12 passed | Sim | `tests/test_central_escrita.py:365` | automatizado |
| 7 | `uv run pytest -q tests/test_central_escrita.py -k integrar` | 10 passed, 28 deselected | espera do head anulada: 3 failed; checks ignorados: 3 failed; head mudado ignorado: 1 failed; validação antes do push ignorada: 1 failed; data local em vez de UTC: 1 failed; limite ×10: 1 failed; retomada forçada: 2 failed; registry sem `approved`: 7 failed; `dormir(1)`: 3 failed; restaurado: 10 passed | Sim | `tests/test_central_escrita.py:519` | automatizado |
| 8 | `uv run pytest -q tests/test_central_escrita.py -k executor` | 2 passed, 36 deselected | `login in approvers` → `False`: 1 failed; `not approvers` → `False`: 1 failed; sem a guarda em `conferir`: 2 failed; sem a guarda em `abrir_pr`: 2 failed; restaurado: 2 passed | Sim | `tests/test_central_escrita.py:328` | automatizado |
| 9 | `uv run pytest -q tests/test_publicacao.py -k documento` | 25 passed, 33 deselected | `exigir_ramo_documento` anulado: 16 failed; regex com `adr` e sem `$`: 5 failed; merge sem checar base: 1 failed; merge sem checar head: 2 failed; merge sem `sha`: 1 failed; push sem guarda: 8 failed; guarda de `fazer_merge_em_develop` anulada: 2 failed; restaurado: 25 passed | Sim | `tests/test_publicacao.py:140` | automatizado |
| 10 | `uv run pytest -q tests/test_central_escrita.py -k cli` | 7 passed, 31 deselected | inválida → `return 0`, `PublicacaoRecusada` fora do `except`, ramo `NO_CENTRAL` anulado, `descobrir` sem capturar `EscritaRecusada`: 1 failed cada; restaurado: 7 passed | Sim | `tests/test_central_escrita.py:654` | automatizado |
| 11 | Roteiro manual do owner, sobre `42f1caf`, com o token da `fabricaagenticamichel` (registro no `HANDOFF.md`); conferido aqui por `git -C ~/fabrica-central-teste log` e pelo front-matter da `SPEC-ZERO-0002` | PR michelpessoa/fabrica-central-teste#5 (`docs/spec-zero-0002`, rascunho `1449732`); review `Aprovado` `pull/5#pullrequestreview-5967331260` às 00:17:36Z; commit de aprovação `5447cb8` às 00:18:05Z, só `status`, `updated` e `approved_by` (`actor: "michelpessoa"`) no documento e status/`updated` no registry; run `framework-check` https://github.com/michelpessoa/fabrica-central-teste/actions/runs/44427903822 criado 00:18:12Z, `success` 00:19:23Z (horários do run vindos do registro do owner; a API não estava acessível ao verificador); merge `658cecdacafa77f589e047e05a05707e08bff74f` às 00:19:27Z, pais `5111fcd` e `5447cb8`. Depois de `42f1caf` só entrou `460b4cb` (data UTC no `updated`), coberto pelo critério 7 | sem teste automatizado (manual) | Sim | n/a | manual |
| 12 | `uv run ruff check . && uv run ruff format --check . && uv run pytest -q` com o kit em `efe1c71`, `fabrica-cobaia` e o central de teste presentes | "All checks passed!", "98 files already formatted", "412 passed, 29 deselected" (sem skip); repetido depois de todos os sensores: igual | espera do head anulada na suíte inteira: falhas (ex.: `test_integrar_na_retomada_tambem_espera_o_head`); `import os` sem uso: ruff F401; espaçamento fora do formato: "1 file would be reformatted"; restaurado: verde | Sim | `tests/test_central_escrita.py:519` | automatizado |

## Rastreabilidade
| Campo | Valor |
|---|---|
| source_docs | SPEC-DTF-0030, ADR-DTF-0008 |
| contexto local | ADR-0012 da fábrica (aceita), fora de `source_docs` até a SPEC da ADR-DTF-0009 |
| fase | RFC-DTF-0009, fase 4, primeira SPEC (escrita e aprovação por review), parte da fábrica |
| kit | tag `2.6.0` em `efe1c71e96bf72d5627a69f21fa8655c8c810425` |
| Ajuste pós-aprovação | 2026-11-18, depois do critério 11 (manual) reprovar: a descoberta da ZERO parou em 3 tentativas porque o agente não sabia o formato da tabela sweep da SPEC (categorias e `n/a` com motivo) que o `validate_doc.py` cobra. Entra a terceira regra do `agents/descobridor.md`, com as sete categorias do kit, e o critério 3 passa a conferir essas categorias no prompt. A nova aprovação é a review do owner na PR da implementação (michelpessoa/fabrica-agentica#39), registrada em `approved_by` |
| Ajuste pós-aprovação | 2026-11-18, depois do critério 11 (manual) reprovar de novo: o `conferir` da michelpessoa/fabrica-central-teste#4 fez o merge `5111fcd` às 23:38:04Z, no mesmo segundo em que o run do CI sobre o commit de aprovação `40f825b` foi criado, porque o GitHub ainda reportava o head anterior da PR, já verde. Entra o passo 4 de `integrar` (espera do head da PR igual ao commit enviado, com `ESPERA_DO_HEAD_SEGUNDOS`, `LIMITE_DO_HEAD_SEGUNDOS`, `dormir` e a mensagem de recusa), o RF06 passa a citá-lo, o critério 7 ganha o `Github` falso com head atrasado, o critério 11 passa a conferir o horário do merge contra o job `validate` e aceita o id seguinte, e "Riscos conhecidos" registra a corrida. `esperar_checks` não muda. A `SPEC-ZERO-0001` fica em `main` do central de teste como está. A nova aprovação é a review do owner na michelpessoa/fabrica-agentica#39, registrada em `approved_by` |
| Ajuste pós-aprovação | 2026-11-19, depois da verificação independente reprovar o passo 0 (Fidelidade à origem): duas diferenças da SPEC-DTF-0030, Parte 2, estavam na SDD sem registro. Entram em "Decisões nesta compilação" o `framework: Framework` no lugar de `Path` no construtor e o retorno do `conferir` na retomada sem rodar `review_approval.py`. O código não muda. A nova aprovação é a review do owner na michelpessoa/fabrica-agentica#39, registrada em `approved_by` |

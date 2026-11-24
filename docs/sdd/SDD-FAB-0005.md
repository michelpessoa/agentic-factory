---
id: SDD-FAB-0005
type: SDD
title: "SDD enxuta na fábrica: descoberta com origem escreve requisitos por referência em projeto sob 2.7.0, compilador lê a Parte 2 e o EARS da SPEC no central, e framework 2.7.0"
status: implemented
project: "FAB"
owner: "Michel Pessoa"
created: "2026-11-20"
updated: "2026-11-21"
relates_to: [SDD-FAB-0002, SDD-FAB-0003]
source_docs:
  - id: "SPEC-DTF-0031"
    url: "https://github.com/michelpessoa/doc-traceability-central/blob/main/docs/DTF/03-spec/SPEC-DTF-0031.md"
  - id: "ADR-DTF-0008"
    url: "https://github.com/michelpessoa/doc-traceability-central/blob/main/docs/DTF/02-adr/ADR-DTF-0008.md"
sizing: "large"
approved_by:
  kind: human
  actor: michelpessoa
  at: "2026-11-20T21:04:14Z"
  content_sha256: "d7a4af94e9313d9f21a4b5a4ec34f5deafda533b506c6cc02631b769090868ca"
  evidence: "https://github.com/michelpessoa/fabrica-agentica/pull/42#pullrequestreview-5999369612"
consumption_instructions: "Compilada dos RF15 a RF17 da SPEC-DTF-0031 (approved), a parte da fábrica; os RF01 a RF14 são do kit e estão na SDD-DTF-0057 (implemented, tag 2.7.0). ADR-DTF-0008 (approved) é a parent_adr da SPEC. Os requisitos RF01 a RF05 abaixo são o escopo inteiro: não acrescentar campo, chave, exceção ou mensagem que esta SDD não declara. Teste primeiro, visto falhar. contracts/contrato.schema.json não muda, e o núcleo (fabrica/pipeline.py) segue recebendo especificacao e requisitos como hoje. O central de teste muda por branch e PR próprios no fabrica-central-teste."
supersedes: null
superseded_by: null
tags: [documentacao-enxuta, sdd, compilador, descoberta, framework-fixado, fabrica-agentica]
---

# SDD enxuta na fábrica: descoberta com origem escreve requisitos por referência em projeto sob 2.7.0, compilador lê a Parte 2 e o EARS da SPEC no central, e framework 2.7.0

> Este documento é COMPILADO a partir de `source_docs` — não é escrito do
> zero. É o artefato de entrada (input) para ferramentas de IA realizarem
> a implementação. Vive no repositório de CÓDIGO deste projeto (não no
> repositório central do framework) porque é o único documento pensado
> para ser lido pela IA no momento de implementar.

## Resumo executivo

Parte da fábrica da SPEC-DTF-0031, a fase 5 da RFC-DTF-0009
(documentação enxuta). O kit já tem a sua parte na 2.7.0 (SDD-DTF-0057,
tag `2.7.0` em `4293d7a`):

- a SDD enxuta: SDD com `source_docs`, criada a partir da 2.7.0, em
  projeto sob 2.7.0 ou maior;
- a tabela `RF-ID | Origem | Requisito (resumo) | Arquivos`, sem as seções
  que copiam a SPEC e a ADR;
- a fidelidade de RF nas duas direções no `check_source_docs.py`.

Esta SDD leva o formato para a fábrica:

- **Na descoberta com `--origem`.** Quando o projeto está sob 2.7.0 ou
  maior, o agente para de reescrever a SPEC. Por RF, ele entrega só `id`,
  `origem`, `requisito` (até 200 caracteres) e `arquivos`. A fábrica
  escreve a SDD enxuta, e os validadores do kit fixado a conferem. Em
  projeto abaixo da 2.7.0, a descoberta segue como na 2.6.0.
- **No compilador.** A SDD enxuta é resolvida no clone do central:
  `especificacao` traz a Parte 2 de cada SPEC e a "Decisão" de cada ADR, e
  o `aceite` de cada requisito traz o critério EARS da SPEC. O contrato
  entregue ao pipeline tem o mesmo formato de hoje.
- **Na versão.** A fábrica sobe para o framework 2.7.0. O
  `fabrica-central-teste` recebe o `_framework/` da 2.7.0, e os
  `registry.md` de `docs/ZERO/` e `docs/COBAIA/` são regenerados. Esse é o
  item 9 do plano do kit na SPEC, que a SDD-DTF-0057 deixou fora.

## Decisão(ões) de arquitetura aplicável(is)

- **SPEC-DTF-0031 (approved), RF15 a RF17 e "Plano de implementação",
  parte da fábrica:** origem dos requisitos desta SDD. O item 9 da parte
  do kit (central de teste em 2.7.0) entra aqui, pelo mesmo motivo da
  SDD-FAB-0003 com o central de teste em 2.6.0. A SDD-FAB-0001 recusa
  central em versão diferente da do projeto, e a SDD-DTF-0057 deixou esse
  item de fora.
- **ADR-DTF-0008 (approved):** o executor consome o framework pelo
  `executor_contract`. O formato da SDD fica no adaptador
  (`adapters/doc_traceability/`), e `contract_version` continua 1.
- **ADR-0012 (fábrica, aceita):** o núcleo não conhece o framework. A
  descoberta recebe do adaptador o formato da SDD como um texto opaco
  (`"enxuta"` ou `"completa"`) e confere só os campos do rascunho.
- **Decisões nesta compilação:**
  - **SDD enxuta só em projeto sob 2.7.0 ou maior.** Decisão do owner,
    2026-11-20. O RF15 da SPEC diz "quando a descoberta tiver
    `--origem`". O kit, porém, só trata a SDD como enxuta (e só confere a
    tabela e a fidelidade de RF) quando o `framework_version` do
    `docs/sdd/registry.yaml` do projeto é 2.7.0 ou maior. O
    `fabrica-cobaia` declara `2.3.2`. Se a fábrica escrevesse a SDD
    enxuta nele, o kit aceitaria uma SDD sem um RF da SPEC sem dizer
    nada. Por isso a fábrica escreve a SDD enxuta com `--origem` só
    quando o registry do projeto declara 2.7.0 ou maior. Projeto sem
    registry também conta, porque `redacao.registrar` cria o registry com
    a versão do kit fixado. Abaixo disso, o rascunho e a SDD seguem como
    na 2.6.0, também com `--origem`. É o caso de borda "SDD em projeto
    sob 2.6.0: nada muda" da SPEC.
  - **Rascunho enxuto validado também em `draft`.** A descoberta valida
    a SDD gravada como `approved`, porque o compilador só aceita
    `approved`. O `check_lean_sdd` do kit (RF01, RF02 e RF04 da SPEC) só
    roda em `draft` e `in_review`. Na SDD enxuta, a descoberta passa
    também a rodar o `validate_doc.py` sobre a cópia em `draft` que ela já
    escreve hoje. Na SDD completa, nada muda, para não aplicar a drafts
    da 2.6.0 checagens que a descoberta nunca rodou.
  - **Texto da origem lido pelo registry, sem conferir status.** A SPEC
    diz que `compilar` lê o texto por `origem(doc_id)["texto"]`. O
    `origem()` recusa documento fora de `approved`, e o caso de borda da
    SPEC aceita origem `implemented`, que a SPEC da release vai gravar.
    O compilador recebe o texto lido pelo `path` do registry central, sem
    olhar o status. Quem confere o status é o `check_source_docs.py`, que
    já roda na entrada.
  - **SDD enxuta reconhecida pela tabela.** O compilador não sabe a
    versão do projeto. Ele trata como enxuta a SDD com `source_docs` não
    vazio cuja tabela de "Requisitos consolidados" tem exatamente as
    colunas `RF-ID | Origem | Requisito (resumo) | Arquivos`. É o mesmo
    teste do `consolidated_rf_rows` do kit.

## Requisitos consolidados

- **RF01 — Formato da SDD escolhido pela versão do projeto.** O
  adaptador decide o formato a partir das origens da sessão e do
  `framework_version` do `docs/sdd/registry.yaml` da base do projeto. Sem
  registry, vale a versão do kit fixado. O formato é `"enxuta"` com
  origens e versão 2.7.0 ou maior, e `"completa"` nos outros casos. A
  descoberta pergunta uma vez por sessão, guarda a resposta e a entrega
  ao agente. Origem: SPEC-DTF-0031, RF15, com a decisão do owner acima.
- **RF02 — Rascunho enxuto.** Com `"enxuta"`, o agente entrega por RF só
  `id`, `origem`, `requisito` e `arquivos`, e `arquitetura`,
  `especificacao` e `aceite` vêm `null`. A descoberta recusa com motivo:
  - o rascunho enxuto com algum desses três não nulo;
  - `origem` fora das SPECs da sessão;
  - `requisito` com mais de 200 caracteres;
  - o rascunho completo com algum dos três nulo.

  Origem: SPEC-DTF-0031, RF15 e caso de borda "Agente entrega
  `especificacao` ou `aceite` com `--origem`".
- **RF03 — SDD enxuta escrita e conferida.** Com o rascunho enxuto,
  `redacao.montar_sdd` escreve as seções do template 2.7.0 e a tabela
  `RF-ID | Origem | Requisito (resumo) | Arquivos`, com `sizing` igual ao
  da SPEC. A SDD só segue se os validadores do kit fixado aprovarem a
  cópia `approved` e a cópia `draft`. Os validadores são
  `validate_doc.py`, `registry_tools.py validate` e
  `check_source_docs.py`, com a fidelidade de RF. Com o rascunho completo,
  a SDD sai como hoje. Origem: SPEC-DTF-0031, RF15.
- **RF04 — O compilador resolve a referência.** Ao compilar a SDD enxuta,
  `compilar_sdd` recebe o texto de cada `source_docs` lido no clone do
  central e monta a entrada do contrato no formato de hoje:
  - `especificacao` traz a Parte 2 de cada SPEC, sem "Autorrevisão", e
    depois a "Decisão" de cada ADR, na ordem de `source_docs`;
  - o `aceite` de cada requisito traz o critério EARS do mesmo RF-ID na
    SPEC da coluna `Origem`.

  A compilação levanta `SddInvalida`, nomeando o id, em três casos:
  origem ausente do clone, SPEC sem `# Parte 2` e ADR sem "Decisão". O
  RF sem critério na SPEC também levanta `SddInvalida`, nomeando o
  RF-ID. A SDD que não é enxuta compila igual a hoje. Origem:
  SPEC-DTF-0031, RF16.
- **RF05 — Framework 2.7.0 na fábrica e no central de teste.** A fábrica
  declara `framework: "2.7.0"` nos projetos e fixa o kit em `4293d7a`
  (tag `2.7.0`) no CI. O `fabrica-central-teste` recebe o `_framework/`
  do kit nesse commit. `docs/ZERO/registry.yaml` e
  `docs/COBAIA/registry.yaml` passam a `framework_version: "2.7.0"`, e os
  `registry.md` são regenerados. Origem: SPEC-DTF-0031, RF17, e plano do
  kit, item 9.

**Fora de escopo** (SPEC-DTF-0031, "Fora de escopo", e esta compilação):

- compilação automática da SDD quando a SPEC é aprovada, aprovação da
  SDD por política, `approved_by.transitions` escrito pela fábrica,
  polling e hook de `post-merge` (SPEC do vigia);
- subir o `framework_version` do registry de projetos (`fabrica-cobaia`)
  ou migrar SDDs existentes para o formato enxuto;
- mudar `contracts/contrato.schema.json`, `fabrica/pipeline.py`, a
  descoberta sem origem (documento do central, SDD-FAB-0003) ou a SDD
  `small` sem origem;
- conferir na fábrica a fidelidade de RF, que é do `check_source_docs.py`
  do kit;
- `molde` na descoberta. O compilador já lê o campo, e nada muda nele.

## Especificação técnica consolidada

Contratos completos na SPEC-DTF-0031, "Contratos técnicos", parte da
fábrica. O que a implementação precisa acertar:

**`adapters/doc_traceability/redacao.py` (RF01, RF03).**

- `VERSAO_SDD_ENXUTA = "2.7.0"` e `LIMITE_DO_RESUMO = 200`, constantes do
  módulo.
- `_versao(texto: str) -> tuple[int, ...]`: `tuple(int(p) for p in texto.split("."))`.
- `formato_da_sdd(repo: Path, origens: tuple | list, versao_framework: str) -> str`:
  - sem `origens`, devolve `"completa"`;
  - senão, lê `framework_version` de `docs/sdd/registry.yaml` em `repo`.
    Sem arquivo, ou sem o campo, usa `versao_framework`;
  - devolve `"enxuta"` se `_versao(versao) >= _versao(VERSAO_SDD_ENXUTA)`,
    e `"completa"` nos outros casos.
- `montar_sdd(...)` mantém a assinatura. Com
  `rascunho["especificacao"] is None` (rascunho enxuto), escreve a SDD
  enxuta. Senão, escreve exatamente como hoje. A SDD enxuta:
  - tem o mesmo front-matter de hoje, com `source_docs` das origens e
    `sizing: <rascunho["sizing"]>`;
  - tem as seções, nesta ordem: `# <titulo>`, "Resumo executivo"
    (`rascunho["resumo"]`), "Requisitos consolidados", "Decomposição em
    tasks" (só com `tarefas`, como hoje), "Critérios de aceite / definição
    de pronto", "Instruções específicas para a IA implementadora",
    "Verificação de escopo (nada a mais, nada a menos)", "Evidência de
    verificação (preencher antes de status `implemented`)" e
    "Rastreabilidade". Todas, menos "Requisitos consolidados", têm o
    mesmo texto de hoje;
  - não tem "Decisão(ões) de arquitetura aplicável(is)" nem
    "Especificação técnica consolidada";
  - tem em "Requisitos consolidados" a linha
    `Desenho, decisão e critério EARS na SPEC e na ADR de source_docs, por referência.`
    e a tabela:

    ```
    | RF-ID | Origem | Requisito (resumo) | Arquivos |
    |---|---|---|---|
    | {r['id']} | {r['origem']} | {r['requisito']} | {_crases(r['arquivos'])} |
    ```

**`adapters/doc_traceability/__init__.py` (RF01, RF03, RF04).** Em
`FonteDocTraceability`:

- `formato_da_sdd(self, repo: Path, origens) -> str`: repassa a
  `redacao.formato_da_sdd(repo, origens, self._framework.versao())`.
- `problemas_de_redacao(self, repo: Path, caminho_sdd: str) -> list[str]`:
  roda `self._framework.validar_documento(repo, repo / caminho_sdd)` e
  devolve `[f"{r.nome}: {m}" for m in r.problemas]` quando `not r.ok`,
  ou `[]`.
- `_textos_de_origem(self, sdd: Path) -> dict[str, str]`: para cada id de
  `source_docs` da SDD que está no registry central (`_registry_central`)
  e cujo `path` existe no clone, o texto do arquivo. Não confere status.
  Sem central, ou sem front-matter, devolve `{}`.
- `problemas_de_entrada` e `compilar` passam a chamar
  `compilar_sdd(sdd, repo, self._textos_de_origem(sdd))`.
- `formato_da_sdd` e `problemas_de_redacao` entram no protocolo
  `Redator` de `fabrica/descoberta.py`.

**`adapters/doc_traceability/compilador.py` (RF04).**

- `LEAN_COLUNAS = ["rf-id", "origem", "requisito (resumo)", "arquivos"]`,
  comparada com o `Tabela.cabecalho` já normalizado.
- `compilar_sdd(caminho: Path, raiz_projeto: Path | None = None, origens: dict[str, str] | None = None) -> dict`.
  A saída tem as mesmas chaves de hoje.
- `_enxuta(frente: dict, corpo: str) -> bool`: `source_docs` não vazio e
  `primeira_tabela(secao(corpo, "Requisitos consolidados")).cabecalho == LEAN_COLUNAS`.
- `_parte_2(texto: str) -> str | None`: o texto da linha
  `# Parte 2` (início de linha, fora de cercas de código) até o fim, sem
  a seção `## Autorrevisão…` (do heading até o próximo `## ` ou `# `, ou
  até o fim), com `strip()`. Sem a linha, `None`.
- `_decisao(texto: str) -> str | None`: `secao(texto, "Decisão")`.
- `_rf(rf: str) -> str`: `rf.replace("-", "")`.
- `_aceites(texto: str) -> dict[str, str]`: da primeira tabela de
  `secao(texto, "Requisitos funcionais")`, de `_rf(<coluna rf-id>)` para a
  coluna cujo cabeçalho contém `criterio`.
- Na SDD enxuta, depois de `_criterios`, `_requisitos` e
  `_arquivos_permitidos`:
  1. Para cada `id` de `source_docs` sem texto em `origens`:
     problema `f"origem {id} não está no clone do central"`.
  2. Para cada SPEC (`id` com prefixo `SPEC-`), em ordem: `_parte_2`. Se
     vier `None`, problema `f"{id} sem '# Parte 2'"`. Para cada ADR
     (prefixo `ADR-`), em ordem: `_decisao`. Se vier `None`, problema
     `f"{id} sem seção 'Decisão'"`.
  3. `especificacao` é a junção, com `"\n\n"`, de `f"# {id}\n\n{bloco}"`:
     primeiro as SPECs, depois as ADRs.
  4. Para cada requisito, o `aceite` vem de `_aceites` da SPEC da coluna
     `Origem` da mesma linha, com a chave `_rf(id)`. Sem a chave,
     problema `f"{id} sem critério de aceite em {origem}"`.
  5. Com problemas, `SddInvalida` com todos eles, como hoje.
- Na SDD que não é enxuta, `origens` é ignorado, e a saída é igual à de
  hoje, byte a byte.

**`contracts/resposta-descoberta.schema.json` (RF02).** Em `rascunho`:

- `arquitetura` e `especificacao` passam a `"type": ["string", "null"]`,
  com os mesmos `minLength` e `maxLength`;
- cada item de `requisitos` ganha `origem` em `required`, com
  `"type": ["string", "null"]` e `"pattern": "^(SPEC|ADR)-[A-Z0-9]+-[0-9]{4}$"`;
- `aceite` passa a `"type": ["string", "null"]`, com o resto igual.

Nada mais muda no esquema. O limite de 200 caracteres do `requisito`
enxuto é conferido pela descoberta, porque o esquema não depende do
formato.

**`fabrica/descoberta.py` (RF01, RF02, RF03).**

- `problemas_do_formato(rascunho: dict, formato: str, origens: list[str]) -> list[str]`,
  função nova ao lado de `problemas_do_rascunho`, chamada logo depois
  dela em `_receber_rascunho`:
  - com `"enxuta"`:
    - `f"SDD enxuta: {campo} vem null, o desenho fica na SPEC de origem"`,
      para `arquitetura` e `especificacao` não nulos;
    - `f"SDD enxuta: {rf} traz aceite, que vem null: o critério EARS fica na SPEC de origem"`;
    - `f"{rf} com origem {origem!r} fora das SPECs da sessão: {', '.join(specs)}"`,
      onde `specs` são os ids de `origens` com prefixo `SPEC-`;
    - `f"{rf} com requisito de {n} caracteres: o limite da SDD enxuta é {LIMITE_DO_RESUMO}"`,
      com `LIMITE_DO_RESUMO = 200` no módulo;
  - com `"completa"`:
    - `f"SDD completa: {campo} é obrigatório"`, para `arquitetura` e
      `especificacao` nulos;
    - `f"SDD completa: {rf} sem aceite"`.
- Em `_rodada`, antes de montar `entrada`, se `"sdd"` não estiver em
  `dados`:
  - `copia = self._copia_da_base(sessao, "formato")`;
  - `dados["sdd"] = self.redator.formato_da_sdd(copia, dados.get("origens", []))`;
  - `shutil.rmtree(copia, ignore_errors=True)` num `finally`.

  `entrada` ganha `"sdd": dados["sdd"]`. Sessões criadas antes desta SDD
  ganham o campo na primeira rodada seguinte.
- Em `_receber_rascunho`, com `dados["sdd"] == "enxuta"`, depois de
  escrever a cópia `draft` em `leitura` e antes de copiar o arquivo para
  o diretório da sessão:
  `problemas = self.redator.problemas_de_redacao(copia, caminho)`. Com
  problemas, a cópia é apagada, e `_recusar(sessao, dados, problemas)`
  encerra a rodada sem avisar `pronto`.

**`agents/descobridor.md` (RF02).** Na lista "Quando entregar
`rascunho`", um item novo:

```
- `sdd` diz o formato. Com `enxuta`, cada requisito traz `origem` (o id da SPEC de `origens` de onde ele vem), `requisito` com até 200 caracteres e `arquivos`; `arquitetura`, `especificacao` e `aceite` vêm null, porque o desenho e o critério EARS ficam na SPEC. Os RF-IDs são os da SPEC. Com `completa`, `arquitetura`, `especificacao` e `aceite` são obrigatórios, e `origem` é null.
```

O item sobre `aceite` em EARS passa a começar por "Com `completa`,".

**`projetos/*.yaml`, `.github/workflows/ci.yml` e
`tests/test_central_escrita.py` (RF05).**

- `projetos/cobaia.yaml`, `projetos/zero.yaml` e `projetos/exemplo.yaml`
  passam a `framework: "2.7.0"`.
- No CI, `FRAMEWORK_SHA` vira
  `4293d7a44ca66ffbf91d2d4745e3e78b4d1f8725`, com o comentário
  `# framework 2.7.0`, no mesmo commit, como o próprio CI pede.
- O registry de teste em `tests/test_central_escrita.py` passa a
  `framework_version: "2.7.0"`.

**`fabrica-central-teste` (RF05), por branch e PR no próprio
repositório.**

- `_framework/` vira cópia do `_framework/` do kit em `4293d7a`.
- `docs/ZERO/registry.yaml` e `docs/COBAIA/registry.yaml` passam a
  `framework_version: "2.7.0"`. `approvers` e os documentos não mudam. A
  SPEC-ZERO-0001 e a SPEC-ZERO-0002 não são tocadas.
- `registry.md` é regenerado com o `generate_registry_md.py` da 2.7.0,
  e o `framework_check.py --auto` desse repositório tem que passar.

Sem esse merge, o CI da fábrica com `framework: "2.7.0"` recusa o
central pela regra da SDD-FAB-0001.

**`docs/propostas-framework/004-sdd-curta.md`.** Ganha no topo a linha
`> Absorvida pela SPEC-DTF-0031 (framework 2.7.0): campo molde em frontmatter_schema, só em SDD small.`

## Decomposição em tasks

| # | Task | RF(s) de origem | Arquivos tocados | Depende de (#) |
|---|---|---|---|---|
| 1 | Framework 2.7.0 na fábrica e no central de teste | RF05 | `projetos/cobaia.yaml`, `projetos/zero.yaml`, `projetos/exemplo.yaml`, `.github/workflows/ci.yml`, `tests/test_central_escrita.py`; no `fabrica-central-teste`: `_framework/`, `docs/ZERO/registry.yaml`, `docs/COBAIA/registry.yaml`, `docs/ZERO/registry.md`, `docs/COBAIA/registry.md` | — |
| 2 | Formato da SDD e redação enxuta | RF01, RF03 | `adapters/doc_traceability/redacao.py`, `tests/test_redacao.py` | 1 |
| 3 | Compilador resolve a referência | RF04 | `adapters/doc_traceability/compilador.py`, `tests/test_compilador.py` | 1 |
| 4 | Adaptador liga redação, validação em draft e textos de origem | RF01, RF03, RF04 | `adapters/doc_traceability/__init__.py`, `tests/test_origem.py` | 2, 3 |
| 5 | Descoberta pede o formato, confere o rascunho e valida o draft | RF01, RF02, RF03 | `contracts/resposta-descoberta.schema.json`, `agents/descobridor.md`, `fabrica/descoberta.py`, `tests/test_descoberta.py`, `docs/propostas-framework/004-sdd-curta.md` | 4 |

## Critérios de aceite / definição de pronto

| # | Critério (origem: RF-ID / contrato) | Comando de verificação | Resultado esperado | Perfil esperado |
|---|---|---|---|---|
| 1 | RF05: fábrica e central de teste em 2.7.0 | `grep -h '^framework:' projetos/*.yaml && grep -n 'FRAMEWORK_SHA:' .github/workflows/ci.yml`; no `fabrica-central-teste` em `main`, `python3 _framework/scripts/framework_check.py --auto` e `grep -n 'framework_version' docs/ZERO/registry.yaml docs/COBAIA/registry.yaml` | três `framework: "2.7.0"`; `4293d7a44ca66ffbf91d2d4745e3e78b4d1f8725  # framework 2.7.0`; `framework_check` verde; `"2.7.0"` nos dois registries | automatizado |
| 2 | RF01: formato pela versão do projeto | `uv run pytest -q tests/test_redacao.py -k formato` | sem origens dá `"completa"`; com origens e registry em `2.3.2` dá `"completa"`; em `2.7.0` e em `2.10.0` dá `"enxuta"`; sem registry, segue a versão do kit passada | automatizado |
| 3 | RF03: SDD enxuta escrita no formato do template 2.7.0 | `uv run pytest -q tests/test_redacao.py -k enxuta` | rascunho enxuto: tabela `RF-ID \| Origem \| Requisito (resumo) \| Arquivos`, sem "Especificação técnica consolidada" nem "Decisão(ões)…"; `validate_doc.py` do kit fixado aprova a SDD em `draft` num registry `2.7.0`; com RF faltando em relação à SPEC de um central em `tmp_path`, `check_source_docs.py` real reprova citando o RF; rascunho completo dá o mesmo texto de hoje | automatizado |
| 4 | RF04: compilador resolve a referência | `uv run pytest -q tests/test_compilador.py -k enxuta` | SDD enxuta com SPEC e ADR em texto: `especificacao` com `# SPEC-…`, a Parte 2 sem "Autorrevisão" e depois `# ADR-…` com a Decisão; `aceite` de cada RF igual ao EARS da SPEC, também com `RF-01` na SPEC e `RF01` na SDD; origem ausente, SPEC sem `# Parte 2`, ADR sem "Decisão" e RF sem critério levantam `SddInvalida` com as mensagens da especificação; SDD da 2.6.0 dá a mesma saída com e sem `origens` | automatizado |
| 5 | RF04: textos de origem pelo registry central | `uv run pytest -q tests/test_origem.py -k textos` | central em `tmp_path`: SPEC `approved` e `implemented` têm o texto entregue; id fora do registry e `path` inexistente ficam fora; `compilar` de SDD enxuta devolve a Parte 2 da SPEC do central | automatizado |
| 6 | RF01, RF02: descoberta pede o formato e confere o rascunho | `uv run pytest -q tests/test_descoberta.py -k formato` | agente falso: o contrato traz `entrada.sdd`, perguntado ao redator uma vez por sessão; com `"enxuta"`, rascunho com `especificacao`, com `aceite`, com `origem` fora das SPECs da sessão ou com `requisito` de 201 caracteres é recusado com a mensagem da especificação; com `"completa"`, rascunho com `arquitetura` nula é recusado; rascunho enxuto válido chega a `AGUARDANDO_APROVACAO` | automatizado |
| 7 | RF03: draft enxuto validado | `uv run pytest -q tests/test_descoberta.py -k redacao` | com `"enxuta"`, `problemas_de_redacao` do redator falso com problema recusa a rodada sem avisar `pronto`; com `"completa"`, `problemas_de_redacao` não é chamado | automatizado |
| 8 | RF02: esquema aceita os dois formatos | `uv run pytest -q tests/test_descoberta.py -k esquema` | `resposta-descoberta.schema.json` aceita rascunho enxuto com `null` e `origem`, e recusa item de requisito sem `origem` | automatizado |
| 9 | RF01 a RF04 de ponta a ponta | Roteiro: num projeto em `tmp_path` com registry `2.7.0`, `uv run python -m fabrica descobrir <projeto> "<ideia>" --origem SPEC-ZERO-<NNNN>` contra `~/fabrica-central-teste`, aprovação no terminal e pipeline até a compilação | SDD enxuta escrita, aprovada pelos validadores do kit 2.7.0; contrato do desenvolvedor com a Parte 2 da SPEC em `especificacao`; saídas registradas na evidência | manual |
| 10 | Suíte inteira e lint, como no CI | `uv run ruff check . && uv run ruff format --check . && uv run pytest -q` com o kit em `4293d7a`, `fabrica-cobaia` e o central de teste em 2.7.0 presentes | tudo verde | automatizado |

## Instruções específicas para a IA implementadora

- Teste primeiro: cada critério automatizado acima tem teste visto
  falhar antes do código.
- Arquivos esperados: os de "Decomposição em tasks", nada além. O núcleo
  muda só como descrito para `descoberta.py`.
- Não altere `contracts/contrato.schema.json`, `fabrica/pipeline.py`,
  `adapters/doc_traceability/central.py`, `evidencia.py`, `arquivo.py`,
  `regras.py` nem `validadores.py`.
- O texto da SDD completa e a saída do compilador para SDD que não é
  enxuta não mudam. Os testes atuais de `test_compilador.py` e de
  `test_descoberta.py` passam sem edição, exceto os que montam rascunho e
  precisam do campo `origem` novo, que ganham `"origem": None`.
- Os testes que usam o kit real rodam sobre o `FRAMEWORK_PADRAO` (o kit
  em `4293d7a`). Central e projeto ficam em `tmp_path`. Não escreva em
  `~/fabrica-central-teste` nem chame o GitHub nos testes.
- A regra da SDD enxuta e a fidelidade de RF são do kit. Não as
  reimplemente na fábrica além das recusas de `problemas_do_formato`.
- A task 1 tem uma parte no `fabrica-central-teste`, com branch e PR
  próprios, mergeada antes do merge desta SDD em `develop`. O CI da
  fábrica clona o central de teste em `main`. Não reverta nem edite a
  SPEC-ZERO-0001 e a SPEC-ZERO-0002.

## Verificação de escopo (nada a mais, nada a menos)

- [x] Todo requisito consolidado acima tem código correspondente (nada
      da SPEC-DTF-0031, RF15 a RF17, ficou de fora).
- [x] Todo arquivo tocado aparece em "Decomposição em tasks".
- [x] Nenhuma abstração, config, feature flag ou refactor extra que não
      foi pedido por nenhum requisito consolidado.

## Evidência de verificação (preencher antes de status `implemented`)

Verificação independente completa em `docs/sdd/validation-SDD-FAB-0005.md`. Veredito da rodada 1: **FAIL** (critério 4, sensor da SDD que não é enxuta). Rodada 2: **FAIL** (critério 9: as SPECs do central de teste, escritas pela própria fábrica, não têm `# Parte 2`, e a descoberta enxuta nunca chega a `AGUARDANDO_APROVACAO`; causa na especificação, não na implementação). Rodada 3: **FAIL** (critério 9 com a SPEC-ZERO-0003, que tem as duas linhas `# Parte`: a cadeia chega a `ENTRADA_OK`, mas o `_parte_2` corta a Parte 2 a partir do texto sem cercas de código, e o bloco ```python com a assinatura `listar(...)`, contrato técnico da SPEC, some da `especificacao`; causa na implementação do RF04). Rodada 4: **PASS** (critério 9 com a SPEC-ZERO-0003 sobre `develop` em `123d5d9`, depois da correção do `_parte_2` na PR #52: a Parte 2 chega inteira à `especificacao`, diff do `difflib` vazio; critérios 4, 5 e 10 de novo verdes, com sensores). A SDD segue `approved`: fica pronta para o owner avançar a `implemented`.

**Verificador independente:** sim (sessão separada, sem o histórico da que implementou; diff `13f33e1..aeee784`; rodada 4, sessão separada que não implementou a SDD nem a correção: diff `64d9568..681c004`)

| Rodada | # | Comando rodado | Saída (resumo) | Sensor | Passou? | Assertion (file:line) | Perfil usado |
|---|---|---|---|---|---|---|---|
| 1 | Fidelidade à origem | `python3 ~/doc-traceability-framework/_framework/scripts/check_source_docs.py docs/sdd/SDD-FAB-0005.md /home/user/doc-traceability-central/docs/DTF`; leitura de RF15 a RF17, casos de borda e Parte 2 (contratos da fábrica) da SPEC-DTF-0031 | `✅ source_docs de SDD-FAB-0005.md conferem com o registry central.` (exit 0); RF15→RF01-RF03, RF16→RF04, RF17→RF05; nenhum critério relaxado; as três diferenças de contrato (gate 2.7.0, texto pelo registry, `_parte_2`/`_decisao` com `None`) estão em "Decisões nesta compilação" | sem teste automatizado (leitura) | Sim | `n/a` | n/a |
| 1 | 1 | `grep -h '^framework:' projetos/*.yaml && grep -n 'FRAMEWORK_SHA:' .github/workflows/ci.yml`; em `~/fabrica-central-teste` (`main`, `f745c8a`): `python3 _framework/scripts/framework_check.py --auto`, `grep -n framework_version docs/ZERO/registry.yaml docs/COBAIA/registry.yaml`; `diff -rq` do `_framework/` contra o kit em `4293d7a` | três `framework: "2.7.0"`; `17: FRAMEWORK_SHA: 4293d7a44ca66ffbf91d2d4745e3e78b4d1f8725  # framework 2.7.0`; `✅ Todas as verificações do framework passaram.` (exit 0); `"2.7.0"` nos dois registries; `_framework/` idêntico | `projetos/zero.yaml` em `2.6.0`: 2 de 3 em 2.7.0; restaurado: 3 de 3 | Sim | n/a (comando) | automatizado |
| 1 | 2 | `uv run pytest -q tests/test_redacao.py -k formato` | `7 passed, 4 deselected` | `>=` trocado por `>` em `formato_da_sdd`: `2 failed, 5 passed`; restaurado: `7 passed` | Sim | `tests/test_redacao.py:76` | automatizado |
| 1 | 3 | `uv run pytest -q tests/test_redacao.py -k enxuta` e `uv run pytest -q tests/test_redacao.py::test_sdd_completa_segue_identica_a_de_antes` (a parte "rascunho completo dá o mesmo texto" não é selecionada por `-k enxuta`) | `6 passed, 5 deselected`; `1 passed` | cabeçalho sem "(resumo)": `3 failed`; "Especificação técnica" de volta na enxuta: `2 failed`; colunas trocadas na completa: `1 failed`; restaurados: verdes | Sim | `tests/test_redacao.py:174`, `tests/test_redacao.py:115` | automatizado |
| 1 | 4 | `uv run pytest -q tests/test_compilador.py -k enxuta` | `6 passed, 13 deselected` | sem tirar "Autorrevisão": `1 failed`; `_rf` sem tirar hífen: `2 failed`; **`_enxuta` trocado por `frente.get("source_docs")`: `6 passed` no critério e `474 passed` na suíte inteira**. O teste da SDD não enxuta usa `source_docs: []`, e nenhum teste cobre SDD completa com `source_docs` (a da descoberta com `--origem` em projeto abaixo de 2.7.0) | **Não** | `tests/test_compilador.py:234`, `tests/test_compilador.py:290` | automatizado |
| 1 | 5 | `uv run pytest -q tests/test_origem.py -k textos` | `3 passed, 9 deselected` | só `approved` entra: `2 failed`; `path` inexistente entra: `1 failed`; restaurados: `3 passed` | Sim | `tests/test_origem.py:218` | automatizado |
| 1 | 6 | `uv run pytest -q tests/test_descoberta.py -k formato` | `12 passed, 63 deselected` | limite em 201: `1 failed`; formato perguntado toda rodada: `1 failed`; `origem` não conferida: `1 failed`; nulo aceito na completa: `2 failed`; restaurados: `12 passed` | Sim | `tests/test_descoberta.py:923`, `tests/test_descoberta.py:949` | automatizado |
| 1 | 7 | `uv run pytest -q tests/test_descoberta.py -k redacao` | `2 passed, 73 deselected` | `problemas_de_redacao` nunca chamado: `1 failed`; chamado também na completa: `1 failed`; restaurados: `2 passed` | Sim | `tests/test_descoberta.py:988` | automatizado |
| 1 | 8 | `uv run pytest -q tests/test_descoberta.py -k esquema` | `1 passed, 74 deselected` | `origem` fora de `required`: `1 failed`; restaurado: `1 passed` | Sim | `tests/test_descoberta.py:1008` | automatizado |
| 1 | 9 | sem execução na rodada 1: a rodada parou no FAIL do critério 4 (executado nas rodadas 2, 3 e 4, linhas abaixo) | pendente na rodada 1 | sem teste automatizado (roteiro manual) | Pendente na rodada 1 | `n/a` | manual |
| 1 | 10 | `uv run ruff check . && uv run ruff format --check . && uv run pytest -q` (kit em `4293d7a`, `fabrica-cobaia` e central de teste em `main`) | `All checks passed!`; `103 files already formatted`; `474 passed, 29 deselected` | coberto pelos sensores 1 a 8 | Sim | n/a (suíte) | automatizado |
| 2 | 4 | `uv run pytest -q tests/test_compilador.py -k enxuta`, com dois testes novos escritos pelo verificador, por decisão do owner: SDD completa com `source_docs` ignora `origens` e tabela enxuta sem `source_docs` não é enxuta (só teste, nenhum código de produção mudou) | `8 passed, 13 deselected` | `_enxuta` trocado por `source_docs` não vazio: `1 failed`; `_enxuta` sem conferir a tabela: `1 failed`; `_enxuta` sem conferir `source_docs`: `1 failed`; sem tirar "Autorrevisão": `1 failed`; `_rf` sem tirar hífen: `2 failed`; restaurados: `8 passed` | Sim | `tests/test_compilador.py:234`, `tests/test_compilador.py:306`, `tests/test_compilador.py:317` | automatizado |
| 2 | 2, 3, 5 a 8 | os mesmos comandos da rodada 1, sem código de produção alterado | `7 passed`; `6 passed` e `1 passed`; `3 passed`; `12 passed`; `2 passed`; `1 passed` | sensores da rodada 1 (código igual) | Sim | os da rodada 1 | automatizado |
| 2 | 9 | Roteiro com componentes reais e agente roteirizado: projeto git em diretório temporário com `docs/sdd/registry.yaml` em `2.7.0`, `FonteDocTraceability(central=~/fabrica-central-teste, codigo="ZERO")`, `origem()` real, `Descoberta` real, validadores do kit `4293d7a`; o agente devolve um rascunho enxuto com todos os RFs da SPEC. Rodado com `--origem` SPEC-ZERO-0001 e SPEC-ZERO-0002 | `entrada.sdd: enxuta`; `estado: PARADA`; três recusas `SPEC-ZERO-0001 sem '# Parte 2'` (igual para a 0002). As duas SPECs `approved` do central de teste, escritas pela descoberta da fábrica (`agents/descobridor.md`, linha 9), não têm `# Parte 1` nem `# Parte 2`. Controle: numa cópia descartável do central, com as duas linhas acrescentadas à SPEC-ZERO-0001, a sessão chega a `AGUARDANDO_APROVACAO`, a SDD enxuta passa nos validadores, `problemas_de_entrada` volta `[]` e o contrato traz `# SPEC-ZERO-0001 / # Parte 2 — Desenho…` em `especificacao` e o EARS do RF01 em `aceite` | sem teste automatizado (roteiro manual) | **Não** | `n/a` | manual (agente roteirizado no lugar do Claude real: a sessão não tem `CLAUDE_CODE_OAUTH_TOKEN`, que o HANDOFF proíbe pôr em variável; aprovação por PR no `fabrica-zero` não exercida) |
| 2 | 10 | `uv run ruff check . && uv run ruff format --check . && uv run pytest -q` | `All checks passed!`; `104 files already formatted`; `476 passed, 29 deselected` | coberto pelos sensores | Sim | n/a (suíte) | automatizado |
| 3 | 9 | Roteiro com componentes reais e agente roteirizado, como na rodada 2, sobre `develop` em `64d9568`: projeto git em diretório temporário com `docs/sdd/registry.yaml` em `2.7.0` (`documents:` vazio); `FonteDocTraceability(central=~/fabrica-central-teste, codigo="ZERO")` com `exigir_versao("2.7.0")`; `origem("SPEC-ZERO-0003")` real (central em `main`, `3667377`); `Descoberta` real com o agente roteirizado devolvendo um rascunho enxuto com RF01 a RF05 da SPEC, `aceite` e desenho nulos e duas tarefas; `aprovar` real (ramo, commit, push e `Aprovacoes.registrar`; PR e merge como git local no remoto); depois `Pipeline._entrada` real (aprovação, `problemas_de_entrada`, `compilar`). Kit `4293d7a`. Comparação da `especificacao` com a Parte 2 da SPEC por `difflib` | `entrada.sdd: enxuta`; `AGUARDANDO_APROVACAO` na tentativa 1, sem recusas; SDD-ZERO-0001 enxuta (`source_docs` com a SPEC-ZERO-0003, tabela `RF-ID \| Origem \| Requisito (resumo) \| Arquivos`); `aprovar`: `APROVADA`; `Pipeline._entrada`: `DETECTADO -> ENTRADA_OK : aprovada por michelpessoa`; `especificacao` começa por `# SPEC-ZERO-0003\n\n# Parte 2 — Desenho (o COMO e o ONDE)`, sem `# Parte 1`; `aceite` de RF01 a RF05 igual ao EARS da SPEC (5 de 5); **mas a Parte 2 não chega inteira**: o diff mostra que o bloco ```python com `def listar(diretorio, responsavel=None, status=None, texto=None) -> list[dict]` some. `_parte_2` (`adapters/doc_traceability/compilador.py:202`) acha a linha e corta a partir de `_sem_cercas_de_codigo(texto)`, e não do texto original. A especificação desta SDD pede "o texto da linha `# Parte 2` (início de linha, fora de cercas de código) até o fim": a cerca vale para achar a linha. Nenhum teste do critério 4 tem cerca de código na Parte 2 | sem teste automatizado (roteiro manual; o defeito foi achado pelo diff contra a SPEC) | **Não** | `n/a` | manual (agente roteirizado no lugar do Claude real, como na rodada 2: a sessão não tem `CLAUDE_CODE_OAUTH_TOKEN`; PR e merge no `fabrica-zero` simulados por git local) |
| 4 | Escopo do diff | `git diff --name-only 64d9568..681c004` | `adapters/doc_traceability/compilador.py`, `tests/test_compilador.py`: os dois arquivos da task 3 (RF04) na decomposição; nenhum outro | sem teste automatizado (leitura do diff) | Sim | `n/a` | n/a |
| 4 | 4 | `PYTHONDONTWRITEBYTECODE=1 uv run pytest -q tests/test_compilador.py -k enxuta` (com os três testes novos da PR #52) | `11 passed, 13 deselected` | em cópia descartável (`cp` do arquivo, sem `git stash`): A) `_parte_2` de volta ao de `64d9568` (recorte do texto limpo): `2 failed` (`test_enxuta_especificacao_mantem_bloco_cercado_da_parte_2`, `test_enxuta_autorrevisao_dentro_de_cerca_nao_e_secao_e_fica`); B) `# Parte 2` procurada também dentro de cercas: `1 failed` (`test_enxuta_parte_2_dentro_de_cerca_nao_conta`); C) cabeçalhos de seção procurados também dentro de cercas: `1 failed` (`test_enxuta_autorrevisao_dentro_de_cerca_nao_e_secao_e_fica`); restaurado: `11 passed` | Sim | `tests/test_compilador.py:267`, `tests/test_compilador.py:276`, `tests/test_compilador.py:289` | automatizado |
| 4 | 5 | `uv run pytest -q tests/test_origem.py -k textos` | `3 passed, 9 deselected` | sensores da rodada 1 (`__init__.py` não mudou em `64d9568..681c004`) | Sim | `tests/test_origem.py:218` | automatizado |
| 4 | 9 | Roteiro igual ao da rodada 3, sobre `develop` em `123d5d9` (inclui o merge `681c004` da PR #52): projeto git em diretório temporário com `docs/sdd/registry.yaml` em `2.7.0` (`documents:` vazio); `FonteDocTraceability(central=~/fabrica-central-teste, codigo="ZERO")` com `exigir_versao("2.7.0")`; `origem("SPEC-ZERO-0003")` real (central em `main`, `844800d`; a SPEC-ZERO-0003 não mudou desde `3667377`, só entrou a SPEC-ZERO-0004); `Descoberta` real com o agente roteirizado devolvendo um rascunho enxuto com RF01 a RF05 da SPEC, `aceite` e desenho nulos e duas tarefas; `aprovar` real (PR e merge como git local no remoto); `Pipeline._entrada` real. Kit `4293d7a`. Parte 2 da SPEC recortada do texto original por regex própria do roteiro e comparada à `especificacao` por `difflib` | `contrato.entrada.sdd: enxuta`; `AGUARDANDO_APROVACAO` na tentativa 1, `recusas: []`, agente chamado 1 vez; SDD-ZERO-0001 enxuta (`source_docs` só com a SPEC-ZERO-0003); `aprovar`: `APROVADA`; `DETECTADO -> ENTRADA_OK : aprovada por michelpessoa`; `aceite` igual ao EARS: 5 de 5; `especificacao` começa por `'# SPEC-ZERO-0003\n\n# Parte 2 — Desenho (o COMO e o ONDE)'`, sem `# Parte 1`; diff do `difflib` contra a Parte 2 da SPEC: vazio (0 linhas); bloco ```python com `def listar(diretorio, responsavel=None, status=None, texto=None) -> list[dict]` inteiro, com as cercas; sem `# ADR-` porque a SDD não tem ADR em `source_docs` (a SPEC-ZERO-0003 tem `parent_adr: null`) e a SPEC não tem `## Autorrevisão` | controle: o mesmo roteiro com o `compilador.py` de `64d9568` (cópia descartável, restaurada depois) dá diff de 13 linhas, sem o bloco ```python, como na rodada 3 | Sim | `n/a` | manual (agente roteirizado no lugar do Claude real, como nas rodadas 2 e 3: a sessão não tem `CLAUDE_CODE_OAUTH_TOKEN`; PR e merge no `fabrica-zero` simulados por git local) |
| 4 | 10 | `uv run ruff check . && uv run ruff format --check . && uv run pytest -q` (kit em `4293d7a`, `fabrica-cobaia` e central de teste em `main`) | `All checks passed!`; `108 files already formatted`; `493 passed, 29 deselected` | coberto pelos sensores | Sim | n/a (suíte) | automatizado |

### Escalonado ao humano
Rodadas tentadas: 3. Veredito de cada uma: FAIL, FAIL, FAIL.
Motivo de cada falha: rodada 1, critério 4 (o teste da SDD que não é enxuta não discriminava `_enxuta`; corrigido pelo verificador com dois testes, por decisão do owner); rodada 2, critério 9 (as SPECs do central de teste, escritas pela descoberta, não tinham `# Parte 2`; causa na especificação, resolvida pela SDD-FAB-0006 e pela SPEC-ZERO-0003); rodada 3, critério 9 (`_parte_2` recortava a Parte 2 do texto sem cercas e perdia o bloco ```python; causa na implementação, corrigida pela PR #52).
Decisão do owner: pedir uma 4ª rodada depois da PR #52, em sessão separada que não implementou a SDD nem a correção. Rodada 4: PASS.

## Rastreabilidade

| Campo | Valor |
|---|---|
| source_docs | SPEC-DTF-0031, ADR-DTF-0008 |
| RF da SPEC cobertos | RF15 (RF01, RF02, RF03), RF16 (RF04), RF17 (RF05) |
| RF da SPEC fora desta SDD | RF01 a RF14, no kit (SDD-DTF-0057) |
| Decisão do owner | SDD enxuta só em projeto sob 2.7.0 ou maior (2026-11-20) |

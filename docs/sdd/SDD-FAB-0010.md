---
id: SDD-FAB-0010
type: SDD
title: "Correções do vigia do central depois da verificação e do A13 da SDD-FAB-0009: sensor do hash com o adaptador real, número da PR no aviso, etiqueta na PR do central, merge da fábrica na entrada por política e vigia que não cai sem a base"
status: implemented
project: "FAB"
owner: "Michel Pessoa"
created: "2026-11-23"
updated: "2026-11-23"
relates_to: [SDD-FAB-0009]
source_docs: []
sizing: "small"
approved_by:
  kind: human
  actor: michelpessoa
  at: "2026-11-23T15:30:29Z"
  content_sha256: "64b5e7a85af09266ecc00c5f38bcfcbe7ca2ef392b0023125a7d431bb382f0a2"
  evidence: "https://github.com/michelpessoa/fabrica-agentica/pull/63#pullrequestreview-6024387096"
consumption_instructions: "SDD small, sem SPEC de origem: o requisito e o desenho estão aqui. Nasce dos dois motivos de FAIL, dos descompassos 3 e 4 e dos achados 1 a 5 do A13 registrados em docs/sdd/validation-SDD-FAB-0009.md. Os requisitos RF01 a RF06 e as assinaturas de 'Especificação técnica consolidada' são o escopo inteiro: não acrescentar campo, tabela, chave, exceção ou mensagem que esta SDD não declara. A seção 'Escopo declarado da SDD-FAB-0009' só registra código que já está em develop: não muda código. Teste primeiro, visto falhar. O núcleo (fabrica/vigia.py, fabrica/pipeline.py, fabrica/descoberta.py) não conhece pasta, registry nem script do framework (ADR-0012). Chamadas ao GitHub pela API REST (gh api). A SDD-FAB-0009 não é editada: o corpo dela está sob o content_sha256 da aprovação."
supersedes: null
superseded_by: null
tags: [vigia, central, approval_policy, pipeline, entrada, publicacao, verificacao, fabrica-agentica]
---

# Correções do vigia do central depois da verificação e do A13 da SDD-FAB-0009: sensor do hash com o adaptador real, número da PR no aviso, etiqueta na PR do central, merge da fábrica na entrada por política e vigia que não cai sem a base

## Resumo executivo

A rodada 1 da verificação independente da SDD-FAB-0009 deu FAIL por dois
motivos, e o A13, rodado pelo owner, achou mais cinco problemas
(`docs/sdd/validation-SDD-FAB-0009.md`):

- **A11 não discrimina.** O comando do A07 só usa `FonteFalsa`, então o
  mutante que tira o `validate_state.py` de `aprovacao_por_politica`
  sobrevive.
- **O aviso de PR do central sai sem o número da PR**, porque
  `prs_da_fabrica` devolve só ids.
- **A PR de documento do central sai sem a etiqueta `fabrica`**, e o RF04
  da SDD-FAB-0009 só confere PR etiquetada. Sem a etiqueta posta à mão, a
  PR nunca é conferida.
- **A SDD aprovada por política é recusada na entrada**, porque o merge
  dela é da conta da fábrica, que não está em `permitidos`. O caminho sem
  humano não fecha.
- **O vigia cai com traceback quando o clone da base falha.**
- **O texto de progresso da compilação automática** pede uma aprovação
  que a política dispensa.
- **Interfaces, mensagens e a ordem do ciclo** estão em `develop` sem
  estar declaradas na SDD-FAB-0009.

Esta SDD corrige o código onde o defeito é de comportamento (RF01 a RF06).
Onde o código já está certo e falta a declaração, ela declara o escopo
(seção "Escopo declarado da SDD-FAB-0009"). Editar a SDD-FAB-0009
invalidaria a aprovação dela. Depois desta SDD implementada, a
verificação rodada 2 da SDD-FAB-0009 roda sobre o diff das duas.

## Decisão(ões) de arquitetura aplicável(is)

- **ADR-0012 (fábrica, aceita):** o núcleo não conhece o framework. O
  teste do RF01 usa o adaptador real (`FonteDocTraceability`) só no
  teste. O núcleo segue recebendo `(bool, motivos)`.
- **Decisões nesta SDD.** As marcadas como *proposta ao owner* são
  confirmadas ou trocadas na review desta SDD em `in_review`. Se o owner
  trocar uma delas, a SDD volta a `draft` com o texto novo antes da
  aprovação.
  - **Descompasso 1 (A11): mudar os testes, não a SDD-FAB-0009.** Um teste
    de `tests/test_pipeline.py` com `politica` no nome passa a exercer o
    adaptador real com o kit fixado. Assim o comando do A07 da SDD-FAB-0009
    mata o mutante do A11 como está escrito.
  - **Descompasso 2 (RF10): mudar o código.** `prs_da_fabrica` passa a
    devolver pares `(id, número)`, lidos da mesma listagem REST. Não há
    chamada nova ao GitHub. O vigia leva o número até o aviso.
  - **Achado 1 do A13: a PR de documento sai etiquetada**, do mesmo jeito
    que `abrir_pr` etiqueta a PR da base (`_garantir_etiqueta` antes,
    `_etiquetar` depois).
  - **Achado 2 do A13 (RF09 contra `permitidos`), proposta ao owner.**
    Na entrada, a SDD com `aprovacao_por_politica` igual a `(True, [])`
    aceita o merge feito pela conta do executor (`Github.login()`), além
    das contas de `permitidos`. Nos outros casos, `permitidos` segue como
    hoje. A SDD do terminal mergeada pela conta da fábrica segue
    recusada. A SDD de política mergeada por terceira conta também.
  - **Achado 3 do A13 (vigia cai sem a base), proposta ao owner: entra.**
    O defeito é anterior à SDD-FAB-0009, mas o requisito não funcional
    dela já diz que falha do `git` não para o ciclo. O clone que falha no
    passo 3 vira uma linha impressa e o ciclo segue. O clone que falha no
    RF06 do passo 2 vira aviso da SPEC.
  - **Achado 4 do A13: o texto de progresso da compilação automática muda.**
    O texto interativo não muda.
  - **Achado 5 do A13: o disparo no mesmo ciclo fica como está e é
    declarado aqui.** O passo 3 clona a base depois do passo 2, então a
    SDD que acabou de entrar já é vista no mesmo ciclo. O comportamento é
    melhor do que a frase da SDD-FAB-0009, e esta SDD o declara.
  - **Descompassos 3 e 4: declarar, não remover.** Remover as pontes
    núcleo-adaptador violaria a ADR-0012. A linha de falha e a sentinela
    são o que os testes do RF10 e do RF05 da SDD-FAB-0009 exercem.
- **Fora de escopo:**
  - **A SPEC de outro projeto com o código na coluna `Projeto`** (lacuna
    do RF05 da SPEC-DTF-0032). `FonteDocTraceability.origem` e
    `check_source_docs.py` leem só `docs/<codigo>/` do central. Corrigir
    muda a origem e pede decisão do owner na SPEC, não nesta SDD.
  - **As ressalvas do A02 e do A05** (cobertura fora do comando do
    critério). Não bloqueiam a SDD-FAB-0009, e o comportamento já está
    testado em outro arquivo.
  - **O kit, `contracts/*.schema.json` e a SDD-FAB-0009.**

## Requisitos consolidados

| RF-ID | Origem | Requisito (resumo) | Arquivos |
|---|---|---|---|
| RF01 | — | Quando a SDD de política com hash quebrado chegar à entrada pelo adaptador real e o kit fixado, o pipeline deve parar em `RECUSADA_ENTRADA` com o motivo do `validate_state.py`, num teste do comando do A07. | `tests/test_pipeline.py` |
| RF02 | — | Se a conferência ou o merge de uma PR do central falhar, então o vigia deve avisar com o número da PR, mesmo quando o texto do motivo não o traz. | `adapters/doc_traceability/central.py`, `fabrica/vigia.py`, `tests/test_vigia_central.py`, `tests/mutacoes.yaml` |
| RF03 | — | Quando a fábrica abrir PR de documento no central, a PR deve sair com a etiqueta `fabrica`, criada antes se faltar. | `fabrica/publicacao.py`, `tests/test_publicacao.py`, `tests/mutacoes.yaml` |
| RF04 | — | Quando a SDD tiver `aprovacao_por_politica` `(True, [])` e o merge for da conta do executor, a entrada deve aceitá-la; nos outros casos, `permitidos` segue como hoje. | `fabrica/pipeline.py`, `tests/test_pipeline.py`, `tests/mutacoes.yaml` |
| RF05 | — | Se o clone da base falhar num ciclo, então o vigia deve imprimir o motivo e seguir para o ciclo seguinte, sem traceback e sem parar o processo. | `fabrica/vigia.py`, `tests/test_vigia.py`, `tests/test_vigia_central.py` |
| RF06 | — | Quando a compilação automática tiver rascunho válido, o progresso deve dizer que a SDD sai aprovada por política, sem pedir `fabrica aprovar`. | `fabrica/descoberta.py`, `fabrica/__main__.py`, `tests/test_descoberta.py` |

## Especificação técnica consolidada

**`adapters/doc_traceability/central.py` (RF02).**
`EscritaNoCentral.prs_da_fabrica(self) -> list[tuple[str, int]]` devolve
pares `(id, número)`, com `número = pr["number"]` da mesma listagem
`GET repos/{dono}/{repo}/pulls?state=open&per_page=100`. Filtro, ordem e
número de chamadas ao `gh` não mudam.

**`fabrica/vigia.py` (RF02, RF05).**

- `_prs_do_central`: `for doc_id, numero in escrita.prs_da_fabrica():` e,
  no `except`, `self._avisar(notificador, doc_id, str(erro), numero)`. A
  chave de deduplicação de `avisos` segue `(projeto, documento, motivo)`.
- `verificar`: se `self._aprovadas()` levantar
  `subprocess.CalledProcessError`, imprime
  `base: cópia de <base> falhou, segue no próximo ciclo: <erro>` (com
  `flush=True`) e devolve `[]`, sem tocar `sdds_vistas`.
- `verificar_central`: se `self._motivo_para_nao_compilar(spec_id)`
  levantar `subprocess.CalledProcessError`, chama
  `self._avisar(notificador, spec_id, f"cópia da base falhou: {erro}")`,
  põe `spec_id` em `resultado["paradas"]` e segue para a SPEC seguinte.
  A SPEC continua marcada como vista: compilar de novo segue sendo
  decisão do owner, como no RF06 da SDD-FAB-0009.

**`fabrica/publicacao.py` (RF03).** `Github.abrir_pr_documento`: depois de
`exigir_ramo_documento(ramo)`, chama `self._garantir_etiqueta()`. Depois
do `POST`, chama `self._etiquetar(numero)` e devolve o número. A
assinatura não muda.

**`fabrica/pipeline.py` (RF04).** Em `_entrada`, a chamada
`self.fonte.aprovacao_por_politica(leitura, caminho_sdd)` sobe para antes
da conferência de `permitidos`. A conferência passa a ser
`if aprovador not in self.projeto.permitidos and not (por_politica and aprovador == self.github.login()):`,
com a mesma mensagem de hoje. O resto de `_entrada` não muda: a ordem das
recusas, as mensagens e o `aprovada por {aprovador}` de `ENTRADA_OK`.
`self.github.login()` só é chamado quando `por_politica` é verdadeiro e o
aprovador está fora de `permitidos`.

**`fabrica/descoberta.py` e `fabrica/__main__.py` (RF06).**

- `Descoberta`: o evento `"pronto"` ganha o detalhe
  `automatica=bool(dados.get("automatica"))`.
- `_texto_do_progresso`: no evento `"pronto"` com `automatica` verdadeiro,
  a frase final é
  `Compilação do vigia: a SDD sai aprovada por política e entra na base por PR, sem fabrica aprovar.`
  Sem `automatica`, o texto de hoje não muda.

**Testes.**

- `tests/test_pipeline.py` (RF01, RF04):
  - `test_politica_adaptador_real_hash_quebrado_para_em_recusada_entrada`,
    com o `skipif` de framework ausente dos testes que já usam o kit. A
    base tem uma SDD aprovada por `aprovar_por_politica` do adaptador e
    editada depois. Com `fonte=FonteDocTraceability()`, o estado é
    `RECUSADA_ENTRADA` e o motivo contém `mudou depois da aprovação`;
  - `GithubFalso` ganha `login()`, que devolve `"fabrica"` por padrão;
  - `test_politica_merge_pela_conta_da_fabrica_entra`: `FonteFalsa(politica=(True, []))`
    com `GithubFalso(aprovador="fabrica")` chega a `ENTRADA_OK`;
  - `test_politica_sdd_do_terminal_mergeada_pela_fabrica_segue_recusada`:
    `FonteFalsa()` sem política, com `GithubFalso(aprovador="fabrica")`,
    para em `RECUSADA_ENTRADA` com `quem pode aprovar`.
- `tests/test_vigia_central.py` (RF02, RF05):
  - a `prs_da_fabrica` falsa passa a devolver pares;
  - `test_avisos_pr_do_central_sem_numero_no_motivo_avisa_com_a_pr`: o
    `conferir` falso levanta exceção com texto sem `#`, e o aviso contém
    `(PR #<número>)`;
  - `test_prs_da_fabrica_filtra_por_ramo_conta_e_etiqueta` confere os
    números;
  - `test_clone_da_base_falha_no_rf06_avisa_e_segue`.
- `tests/test_vigia.py` (RF05): `test_clone_da_base_falha_segue_sem_traceback`.
  Com `repo` apontando para caminho inexistente, `verificar` devolve `[]`
  e imprime `base: cópia de`.
- `tests/test_publicacao.py` (RF03):
  `test_pr_de_documento_sai_com_a_etiqueta_da_fabrica`. A criação da
  etiqueta vem antes do `POST`, e a etiquetagem do número devolvido vem
  depois. `test_pr_de_documento_vai_para_main_pela_api_rest` passa a
  achar a chamada do `POST` entre as outras, em vez de exigir chamada
  única.
- `tests/test_descoberta.py` (RF06):
  `test_cli_progresso_pronto_automatica_nao_pede_fabrica_aprovar`, sobre
  `_texto_do_progresso("pronto", {..., "automatica": True})`, e o mesmo
  sem `automatica`, que segue com `Agora é com você`.
- `tests/mutacoes.yaml` (RF02 a RF04), três entradas novas sob
  `# SDD-FAB-0010`:
  - `fabrica/vigia.py`: `str(erro), numero)` trocado por `str(erro), None)`,
    teste `tests/test_vigia_central.py`;
  - `fabrica/publicacao.py`: a linha `self._etiquetar(numero)` de
    `abrir_pr_documento` trocada por `pass`, teste `tests/test_publicacao.py`.
    O `procurar` precisa ser único no arquivo;
  - `fabrica/pipeline.py`: `not (por_politica and aprovador == self.github.login())`
    trocado por `True`, teste `tests/test_pipeline.py`.

## Escopo declarado da SDD-FAB-0009

Código que já está em `develop` (merge da PR #61) e que a SDD-FAB-0009
não declara. Esta SDD o declara como escopo da SDD-FAB-0009, sem mudar
código, para a verificação rodada 2 (descompassos 3 e 4 e achado 5).

- **Pontes núcleo-adaptador (descompasso 3):**
  - `FonteDocTraceability.sdd_com_origem(self, repo: Path, spec_id: str) -> str | None`:
    a SDD da base com a SPEC em `source_docs`, para o RF06. A leitura é
    do front-matter de `docs/sdd/SDD-*.md`, porque o `registry.yaml` do
    projeto não guarda `source_docs`;
  - `FonteDocTraceability.aprovar_por_politica(self, repo: Path, caminho_sdd: str, agora: str) -> dict`:
    o invólucro de `redacao.aprovar_por_politica` com o `Framework` do
    adaptador, para o RF08;
  - o atributo `LeituraDoCentral.recusadas: dict[str, list[str]]`,
    preenchido por `specs_aprovadas`, que leva ao núcleo os motivos da SPEC
    com `validate_state.py` vermelho;
  - nos `Protocol`: `Redator.origem`, `Redator.aprovar_por_politica` e
    `Redator.aprovacao_por_politica` (`fabrica/descoberta.py`), e
    `FonteDeContrato.aprovacao_por_politica` (`fabrica/pipeline.py`).
- **Mensagens e convenções (descompasso 4):**
  - a linha `central: leitura falhou, segue na base: <erro>`, impressa por
    `verificar_central` no ciclo em que a leitura do central falha, junto
    da linha por ciclo;
  - a linha sentinela `(projeto, "", "")` em `specs_vistas`, que marca o
    projeto como lido. É a mesma convenção de `sdds_vistas`;
  - o commit `docs(sdd): <id> aprovada por política` e o corpo de PR
    `<id>, compilada pelo vigia e aprovada por política.` de
    `Descoberta._abrir_pr` com `politica=True`.
- **Ordem do ciclo (achado 5):** o passo 3 clona a base depois do passo 2,
  então a SDD que o passo 2 levou à base no mesmo ciclo é vista e
  disparada nesse ciclo.

## Decomposição em tasks

| # | Task | RF(s) de origem | Arquivos tocados | Depende de (#) |
|---|---|---|---|---|
| 1 | Teste do pipeline com o adaptador real e o hash quebrado | RF01 | `tests/test_pipeline.py` | |
| 2 | Número da PR do central no aviso | RF02 | `adapters/doc_traceability/central.py`, `fabrica/vigia.py`, `tests/test_vigia_central.py` | |
| 3 | Etiqueta na PR de documento | RF03 | `fabrica/publicacao.py`, `tests/test_publicacao.py` | |
| 4 | Merge da conta do executor na entrada por política | RF04 | `fabrica/pipeline.py`, `tests/test_pipeline.py` | 1 |
| 5 | Vigia que segue quando o clone da base falha | RF05 | `fabrica/vigia.py`, `tests/test_vigia.py`, `tests/test_vigia_central.py` | 2 |
| 6 | Texto de progresso da compilação automática | RF06 | `fabrica/descoberta.py`, `fabrica/__main__.py`, `tests/test_descoberta.py` | |
| 7 | Mutantes novos | RF02, RF03, RF04 | `tests/mutacoes.yaml` | 2, 3, 4 |

## Critérios de aceite / definição de pronto

Executar na raiz da fábrica, na branch de implementação, com o kit da tag
2.8.0 (`1d9b16cf89d8ef63852a26eafce668966b168447`) em `FABRICA_FRAMEWORK`
e `fabrica-cobaia` e `fabrica-central-teste` presentes, como no CI.

| # | Critério (origem: RF-ID / contrato) | Comando de verificação | Resultado esperado | Perfil esperado |
|---|---|---|---|---|
| C01 | RF01: hash quebrado pelo adaptador real | `uv run pytest -q tests/test_pipeline.py -k "politica and adaptador"` | 1 passed, sem skip; `RECUSADA_ENTRADA` com `mudou depois da aprovação` | automatizado |
| C02 | RF01: o A11 da SDD-FAB-0009 discrimina | Em cópia descartável, `aprovacao_por_politica` devolve `(True, [])` sem rodar `validate_state.py`; `uv run pytest -q tests/test_pipeline.py tests/test_vigia.py -k politica`; restaurar | Pelo menos 1 failed; restaurado, 0 failed | automatizado |
| C03 | RF02: número da PR do central no aviso | `uv run pytest -q tests/test_vigia_central.py -k "avisos or prs"` | aviso com `(PR #<número>)` com motivo sem `#`; pares `(id, número)` de `prs_da_fabrica` | automatizado |
| C04 | RF02: sensor do número | Em cópia descartável, `_avisar(notificador, doc_id, str(erro), None)` em `_prs_do_central`; `uv run pytest -q tests/test_vigia_central.py -k avisos`; restaurar | Pelo menos 1 failed; restaurado, 0 failed | automatizado |
| C05 | RF03: etiqueta na PR do central | `uv run pytest -q tests/test_publicacao.py -k "documento"` | criação da etiqueta antes do `POST` e etiquetagem do número depois; o `POST` segue para `main` | automatizado |
| C06 | RF04: merge da fábrica na entrada por política | `uv run pytest -q tests/test_pipeline.py -k politica` | política verde mergeada pela conta da fábrica: `ENTRADA_OK`; SDD do terminal mergeada pela fábrica e política mergeada por outra conta: `RECUSADA_ENTRADA` | automatizado |
| C07 | RF04: sensor da exceção | Em cópia descartável, `por_politica and aprovador == self.github.login()` trocado por `aprovador == self.github.login()`; pytest de C06; restaurar | Pelo menos 1 failed; restaurado, 0 failed | automatizado |
| C08 | RF05: clone da base falha | `uv run pytest -q tests/test_vigia.py tests/test_vigia_central.py -k clone` | passo 3: `[]` e `base: cópia de` impresso; RF06: aviso `cópia da base falhou` e a SPEC em `paradas`; nenhum traceback | automatizado |
| C09 | RF06: texto de progresso | `uv run pytest -q tests/test_descoberta.py -k "progresso and automatica"` | com `automatica`: `aprovada por política` e sem `Agora é com você`; sem `automatica`: o texto de hoje | automatizado |
| C10 | RF02 a RF04: mutantes | `uv run python scripts/selftest.py` | todas as mutações mortas, as três novas incluídas | automatizado |
| C11 | Suíte inteira e lint, como no CI | `uv run ruff check . && uv run ruff format --check . && uv run pytest -q` | tudo verde | automatizado |
| C12 | RF03 e RF04 de ponta a ponta (A13 de novo) | Roteiro do A13 da SDD-FAB-0009, na máquina do owner: `uv run python -m fabrica vigiar cobaia --uma-vez` contra `~/fabrica-central-teste`, sem pôr a etiqueta à mão | PR do central etiquetada pela fábrica e integrada; SDD por política na base; pipeline passa de `ENTRADA_OK`; links e saídas registrados na evidência | manual |

## Instruções específicas para a IA implementadora

- **Branch e commit:** `feature/sdd-fab-0010-correcoes-do-vigia`, a partir
  de `origin/develop`, depois do merge desta SDD `approved`. Commits com
  `Refs: SDD-FAB-0010`. Nunca em `main` nem direto em `develop`.
- **Teste primeiro** em cada task, com a falha guardada.
- **Arquivos esperados:** os da coluna `Arquivos` e de "Decomposição em
  tasks", nada além. `docs/sdd/SDD-FAB-0009.md` não muda.
- **Não acrescentar** tabela, coluna, chave, exceção ou mensagem que esta
  SDD não declara.
- **Testes** usam o kit da tag 2.8.0 em `FABRICA_FRAMEWORK`; base e
  central ficam em `tmp_path` com remoto nu. Não escreva em
  `~/fabrica-central-teste` nem chame o GitHub nos testes automatizados.
- **C12 é manual**, na máquina do owner, contra `fabrica-cobaia` e
  `fabrica-central-teste`, nunca contra o central real. Ele não roda no
  container.
- **Evidência de verificação** só por verificador independente, numa sessão
  que não implementou esta SDD nem a SDD-FAB-0009. A mesma sessão roda a
  rodada 2 da SDD-FAB-0009 sobre o diff das duas.

## Verificação de escopo (nada a mais, nada a menos)

Antes de marcar `implemented`, confirme as duas direções — SDD incompleta
tanto quanto SDD estourada são falha:
- [x] Todo requisito consolidado acima tem código correspondente.
- [x] Todo arquivo tocado aparece na coluna `Arquivos` dos requisitos ou
      das tasks.
- [x] Nenhuma abstração, config, feature flag ou refactor extra que não
      foi pedido por nenhum requisito consolidado.

## Evidência de verificação (preencher antes de status `implemented`)

Verificação independente completa em `docs/sdd/validation-SDD-FAB-0010.md`. Veredito: **PASS**.

**Verificador independente:** sim. A sessão `session_01RJ9BCmTpCp89YJf9zppMYE` não compilou nem implementou esta SDD (`session_01RJ9BCp859Hp5cRz967jUgJ`) nem a SDD-FAB-0009 (`session_01RJ9BCnp9buEznvAVqPkMJc`). Diff verificado: `21facbe..7a32640`, em `develop` `c340598` (a PR #65, só HANDOFF, entrou depois de `7a32640`). Kit 2.8.0 em `1d9b16c` (`FABRICA_FRAMEWORK=$HOME/kit-2.8.0`), `fabrica-cobaia` e `fabrica-central-teste` por `git clone --depth 1`, como no CI. As mutações partiram de cópias no scratchpad e foram restauradas por elas, com `git status` limpo no fim. Não houve `git stash` nem commit.

| Rodada | # | Comando rodado | Saída (resumo) | Sensor | Passou? | Assertion (file:line) | Perfil usado |
|---|---|---|---|---|---|---|---|
| 1 | Escopo | `git diff --stat 21facbe..7a32640` e leitura do diff contra RF01 a RF06 e "Especificação técnica consolidada" | 12 arquivos, todos na coluna `Arquivos` ou em "Decomposição em tasks"; todo RF tem código e teste; nenhuma abstração, chave ou mensagem fora da SDD. O `procurar` do mutante do RF03 usa `self._etiquetar(numero_do_documento)`, e não `numero`, para ser único no arquivo, como a SDD pede | sem teste automatizado (leitura do diff) | Sim | `n/a` | n/a |
| 1 | C01 | `uv run pytest -q tests/test_pipeline.py -k "politica and adaptador"` | `1 passed, 64 deselected`, sem skip (`-rs` sem linha de skip) | `aprovacao_por_politica` do adaptador devolve `True, []` sem `validar_estado`: `1 failed`; restaurado: `1 passed` | Sim | `tests/test_pipeline.py:955`, `:956` | automatizado |
| 1 | C02 | Cópia no scratchpad; em `adapters/doc_traceability/__init__.py`, `validar_estado` e o `return` trocados por `return True, []`; `uv run pytest -q tests/test_pipeline.py tests/test_vigia.py -k politica`; restaurar | mutante: `1 failed, 8 passed, 69 deselected`; restaurado: `9 passed, 69 deselected` | o próprio critério: discrimina | Sim | `tests/test_pipeline.py:956` | automatizado |
| 1 | C03 | `uv run pytest -q tests/test_vigia_central.py -k "avisos or prs"` | `10 passed, 15 deselected` | `pr["number"]` trocado por `0` em `prs_da_fabrica`: `1 failed`; restaurado: `10 passed` | Sim | `tests/test_vigia_central.py:248`, `:544`, `:545` | automatizado |
| 1 | C04 | Cópia no scratchpad; `str(erro), numero)` trocado por `str(erro), None)` em `fabrica/vigia.py`; `uv run pytest -q tests/test_vigia_central.py -k avisos`; restaurar | mutante: `1 failed, 5 passed, 19 deselected`; restaurado: `6 passed, 19 deselected` | o próprio critério: discrimina | Sim | `tests/test_vigia_central.py:544` | automatizado |
| 1 | C05 | `uv run pytest -q tests/test_publicacao.py -k documento` | `26 passed, 33 deselected` | `self._etiquetar(numero_do_documento)` trocado por `pass`: `1 failed`; `self._garantir_etiqueta()` de `abrir_pr_documento` trocado por `pass`: `1 failed`; restaurado: `26 passed` | Sim | `tests/test_publicacao.py:397`, `:398` | automatizado |
| 1 | C06 | `uv run pytest -q tests/test_pipeline.py -k politica` | `7 passed, 58 deselected` (inclui a política mergeada por `outra-pessoa`, `test_politica_nao_dispensa_o_merge_por_quem_pode`) | a exceção `not (...)` trocada por `True`: `1 failed`; restaurado: `7 passed` | Sim | `tests/test_pipeline.py:969`, `:975`, `:976`, `:938` | automatizado |
| 1 | C07 | Cópia no scratchpad; `por_politica and aprovador == self.github.login()` trocado por `aprovador == self.github.login()`; pytest de C06; restaurar | mutante: `1 failed, 6 passed, 58 deselected`; restaurado: `7 passed, 58 deselected` | o próprio critério: discrimina | Sim | `tests/test_pipeline.py:975` | automatizado |
| 1 | C08 | `uv run pytest -q tests/test_vigia.py tests/test_vigia_central.py -k clone` | `2 passed, 36 deselected` | passo 3: o `print` e o `return []` trocados por `raise`: `1 failed`; RF06: o `paradas.append` e o `continue` trocados por `raise`: `1 failed`; restaurado: `2 passed` | Sim | `tests/test_vigia.py:169`; `tests/test_vigia_central.py:587` | automatizado |
| 1 | C09 | `uv run pytest -q tests/test_descoberta.py -k "progresso and automatica"` | `2 passed, 84 deselected` | `elif d.get("automatica"):` trocado por `elif False:` em `fabrica/__main__.py`: `1 failed`; `automatica=False` fixo no evento `pronto` de `fabrica/descoberta.py` (com `-k automatica`): `1 failed`; restaurado: verde | Sim | `tests/test_descoberta.py:1204`, `:1205`, `:1207` | automatizado |
| 1 | C10 | `uv run python scripts/selftest.py` | `70/70 mutações mortas`, as três da SDD-FAB-0010 incluídas (`aviso de PR do central sem o número da PR (RF02)`, `PR de documento do central sai sem a etiqueta (RF03)`, `entrada sem permitidos dispensa a conferência de quem mergeou (RF04)`) | o próprio critério é de mutação | Sim | `n/a` (agregado) | automatizado |
| 1 | C11 | `uv run ruff check . && uv run ruff format --check . && uv run pytest -q` | `All checks passed!`; `114 files already formatted`; `550 passed, 29 deselected in 134.73s` (marcadores `docker` e `claude` fora, por `addopts`) | os sensores de C01 a C09 | Sim | `n/a` (agregado) | automatizado |
| 1 | C12 | Manual, rodado pelo owner fora do container, na máquina dele, com o `gh` na conta `fabricaagenticamichel`, Docker, `fabrica-cobaia` e `fabrica-central-teste`. Rodado pelo owner em 2026-11-23, com o kit em `292f764` (o `_framework/` sem diff para `1d9b16c`, por `git diff --stat`), e saídas coladas na sessão: descoberta `medium` sem `--origem`; `gh pr view 11 --json labels`; `uv run python -m fabrica vigiar cobaia --uma-vez`; `fabrica historico 0e5248d0-21ae-453d-969e-5dede5a327cb` | SPEC-COBAIA-0002 na PR https://github.com/michelpessoa/fabrica-central-teste/pull/11, com a etiqueta `fabrica` posta pela fábrica, sem etiqueta à mão, e review "Aprovado" do owner. Progresso: `Compilação do vigia: a SDD sai aprovada por política e entra na base por PR, sem fabrica aprovar.` Ciclo: `central: integradas ['SPEC-COBAIA-0002'], compiladas ['SPEC-COBAIA-0002']; disparadas: ['docs/sdd/SDD-COBAIA-0013.md']`. SDD-COBAIA-0013 na PR https://github.com/michelpessoa/fabrica-cobaia/pull/19, com a etiqueta `fabrica` e `mergedBy` `fabricaagenticamichel`. Pipeline: `DETECTADO -> ENTRADA_OK: aprovada por fabricaagenticamichel`, e depois `ENTRADA_OK -> PAUSADA_DECISAO` na etapa de risco (`risco medio`, confiança 0.7), posterior à entrada e fora do escopo | sem teste automatizado (manual) | Sim | `n/a` | manual |

## Rastreabilidade

| Campo | Valor |
|---|---|
| source_docs | nenhum (sizing `small`) |
| Origem dos achados | SDD-FAB-0009, verificação rodada 1 e A13 (`docs/sdd/validation-SDD-FAB-0009.md`) |
| Relaciona | SDD-FAB-0009 (vigia do central) |

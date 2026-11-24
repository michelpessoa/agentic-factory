# Verificação — SDD-FAB-0006

- **Veredito:** PASS na rodada 3 (rodada 1: pendente, critérios 1 a 4 PASS e critério 5 sem execução; rodada 2: critério 5 FAIL, causa na especificação; rodada 3: critério 5 PASS, depois da SDD-FAB-0007)
- **Diff verificado:** `b736c77..d1d4320` (`develop` antes da PR #46 até o head dela; merge `84fa72c`, pais `b736c77` e `d1d4320`)
- **Verificador independente:** sim (sessão separada, sem o histórico da que implementou)

A tabela completa, com comando, saída, sensor e asserção por critério, está
na seção "Evidência de verificação" da SDD-FAB-0006.

Ambiente, como no CI: kit `doc-traceability-framework` em `4293d7a`
(`FABRICA_FRAMEWORK=~/doc-traceability-framework`), `fabrica-cobaia` em
`d4e8cf1`, `fabrica-central-teste` em `f745c8a`, `uv sync`.

| Critério | Comando rodado | Saída (resumo) | Sensor | Passou? |
|---|---|---|---|---|
| Fidelidade à origem | não se aplica (`source_docs: []`, `small`) | requisito e desenho na própria SDD | — | Sim |
| Escopo | `git diff --stat b736c77 d1d4320` e o mesmo restrito a `fabrica/descoberta.py`, `compilador.py` e `contracts/` | 3 arquivos, todos em `Arquivos`; nada nos proibidos; o kit não é tocado | leitura | Sim |
| 1 | `pytest tests/test_central_escrita.py -k "partes and descobridor"` | 1 passed | linha `# Parte 2` tirada: 1 failed; só a `# Parte 2` sobrando: 1 failed | Sim |
| 2 | `pytest tests/test_central_escrita.py -k "partes and not descobridor and not compilador"` | 7 passed | 7 mutações em `_problemas_das_partes` e `problemas`: 4, 2, 1, 1, 1, 1 e 6 failed | Sim |
| 3 | `pytest tests/test_central_escrita.py -k "partes and compilador"` | 1 passed | `PARTE_2` diferente do template: 1 failed; `_parte_2` devolvendo `None`: 1 failed | Sim |
| 4 | `ruff check . && ruff format --check . && pytest -q` | `All checks passed!`; 105 files already formatted; 485 passed, 29 deselected | sensores 1 a 3 | Sim |
| 5 | roteiro manual do owner (`fabrica descobrir zero "<ideia medium>"` até a SPEC-ZERO-0003 em `in_review`) | não rodado | — | Pendente do owner |
| 5 (rodada 2) | `fabrica descobrir zero "Avisar o responsável por e-mail…"`, pelo owner, sobre `0b05469`, kit `4293d7a` | SPEC medium; 3 tentativas recusadas com os mesmos 7 problemas de EARS (RF01 a RF07, citando caminhos de arquivo); parada na etapa 3, nenhuma PR | — | **Não** |
| 5 (rodada 3) | `fabrica descobrir zero "<ideia medium>"`, pelo owner, sessão `e3a45134-…`, sobre `af2db69` (com a SDD-FAB-0007), kit `4293d7a` | SPEC-ZERO-0004 em `in_review` na PR fabrica-central-teste#8, `medium`, `# Parte 1` na linha 25 e `# Parte 2` na 56; `validate_doc.py` verde; `_problemas_das_partes` `[]`; `_parte_2` começa por `# Parte 2 — Desenho…` | — | Sim |

Os sensores foram feitos com cópia do arquivo no scratchpad da sessão,
sem `git stash` e sem commit. Depois de cada um, o arquivo foi restaurado
pela cópia. No fim, `git status --porcelain` saiu vazio e
`pytest -k partes` deu `9 passed`.

## Rodada 2

O owner rodou o critério 5 na máquina dele (sessão `222bb219…`), sobre
`develop` em `0b05469`, com `FABRICA_FRAMEWORK` no kit `4293d7a` e o
`fabrica-central-teste` em `main` atualizado. A primeira tentativa dele
falhou antes da descoberta (`o projeto exige o framework 2.6.0, e o clone
em ~/doc-traceability-central está na 2.3.2`): era a branch antiga
`claude/vigilant-allen-9qwbh0` e o kit padrão. Não conta como rodada.

A descoberta passou pelas 4 rodadas de perguntas e entregou SPEC `medium`.
As 3 tentativas da etapa 3 foram recusadas com os mesmos 7 problemas:
`critério de RF0N não está em EARS — falta o verbo de obrigação ('deve')`,
com o trecho citado sendo caminhos de arquivo. A sessão parou sem gravar
nada no central.

Causa, conferida contra o kit `4293d7a`: o `check_ears` do `validate_doc.py`
(linha 440) lê o critério na 3ª coluna da tabela de Requisitos funcionais,
como no template (`| RF-ID | Requisito | Critério de aceite (EARS) | Arquivos |`).
O agente escreveu a tabela sem a coluna `Requisito`, e a 3ª coluna virou
`Arquivos`. O `agents/descobridor.md:9` pede só "tabela com RF-ID, critério de
aceite em EARS e coluna Arquivos" e não dá o cabeçalho. Esse trecho vem da
SDD-FAB-0003, e a SDD-FAB-0006 o manteve. A SPEC-ZERO-0001 e a 0002 têm as
quatro colunas: o agente acertou por acaso.

O que a rodada mostra da SDD-FAB-0006: na última tentativa nenhum dos 7
problemas é de `# Parte`, então a SPEC tinha as duas linhas na ordem. Sem a
PR aberta, isso não fecha o critério 5.

Decisão do owner (2026-11-20): caminho 1. Uma SDD small nova, a
SDD-FAB-0007, faz o descobridor dar o cabeçalho exato e a escrita no central
recusar a tabela fora do template com uma mensagem que o agente entenda.
Depois dela, o owner roda o critério 5 de novo.

## Rodada 3

Com a SDD-FAB-0007 mergeada (PR #49, `af2db69`), o owner rodou a descoberta
de novo. A sessão `e3a45134-47ee-4d05-85f9-f13957bb5b92` foi criada em
2026-11-21T01:32:20Z, 12 s depois do `pull --ff-only` de `develop` para
`af2db69`, segundo o reflog do owner. O `git diff af2db69` dos dois arquivos
de produção saiu vazio.

Resultado: a PR michelpessoa/fabrica-central-teste#8, com um commit só sobre
`main` (`d9d4c86`, autor "Fábrica Agêntica", 01:36:17Z), abre a SPEC-ZERO-0004
em `in_review`, `sizing: "medium"`. Conferi num clone próprio do central, em
`pull/8/head`, sem escrever em `~/fabrica-central-teste`:

- `# Parte 1 — Requisito (o QUÊ)` na linha 25 e `# Parte 2 — Desenho (o COMO e o ONDE)`
  na linha 56, nessa ordem;
- `validate_doc.py` do `_framework/` do central (2.7.0): `✅ 1 documento(s) passaram`;
- `_problemas_das_partes(texto)`: `[]`;
- `compilador._parte_2(texto)` começa por `# Parte 2 — Desenho (o COMO e o ONDE)`.

Isso fecha RF01 a RF03 de ponta a ponta. A SPEC-ZERO-0003 (sessão `ef10e0ac-…`,
sobre `0b05469`, já com o código desta SDD) também saiu com as duas linhas.
Como ela rodou sem a SDD-FAB-0007, o owner a descartou como evidência.

## Status

`implemented` na rodada 3, no front-matter, no `registry.yaml` e no
`registry.md`. O `validate_state.py` do kit `4293d7a` sai com 0 nesta SDD.

A linha `1 | 5` da tabela de evidência dizia "não rodado" na coluna de
comando. O `validate_state.py` reprova esse termo em qualquer linha, mesmo
numa rodada antiga já superada. A linha continua lá, sem apagar o histórico,
mas reescrita como "sem execução na rodada 1 … (executado nas rodadas 2 e 3,
linhas abaixo)". O fato registrado é o mesmo.

## Descompassos encontrados

- Requisito sem código: nenhum. RF01 está em `agents/descobridor.md:9`. O texto
  da especificação técnica está nele, palavra por palavra. RF02 está em
  `adapters/doc_traceability/central.py`, com as constantes `PARTE_1` e
  `PARTE_2`, `_problemas_das_partes` e o acréscimo em `EscritaNoCentral.problemas`
  só para `type == "SPEC"`. As mensagens são as da SDD. RF03 é coberto pelo
  teste com o `_parte_2` do compilador.
- Código sem requisito: nenhum. O `return` de dentro do `with` virou uma
  atribuição seguida de `return` depois do bloco. Isso é o mínimo para acrescentar
  os problemas das partes ao fim da lista, e o comportamento do `validar_documento`
  não muda.
- Arquivo fora da SDD: nenhum. Não tocados, como pedido: `fabrica/descoberta.py`,
  `adapters/doc_traceability/compilador.py`, `contracts/*.schema.json` e o kit.
- Observação, sem descompasso: há um teste a mais além dos listados na
  especificação, `test_partes_parte_fora_do_inicio_da_linha_conta_como_ausente`.
  Ele cobre a cláusula "em início de linha" do RF02, é selecionado pelo critério 2
  e fica no arquivo declarado. Sem ele, a mutação que tira a âncora `^` passaria
  (sensor S2e).
- Observação: o trecho "a descoberta não abre a PR" do RF02 depende do
  `fabrica/descoberta.py`, que não muda. Ali, `problemas` não vazio volta ao
  agente antes do `abrir_pr` (`fabrica/descoberta.py:322-325`). Isso já está
  coberto por `tests/test_descoberta.py:501`, de antes desta SDD.

## Lições

- Red flag do registro: escrever `Perfil usado` entre crases (`` `automatizado` ``)
  faz o `validate_state.py` acusar perfil divergente do esperado (`automatizado`).
  A coluna vai sem crase.
- Red flag (rodada 2): instrução ao agente que lista colunas por nome solto
  ("tabela com RF-ID, critério … e coluna Arquivos") em vez do cabeçalho
  exato, quando o validador lê a coluna pela posição. Os testes usavam uma
  tabela escrita à mão, sempre certa, e não pegam isso.
- Red flag (rodada 2): mensagem de recusa que cita o conteúdo da coluna
  errada ("falta 'deve'" sobre caminhos de arquivo) não ensina o agente a
  corrigir: as 3 tentativas repetiram o erro. Quando o formato é posicional,
  a checagem do formato vem antes da checagem do conteúdo.
- Red flag (rodada 3): o `validate_state.py` lê todas as rodadas da tabela,
  não só a última. Linha de rodada antiga com "não rodado" barra o
  `implemented` mesmo depois da execução real. Ao registrar uma pendência,
  descreva o fato ("sem execução na rodada N") em vez do termo da lista.
- Red flag: em SDD `small` com critério manual do owner, a verificação
  automatizada fecha antes do roteiro manual. A SDD fica `approved` com a linha
  "não rodado" na tabela, e o `validate_state.py` impede o `implemented`. Para o
  verificador seguinte não refazer tudo, o que falta fica escrito no
  `validation`.

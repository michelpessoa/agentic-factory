---
id: SDD-FAB-0004
type: SDD
title: "Progresso da descoberta no terminal: em que etapa do fluxo a sessão está e por quê, por eventos do núcleo e texto do CLI"
status: implemented
project: "FAB"
owner: "Michel Pessoa"
created: "2026-11-19"
updated: "2026-11-19"
relates_to: [SDD-FAB-0003]
source_docs: []
sizing: "small"
approved_by:
  kind: human
  actor: michelpessoa
  at: "2026-11-19T10:40:12Z"
  content_sha256: "3501941e6d9defcb7c9cb4807a4e337f47797464a37dcca5e6d58ad36823dd85"
  evidence: "https://github.com/michelpessoa/fabrica-agentica/pull/40#pullrequestreview-5973426059"
consumption_instructions: "SDD small, sem SPEC nem ADR: o requisito e o desenho estão aqui. Os requisitos RF01 a RF04 abaixo são o escopo inteiro: os eventos têm os nomes e campos da tabela de RF01, os textos são os de RF02 e RF03, e não se acrescenta evento, texto, flag, cor ou nível de verbosidade que esta SDD não declara. Os avisos só informam: nunca pedem confirmação nem leem entrada. Teste primeiro, visto falhar. O núcleo (`fabrica/descoberta.py`) não imprime nem tem texto para o usuário: emite eventos por um callback recebido no construtor, e só o `fabrica/__main__.py` escreve no terminal."
supersedes: null
superseded_by: null
tags: [descoberta, terminal, progresso, cli, sdlc]
---

# Progresso da descoberta no terminal: em que etapa do fluxo a sessão está e por quê, por eventos do núcleo e texto do CLI

> Este documento é COMPILADO a partir de `source_docs` — não é escrito do
> zero. É o artefato de entrada (input) para ferramentas de IA realizarem
> a implementação. Vive no repositório de CÓDIGO deste projeto (não no
> repositório central do framework) porque é o único documento pensado
> para ser lido pela IA no momento de implementar. Em sizing `small`,
> `source_docs` é vazio: não há upstream, e isso é registro, não lacuna.

## Resumo executivo

`uv run python -m fabrica descobrir <projeto> "<ideia>"` não mostra nada
entre as perguntas e o resultado final. Enquanto o agente descobridor
roda, enquanto os validadores recusam o rascunho e o comando tenta de
novo, e enquanto a PR é aberta no central, o terminal fica parado. E
quando aparecem perguntas, nada diz por que elas existem nem o que vem
depois. Na primeira descoberta do ensaio do critério 11 da SDD-FAB-0003,
em 2026-11-18, a sessão parou depois de 3 tentativas
(`TENTATIVAS_DE_RASCUNHO = 3`) por causa da tabela sweep da SPEC, e o
owner só viu o motivo no fim.

Esta SDD dá ao usuário a visão do fluxo inteiro enquanto a descoberta
roda. No início, o terminal mostra as seis etapas, da ideia até a
release. A cada etapa macro, um cabeçalho `── n/6 … ──` diz onde a
sessão está, e linhas curtas dizem o que acontece e por quê: por que o
agente pergunta, por que o rascunho é validado antes de o usuário ler,
por que uma recusa volta ao agente, e por que um documento vai ao
central antes de qualquer SDD. No fim, o terminal diz o próximo passo,
e uma sessão parada mostra os motivos de cada tentativa organizados,
os da última primeiro. Os avisos só informam. Nenhum pede resposta.

## Decisão(ões) de arquitetura aplicável(is)

Sem ADR — sizing `small`: nenhum critério do gate `rfc_to_adr` se aplica.
Não há padrão arquitetural novo, decisão cara de reverter, trade-off
relevante, impacto entre times nem dependência nova.

- **Regra das SDDs anteriores (SDD-FAB-0002, SDD-FAB-0003):** o núcleo
  (`fabrica/descoberta.py`, `fabrica/pipeline.py`) não conhece o
  framework nem o terminal. Por isso:
  - o núcleo emite **eventos com dados**, sem texto para o usuário, por
    um callback `progresso: Callable[[str, dict], None]` recebido no
    construtor da `Descoberta`, como os colaboradores que ela já recebe
    (`runner`, `redator`, `escritor`);
  - o **texto explicativo** vive em `fabrica/__main__.py`, que é a
    camada de terminal.

  O que o texto diz sobre o framework, como o tipo de documento exigido
  pelo sizing, vem no próprio evento (`tipo`, que o núcleo já recebe de
  `escritor.tipo_do_central`), e não de uma tabela repetida no CLI.
- **Sizing `small`, justificado:** toca 3 arquivos de código e testes
  (`fabrica/descoberta.py`, `fabrica/__main__.py`,
  `tests/test_descoberta.py`). Estados, tentativas, schema e PRs não
  mudam. Muda só o que o terminal mostra durante a espera.

## Requisitos consolidados

- **RF01 — O núcleo emite um evento por etapa.** `Descoberta.__init__`
  ganha o parâmetro nomeado `progresso: Callable[[str, dict], None] |
  None = None`. Sem callback, nada é emitido e o comportamento é o de
  hoje. Com callback, a descoberta chama `progresso(evento, detalhes)`
  nestes pontos, com exatamente estes campos em `detalhes`
  (`tentativas` é `TENTATIVAS_DE_RASCUNHO`, `rodadas` é
  `RODADAS_DE_PERGUNTAS`):

  | Evento | Momento | `detalhes` |
  |---|---|---|
  | `agente` | em `_rodada`, logo antes de `runner.executar` | `tentativa`, `tentativas`, `respostas` (bool: a conversa tem pelo menos uma rodada respondida) |
  | `perguntas` | em `_rodada`, logo antes de salvar `AGUARDANDO_RESPOSTAS` | `quantidade` (perguntas desta rodada), `rodada` (`len(conversa)` depois de acrescentar esta), `rodadas` |
  | `validando` | no início de `_receber_rascunho`, antes de `problemas_do_rascunho`; em `_receber_documento`, depois das recusas de caminho e logo antes de `escritor.montar` | `tipo` (`"SDD"`, ou o `tipo` do documento), `sizing`, `origens` (lista dos `id` das origens da sessão), `tentativa`, `tentativas` |
  | `recusa` | em `_recusar`, depois de registrar em `dados["recusas"]` e antes do `_salvar` | `tentativa` (a recusada), `tentativas`, `problemas` (int, quantos), `parando` (bool: vai para `PARADA`) |
  | `pr_central` | em `_receber_documento`, logo antes de `escritor.abrir_pr` | `doc_id`, `tipo`, `tentativa`, `tentativas` |
  | `pronto` | em `_receber_rascunho`, logo antes de salvar `AGUARDANDO_APROVACAO` | `sdd_id`, `tentativa`, `tentativas` |

  As recusas que acontecem antes de `validando` (resposta fora do
  contrato, perguntas sem rodada, rascunho de SDD quando o sizing pede
  documento do central, documento fora do caminho) emitem só `recusa`.
  O núcleo não tem texto para o usuário.
- **RF02 — O CLI explica a etapa e o porquê.** `fabrica/__main__.py`
  ganha `mostrar_progresso(evento: str, detalhes: dict) -> None`, que
  imprime com `flush=True` o texto da tabela abaixo, com os campos de
  `detalhes` no lugar das chaves. `montar_descoberta` o passa como
  `progresso=mostrar_progresso`. Uma linha em branco separa cada bloco
  do anterior. `{origens}` é a lista unida por `", "`. `problema(s)` e
  `pergunta(s)` ficam literalmente assim. Evento desconhecido, e
  condição sem linha na tabela, não imprimem nada.

  | Evento (condição) | Texto |
  |---|---|
  | `agente` (`tentativa == 1` e sem `respostas`) | `── 1/6 Entender a ideia ──` / `O agente lê a sua ideia e decide se já dá para escrever ou se falta informação.` / `A chamada ao agente demora, e o terminal fica parado enquanto ela roda. Aguarde.` |
  | `agente` (`tentativa == 1` e com `respostas`) | `Respostas enviadas. O agente decide se ainda falta algo ou se já escreve. Aguarde.` |
  | `agente` (`tentativa > 1`) | nada: a linha de `recusa` já disse que o agente refaz |
  | `perguntas` | `O agente tem {quantidade} pergunta(s) (rodada {rodada} de até {rodadas}).` / `Por que perguntar: as respostas fecham o escopo, os critérios de aceite e o tamanho` / `da mudança. O tamanho decide quais documentos o framework exige antes do código.` |
  | `validando` (`tentativa == 1`, `tipo == "SDD"`, com `origens`) | `── 2/6 Escrever o documento ──` / `O agente entregou um rascunho de SDD, tamanho {sizing}.` / `A SDD nasce de {origens}, já aprovada(s) no central.` / (linha em branco) / `── 3/6 Validar ──` / `Os validadores do framework conferem o rascunho como ele entraria na base, antes de você ler.` |
  | `validando` (`tentativa == 1`, `tipo == "SDD"`, sem `origens`) | igual à anterior, com a terceira linha `{sizing} sem --origem: basta a SDD, sem SPEC nem RFC antes.` |
  | `validando` (`tentativa == 1`, outro `tipo`) | `── 2/6 Escrever o documento ──` / `O agente entregou um rascunho de {tipo}, tamanho {sizing}.` / `{sizing} sem --origem: o framework pede uma {tipo} aprovada no central antes da SDD.` / (linha em branco) / `── 3/6 Validar ──` / `Os validadores do framework conferem o rascunho como ele entraria no central, antes de você ler.` |
  | `validando` (`tentativa > 1`) | `Tentativa {tentativa} de {tentativas}: o agente entregou um novo rascunho de {tipo} ({sizing}), e os validadores o conferem.` |
  | `recusa` (sem `parando`) | `Tentativa {tentativa} de {tentativas} recusada: {problemas} problema(s). O agente recebe os motivos e refaz. Aguarde.` |
  | `recusa` (`parando`) | nada: o bloco de parada de RF03 mostra os motivos |
  | `pr_central` | `── 4/6 Aprovar ──` / `{doc_id} passou nos validadores na tentativa {tentativa} de {tentativas}.` / `Abrindo a PR no central, onde o documento fica em in_review.` |
  | `pronto` | `── 4/6 Aprovar ──` / `{sdd_id} passou nos validadores na tentativa {tentativa} de {tentativas}.` / `Agora é com você: nada entra na base sem a sua aprovação.` |

  Na tabela, ` / ` separa linhas do terminal.
- **RF03 — `conversar` abre com o mapa e fecha com o próximo passo.**
  - Logo depois de `sessão {sessao}`, uma vez por chamada (também com
    `--retomar`), uma linha em branco e o mapa:

    ```
    Descoberta: da sua ideia até um documento aprovado, antes de qualquer código.
      1. Entender a ideia      o agente pergunta o que faltar
      2. Escrever o documento  o tamanho da mudança decide qual
      3. Validar               os validadores do framework conferem
      4. Aprovar               só você aprova; nada entra sem isso
      5. Implementar           a fábrica implementa e integra em develop
      6. Liberar               release para main, com merge seu
    Esta sessão cuida das etapas 1 a 3. Da 4 em diante, cada etapa começa por um comando seu.
    ```
  - `AGUARDANDO_APROVACAO`: as duas linhas de hoje, seguidas de
    `Depois de aprovada, a SDD vai para develop por PR e o vigia dispara a implementação (etapa 5).`
  - `NO_CENTRAL`: as duas linhas de hoje, seguidas de uma linha que
    depende do tipo, lido do prefixo de `doc_id` (`doc_id.split("-")[0]`):
    - `SPEC`: `Com a SPEC aprovada, a SDD sai de outra descoberta com --origem {doc_id}.`
    - outro tipo: `Com a {tipo} aprovada, o fluxo segue no central até uma SPEC aprovada, que é a --origem da SDD.`
  - `PARADA`: o bloco abaixo troca as linhas de hoje (`Parada: …` e a
    lista com `- `), e a saída continua 1. `{t}` e a lista principal são
    da última entrada de `dados["recusas"]`. Em "Tentativas anteriores",
    cada entrada anterior aparece com os seus problemas numerados, ou
    com `os mesmos motivos da tentativa {t}` quando a lista dela é igual
    à da última. Sem entradas anteriores, a seção "Tentativas
    anteriores" não aparece.

    ```

    ── Parada na etapa 3/6 Validar ──
    O rascunho foi recusado nas {tentativas} tentativas. Nada foi gravado na base nem no central.

    Motivos da última tentativa ({t} de {tentativas}), {n} problema(s):
      1. <problema>
      2. <problema>

    Tentativas anteriores:
      tentativa 1: {n} problema(s)
        1. <problema>
      tentativa 2: os mesmos motivos da tentativa 3

    O que fazer: ajuste a ideia com base nesses motivos e rode descobrir de novo.
    ```
- **RF04 — Só informa.** Nenhum texto de RF02 ou RF03 lê entrada, pede
  confirmação ou espera o usuário. As perguntas e os prompts `> ` de
  hoje não mudam. Os códigos de saída de `conversar` não mudam.

**Fora de escopo:**

- mudar o número de tentativas ou de rodadas, o schema da resposta do
  agente ou o fluxo do `central conferir`;
- listar os problemas a cada recusa durante a sessão (eles vão ao agente
  como hoje e aparecem no bloco de parada);
- avisos no `aprovar`, que já imprime `publicando em …`, e no pipeline;
- marcar no mapa a etapa atual (o cabeçalho `── n/6 … ──` já diz onde a
  sessão está), cor, barra de progresso, tempo decorrido e flag para
  silenciar;
- comando para rever uma sessão parada;
- os pontos não bloqueantes de `docs/sdd/validation-SDD-FAB-0003.md`
  (asserções fracas do critério 6 e a mensagem "push recusado" de
  `abrir_pr_documento`).

## Especificação técnica consolidada

`fabrica/descoberta.py`:

- `from collections.abc import Callable`.
- `Descoberta.__init__(..., escritor: Escritor | None = None, progresso:
  Callable[[str, dict], None] | None = None)`; guarda
  `self._progresso = progresso`.
- Método privado `_avisar(self, evento: str, **detalhes) -> None`: chama
  `self._progresso(evento, detalhes)` se houver callback; senão, não faz
  nada. Exceção do callback não é tratada.
- Os pontos de RF01 chamam `self._avisar(...)` nos lugares da tabela.
- Nenhum `print`, nenhum import de `sys` e nenhum texto para o usuário
  no módulo.

`fabrica/__main__.py`:

- Constante `MAPA` com o bloco de RF03.
- `mostrar_progresso(evento, detalhes)`: escolhe o texto de RF02 pela
  condição e o imprime com `flush=True`.
- Função `mostrar_parada(sessao: str, dados: dict) -> None`, que imprime
  o bloco de parada de RF03 a partir de `dados["recusas"]`.
- `montar_descoberta` passa `progresso=mostrar_progresso`.
- `conversar`: imprime `MAPA` depois de `sessão {sessao}`, acrescenta a
  linha final de `AGUARDANDO_APROVACAO` e de `NO_CENTRAL` e chama
  `mostrar_parada` em `PARADA`. O resto não muda.

O terminal completo dos três casos (`small` recusado uma vez e depois
aprovado, `medium` sem `--origem` indo ao central, e parada) é a
composição dos textos de RF02 e RF03, na ordem dos eventos de RF01.

## Critérios de aceite / definição de pronto

| # | Critério (origem: RF-ID / contrato) | Comando de verificação | Resultado esperado | Perfil esperado |
|---|---|---|---|---|
| 1 | RF01: eventos de perguntas, validação, recusa, retentativa e pronto, na ordem | `uv run pytest -q tests/test_descoberta.py -k eventos_do_rascunho` | runner com perguntas, depois rascunho recusado pelo redator, depois aceito: a lista gravada pelo callback é exatamente `agente` (t=1, sem respostas), `perguntas` (1, rodada 1 de 4), `agente` (t=1, com respostas), `validando` (SDD, small, sem origens, t=1), `recusa` (t=1 de 3, 1 problema, sem parar), `agente` (t=2), `validando` (t=2), `pronto` (SDD-ZERO-0001, t=2), com os campos de RF01 | automatizado |
| 2 | RF01: recusa de `problemas_do_rascunho` e parada | `uv run pytest -q tests/test_descoberta.py -k eventos_da_parada` | três rascunhos com 2 problemas cada em `problemas_do_rascunho`: `agente`, `validando`, `recusa` em cada tentativa; `parando` falso em t=1 e t=2 e verdadeiro em t=3; nenhum `pronto` | automatizado |
| 3 | RF01: eventos do documento do central, antes da PR, e origens | `uv run pytest -q tests/test_descoberta.py -k eventos_do_documento` | documento SPEC medium aceito: `agente`, `validando` (SPEC, medium), `pr_central` (SPEC-ZERO-0001, SPEC, t=1), e `pr_central` é gravado antes de `EscritorFalso.abrir_pr`; documento de tipo errado emite `recusa` sem `validando`; sessão com origem emite `validando` com `origens` igual à lista de ids | automatizado |
| 4 | RF01: sem callback, nada muda | `uv run pytest -q tests/test_descoberta.py -k eventos_sem_callback` | sem `progresso`, a descoberta chega a `AGUARDANDO_APROVACAO` com os mesmos `dados` de hoje | automatizado |
| 5 | RF01: o núcleo não imprime | `uv run pytest -q tests/test_descoberta.py -k nucleo_nao_imprime` | a árvore `ast` de `fabrica/descoberta.py` não tem chamada a `print` nem import de `sys` | automatizado |
| 6 | RF02: cada evento vira o texto da tabela | `uv run pytest -q tests/test_descoberta.py -k textos_do_progresso` | `mostrar_progresso` com cada linha da tabela de RF02, condições incluídas, imprime exatamente o texto, com os campos preenchidos; `agente` com `tentativa > 1`, `recusa` com `parando` e evento desconhecido não imprimem nada | automatizado |
| 7 | RF03: bloco de parada | `uv run pytest -q tests/test_descoberta.py -k bloco_de_parada` | com 3 recusas, a 2ª igual à 3ª e a 1ª diferente, a saída é exatamente o bloco de RF03, com "os mesmos motivos da tentativa 3" na 2ª e os problemas numerados na 1ª; com uma só recusa, a seção "Tentativas anteriores" não aparece | automatizado |
| 8 | RF02, RF03, RF04: CLI mostra mapa, avisos e próximo passo entre as linhas de hoje | `uv run pytest -q tests/test_descoberta.py -k cli_progresso` | `montar_descoberta` (com fonte, runner e escrita trocados por `monkeypatch`) entrega uma `Descoberta` cujo callback é `cli.mostrar_progresso`; `conversar` com esse callback e uma recusa imprime `sessão …`, o `MAPA`, os avisos, as duas linhas finais de hoje e a linha "Depois de aprovada…", sai com 0 e não lê `input` além das perguntas; `NO_CENTRAL` com SPEC e com RFC imprime a linha certa; `PARADA` sai com 1 | automatizado |
| 9 | Suíte inteira e lint, como no CI | `uv run ruff check . && uv run ruff format --check . && uv run pytest -q` com kit em `efe1c71`, `fabrica-cobaia` e central de teste presentes | tudo verde; os testes existentes de `conversar` (inclusive `test_cli_conversar_no_central_mostra_a_pr_e_o_conferir`) passam sem mudança | automatizado |
| 10 | RF02, RF04: os avisos aparecem durante a espera e se entendem sem o código | `uv run python -m fabrica descobrir zero "<ideia>"` na máquina do owner | cada bloco aparece antes de a etapa seguinte terminar, o owner entende em que etapa está e por quê, e o final mostra o próximo passo | manual |

## Instruções específicas para a IA implementadora

- Teste primeiro: cada critério automatizado tem teste visto falhar antes
  do código.
- Arquivos esperados: `fabrica/descoberta.py`, `fabrica/__main__.py` e
  `tests/test_descoberta.py`, mais esta SDD e `docs/sdd/registry.yaml` /
  `registry.md`. Nada além.
- Os testes usam os falsos já existentes em `tests/test_descoberta.py`
  (`RunnerFila`, `RedatorFalso`, `EscritorFalso`, fixture `montar`). A
  fixture `montar` pode ganhar o parâmetro `progresso`, repassado ao
  construtor.
- Não altere `TENTATIVAS_DE_RASCUNHO`, `RODADAS_DE_PERGUNTAS`, o schema
  `contracts/resposta-descoberta.schema.json`, `problemas_do_rascunho`,
  os estados nem `adapters/`.
- Não mude o texto nem a ordem das linhas que `conversar` imprime hoje,
  fora o que RF03 manda: o `MAPA`, as linhas finais acrescentadas e o
  bloco de parada no lugar das linhas de `PARADA`.

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

Verificação independente completa em `docs/sdd/validation-SDD-FAB-0004.md`. Veredito: **PASS**.

**Verificador independente:** sim

Diff verificado: `0a33050..162fc96` (`0a33050` é o merge-base com `origin/develop`); kit em `efe1c71e96bf72d5627a69f21fa8655c8c810425` (2.6.0) via `FABRICA_FRAMEWORK`; `fabrica-cobaia` em `d4e8cf1`; `fabrica-central-teste` em `658cecd`; 2026-11-19. Sensores rodados com `PYTHONDONTWRITEBYTECODE=1` e restaurados com `git checkout -- <arquivo>`.

| Rodada | # | Comando rodado | Saída (resumo) | Sensor | Passou? | Assertion (file:line) | Perfil usado |
|---|---|---|---|---|---|---|---|
| 1 | Fidelidade à origem | não se aplica: sizing `small`, `source_docs: []` (sem SPEC nem ADR de origem); por conferência, `python3 $FABRICA_FRAMEWORK/_framework/scripts/check_source_docs.py docs/sdd/SDD-FAB-0004.md ~/fabrica-central-teste/docs/ZERO` | "✅ source_docs de SDD-FAB-0004.md conferem com o registry central.", exit 0 (lista vazia); itens 2 a 4 do passo 0 não têm origem contra a qual comparar | sem teste automatizado (passo não se aplica) | Sim | n/a | n/a |
| 1 | 1 | `uv run pytest -q tests/test_descoberta.py -k eventos_do_rascunho` | 1 passed, 59 deselected | `perguntas` sem emitir: 1 failed; `respostas` sempre `False`: 1 failed; `pronto` com `tentativa=1` fixo: 1 failed; `problemas` da recusa +1: 1 failed; restaurado: 1 passed | Sim | `tests/test_descoberta.py:563` | automatizado |
| 1 | 2 | `uv run pytest -q tests/test_descoberta.py -k eventos_da_parada` | 1 passed, 59 deselected | `parando` com `>` em vez de `>=`: 1 failed; `_validando` removido de `_receber_rascunho`: 1 failed; `recusa` sem emitir: 1 failed; restaurado: 1 passed | Sim | `tests/test_descoberta.py:584` | automatizado |
| 1 | 3 | `uv run pytest -q tests/test_descoberta.py -k eventos_do_documento` | 2 passed, 58 deselected | `pr_central` emitido depois de `abrir_pr`: 1 failed (`:609`); `origens` sempre `[]`: 1 failed (`:628`); `validando` antes da recusa de tipo: 2 failed; restaurado: 2 passed | Sim | `tests/test_descoberta.py:609` | automatizado |
| 1 | 4 | `uv run pytest -q tests/test_descoberta.py -k eventos_sem_callback` | 1 passed, 59 deselected | `_avisar` sem a guarda de `None`: 1 failed; `recusas` gravadas só com callback: 1 failed; restaurado: 1 passed | Sim | `tests/test_descoberta.py:638` | automatizado |
| 1 | 5 | `uv run pytest -q tests/test_descoberta.py -k nucleo_nao_imprime` | 1 passed, 59 deselected | `print(evento)` em `_avisar`: 1 failed (`:650`); `import sys`: 1 failed (`:652`); `from sys import stderr`: 1 failed (`:654`); restaurado: 1 passed | Sim | `tests/test_descoberta.py:650` | automatizado |
| 1 | 6 | `uv run pytest -q tests/test_descoberta.py -k textos_do_progresso` | 13 passed, 47 deselected | "Aguarde." trocado por "Espere.": 1 failed; `agente` com `tentativa >= 1` imprime: 1 failed (`:755`); `recusa` com `parando` imprime: 1 failed; destino "na base" para SPEC: 1 failed; origens unidas por " e ": 1 failed; sem a linha em branco: 10 failed; restaurado: 13 passed. `flush=True` removido: 13 passed (capsys não vê o flush; coberto só pelo critério 10) | Sim | `tests/test_descoberta.py:742` | automatizado |
| 1 | 7 | `uv run pytest -q tests/test_descoberta.py -k bloco_de_parada` | 2 passed, 58 deselected | "os mesmos motivos" sem a comparação (`if True`): 1 failed; comparação nunca verdadeira: 1 failed; "Tentativas anteriores" sempre impressa: 1 failed (`:787`); primeira recusa no lugar da última: 1 failed; restaurado: 2 passed | Sim | `tests/test_descoberta.py:765` | automatizado |
| 1 | 8 | `uv run pytest -q tests/test_descoberta.py -k cli_progresso` | 5 passed, 55 deselected | `print(MAPA)` removido: 3 failed; `progresso=mostrar_progresso` removido de `montar_descoberta`: 1 failed (`:796`); linha "Depois de aprovada…" removida: 1 failed; `NO_CENTRAL` com `== "RFC"`: 2 failed (`:863`); `PARADA` com `return 0`: 1 failed (`:874`); `input("Confirma? ")` depois do rascunho: 1 failed; linha antiga "Parada: …" mantida: 1 failed (`:879`); restaurado: 5 passed | Sim | `tests/test_descoberta.py:830` | automatizado |
| 1 | 9 | `uv run ruff check . && uv run ruff format --check . && uv run pytest -q` com o kit em `efe1c71`, `fabrica-cobaia` (`d4e8cf1`) e `fabrica-central-teste` (`658cecd`) presentes | "All checks passed!", "100 files already formatted", "438 passed, 29 deselected in 116.00s"; `test_cli_conversar_no_central_mostra_a_pr_e_o_conferir` passa e não está no diff | linha "Depois de aprovada…" removida, suíte inteira: "1 failed, 437 passed" (`test_cli_progresso_conversar_mostra_mapa_avisos_e_proximo_passo`, `:830`); `import os` sem uso: ruff "Found 2 errors."; `print( MAPA, …)`: "1 file would be reformatted"; restaurado: verde | Sim | `tests/test_descoberta.py:830` | automatizado |
| 1 | 10 | `uv run python -m fabrica descobrir zero "Converter temperatura entre Celsius e Fahrenheit em Python, com testes"`, rodado pelo owner na máquina dele em 2026-11-19 sobre `162fc96` (sessão `3554d03e-95a2-4384-a165-085b0c7e9a37`); saída colada pelo owner, conferida aqui contra RF02 e RF03 | na ordem: `sessão …`; o `MAPA` das 6 etapas; `── 1/6 Entender a ideia ──` com as duas linhas; três rodadas (4, 5 e 2 perguntas; rodadas 1, 2 e 3 de até 4), cada uma com "Por que perguntar…" antes das perguntas e "Respostas enviadas. … Aguarde." depois; `── 2/6 Escrever o documento ──`, "rascunho de SDD, tamanho small", "small sem --origem: basta a SDD…"; `── 3/6 Validar ──`; `── 4/6 Aprovar ──`, "SDD-ZERO-0002 passou nos validadores na tentativa 1 de 3.", "Agora é com você…"; as duas linhas finais de hoje e "Depois de aprovada, a SDD vai para develop por PR e o vigia dispara a implementação (etapa 5)." Sem recusa nem parada: esses caminhos ficam com os critérios 1, 2, 6, 7 e 8. O owner confirmou que os avisos deixaram claro em que etapa a sessão estava | sem teste automatizado (manual) | Sim | n/a | manual |

## Rastreabilidade
| Campo | Valor |
|---|---|
| source_docs | — (sizing `small`) |
| origem do pedido | owner, depois do ensaio do critério 11 da SDD-FAB-0003 (2026-11-18), em que a descoberta parou após 3 tentativas sem aviso intermediário |
| direção do owner | 2026-11-19, na PR #40: os avisos explicam em que etapa do fluxo a sessão está e por que as perguntas existem, como visão global, sem interação com o usuário; textos por etapa macro, 6 etapas, e os problemas no fim, com mais clareza |
| relacionada | SDD-FAB-0003 (caminho `NO_CENTRAL` e `abrir_pr` do escritor) |

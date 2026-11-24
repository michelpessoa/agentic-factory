# Verificação — SDD-FAB-0005

- **Veredito:** FAIL (rodada 1: critério 4; rodada 2: critério 9, causa na especificação; rodada 3: critério 9, causa na implementação do RF04); **PASS** na rodada 4 (critério 9 com a SPEC-ZERO-0003, depois da PR #52)
- **Diff verificado:** `13f33e1..aeee784` (merge-base com `develop` até o head da PR #44); rodada 4: `64d9568..681c004` (correção da PR #52, commit `3a824ab`)
- **Verificador independente:** sim (sessão separada, sem o histórico da que implementou; a sessão da rodada 4 não implementou a SDD nem a correção)

A tabela completa, com comando, saída, sensor e asserção por critério, está
na seção "Evidência de verificação" da SDD-FAB-0005.

| Critério | Comando rodado | Saída (resumo) | Sensor | Passou? |
|---|---|---|---|---|
| Fidelidade à origem | `check_source_docs.py` + leitura da SPEC-DTF-0031 | exit 0; RF15 a RF17 cobertos; nada relaxado | leitura | Sim |
| 1 | grep, `framework_check.py --auto` no central de teste | 2.7.0 em tudo; framework_check verde | quebrado: 2 de 3 | Sim |
| 2 | `pytest tests/test_redacao.py -k formato` | 7 passed | 2 failed | Sim |
| 3 | `pytest tests/test_redacao.py -k enxuta` + teste da completa | 6 passed; 1 passed | 3, 2 e 1 failed | Sim |
| 4 | `pytest tests/test_compilador.py -k enxuta` | 6 passed | **mutação em `_enxuta` não detectada (474 passed)** | **Não** |
| 5 | `pytest tests/test_origem.py -k textos` | 3 passed | 2 e 1 failed | Sim |
| 6 | `pytest tests/test_descoberta.py -k formato` | 12 passed | 1, 1, 1 e 2 failed | Sim |
| 7 | `pytest tests/test_descoberta.py -k redacao` | 2 passed | 1 e 1 failed | Sim |
| 8 | `pytest tests/test_descoberta.py -k esquema` | 1 passed | 1 failed | Sim |
| 9 | roteiro manual | não rodado (rodada parou no FAIL) | — | Não rodado |
| 10 | ruff + `pytest -q` | 474 passed, 29 deselected | sensores 1 a 8 | Sim |
| 4 (rodada 2) | `pytest tests/test_compilador.py -k enxuta`, com 2 testes novos | 8 passed | as três mutações em `_enxuta` agora falham | Sim |
| 9 (rodada 2) | roteiro com componentes reais e agente roteirizado, SPEC-ZERO-0001 e 0002 | `PARADA`: `SPEC-ZERO-000N sem '# Parte 2'` | controle com `# Parte 2` acrescentado numa cópia: passa | **Não** |
| 10 (rodada 2) | ruff + `pytest -q` | 476 passed, 29 deselected | sensores | Sim |
| 9 (rodada 3) | roteiro com componentes reais e agente roteirizado, SPEC-ZERO-0003 (com as duas linhas `# Parte`), sobre `64d9568` | `ENTRADA_OK`; `aceite` 5 de 5 igual ao EARS; `especificacao` sem o bloco ```python da Parte 2 | diff da `especificacao` contra a Parte 2 da SPEC | **Não** |
| Escopo (rodada 4) | `git diff --name-only 64d9568..681c004` | só `compilador.py` e `test_compilador.py`, os arquivos da task do RF04 | leitura | Sim |
| 4 (rodada 4) | `pytest tests/test_compilador.py -k enxuta`, com os três testes novos | 11 passed | recorte do texto limpo: 2 failed; `# Parte 2` dentro de cerca: 1 failed; cabeçalho dentro de cerca: 1 failed; restaurado: 11 passed | Sim |
| 5 (rodada 4) | `pytest tests/test_origem.py -k textos` | 3 passed | sensores da rodada 1 (código igual) | Sim |
| 9 (rodada 4) | roteiro da rodada 3, SPEC-ZERO-0003, sobre `123d5d9` (central em `844800d`) | `AGUARDANDO_APROVACAO` na tentativa 1, sem recusas; `ENTRADA_OK`; `aceite` 5 de 5 igual ao EARS; `especificacao` começa por `# SPEC-ZERO-0003\n\n# Parte 2 — Desenho…`, sem `# Parte 1`; diff do `difflib` vazio, bloco ```python inteiro | controle com o `compilador.py` de `64d9568`: diff de 13 linhas, bloco some | Sim |
| 10 (rodada 4) | ruff + `pytest -q` | 493 passed, 29 deselected | sensores | Sim |

## Descompassos encontrados

- **Rodada 4: nenhum.** A PR #52 corrigiu o `_parte_2`: a linha `# Parte 2` e
  os cabeçalhos `## Autorrevisão…` são procurados fora de cercas
  (`_fora_de_cercas`), e o recorte sai do texto original. Com a SPEC-ZERO-0003,
  a Parte 2 chega inteira à `especificacao` (diff vazio), inclusive o bloco
  ```python com `def listar(...)`. A SDD-FAB-0005 não tem ADR em `source_docs`
  no projeto do roteiro (a SPEC-ZERO-0003 tem `parent_adr: null`), então a parte
  `# ADR-…` não se aplica ao roteiro; ela segue coberta pelo critério 4
  (`tests/test_compilador.py:234`). A SDD fica pronta para o owner avançar a
  `implemented`.
- Observação da rodada 3 sobre `documents: []`, fora do escopo desta SDD: **ainda
  se reproduz** na rodada 4. Com o mesmo roteiro e o registry do projeto
  terminando em `documents: []`, as três tentativas são recusadas com
  `ParserError` (`expected <block end>, but found '<block sequence start>'`, linha
  4, `- id: SDD-ZERO-0001`) em `validate_doc.py` e `registry_tools.py`, e a
  descoberta para em `PARADA`. Não foi corrigido aqui.

- **Rodada 3, critério 9: o compilador perde os blocos de código da Parte 2.**
  Com a SPEC-ZERO-0003 (escrita pela descoberta depois da SDD-FAB-0006, com
  `# Parte 1` e `# Parte 2`), a cadeia RF01 a RF04 roda inteira: descoberta
  enxuta aprovada pelos validadores na tentativa 1, `aprovar`, e
  `Pipeline._entrada` em `ENTRADA_OK`. O `aceite` de cada RF é o EARS da SPEC.
  Mas a `especificacao` não traz a Parte 2 inteira. O `_parte_2`
  (`adapters/doc_traceability/compilador.py:202`) acha a linha `# Parte 2`
  em `_sem_cercas_de_codigo(texto)` e corta a partir desse mesmo texto
  limpo, então todo bloco cercado da Parte 2 some. Na SPEC-ZERO-0003, sumiu
  o bloco ```python com `def listar(diretorio, responsavel=None, status=None,
  texto=None) -> list[dict]`, a assinatura da biblioteca que a Parte 2
  define como contrato. A especificação desta SDD diz "o texto da linha
  `# Parte 2` (início de linha, fora de cercas de código) até o fim": a
  cerca qualifica a busca da linha, não o recorte. Causa: implementação. O
  critério 4 não pega porque a SPEC dos testes (`tests/test_compilador.py`,
  `SPEC_X`) não tem cerca de código na Parte 2.
- Observação do roteiro, sem descompasso nesta SDD: com
  `docs/sdd/registry.yaml` terminando em `documents: []`, o redator acrescenta
  `  - id: …` depois da lista vazia e o YAML fica inválido (`ParserError` nos
  três validadores). O roteiro usou `documents:` vazio, como os testes da
  fábrica. Os testes do kit usam `documents: []`, então um registry novo nesse
  formato quebraria a primeira descoberta.

- **Critério 4, "SDD da 2.6.0 dá a mesma saída com e sem `origens`", não
  discrimina o caso que importa.** `test_sdd_que_nao_e_enxuta_ignora_origens`
  (`tests/test_compilador.py:287`) usa uma SDD com `source_docs: []`, em que o
  ramo da referência nunca é alcançado. Trocar `_enxuta(frente, corpo)` por
  `frente.get("source_docs")` em `compilador.compilar_sdd` passa no critério e
  na suíte inteira (474 passed). Com essa quebra, uma SDD completa com
  `source_docs` (a que a descoberta com `--origem` escreve no `fabrica-cobaia`,
  em 2.3.2, por decisão do owner) teria `especificacao` e `aceite` trocados pelo
  texto da SPEC. O código atual está correto; o que falta é o teste.
- Arquivo fora da decomposição: `HANDOFF.md` (documento de sessão, não código).
  Não é scope creep.
- Requisito sem código ou código sem requisito: nenhum.

- **Rodada 2, critério 9: a fábrica escreve SPECs que o próprio compilador
  enxuto recusa.** As únicas SPECs `approved` do central de teste
  (SPEC-ZERO-0001 e SPEC-ZERO-0002) saíram da descoberta da fábrica
  (SDD-FAB-0003). O `agents/descobridor.md` (linha 9) lista as seções da SPEC
  sem as linhas `# Parte 1` e `# Parte 2` do template do kit, e o
  `validate_doc.py` do kit aceita a SPEC assim. A SPEC-DTF-0031 define que
  `_parte_2` começa em `# Parte 2` e que a falta da linha é `SddInvalida`, e a
  implementação faz exatamente isso. Com origem nessas SPECs, a descoberta
  enxuta recusa as três tentativas (`SPEC-ZERO-0001 sem '# Parte 2'`) e para em
  `PARADA`. Controle: numa cópia descartável do central, com as duas linhas
  acrescentadas, a cadeia RF01 a RF04 funciona inteira. Causa: especificação
  (SPEC-DTF-0031 e SDD-FAB-0005 pressupõem SPEC no formato do template). A
  decisão é do owner.

## Lições

- Rodada 4: o roteiro ponta a ponta com uma SPEC real (com cerca de código na
  Parte 2) foi o que achou o defeito da rodada 3; vale manter o controle com o
  código antigo, para provar que o diff do `difflib` discrimina.

- Red flag (rodada 3): limpar o texto para achar uma âncora e recortar do
  texto limpo. O recorte tem de vir do original, e o teste do recorte precisa
  de uma SPEC com o que a limpeza tira (cerca de código) na parte recortada.

- Red flag: o teste de "formato antigo não muda" monta o caso mais vazio
  (`source_docs: []`), e não o caso antigo que convive com o novo (SDD completa
  com origem). Quando a regra de detecção tem mais de uma condição (`source_docs`
  e a tabela), o teste negativo tem que satisfazer todas menos uma.
- Red flag do sensor: mutação que troca dois trechos do mesmo tamanho pode
  deixar o `.pyc` velho válido (mtime e tamanho iguais) e dar falso vermelho na
  restauração. Rode os sensores com `PYTHONDONTWRITEBYTECODE=1`.
- Red flag: critério ponta a ponta adiado para "a verificação" esconde
  incompatibilidade entre o que a própria ferramenta produz e o que ela consome.
  Os testes do compilador montam SPEC no formato do template; nenhum usa uma
  SPEC que a descoberta da fábrica escreveu.
- Red flag: validador do kit que aceita SPEC sem `# Parte 2` enquanto um
  consumidor exige a linha. Quando um formato passa a ser lido por máquina, ou
  o produtor é validado contra ele, ou o consumidor tolera a forma antiga.

# Verificação — SDD-FAB-0004

- **Veredito:** PASS (rodada 1)
- **Diff verificado:** 0a33050..162fc96 (fábrica, branch `claude/vigilant-allen-9qwbh0`, PR michelpessoa/fabrica-agentica#40). `0a33050` é o merge-base com `origin/develop`; o código verificado é o de `162fc96`.
- **Verificador independente:** sim (subagente separado, sem ler o histórico da sessão que implementou)
- **Ambiente:** kit em efe1c71e96bf72d5627a69f21fa8655c8c810425 (2.6.0) via `FABRICA_FRAMEWORK`; `~/projetos/fabrica-cobaia` em d4e8cf1; `~/fabrica-central-teste` em 658cecd; 2026-11-19. Sensores rodados com `PYTHONDONTWRITEBYTECODE=1` e restaurados com `git checkout -- <arquivo>`; `git status` limpo no fim, fora os dois arquivos de documentação.

| Rodada | Critério | Comando rodado | Saída (resumo) | Sensor | Passou? |
|---|---|---|---|---|---|
| 1 | Fidelidade à origem | não se aplica (`small`, `source_docs: []`); `check_source_docs.py docs/sdd/SDD-FAB-0004.md ~/fabrica-central-teste/docs/ZERO` por conferência | exit 0, lista vazia; itens 2 a 4 sem origem | sem teste automatizado (passo não se aplica) | Sim |
| 1 | 1 (RF01) | `uv run pytest -q tests/test_descoberta.py -k eventos_do_rascunho` | 1 passed, 59 deselected | 4 mutações: 1 failed cada | Sim |
| 1 | 2 (RF01) | `uv run pytest -q tests/test_descoberta.py -k eventos_da_parada` | 1 passed, 59 deselected | 3 mutações: 1 failed cada | Sim |
| 1 | 3 (RF01) | `uv run pytest -q tests/test_descoberta.py -k eventos_do_documento` | 2 passed, 58 deselected | 3 mutações: 1 a 2 failed cada | Sim |
| 1 | 4 (RF01) | `uv run pytest -q tests/test_descoberta.py -k eventos_sem_callback` | 1 passed, 59 deselected | 2 mutações: 1 failed cada | Sim |
| 1 | 5 (RF01) | `uv run pytest -q tests/test_descoberta.py -k nucleo_nao_imprime` | 1 passed, 59 deselected | `print`, `import sys`, `from sys import`: 1 failed cada | Sim |
| 1 | 6 (RF02) | `uv run pytest -q tests/test_descoberta.py -k textos_do_progresso` | 13 passed, 47 deselected | 6 mutações de texto e condição: 1 a 10 failed cada; `flush=True` removido não é detectado (ver abaixo) | Sim |
| 1 | 7 (RF03) | `uv run pytest -q tests/test_descoberta.py -k bloco_de_parada` | 2 passed, 58 deselected | 4 mutações, inclusive "os mesmos motivos" sem a comparação: 1 failed cada | Sim |
| 1 | 8 (RF02-RF04) | `uv run pytest -q tests/test_descoberta.py -k cli_progresso` | 5 passed, 55 deselected | 7 mutações (`MAPA`, callback, linha final, `NO_CENTRAL`, saída 1, `input` extra, linha antiga de parada): 1 a 3 failed cada | Sim |
| 1 | 9 | `uv run ruff check . && uv run ruff format --check . && uv run pytest -q` | All checks passed; 100 files already formatted; 438 passed, 29 deselected | linha final removida: 1 failed, 437 passed; `import os`: ruff 2 errors; formato: 1 file would be reformatted | Sim |
| 1 | 10 (RF02, RF04, manual) | `uv run python -m fabrica descobrir zero "<ideia>"` pelo owner sobre `162fc96`, sessão `3554d03e-…` | mapa, 1/6, três rodadas (4, 5, 2 perguntas) com o porquê e "Respostas enviadas", 2/6, 3/6, 4/6 com SDD-ZERO-0002 na tentativa 1 de 3, linhas finais e "Depois de aprovada…"; o owner confirmou que ficou claro em que etapa a sessão estava | sem teste automatizado (manual) | Sim |

A tabela completa, com cada mutação, assertion e perfil, está na SDD, em "Evidência de verificação".

## Requisito e código, nas duas direções

- RF01: `Descoberta.__init__(..., progresso=None)` e `_avisar` (`fabrica/descoberta.py`); `agente` antes de `runner.executar` e `perguntas` antes de salvar `AGUARDANDO_RESPOSTAS` em `_rodada`; `validando` por `_validando` no início de `_receber_rascunho` e, em `_receber_documento`, depois das recusas de caminho e antes de `escritor.montar`; `recusa` em `_recusar`, depois de gravar `recusas` e antes do `_salvar`; `pr_central` antes de `abrir_pr`; `pronto` antes de salvar `AGUARDANDO_APROVACAO`. Campos iguais aos da tabela de RF01. As recusas de caminho emitem só `recusa`. Nenhum `print`, `sys` ou texto para o usuário no módulo.
- RF02: `mostrar_progresso` e `_texto_do_progresso` em `fabrica/__main__.py`, com `flush=True` e uma linha em branco antes de cada bloco; `montar_descoberta` passa `progresso=mostrar_progresso`. Os textos batem com a tabela de RF02.
- RF03: `MAPA` impresso depois de `sessão {sessao}` em toda chamada de `conversar`; a linha "Depois de aprovada…" em `AGUARDANDO_APROVACAO`; a linha por tipo (`doc_id.split("-")[0]`) em `NO_CENTRAL`; `mostrar_parada` no lugar das linhas antigas de `PARADA`, que continua saindo com 1.
- RF04: nenhum texto novo lê entrada; os prompts e os códigos de saída de `conversar` não mudam.
- Arquivos do diff: `fabrica/descoberta.py`, `fabrica/__main__.py`, `tests/test_descoberta.py`, `docs/sdd/SDD-FAB-0004.md`, `docs/sdd/registry.yaml` e `docs/sdd/registry.md`. Todos estão na lista da SDD. `TENTATIVAS_DE_RASCUNHO`, `RODADAS_DE_PERGUNTAS`, o schema, `problemas_do_rascunho`, os estados e `adapters/` não foram tocados. Os testes que já existiam só mudaram na fixture `montar`, que ganhou `progresso`, como a SDD permite.
- Código sem requisito: nenhum. `_validando` e `_texto_do_progresso` são helpers privados dos pontos de RF01 e RF02, sem abstração, flag ou config nova.

## Descompassos encontrados

Nenhum bloqueante.

Não bloqueantes, registrados para o humano:

- Nenhum teste automatizado discrimina o `flush=True` de `mostrar_progresso`: com ele removido, o critério 6 e a suíte continuam verdes, porque o `capsys` não vê o flush. Só o critério 10 cobre esse ponto, e num terminal interativo o stdout já sai linha a linha; o flush só faz diferença com a saída redirecionada.
- O critério 4 compara os `dados` com e sem callback no código novo, não contra o código de antes. Como `_avisar` só lê, é equivalente; a mutação que grava `recusas` só com callback foi pega.
- `mostrar_parada(sessao, dados)` não usa `sessao` (a assinatura é a da SDD) e imprime sem `flush`; é a última saída antes do `return 1`, então não atrasa nada.
- `validando` de outro tipo com origens não tem linha na tabela de RF02, mas o núcleo recusa documento do central com `--origem` antes de emitir `validando`, então o caso não ocorre.
- O ensaio manual do critério 10 não passou por recusa nem por parada. Esses caminhos ficam cobertos só pelos critérios automatizados 1, 2, 6, 7 e 8. Para o critério 10 isso basta: ele pede que os avisos apareçam durante a espera e se entendam, e o ensaio mostrou todos os blocos do caminho `small` aprovado, na ordem, até o próximo passo.

## Lições

- Mutação do mesmo tamanho em bytes (`==` → `>=`, `a, *b` → `*b, a`) restaurada dentro do mesmo segundo pode rodar o `.pyc` velho, porque o cache do Python confere só mtime e tamanho. Na primeira passada, dois "restaurado" falharam por isso. Rode os sensores com `PYTHONDONTWRITEBYTECODE=1` ou apague `__pycache__`. Senão um sensor pode parecer não restaurar, ou um teste pode passar sobre código que já não existe.
- `flush=True` é requisito de comportamento que `capsys` não enxerga. Se ele importa, o critério precisa de um teste com um stdout que registre as chamadas de `flush`, ou fica declarado como coberto só pelo manual.

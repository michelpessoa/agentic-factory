# Verificação — SDD-FAB-0007

- **Veredito:** PASS (rodada 1)
- **Diff verificado:** `a2da298..c1d42ca` (`develop` antes da PR #49 até o head dela; merge `af2db69`, pais `a2da298` e `c1d42ca`)
- **Verificador independente:** sim (sessão separada da que implementou, `session_01RJ9BCnZLNghyGFghYWc4jC`, sem o histórico dela)

A tabela completa, com comando, saída, sensor e asserção por critério, está
na seção "Evidência de verificação" da SDD-FAB-0007.

Ambiente, como no CI: kit `doc-traceability-framework` em `4293d7a`
(`FABRICA_FRAMEWORK=~/doc-traceability-framework`), `fabrica-cobaia` em
`d4e8cf1`, `fabrica-central-teste` em `main` (`3667377`), `uv sync`,
`PYTHONDONTWRITEBYTECODE=1`.

| Critério | Comando rodado | Saída (resumo) | Sensor | Passou? |
|---|---|---|---|---|
| Fidelidade à origem | não se aplica (`source_docs: []`, `small`) | requisito e desenho na própria SDD | — | Sim |
| Escopo | `git diff --stat a2da298 c1d42ca` e o mesmo restrito a `fabrica/descoberta.py`, `compilador.py`, `contracts/` e `SDD-FAB-0006.md` | 3 arquivos, todos em `Arquivos`; nada nos proibidos; o kit não é tocado | leitura | Sim |
| 1 | `pytest tests/test_central_escrita.py -k "cabecalho and descobridor"` | 1 passed | texto antigo do descobridor: 1 failed; colunas trocadas no descobridor: 1 failed | Sim |
| 2 | `pytest tests/test_central_escrita.py -k "cabecalho and not descobridor"` | 4 passed | 4 mutações em `_problemas_da_tabela_rf` e `problemas`: 2, 1, 1 e 1 failed | Sim |
| 3 | `ruff check . && ruff format --check . && pytest -q` | `All checks passed!`; 107 files already formatted; 490 passed, 29 deselected | sensores 1 e 2 | Sim |
| 4 | `fabrica descobrir zero "<ideia medium>"`, pelo owner, sessão `e3a45134-…`, sobre `af2db69`, kit `4293d7a` | SPEC-ZERO-0004 em `in_review` na PR fabrica-central-teste#8, `medium`, `# Parte 1` (linha 25), cabeçalho do template (linha 29, RF01 a RF05), `# Parte 2` (linha 56); validadores aprovaram na tentativa 1 de 3 | — | Sim |

Os sensores foram feitos com cópia do arquivo no scratchpad da sessão,
sem `git stash` e sem commit. Depois de cada um, o arquivo foi restaurado
pela cópia. No fim, `git status --porcelain` saiu vazio e
`pytest -k "cabecalho or partes"` deu `14 passed`.

## Critério 4, de ponta a ponta

O owner rodou a descoberta na máquina dele. Segundo o reflog dele,
`develop` foi para `af2db69` às 01:32:08Z, e a sessão
`e3a45134-47ee-4d05-85f9-f13957bb5b92` foi criada 12 s depois. O
`git diff af2db69 -- agents/descobridor.md adapters/doc_traceability/central.py`
saiu vazio.

Conferido aqui num clone próprio do central de teste (`git fetch origin
pull/8/head`), sem escrever em `~/fabrica-central-teste`:

- a PR #8 tem um commit só sobre `main`, `d9d4c86`, do autor "Fábrica
  Agêntica", às 01:36:17Z, com a SPEC-ZERO-0004 e o registry do ZERO;
- front-matter `status: in_review`, `sizing: "medium"`;
- `| RF-ID | Requisito | Critério de aceite (EARS) | Arquivos |` na linha 29,
  com o critério EARS na 3ª coluna de RF01 a RF05;
- `validate_doc.py` do `_framework/` do central (2.7.0): `✅ 1 documento(s) passaram`;
- `_problemas_da_tabela_rf(texto)` e `_problemas_das_partes(texto)`: `[]`;
- `compilador._parte_2(texto)` começa por `# Parte 2 — Desenho (o COMO e o ONDE)`.

Uma ressalva do owner: o agente acertou o cabeçalho na tentativa 1, então a
recusa do RF02 não aconteceu nesta rodada real. Ela fica coberta pelo
critério 2 e pelos sensores dele.

Uma descoberta anterior, a da SPEC-ZERO-0003 (sessão `ef10e0ac-…`), rodou
sobre `0b05469`, sem esta SDD. O owner a descartou como evidência.

## Descompassos encontrados

- Requisito sem código: nenhum. RF01 está em `agents/descobridor.md:9`, com o
  texto da especificação técnica palavra por palavra. RF02 está em
  `adapters/doc_traceability/central.py`, com `CABECALHO_RF`,
  `_problemas_da_tabela_rf` e a chamada depois de `_problemas_das_partes`, só
  para `type == "SPEC"`. A mensagem é a da SDD.
- Código sem requisito: nenhum. A comparação de células usa o `_celulas` que
  já existe no compilador, importado junto do `secao`. A especificação pede
  "cada célula sem espaços nas pontas", e é isso que o `_celulas` faz.
  Nenhuma função nova além da especificada.
- Arquivo fora da SDD: nenhum. Não tocados: `fabrica/descoberta.py`,
  `adapters/doc_traceability/compilador.py`, `contracts/*.schema.json`,
  `docs/sdd/SDD-FAB-0006.md` e o kit.

## Lições

- Red flag: na descoberta real, um formato acertado por acaso não prova a
  instrução. A SPEC-ZERO-0001, a 0002 e a 0003 tinham o cabeçalho certo antes
  desta SDD. A evidência vale quando a execução comprovadamente usou o código
  sob verificação: commit do checkout, horário da sessão e diff vazio dos
  arquivos de produção.

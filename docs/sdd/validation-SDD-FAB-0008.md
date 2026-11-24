# Verificação — SDD-FAB-0008

- **Veredito:** PASS (rodada 1)
- **Diff verificado:** `f434300..b9b02d5` (o merge da PR #55 em `develop` até o merge da PR #56, que traz o commit `dbcd847`)
- **Verificador independente:** sim (sessão `session_01RJ9BCpfVWSsMkVFRFoFeQr`, separada da que implementou e sem o histórico dela)

Ambiente como no `.github/workflows/ci.yml`: kit `michelpessoa/doc-traceability-framework`
em `4293d7a44ca66ffbf91d2d4745e3e78b4d1f8725` em `~/doc-traceability-framework`,
com `FABRICA_FRAMEWORK` apontando para ele; `fabrica-cobaia` em
`~/projetos/fabrica-cobaia` (`d4e8cf1`); `fabrica-central-teste` em
`~/fabrica-central-teste` (`844800d`); `uv sync`.

A tabela completa, com comando, saída, sensor e asserção por critério, está
na seção "Evidência de verificação" da SDD-FAB-0008.

| Critério | Comando rodado | Saída (resumo) | Sensor | Passou? |
|---|---|---|---|---|
| Fidelidade à origem | não se aplica (`source_docs: []`, sizing `small`) | — | não se aplica | Sim |
| Escopo | `git diff --stat f434300..b9b02d5` | 3 arquivos, os da coluna `Arquivos`; `fabrica/descoberta.py`, `contracts/` e `docs/sdd/registry.yaml` intactos | leitura do diff | Sim |
| 1 | `uv run pytest -q tests/test_redacao.py -k "registry and fluxo"` | 2 passed | pré-correção: 2 failed; no-op: 2 failed; sem chamada: 2 failed; itens descartados: 1 failed | Sim |
| 2 | `uv run pytest -q tests/test_redacao.py -k "registry and bloco"` | 3 passed | reformata sempre: 1 failed (`[com-item]`); pré-correção: 3 passed (regressão, como previsto) | Sim |
| 3 | `uv run pytest -q tests/test_descoberta.py -k registry` | 3 passed (o teste novo sem skip) | pré-correção: 1 failed; no-op: 1 failed; sem chamada: 1 failed | Sim |
| 4 | ruff check + ruff format --check + `pytest -q` | All checks passed; 109 files already formatted; 499 passed, 29 deselected | sensores 1 a 3 | Sim |

Todos os mutantes foram feitos sobre `adapters/doc_traceability/redacao.py`
com cópia de segurança no scratchpad e restaurados por ela (`cmp` igual,
`git status` limpo), sem `git stash` nem commit.

## Descompassos encontrados

Nenhum bloqueante. Duas observações:

- **Branch da implementação.** A PR #56 veio de `fix/sdd-fab-0008-registry-em-fluxo`,
  não de `sdd/SDD-FAB-0008` (nome usado pela PR #55, da própria SDD). O id
  está no nome e no commit, então a rastreabilidade se mantém; fica o registro
  do desvio da convenção.
- **`documents` em fluxo que não é a última chave.** A troca preserva o texto
  depois do fluxo, mas o append continua no fim do arquivo; com
  `documents: []` seguido de outra chave, a SDD nova cairia sob a chave
  seguinte. A SDD só declara fora de escopo o caso em bloco que não é a última
  chave; o caso em fluxo não foi visto e não é pedido por nenhum RF. Não muda
  o veredito.

## Lições

- **Filtro `-k` mais largo que o critério.** O `-k registry` do critério 3
  seleciona três testes, dois deles anteriores à SDD. Red flag: ao escrever o
  comando do critério, confira com `--collect-only` que o filtro pega só os
  testes daquele critério, ou cite o nome do teste.
- **Teste de regressão byte a byte só discrimina com item de formato não
  canônico.** Sem o `type: 'SDD'` entre aspas no caso `com-item`, a
  "correção que reformata sempre" passaria nos três testes do critério 2: o
  `safe_dump` reproduz o bloco canônico e o `registrar` devolve a quebra de
  linha final (conferido nesta sessão). O comentário do topo não ajuda,
  porque fica antes do trecho trocado.

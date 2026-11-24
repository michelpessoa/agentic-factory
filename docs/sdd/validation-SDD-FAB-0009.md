# Verificação — SDD-FAB-0009

- **Veredito:** PASS (rodada 2, diff `77a3b9c..7a32640`; ver "Rodada 2" no fim). Rodada 1: FAIL. O A13, manual, foi rodado depois pelo owner e também falhou no RF09 (ver "Resultado do A13").
- **Diff verificado:** 77a3b9c..62f2b12
- **Verificador independente:** sim. Verificador em subagente despachado pela sessão que implementou, a pedido explícito do owner, com contexto limpo (sem ler o histórico da implementação). Pelo procedimento, despachar pela sessão builder é um red flag. Por isso o owner precisa saber deste arranjo.
- **Ambiente:** `FABRICA_FRAMEWORK=$HOME/kit-2.8.0` (kit em `1d9b16c`, `version: "2.8.0"`), `uv run`, branch `claude/determined-wright-any5qu` igual a `origin/develop` em `1e9579e`.

| Critério | Comando rodado | Saída (resumo) | Sensor | Passou? |
|---|---|---|---|---|
| Fidelidade à origem | `check_source_docs.py docs/sdd/SDD-FAB-0009.md docs/DTF` no central, mais a leitura da SPEC-DTF-0032 | exit 0, `source_docs ... conferem`. RF04 a RF10 iguais à SPEC; nenhum critério relaxado; contratos da Parte 2 iguais | sem teste automatizado | Sim |
| A01 | `grep` em `projetos/*.yaml` e `ci.yml`; `pytest tests/test_framework_versao.py` | 3x `2.8.0`; SHA `1d9b16cf…` com `# framework 2.8.0`; 17 passed | `cobaia.yaml` em 2.7.0: 1 failed; restaurado: 17 passed | Sim |
| A02 | `pytest tests/test_vigia_central.py -k prs` | 4 passed. `CHANGES_REQUESTED` só é coberto fora do comando, em `test_central_escrita.py::test_conferir_changes_requested_posterior_derruba` (1 passed) | ver A09 | Sim |
| A03 | `pytest tests/test_vigia_central.py -k specs` | 10 passed | `kind`, coluna `Projeto` e `validate_state`: 1 failed cada; restaurado: 10 passed | Sim |
| A04 | `pytest tests/test_vigia_central.py -k atendida` | 3 passed | `source_docs` e versão: 1 failed cada; restaurado: 3 passed | Sim |
| A05 | `pytest tests/test_descoberta.py -k compilar` | 3 passed | `automatica` e pedido: 1 failed cada. **Sobreviveu** a retirada da sessão do aviso: 3 passed, porque o aviso só é testado em `test_vigia_central.py -k compilar` | Sim, com ressalva |
| A06 | `pytest tests/test_descoberta.py -k politica` | 5 passed | `automatica`, ator e política antes da PR: 1 failed cada; restaurado: 5 passed | Sim |
| A07 | `pytest tests/test_pipeline.py tests/test_vigia.py -k politica` | 6 passed | pipeline (2 mutantes) e vigia: failed; restaurado: 6 passed | Sim |
| A08 | `pytest tests/test_vigia_central.py -k avisos` | 5 passed | dedup, contagem de fetch e ciclo seguindo: failed. **Sobreviveu** `pr` para `None` no aviso da PR da base: 5 passed | Sim, com ressalva |
| A09 | mutante sem o filtro `user.login`; pytest de A02 | 1 failed; restaurado: 4 passed | discrimina | Sim |
| A10 | mutante sem `or primeira_leitura`; pytest de A03 | 1 failed; restaurado: 10 passed | discrimina | Sim |
| A11 | mutante em que `aprovacao_por_politica` devolve `True, []` sem `validate_state`; pytest de A07 | **0 failed (6 passed)**; restaurado: 6 passed | **sobreviveu**. Só `tests/test_origem.py` o mata | **Não** |
| A12 | `python -m fabrica vigiar --help` | mostra `--intervalo`, `--uma-vez` e `--sem-central` | opção renomeada: ausente do help; restaurado: presente | Sim |
| A13 | não rodado (manual, máquina do owner) | pendente | sem teste automatizado | Pendente |
| A13 (owner) | `fabrica vigiar cobaia --uma-vez`, rodadas 0 e 1, contra `fabrica-central-teste` | integradas e compiladas `SPEC-COBAIA-0001`; SDD-COBAIA-0012 por política na PR #18 da cobaia; pipeline em `RECUSADA_ENTRADA` (merge por `fabricaagenticamichel`) | sem teste automatizado (manual) | Não |
| A14 | `ruff check . && ruff format --check . && pytest -q` | All checks passed; 112 files already formatted; 541 passed, 29 deselected | sensores de A01 a A12 | Sim |

Todas as mutações partiram de cópias em `/tmp/claude-0/-home-user/e06b4a98-d8c4-546e-97d2-9cfeb52551a0/scratchpad/orig` e foram restauradas por elas. Depois de cada uma, `git diff --quiet` confirmou o arquivo idêntico ao HEAD. Não houve `git stash` nem commit.

## Descompassos encontrados

1. **A11 não cumprido como escrito (bloqueante).** O sensor pede "pelo menos 1 failed" no pytest de A07. Com `aprovacao_por_politica` sem `validate_state.py` (`adapters/doc_traceability/__init__.py:216-217`), deu 0 failed: os testes de A07 (`tests/test_pipeline.py:904-925`, `tests/test_vigia.py:142-157`) usam `FonteFalsa`. Quem mata o mutante é `tests/test_origem.py:298`, e é esse o teste que `tests/mutacoes.yaml` registra para o mutante. O caminho é decisão do owner:
   - **atualizar a SDD:** A11 (e A07, se for o caso) passa a rodar `tests/test_origem.py -k politica` junto. Isso muda o corpo da SDD `approved`, e ela precisa de nova aprovação.
   - **mudar os testes:** um teste no comando de A07 passa a usar o adaptador real (`FonteDocTraceability`) com o kit fixado.
2. **RF10 parcial nas PRs do central (bloqueante).** RF10 pede o aviso "com o id do documento, o número da PR quando houver e o motivo". Em `fabrica/vigia.py:182`, `_prs_do_central` chama `self._avisar(notificador, doc_id, str(erro))` sem `pr`. `prs_da_fabrica` (`adapters/doc_traceability/central.py:261-277`) devolve só ids, então o vigia não tem o número. O número só aparece quando o texto da exceção o traz, como em `checks da PR #N`. `merge recusado: head → base` (`fabrica/publicacao.py:287`), `aprovação inválida` e `nenhuma PR aberta` saem sem ele. O teste de A08 (`tests/test_vigia_central.py:519-524`) passa porque o número está no texto da exceção falsa. O caminho é decisão do owner:
   - **atualizar a SDD:** declarar que, na PR do central, o número vai só no texto do motivo.
   - **mudar o código:** levar o número da PR até o aviso. Isso pede mudar o retorno de `prs_da_fabrica` ou fazer uma leitura extra, e as duas coisas precisam de declaração na SDD.
3. **Interfaces não declaradas na SDD (escopo não registrado).** Servem a requisitos declarados, mas a SDD diz que suas assinaturas são "o escopo inteiro":
   - `FonteDocTraceability.sdd_com_origem` (`adapters/doc_traceability/__init__.py:192-200`), para o RF06. Ela lê o front-matter das SDDs em `docs/sdd/SDD-*.md`, e não o `registry.yaml`, como diz o texto do RF06;
   - `FonteDocTraceability.aprovar_por_politica` (`adapters/doc_traceability/__init__.py:202-204`), um invólucro para o RF08;
   - o atributo público `LeituraDoCentral.recusadas` (`adapters/doc_traceability/central.py:428`, lido em `fabrica/vigia.py:236`), que leva o aviso de SPEC com `validate_state` vermelho até o núcleo;
   - métodos novos nos `Protocol`: `Redator.origem`, `aprovar_por_politica` e `aprovacao_por_politica` (`fabrica/descoberta.py:54-56`) e `FonteDeContrato.aprovacao_por_politica` (`fabrica/pipeline.py:80`).
   O caminho é decisão do owner: **atualizar a SDD**, declarando essas assinaturas, ou **remover o código**, trocando por interfaces já declaradas. Remover não é viável sem violar o núcleo sem framework.
4. **Mensagem e convenção não declaradas (código sem requisito).**
   - `fabrica/vigia.py:233` imprime `central: leitura falhou, segue na base: ...`, uma linha fora do formato por ciclo da SDD (`central: integradas [...], compiladas [...]; disparadas: [...]`). A SDD diz para não acrescentar mensagem.
   - `fabrica/vigia.py:247-249` grava a linha sentinela `("", "")` em `specs_vistas` para marcar o projeto como lido.
   - Textos novos de commit e de PR em `fabrica/descoberta.py:495` e `:502-506`.
   O caminho é decisão do owner: **atualizar a SDD**, declarando a linha de falha e a sentinela, ou **remover**, sem o `print` e com a primeira leitura marcada de outro jeito.
5. **Cobertura fora do comando do critério (ressalva, não bloqueia sozinha).**
   - A05: o aviso com o id da SPEC e da sessão só é testado em `tests/test_vigia_central.py:481-491`, que o comando de A05 não roda.
   - A02: o `CHANGES_REQUESTED` só é testado em `tests/test_central_escrita.py`.
   - A08: o argumento `pr` de `_avisar` não é discriminado (o mutante sobreviveu).

Arquivos: todos os 19 arquivos do diff estão em "Decomposição em tasks". `fabrica/notificacao.py`, listado na task 6, não foi tocado; o código usa o `Notificador.avisar` que já existia. Isso não é descompasso.

## A13 e o veredito

O A13 (ponta a ponta contra `fabrica-central-teste`) é manual e depende da máquina do owner. Não foi rodado e segue pendente. Mesmo que os itens 1 e 2 acima se resolvessem, o veredito seria no máximo "PASS condicionado ao A13". Sem os links das PRs e a saída das duas rodadas registrados na tabela, a SDD não pode ir a `implemented`. Como o veredito sem o A13 já é FAIL, a checagem do `validate_state.py` numa cópia com `implemented` não foi feita. A SDD segue `approved`.

## Resultado do A13 (rodado pelo owner, saídas coladas na sessão)

Não foi rodado nesta sessão: o owner rodou na máquina dele, com o `gh` ativo em `fabricaagenticamichel`, kit em `292f764` (mesmo conteúdo da tag 2.8.0), `fabrica-cobaia` com o registry em 2.8.0 (PR #17) e `fabrica-central-teste` em `main` `2169958`.

- PR do central: https://github.com/michelpessoa/fabrica-central-teste/pull/10 (SPEC-COBAIA-0001, review "Aprovado" de michelpessoa, merge pelo vigia).
- PR da base: https://github.com/michelpessoa/fabrica-cobaia/pull/18 (SDD-COBAIA-0012, aprovada por política, merge pelo vigia).
- Execução `374d6b59-ec68-4f24-926b-f9464cd53765`: `DETECTADO -> RECUSADA_ENTRADA: SDD não chegou à base por PR de quem pode aprovar (merge por 'fabricaagenticamichel')`.

Achados do A13, além dos descompassos da rodada 1:

1. **PR de documento do central sem a etiqueta** (`fabrica/publicacao.py`, `Github.abrir_pr_documento`): o RF04 filtra pela etiqueta, e a fábrica não a põe nas PRs do central. Sem a etiqueta posta à mão, a PR nunca é conferida.
2. **RF09 contra `permitidos`** (`fabrica/pipeline.py`, entrada): o merge da SDD de política é feito pela conta da fábrica, que não está em `permitidos`; a SDD é recusada, e o caminho sem humano não fecha.
3. **Vigia cai quando o clone da base falha** (`fabrica/vigia.py`, `_aprovadas` → `preparar_copia`): traceback e fim do processo no modo contínuo. Comportamento anterior à SDD-FAB-0009.
4. **Texto de progresso da compilação automática** ("Agora é com você: nada entra na base sem a sua aprovação") pede uma aprovação que a política dispensa.
5. **A SDD nova é disparada no mesmo ciclo**, não no seguinte como diz "Decisão(ões) de arquitetura": o passo 3 clona a base depois do passo 2. O comportamento é melhor; o texto da SDD é que diverge.

## Lições

- **Red flag:** o critério-sensor cita "o pytest de A_n", mas o teste que de fato mata o mutante está em outro arquivo. Quem escreve o sensor deve conferir que o comando do critério contém o teste registrado em `tests/mutacoes.yaml` para aquele mutante.
- **Red flag:** os testes do núcleo usam a fonte falsa, e o critério de segurança (hash) depende do adaptador real. Quando o critério é "recusar hash quebrado", o comando do critério precisa exercer o adaptador real com o kit fixado.
- **Red flag:** "o número da PR quando houver" vira "o número está no texto da exceção". Um teste com o número dentro da mensagem falsa não discrimina o parâmetro.
- **Red flag:** um método de adaptador novo, criado para manter o núcleo sem framework, fica fora da "Especificação técnica consolidada". Quando a SDD diz que as assinaturas são o escopo inteiro, toda ponte núcleo-adaptador nova precisa estar nela.

## Rodada 2

- **Veredito:** PASS
- **Diff verificado:** 77a3b9c..7a32640. É o diff da SDD-FAB-0009 com o da SDD-FAB-0010 e inclui os commits só de documentação das PRs #62 e #63.
- **Verificador independente:** sim. A sessão `session_01RJ9BCmTpCp89YJf9zppMYE` não implementou a SDD-FAB-0009 (`session_01RJ9BCnp9buEznvAVqPkMJc`) nem a SDD-FAB-0010 (`session_01RJ9BCp859Hp5cRz967jUgJ`). Ela não foi despachada pela sessão builder e não leu o histórico das sessões que implementaram.
- **Ambiente:** o mesmo da verificação da SDD-FAB-0010 (`docs/sdd/validation-SDD-FAB-0010.md`):
  - kit em `1d9b16c`;
  - `develop` em `c340598`;
  - o central em `origin/main` `905602f`, para o `check_source_docs.py`.
- **Escopo declarado:** a seção "Escopo declarado da SDD-FAB-0009" da SDD-FAB-0010 (approved, PR #63).

| Critério | Comando rodado | Saída (resumo) | Sensor | Passou? |
|---|---|---|---|---|
| Fidelidade à origem | `check_source_docs.py docs/sdd/SDD-FAB-0009.md docs/DTF` no central e releitura dos RF04 a RF10 | exit 0; SPEC-DTF-0032 e ADR-DTF-0008 `approved` e sem commit depois da aprovação; RFs iguais | sem teste automatizado | Sim |
| Escopo | `git diff --stat 77a3b9c..7a32640` | 27 arquivos, todos declarados nesta SDD ou na SDD-FAB-0010 | sem teste automatizado | Sim |
| A01 | `grep` em `projetos/*.yaml` e `ci.yml`; `pytest tests/test_framework_versao.py` | 3x `2.8.0`; SHA `1d9b16cf…`; 17 passed | `cobaia.yaml` em 2.7.0: 1 failed | Sim |
| A02 | `pytest tests/test_vigia_central.py -k prs` | 4 passed | ver A09 | Sim (ressalva da rodada 1, fora de escopo) |
| A03 | `pytest tests/test_vigia_central.py -k specs` | 10 passed | ver A10 | Sim |
| A04 | `pytest tests/test_vigia_central.py -k atendida` | 3 passed | `if sdd:` desligado: 1 failed | Sim |
| A05 | `pytest tests/test_descoberta.py -k compilar` | 3 passed | sem `automatica = True`: 1 failed | Sim (ressalva da rodada 1, fora de escopo) |
| A06 | `pytest tests/test_descoberta.py -k politica` | 5 passed | ator trocado: 1 failed | Sim |
| A07 | `pytest tests/test_pipeline.py tests/test_vigia.py -k politica` | 9 passed, o adaptador real incluído | sem `if motivos`: 2 failed; sem `de_politica`: 2 failed | Sim |
| A08 | `pytest tests/test_vigia_central.py -k avisos` | 6 passed | dedup: 1 failed; número da PR do central para `None`: 1 failed. **Sobreviveu:** o número da PR da base para `None` | Sim, com ressalva |
| A09 | sem o filtro `user.login`; pytest de A02 | 1 failed; restaurado: 4 passed | discrimina | Sim |
| A10 | sem `or primeira_leitura`; pytest de A03 | 1 failed; restaurado: 10 passed | discrimina | Sim |
| A11 | `aprovacao_por_politica` sem `validate_state`; pytest de A07 | **1 failed**; restaurado: 9 passed | discrimina | Sim |
| A12 | `python -m fabrica vigiar --help` | mostra `--intervalo`, `--uma-vez` e `--sem-central` | opção renomeada: ausente do help | Sim |
| A13 | o C12 da SDD-FAB-0010, rodado pelo owner na máquina dele em 2026-11-23 | central PR #11 etiquetada pela fábrica e integrada; SDD-COBAIA-0013 por política na PR #19 da cobaia; `DETECTADO -> ENTRADA_OK` | sem teste automatizado (manual) | Sim |
| A14 | `ruff check . && ruff format --check . && pytest -q`; `selftest.py` | All checks passed; 114 files already formatted; 550 passed, 29 deselected; 70/70 mutações mortas | sensores de A01 a A12 | Sim |

### O que a rodada 1 apontou e como ficou

1. **A11:** resolvido pelo teste com o adaptador real no comando do A07 (RF01 da SDD-FAB-0010). O mutante morre no comando do critério como ele está escrito.
2. **RF10, número da PR do central:** resolvido no código pelo RF02 da SDD-FAB-0010. O aviso traz `(PR #N)` mesmo quando o motivo não o traz.
3. **Interfaces não declaradas:** declaradas pela SDD-FAB-0010, em "Escopo declarado da SDD-FAB-0009".
4. **Mensagem e convenção não declaradas:** declaradas pela SDD-FAB-0010, pelo mesmo caminho.
5. **Ressalvas do A02 e do A05:** fora de escopo pela SDD-FAB-0010. O comportamento está testado em outro arquivo.
6. **A13:**
   - o RF04 passa sem etiqueta posta à mão (RF03 da SDD-FAB-0010);
   - o RF09 passa com o merge da conta da fábrica (RF04 da SDD-FAB-0010);
   - o vigia não cai sem a base (RF05 da SDD-FAB-0010);
   - o texto de progresso mudou (RF06 da SDD-FAB-0010);
   - o disparo no mesmo ciclo foi declarado como comportamento.

### Ressalvas desta rodada, que não bloqueiam

- **O número da PR da base no aviso não é discriminado.** A ressalva do A08 da rodada 1 segue igual. `fabrica/vigia.py:204` passa o `pr` lido de `descoberta.dados(sessao)`, então o código cumpre o RF10. Mesmo assim, o mutante `pr` → `None` sobrevive a `tests/test_vigia_central.py -k avisos`, porque a exceção falsa já traz `#9` no texto. A SDD-FAB-0010 corrigiu só o caso da PR do central e não declara este. Um teste com motivo sem `#` no caminho de `publicar_por_politica` fecha a lacuna.
- **A lacuna do RF05 da SPEC-DTF-0032** (SPEC de outro projeto pela coluna `Projeto`): a SDD-FAB-0010, aprovada pelo owner, a declara fora de escopo. A decisão fica na SPEC.

### Lições

- **Red flag:** a correção de um descompasso cobre só a instância que a rodada citou. Na rodada 1, o A08 apontou o número da PR da base e o RF10 apontou o da PR do central. A SDD de correção pegou só o segundo. Quando um mesmo parâmetro (`pr` de `_avisar`) tem mais de um chamador, o sensor precisa cobrir cada um.


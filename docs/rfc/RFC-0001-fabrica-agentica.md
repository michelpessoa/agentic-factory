---
id: RFC-0001
status: aceita
data: 2026-11-05
---

# Fábrica Agêntica: reaproveitamento do framework, arquitetura e plano

Aprovada pelo owner em 2026-11-05. Medições feitas em
2026-11-04, em leitura, nos repositórios `doc-traceability-central` (framework
2.3.2) e um projeto real do owner.

## Decisões do owner

- **Projetos reais ficam para depois.** A fábrica nasce e é testada num repositório de
  teste com código e SDDs fictícios. Os projetos reais do owner só entram quando o owner decidir.
- **Gitflow com release.** Feature em branch própria, validada, vai para `develop`. A fábrica
  abre a PR de `release/X.Y.Z`, e só o humano a aprova para ir a `main`.
- **Isolamento em Docker**, desde o primeiro agente executado.
- **A fábrica tem RFC e ADR próprios**, sem misturar com o framework hoje.

## 1. Como o framework entra

A fábrica não é construída pelo fluxo do framework. Ele entra de três formas:

| Papel | O que significa | Consequência |
|---|---|---|
| **Insumo** | Os projetos atendidos usarão o framework, e a SDD deles é a entrada do pipeline | A fábrica lê e valida as SDDs; hoje, só as do repositório de teste |
| **Material** | Código, procedimentos e dados que valem ser chamados ou copiados | Licença MIT, autoria do owner; cópia fica neste repositório |
| **Referência** | Ideias que já custaram falhas reais para aprender | Viram invariantes e testes da fábrica |

**Decisão de desenho:** o núcleo da fábrica (estados, contrato, gates, publicação)
não conhece o framework. Tudo o que é específico dele fica em
`adapters/doc_traceability/`, atrás de uma interface `FonteDeContrato`. Assim o
framework pode evoluir, e um projeto sem ele pode entrar depois com outro adaptador.

## 2. Inventário

### Chamar como está (subprocesso, somente leitura, com SHA registrado)

| Peça | Uso na fábrica | Etapa |
|---|---|---|
| `validate_doc.py` | Recusa SDD com placeholder ou `NEEDS CLARIFICATION` antes de gastar tokens. Falha aqui é `causa=especificacao` | 2 |
| `check_source_docs.py` | Confere se a origem da SDD existe, está aprovada e a URL bate | 2 |
| `registry_tools.py validate` | Consistência entre registry e documento na entrada | 2 |
| `parallel_plan.py --json` | Já decompõe tasks e grupos paralelos em JSON, sem LLM | 3 e 5 |
| `check_commit.py --range` | Mensagens dos commits da branch da fábrica | 6 |
| `validate_state.py` | Evidência completa antes de `implemented` | 6 |
| `ci_gate_verify_sdd.py --json` | Ensaio local do gate de CI antes de abrir a PR | 6 |
| `generate_registry_md.py` | Regenera a visão do registry após mudança de status | 7 |
| `registry_tools.py audit` | Mede commits sem documento: detecta o que passou por fora da fábrica | 8 |

Limite: quase todos só devolvem exit code e texto. O adaptador usa o exit code para
decidir e guarda o texto como evidência, sem interpretar prosa.

### Copiar e adaptar

| Peça | O que aproveitar | O que muda |
|---|---|---|
| `procedures/verify-sdd.md` | Passos 0 a 3, sensor de discriminação, red flags | Saída em JSON com `causa`; sensor em worktree descartável; a fábrica despacha e grava a tabela e o `validation-SDD-*.md` |
| `validate_doc.py`, `validate_state.py`, `framework_lib.py` | `read_frontmatter`, `section_body`, `table_rows`, `split_table_row` | Base do compilador SDD → contrato, com teste de paridade contra o original |
| `selftest.py` + `mutations.yaml` | Mutar o validador e exigir que o teste falhe | Teste dos gates da fábrica: gate que nunca reprova é ruído |
| `guard_bash.sh` | Estrutura de análise por segmento | Falha fechada, com `gh pr merge` e push; é segunda camada, não contenção |
| `check_hooks.py`, `hook_post_edit.py` | Regras aprendidas: stdout de PostToolUse não chega ao modelo, só exit 2; `type: prompt` não injeta em SessionStart | Checagem na partida da fábrica e hook de caminhos protegidos |
| `procedures/handover.md`, `pickup.md` | Seções fixas, "Don't do", "disco vence resumo" | Viram os campos do contrato de correção entre tentativas |
| `lessons_policy`, `lessons_check.py` | Formato de lição, chave de recorrência, regra de não promover falha local a lei | Camada 3 de contexto e limite ao crescimento do contexto vivo |
| `sizing` e `decision_gates` do YAML | Os 5 critérios e os níveis são um classificador pronto | Entrada do risco; o limite de cerca de 3 arquivos passa a ser conferido contra o diff real |
| `prompts/onboarding-bootstrap.md` | BASE, `known_gaps`, ADR reconstruído em revisão | Acrescenta a geração do contexto vivo (fase 4) |
| `templates/ci/verify-sdd-gate.yml.example` | Gate de CI independente da fábrica | Adoção no repositório de teste, após resolver o nome do arquivo de validação (seção 3) |

### Só a ideia

- **Leis inegociáveis** viram invariantes testadas na máquina de estados, por exemplo
  "não existe transição para `AGENTE_RODANDO` sem SDD aprovada".
- **Red flags:** só entram no prompt do agente onde não há gate mecânico.
- **`workflow-rules.map.md` e o teto de bytes:** mapa com leitura sob demanda e limite
  testado. É o modelo do contexto vivo, com tamanho máximo que reprova no teste.
- **YAML como fonte única e renderizações com teste de divergência:** o mesmo princípio
  para gerar agentes e hooks, sem copiar as cerca de 1.700 linhas de `render_*`.
- **`.ignore` do ripgrep:** tira histórico do caminho da busca sem apagar nada.

### Dados: o ativo mais subestimado

| Dado | Quantidade | Uso |
|---|---|---|
| SDDs do projeto real com PR e diff reais | 68 | Replay: rodar a fábrica no SHA anterior, sem publicar. **Só quando o projeto entrar** |
| Relatórios `validation*.md` | 58 (56 PASS, 2 FAIL) | Referência do wrapper do Verify. Muito enviesado para PASS: exige casos com falha injetada |
| Entradas de `LESSONS.md` no projeto real | 7 | Cenários de regressão, por exemplo SDD implementada ainda em `draft` e evidência só no `validation` |

### Não aproveitar

- Ciclo RFC → ADR → SPEC → SDD e registry para construir a própria fábrica.
- `render_indexes.py`, `render_prompts.py`, `check_renderings.py`: resolvem a manutenção do kit.
- `framework_check.py --auto`: descobre diretórios e mistura resultados; a fábrica chama cada validador.
- `hook_session_start.py`: o agente da fábrica não retoma sessão.
- Prompts de Cursor e Copilot, `universal.md`.
- Fluxo INC e PM no MVP.

### O que o framework não tem

Máquina de estados, contrato e token, isolamento, execução de agente, publicação,
schemas JSON, risco, notificação e registro de custo. É este o código novo da fábrica.

## 3. Lacunas e achados medidos

**O compilador SDD → contrato pode ser código, sem LLM.** Medição por expressão
regular nas 68 SDDs do projeto real:

| Campo do contrato | Fonte na SDD | Cobertura |
|---|---|---|
| Critérios com comando | Tabela "Critérios de aceite" | 59/68 (as 9 fora são as SDDs 0001 a 0009, as mais antigas) |
| Perfil do critério | Coluna "Perfil esperado" | 34/68 |
| Requisitos com RF-ID | "Requisitos consolidados" | 60/68 |
| Arquivos permitidos | Coluna "Arquivos tocados" das tasks | 53/68 |
| Arquivos por requisito | Coluna "Arquivos" dos RF | 41/68 |
| Instruções ao agente | "Instruções específicas" | 68/68 |

Isso também rende um **gate de escopo determinístico**: diff com arquivo fora da lista
é reprovado antes do Verify. SDD que não compilar para contrato para na entrada, com
`causa=especificacao`.

Outras lacunas:

- `verify-sdd` só produz Markdown e não tem `causa`.
- O procedimento manda todo FAIL ao humano; o loop automático vale só para
  `causa=implementacao` e o wrapper da fábrica é quem aplica isso.
- `ci_gate_verify_sdd.py` exige `validation-SDD-REAL-0068.md`, e o projeto real grava
  `validation-REAL-0068.md`. O gate não está ligado no projeto real e reprovaria hoje.
- SDD chega a 76 KB, acima do limite de 65.536 caracteres do corpo da PR no GitHub.
- O molde de uma linha contraria "small já é o piso". A SDD curta precisa continuar
  passando em `validate_doc`, o que será testado na fase 0.
- SDD efêmera: apagar a entrada quebra `audit`, apagar o arquivo quebra `validate`, e
  `trace` corta a cadeia sem avisar. Proposta: status `archived`, arquivo em
  `docs/sdd/arquivo/` e leitura negada aos agentes.

## 4. Arquitetura

### Componentes

```text
fabrica-agentica/
  fabrica/                    núcleo: estados, gates, runners, publicação
  adapters/doc_traceability/  compilador SDD → contrato e chamadas ao framework
  contracts/                  JSON Schemas versionados
  agents/                     subagentes por papel, com ferramentas mínimas
  rules/                      roteamento e risco, em YAML
  moldes/                     padrões referenciados por SDD curta
  docker/                     imagens do agente, dos gates e do proxy de saída
  docs/rfc/ e docs/adr/       histórico de decisões da própria fábrica
  docs/licoes.md              lições de operação da fábrica
  docs/propostas-framework/   ajustes sugeridos, sem aplicar no framework
  .fabrica/                   não versionado: fabrica.db e runs/<run_id>/
```

**Orquestrador:** Python com SQLite chamando `claude -p` atrás da interface
`AgentRunner`. Mesma linguagem do material reaproveitado, sem serviço novo, com
retomada após queda. Temporal, n8n e similares são desproporcionais; Agent SDK como
orquestrador põe o loop em torno do modelo, contra a tese. `claude -p` usa os limites
do plano hoje, mas a mudança de cobrança anunciada só foi pausada. A fábrica recusa
iniciar com `ANTHROPIC_API_KEY` definida. `--bare` não serve, porque ignora o login OAuth.

### Máquina de estados

Fluxo de uma feature, sempre em branch própria:

```text
DETECTADO -> ENTRADA_OK -> ROTEADO -> CONTRATO_EMITIDO -> AGENTE_RODANDO
  -> RESPOSTA_VALIDA -> GATES_LOCAIS -> SEGURANCA -> VERIFY_SDD
  -> PR_PARA_DEVELOP -> CI_E2E -> MERGE_EM_DEVELOP -> MEDIDA
                                                 \-> REVERTIDA

reprovado, causa=implementacao, tentativa < 3 -> CORRECAO -> CONTRATO_EMITIDO
reprovado, causa=implementacao, tentativa = 3 -> PARADA_LIMITE
reprovado, causa=especificacao               -> PARADA_ESPECIFICACAO
reprovado, causa=ambiente                    -> PAUSADA_AMBIENTE
limite de uso do plano                       -> PAUSADA_LIMITE_USO
fora do contrato ou token reutilizado        -> RESPOSTA_RECUSADA
```

Fluxo de uma release, separado do fluxo da feature:

```text
MERGE_EM_DEVELOP -> BRANCH_RELEASE_CRIADA -> GATES_DA_RELEASE -> PR_PARA_MAIN
  -> AGUARDANDO_HUMANO -> MERGE_HUMANO_EM_MAIN -> TAG_CRIADA -> DEVELOP_ATUALIZADA
                     \-> RECUSADA_HUMANO
```

Cada transição é gravada na mesma transação que muda o estado. Depois de uma queda, a
fábrica retoma do último estado e nunca reutiliza contrato emitido.

Mudanças em relação ao desenho original:

- **Gates por custo:** contrato, escopo, build, lint, testes e segurança determinística
  antes do Verify, que é o gate caro.
- **PR antes do e2e:** o CI costuma disparar em `pull_request`, então a PR para `develop`
  abre antes do gate de e2e, e o merge só ocorre com todos os gates aprovados.
- **`causa=ambiente`:** falha de infraestrutura não consome tentativa.

### Contratos

Schemas em `contracts/`; instâncias em `.fabrica/runs/<run_id>/`. O token vem de
`secrets.token_urlsafe`, só o hash vai ao banco, e o consumo é
`UPDATE ... WHERE usado_em IS NULL`. Serve contra replay. **Não é autenticação**, porque
o agente o enxerga. A fábrica calcula o diff, roda os testes e confere a evidência, sem
confiar no que o agente declara.

### Gitflow

| Branch | Nasce de | Vai para | Quem faz o merge |
|---|---|---|---|
| `feature/<id>` | `develop` | `develop` | Fábrica, só com todos os gates aprovados |
| `release/X.Y.Z` | `develop` | `main` | **Só o humano** |
| `hotfix/X.Y.Z` | `main` | `main` e `develop` | **Só o humano** em `main` |

- Nenhuma alteração nasce direto em `develop`, `release/*` ou `main`.
- Depois de cada merge em `develop`, a fábrica abre sozinha a branch de release e a PR para
  `main`. O humano só aprova e faz o merge. Havendo PR de release aberta, ela é atualizada.
- O número da release é proposto pela fábrica a partir das mensagens de commit, e o
  humano confirma ao aprovar.
- Correção urgente segue o gitflow: `hotfix/X.Y.Z` nasce de `main`, vai a `main` só com
  aprovação humana e volta para `develop`.
- Depois do merge em `main`, a fábrica cria a tag `vX.Y.Z` e leva `main` de volta a `develop`.
- O agente não faz merge nem tem credencial; quem faz é o código da fábrica.
- **Limite:** o plano Free não oferece proteção de branch em repositório privado, então o
  GitHub não impede a credencial da fábrica de escrever em `main`. As barreiras são: o
  código só tem merge com destino `develop`, um teste prova a recusa de `main`, e um
  workflow alerta se `main` receber algo que não veio de `release/*`.
- O próprio repositório da fábrica segue este fluxo.

### Isolamento em Docker

Verificado no WSL: Docker 29.1.3, Compose 2.37.1, usuário no grupo `docker`. O processo da
fábrica fica no host e tem as credenciais. O agente fica no contêiner.

| Contêiner | Roda | Token do Claude | Rede |
|---|---|---|---|
| **agente** | `claude -p` e seus comandos | Sim | Só `api.anthropic.com`, via proxy com lista de domínios |
| **gates** | Build, lint, testes e sensor: código escrito pelo agente | Não | Nenhuma, além dos serviços do teste |
| **dependências** | Instalação preparada pela fábrica antes do agente | Não | Só o registro de pacotes |
| **proxy** | Saída com lista de domínios | Não | Internet |

- Contêineres sem root, com `--cap-drop=ALL`, `no-new-privileges`, sistema de arquivos
  somente leitura e limites de memória e processos.
- **Nunca montar** socket do Docker, `~/.ssh`, `~/.config/gh`, `~/.claude` ou `.env`.
- O agente recebe uma cópia do código num diretório por execução, sem remoto e sem hooks,
  destruído ao fim.
- O diff é extraído **dentro de um contêiner sem rede e sem token**: rodar `git` no host
  sobre um `.git` que o agente alterou executaria o que ele plantasse na configuração.
- A fábrica aplica o patch num clone limpo no host e publica com `core.hooksPath=/dev/null`.
- Diff em `.github/`, `.claude/`, `.husky/`, `_framework/` ou `deploy/` só passa se a SDD
  listar o arquivo e o risco for alto. Dependência nova também é risco alto.
- Gatilho só por PR mergeada por quem está na lista de permitidos. O front-matter sozinho
  pode ser forjado.

**Risco residual aceito:** o agente precisa do token do Claude dentro do contêiner, e a
documentação oficial avisa que contêiner não impede um projeto malicioso de extrair o que
está nele. Mitigação: token próprio da fábrica via `claude setup-token`, revogável, com
saída restrita ao domínio da API e ausente do contêiner de gates. O uso desse token em
`claude -p` num contêiner ainda precisa ser validado na Fase 0.

### Memória e histórico

A resposta é: as duas, separadas.

| Memória | Sobre o quê | Onde | Quem lê |
|---|---|---|---|
| **Da fábrica** | Decisões e lições da própria fábrica | Este repositório: `docs/rfc/`, `docs/adr/`, `docs/licoes.md` | Owner e quem desenvolve a fábrica. Agentes em execução, nunca |
| **Do projeto** | Contexto vivo, ADRs ativos, armadilhas, lições de PRs | Repositório do projeto, versionado | Só os agentes daquele projeto |
| **De execução** | Estados, tentativas, custo, tempo, evidência por execução | `.fabrica/fabrica.db`, local, separado por projeto | Owner, via status. Agentes recebem só o relatório da correção |

Regra: agente nunca vê dados de outro projeto nem a memória da fábrica.

**RFC e ADR da fábrica** têm formato próprio, inspirado no do framework, sem depender dos
scripts, do registry nem do repositório central:

- `docs/rfc/RFC-0001-<tema>.md` e `docs/adr/ADR-0001-<tema>.md`, com índice em `docs/README.md`.
- Status: `proposta`, `aceita`, `rejeitada`, `substituida`. ADR aceito é imutável;
  mudança gera novo ADR com `substitui`.
- Primeiros documentos, após aprovar este plano: RFC-0001 (este plano) e ADRs de
  orquestrador, Docker, gitflow, separação em relação ao framework e memória.

### Roteamento e agentes

| Sinal (regra em código) | Risco |
|---|---|
| Caminho protegido, migration, autenticação, dado pessoal, deploy | alto |
| `sizing` `large` ou `complex`, ou mais de um domínio | alto |
| `sizing` `medium` | médio |
| `sizing` `small` com molde | baixo |

Planejador e desenvolvedor são um agente só no MVP: `parallel_plan.py` e a seção de
tasks da SDD já cobrem o plano. Testes do desenvolvedor são cobrados pelo sensor de
discriminação. O testador separado entra na fase 2.

Notificação: toast do Windows via `powershell.exe`, comentário na PR e `.fabrica/status.log`.

## 5. Plano por fases

| Fase | Entregável | Critério de pronto |
|---|---|---|
| **0** | Repositório de teste, schemas, adaptador com compilador SDD → contrato, wrapper JSON do Verify, imagens Docker, RFC e ADRs iniciais | Contratos gerados nas SDDs de teste, com rejeição clara das inválidas; wrapper pega todas as falhas injetadas; `claude -p` funciona no contêiner com token próprio; teste de fuga sem ler credencial do host, sem rede fora da lista e sem push |
| **1** | SDD aprovada → desenvolvedor → gates → PR → e2e → merge em `develop` → notificação; loop de 3 tentativas; fluxo de release com aprovação humana | Tudo no repositório de teste: um caso de cada `causa`; gates aprovados no teste de mutação; merge em `main` pela fábrica recusado; processo morto no meio retoma; release completa até a tag |
| **2** | Planejador e testador, roteamento por risco, SDD efêmera, propostas ao framework | Testador barrado ao mexer em produção; `validate`, `trace` e `audit` verdes com SDDs arquivadas |
| **3** | Strands Decider vs. camada do MVP, painel local | Relatório de acerto, latência e calibração em casos próprios, em português, antes de adotar |
| **4** | Agente de interface e descoberta para projeto do zero | Do zero até SDD aprovada por humano; Teams e e-mail só com caminho gratuito |
| **Depois, por decisão do owner** | Entrada de projeto real: onboarding, contexto vivo, replay no histórico | Decisão sobre dados pessoais tomada antes; início por módulo e tarefas de baixo risco |

Ferramentas novas: `jsonschema`, `gitleaks` e `semgrep` no MVP, e um proxy de saída
open source em contêiner. MCP próprio só se o CLI não bastar.

## 6. Riscos

| Risco | Mitigação |
|---|---|
| Resposta fora do contrato ou repetida | Schema e token |
| Código que não compila ou quebra padrão | Build e lint |
| Mudança fora do escopo | Gate de escopo por lista de arquivos, depois Verify |
| Teste verde que não testa | Sensor de discriminação |
| Alucinação | Revisor em contexto isolado, evidência conferida |
| Quebra em fluxo real | E2E no CI |
| Segredo ou falha de segurança | `gitleaks`, `semgrep`, caminhos protegidos, revisão de segurança |
| Fuga de credencial, injeção de prompt | Contêineres sem credencial do host, rede por lista e teste de fuga. Token do Claude é risco residual aceito |
| Código ruim em `develop` sem revisão humana | Todos os gates antes do merge, reversão pela fábrica e aprovação humana na release |
| Merge indevido em `main` | Código sem esse caminho, teste de recusa e alerta por workflow. Sem proteção de branch no plano Free, resta risco residual |
| Framework muda e quebra o adaptador | SHA fixado por execução, teste de paridade, núcleo sem dependência dele |
| Estouro do plano | 3 tentativas, pausa em limite de uso, custo por etapa |

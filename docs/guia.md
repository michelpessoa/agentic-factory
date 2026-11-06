# Guia de uso

Do zero até a primeira release de um projeto, com o exemplo real do repositório público
[`fabrica-zero`](https://github.com/michelpessoa/fabrica-zero): uma biblioteca Python pequena de
conversão de temperatura, feita pela fábrica em 2026-11-05. Dá para ler lá a SDD aprovada
([PR #1](https://github.com/michelpessoa/fabrica-zero/pull/1)), o código com a evidência de
verificação ([PR #2](https://github.com/michelpessoa/fabrica-zero/pull/2)), o arquivamento da SDD
([PR #3](https://github.com/michelpessoa/fabrica-zero/pull/3)) e a release
([PR #4](https://github.com/michelpessoa/fabrica-zero/pull/4)).

## 1. Pré-requisitos

- Linux ou WSL2, com Docker e [uv](https://docs.astral.sh/uv/).
- [`gh`](https://cli.github.com/) logado numa conta com acesso de escrita ao repositório do projeto.
  Para projeto real, use a conta própria da fábrica (veja o [README](../README.md#conta-da-fábrica-no-github)).
- Assinatura do Claude que permita `claude setup-token`. Os agentes rodam com esse token, dentro de
  contêineres.
- Clone do [doc-traceability-framework](https://github.com/michelpessoa/doc-traceability-framework),
  que fornece os modelos de SDD e os validadores. A fábrica só lê esse clone.

## 2. Instalação

```sh
git clone https://github.com/michelpessoa/doc-traceability-framework ~/doc-traceability-framework
export FABRICA_FRAMEWORK=~/doc-traceability-framework   # sem a variável: ~/doc-traceability-central

uv sync
docker compose -f docker/compose.yml --profile imagens build
docker compose -f docker/compose.yml up -d proxy          # única saída de rede dos agentes
uv run python scripts/gerar_token.py                      # salva em ~/.config/fabrica/claude-token
uv run pytest                                             # cerca de 5 minutos
```

O token não deve aparecer em print, chat ou commit. O script salva sem passar pela área de
transferência.

## 3. Preparar o projeto

O repositório do projeto precisa de:

- branches `main` e `develop`;
- CI que rode os testes em toda PR. Sem checks, a fábrica não faz merge e pausa a execução em
  `CI_E2E`. O `fabrica-zero` nasceu sem CI e parou exatamente aí;
- proteção de `main`: só PR, com o CI verde. Em repositório privado, isso exige plano pago do
  GitHub; sem ela, use ao menos um workflow de alerta para escrita em `main` fora de release. Os
  workflows do exemplo estão em
  [`fabrica-zero/.github/workflows`](https://github.com/michelpessoa/fabrica-zero/tree/develop/.github/workflows).

Depois, copie [`projetos/exemplo.yaml`](../projetos/exemplo.yaml) para `projetos/<nome>.yaml`. O do
exemplo ficou assim:

```yaml
codigo: ZERO
repo: git@github.com:michelpessoa/fabrica-zero.git
github: michelpessoa/fabrica-zero
base: develop
principal: main
permitidos: [michelpessoa]
owner: "Michel Pessoa"
comandos:
  build: python3 -m compileall -q .
  testes: python3 -m unittest discover -s tests -v
```

`comandos` rodam nos gates, num contêiner sem rede, depois de cada implementação.

## 4. Descoberta: da ideia ao rascunho de SDD

```sh
uv run python -m fabrica descobrir zero "Biblioteca Python pequena para converter temperaturas entre Celsius, Fahrenheit e Kelvin"
```

O descobridor (Opus, sem ferramentas) faz até 5 perguntas por rodada. No exemplo, uma rodada bastou:

```text
1. Qual framework e comando de testes devo usar (por exemplo `pytest` ou `python -m unittest`) e qual a versão mínima do Python?
> unittest da biblioteca padrão, comando: python3 -m unittest discover -s tests -v. Python 3.11 ou maior.

2. Como deve ser a API pública: uma função por par, uma função genérica, ou outra forma? Informe o nome do módulo/pacote desejado.
> Uma função genérica converter(valor, de, para) com unidades 'C', 'F' e 'K', no pacote temperatura.

3. O que a biblioteca deve fazer com valores abaixo do zero absoluto: lançar exceção ou converter normalmente?
> Lançar ValueError quando o valor estiver abaixo do zero absoluto na unidade de origem.

4. O resultado deve ser arredondado ou retornado como float sem arredondamento?
> Retornar float sem arredondamento.

5. Como tratar entradas inválidas, como texto, None ou unidade desconhecida? Pode haver dependências externas?
> Unidade desconhecida: ValueError. Valor que não é int nem float (inclusive bool e None): TypeError. Só biblioteca padrão.

Rascunho SDD-ZERO-0001 em .fabrica/descobertas/<sessão>/SDD-ZERO-0001.md
Leia e, se estiver certo: uv run python -m fabrica aprovar <projeto> <sessão>
```

Ctrl-D no meio salva a conversa; `descobrir zero --retomar <sessão>` continua dela. O rascunho já
passou pelos validadores do framework. Cada requisito tem critério em EARS e um comando que prova o
critério, por exemplo:

```text
| 2 | RF02: valor abaixo do zero absoluto e unidade desconhecida lançam ValueError |
  `python3 -c "... r(ValueError,c,-300,'C','F'); r(ValueError,c,10,'X','C'); c(0,'K','C')"` | Exit 0 |
```

Custo do exemplo: US$ 0,30.

## 5. Aprovação: só você, no terminal

Leia o rascunho inteiro. Se estiver certo:

```sh
uv run python -m fabrica aprovar zero <sessão>
```

```text
SDD SDD-ZERO-0001: Pacote temperatura: converter(valor, de, para) entre Celsius, Fahrenheit e Kelvin
Digite o id da SDD para aprovar: SDD-ZERO-0001
publicando em develop: abre a PR e espera o CI; sem CI, são 2 minutos
aprovada e em develop pela PR #1
```

A fábrica guarda o sha256 do conteúdo aprovado. Se a SDD mudar depois, mesmo numa vírgula, ela é
recusada até nova aprovação. SDD escrita à mão também passa por aqui:
`fabrica aprovar <projeto> docs/sdd/SDD-X-0001.md`.

## 6. Pipeline: da SDD à PR de release

```sh
uv run python -m fabrica iniciar zero docs/sdd/SDD-ZERO-0001.md
# ou, para disparar sozinho a cada SDD aprovada:
uv run python -m fabrica vigiar zero --intervalo 300
```

O que aconteceu no exemplo, resumido de `fabrica historico <run_id>`:

```text
ENTRADA_OK -> ROTEADO: risco medio (decisor, confiança 0.9)
ROTEADO -> PLANEJANDO: SDD sem tarefas e risco não baixo
PLANEJANDO -> CONTRATO_EMITIDO: 2 tarefas
AGENTE_RODANDO -> RESPOSTA_VALIDA: Criei o pacote temperatura ... a suíte rodou 9 testes, todos OK.
TESTADOR_RODANDO -> GATES_LOCAIS: testador concluiu
GATES_LOCAIS -> CORRECAO: gate escopo: fora da lista da SDD: tests/test_converter_extra.py
AGENTE_RODANDO -> RESPOSTA_VALIDA: Corrigi o gate de escopo. Movi os testes ... para tests/test_converter.py
GATES_LOCAIS -> SEGURANCA: gates aprovados
VERIFY_SDD -> PR_PARA_DEVELOP: verificação aprovada
PR_PARA_DEVELOP -> CI_E2E: PR #2
CI_E2E -> MERGE_EM_DEVELOP: CI aprovado
ARQUIVAMENTO -> MEDIDA: PR #2 em develop. Release 0.1.0 aguarda aprovação: PR #4
```

- O risco decide o modelo: médio foi para o Sonnet.
- O gate de escopo barrou um arquivo que a SDD não listava, e a correção voltou ao agente com o motivo.
- O verificador independente só aprovou depois de quebrar o código de propósito e ver cada teste
  falhar.

Custo do exemplo: US$ 0,55.

## 7. Release: o merge em `main` é seu

A fábrica abre a PR de release, mas não faz merge em `main`. Revise e faça o merge no GitHub. Depois:

```sh
uv run python -m fabrica pos-release zero 0.1.0   # cria a tag v0.1.0 e atualiza develop
```

## 8. Quando a execução para

| Estado | O que quer dizer | O que fazer |
|---|---|---|
| `PAUSADA_DECISAO` | O decisor de risco ficou abaixo da confiança mínima | `fabrica decidir <projeto> <run_id> <baixo\|medio\|alto>` |
| `PAUSADA_AMBIENTE` | Falha de ambiente: Docker, rede, CI ausente ou sem resultado | Corrija o ambiente e rode `fabrica retomar <projeto> <run_id>` |
| `PAUSADA_LIMITE_USO` | O plano do Claude atingiu o limite de uso | Espere o limite renovar e rode `fabrica retomar <projeto> <run_id>` |
| `PARADA_LIMITE` | As tentativas de correção acabaram e os gates ou a revisão seguem reprovando | Leia o relatório em `fabrica historico <run_id>`; em geral a SDD precisa mudar |
| `PARADA_ESPECIFICACAO` | A SDD não basta para implementar, por exemplo sizing errado | Corrija a SDD, aprove de novo e rode `iniciar` |
| `RECUSADA_ENTRADA` | SDD sem aprovação ou com conteúdo diferente do aprovado | `fabrica aprovar` |

`fabrica status` lista as execuções, e `fabrica painel` abre um painel só leitura em
`http://127.0.0.1:8765`. Avisos também vão para `.fabrica/status.log`.

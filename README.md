# Fábrica Agêntica

Sistema local que coloca agentes de IA no fluxo de desenvolvimento como membros do
squad, com as decisões de julgamento nas mãos de humanos.

**O agente só aparece no meio.** A fábrica decide e valida. O agente lê, edita e
responde. O contrato liga os dois.

- **Como usar, com exemplo completo: [docs/guia.md](docs/guia.md)**
- Plano e arquitetura: [RFC-0001](docs/rfc/RFC-0001-fabrica-agentica.md)
- Framework de documentos usado pela fábrica:
  [doc-traceability-framework](https://github.com/michelpessoa/doc-traceability-framework), versão 2.8.0
- A fábrica como executora do fluxo do framework, com o central como fonte das decisões:
  [ADR-0012](docs/adr/ADR-0012-executora-do-fluxo-do-framework.md)
- Decisões e lições: [docs/README.md](docs/README.md)
- Fluxo de branches: `feature/*` → `develop` → `release/X.Y.Z` → `main`, com aprovação
  humana para `main`.

## Repositórios

A fábrica existe em dois repositórios:

| | Privado: `michelpessoa/fabrica-agentica` | Público: `michelpessoa/agentic-factory` |
|---|---|---|
| Para quê | Trabalho do owner: features, releases, projetos dele | Compartilhar: quem quiser instala e usa |
| Conteúdo | Tudo, com histórico e PRs | Cópia de uma versão já lançada, sem histórico |
| Projetos em `projetos/` | Os do owner, como `cobaia` e `zero` | Só `exemplo.yaml`, para copiar |
| Projetos reais citados nos documentos | Pelo nome | Generalizados como "projeto real do owner" |
| Mudanças | `feature/*` → `develop` → `release/X.Y.Z` → `main` | Chegam só por publicação de versão |
| Versão | `develop` à frente da última release | A última release publicada |

Os repositórios de teste são públicos e só têm código ou documento fictício, feito pela fábrica:

- [`fabrica-zero`](https://github.com/michelpessoa/fabrica-zero): o exemplo do guia, nascido vazio;
- [`fabrica-cobaia`](https://github.com/michelpessoa/fabrica-cobaia): os casos de defeito plantado;
- [`fabrica-central-teste`](https://github.com/michelpessoa/fabrica-central-teste): um central de
  teste, com o `_framework/` do kit e documentos fictícios, onde a fábrica abre SPECs e compila SDDs.

Neles, `main` só aceita PR com CI verde. Os testes marcados `docker` e `claude`,
`scripts/e2e_cobaia.py` e `scripts/avaliar_revisor.py` precisam de escrita num repositório assim:
quem usa a cópia pública cria o seu.

Para publicar uma versão, depois do merge da release em `main` e da pós-release. O script fica só
no privado, porque lista os nomes que esconde:

```sh
uv run python scripts/exportar_publico.py vX.Y.Z /tmp/fabrica-publica   # recusa se sobrar termo privado
git clone git@github.com:michelpessoa/agentic-factory.git /tmp/agentic-factory
cd /tmp/agentic-factory
git rm -q -r . && cp -a /tmp/fabrica-publica/. . && git add -A
git commit -m "Fábrica Agêntica X.Y.Z" && git tag -a vX.Y.Z -m "Release X.Y.Z"
git push origin main vX.Y.Z
```

No público, cada versão é um commit sobre a anterior, e `main` recusa force-push. Sugestões
recebidas lá, por issue ou PR, entram no privado como `feature/*`.

## Preparação

```sh
git clone https://github.com/michelpessoa/doc-traceability-framework ~/doc-traceability-framework
export FABRICA_FRAMEWORK=~/doc-traceability-framework   # sem a variável: ~/doc-traceability-central
uv sync
docker compose -f docker/compose.yml --profile imagens build
docker compose -f docker/compose.yml up -d proxy
```

Cada projeto declara em `projetos/<nome>.yaml` a versão do framework que exige (`framework: "2.8.0"`)
e o caminho do clone do central (`central:`), copiados de [`projetos/exemplo.yaml`](projetos/exemplo.yaml).
Se o kit ou o `_framework/` do central estiverem em outra versão, a fábrica recusa iniciar, descobrir e
vigiar. O CI testa contra o commit fixado em `.github/workflows/ci.yml`, com `fabrica-cobaia` e
`fabrica-central-teste` clonados; ao subir a versão, troque esse commit e os projetos juntos.

Token próprio da fábrica, gerado uma vez. O script salva sem passar pela área de
transferência, e o token não deve ir para print, chat ou commit:

```sh
uv run python scripts/gerar_token.py
```

## Operação

```sh
uv run python -m fabrica descobrir <projeto> "ideia"                     # conversa até o rascunho de SDD ou SPEC
uv run python -m fabrica descobrir <projeto> --origem SPEC-X-0001        # SDD compilada de SPEC/ADR approved do central
uv run python -m fabrica central conferir <projeto> <id>                 # confere a review e faz o merge da PR do central
uv run python -m fabrica aprovar <projeto> <sessao|caminho da SDD>       # só você, no terminal
uv run python -m fabrica iniciar <projeto> docs/sdd/SDD-X-0001.md        # do início até a PR de release
uv run python -m fabrica status                                          # todas as execuções
uv run python -m fabrica historico <run_id>                              # transições e dados de uma execução
uv run python -m fabrica retomar <projeto> <run_id>                      # depois de pausa ou queda
uv run python -m fabrica decidir <projeto> <run_id> <baixo|medio|alto>   # resposta a uma decisão de baixa confiança
uv run python -m fabrica vigiar <projeto> --intervalo 300                # PRs e SPECs do central, e SDDs aprovadas na base
uv run python -m fabrica vigiar <projeto> --uma-vez --sem-central        # um ciclo, só as SDDs da base
uv run python -m fabrica release <projeto>                               # abre ou atualiza a PR de release
uv run python -m fabrica pos-release <projeto> 0.1.0                     # tag e develop, depois do seu merge
uv run python -m fabrica painel                                          # painel só leitura em http://127.0.0.1:8765
```

Avisos ficam em `.fabrica/status.log`, com toast do Windows, e vão por e-mail e Teams se configurados
([guia](docs/guia.md#avisos-por-e-mail-e-teams)). Cada projeto tem um arquivo em `projetos/`.

## Quem aprova o quê

A aprovação depende do tamanho da mudança, pelo sizing do framework
([ADR-0012](docs/adr/ADR-0012-executora-do-fluxo-do-framework.md)):

- **`small`, sem SPEC:** a descoberta conversa até o rascunho de SDD, e você aprova no terminal com
  `fabrica aprovar`. A fábrica guarda o sha256 do conteúdo e recusa qualquer mudança depois.
- **`medium` ou maior:** a descoberta abre a SPEC (e a RFC e a ADR, em `large` ou `complex`) numa PR
  do central, com a etiqueta `fabrica`. Você aprova com uma review "Aprovado" na PR. A fábrica confere
  o revisor e o commit revisado, grava `approved_by` e faz o merge.
- **SDD compilada de SPEC aprovada:** o vigia vê a SPEC aprovada em `main` do central, compila a SDD e
  a aprova por política (`approved_by.kind: policy`, presa ao hash). Ela entra na base por PR e dispara
  o pipeline sem passar pelo terminal.
- **Release para `main`:** sempre sua.

Na verificação, a SDD com `source_docs` passa também pelo passo 0 do `verify-sdd`: o
`check_source_docs.py` no host e a leitura da origem pelo revisor.

## Conta da fábrica no GitHub

A fábrica age com o login de quem roda o `gh` no computador. Por isso ela precisa de uma conta
própria, e não a do owner, por três motivos:

- **Autoria.** Com o mesmo login, o merge da fábrica em `develop` e o do owner são indistinguíveis, e
  a lista `permitidos` do projeto não separa ninguém. A aprovação presa ao hash
  ([ADR-0010](docs/adr/ADR-0010-descoberta-e-aprovacao-no-terminal.md)) prova que alguém aprovou neste
  computador, não quem.
- **Alcance.** O token pessoal com escopo `repo` alcança todos os repositórios do owner, não só os
  projetos da fábrica.
- **`main`.** Repositório privado no plano Free não tem proteção de branch. O merge em `main` é
  barrado só pelo código da fábrica (`PublicacaoRecusada`), e o workflow `alerta-main` apenas avisa
  depois.

Toda PR aberta pela fábrica, no projeto e no central, leva a etiqueta `fabrica`, criada no
repositório na primeira PR. Ela serve para filtrar, não prova autoria: qualquer pessoa com escrita no
repositório põe ou tira a etiqueta. Para conferir a etiqueta de uma PR, use
`gh pr view <n> --json labels`.

A conta própria já existe para os repositórios de teste
([ADR-0012](docs/adr/ADR-0012-executora-do-fluxo-do-framework.md)): é colaboradora só deles, não deste
repositório nem do central real, e usa token *classic* até o ensaio final. Antes do primeiro projeto
real, central e projetos vão para uma organização, e o token passa a *fine-grained*.

Para montar a sua, sem colar token em chat:

1. Cria uma conta GitHub gratuita para a fábrica, com outro e-mail e 2FA.
2. Convida essa conta como colaboradora só nos repositórios dos projetos.
3. Logado nela, gera um token *fine-grained* limitado a esses repositórios, com permissão de
   *contents* e *pull requests*, e salva em `~/.config/fabrica/`.
4. Recomendado: GitHub Pro na conta do owner, para ter proteção de branch em repositório privado.
   `main` passa a exigir PR aprovada pelo owner e `develop` passa a exigir CI verde. Sem isso, a
   autoria fica separada, mas `main` continua dependendo da trava da fábrica.

Depois, a fábrica passa a usar esse token no lugar do `gh` do owner, `permitidos` passa a conferir o
autor real, e um teste no `fabrica-zero` confirma que o GitHub recusa o merge em `main` feito pela
conta da fábrica.

Todo projeto também precisa de CI nas PRs antes do primeiro pipeline: sem checks, a execução pausa
em `CI_E2E`.

## Testes

```sh
uv run pytest                              # unidade
uv run pytest -m docker                    # teste de fuga do contêiner
uv run pytest -m claude                    # claude -p no contêiner; consome o limite do plano
uv run python scripts/avaliar_revisor.py   # revisor contra os defeitos plantados
uv run python scripts/selftest.py          # enfraquece cada gate e exige que o teste falhe
uv run python scripts/avaliar_decisor.py relatorio   # tabelas da comparação de decisores (ADR-0008)
uv run python scripts/e2e_cobaia.py implementacao   # defeito plantado, com revisão e correção reais
```

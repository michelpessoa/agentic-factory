# Fábrica Agêntica

Sistema local que coloca agentes de IA no fluxo de desenvolvimento como membros do
squad, com as decisões de julgamento nas mãos de humanos.

**O agente só aparece no meio.** A fábrica decide e valida. O agente lê, edita e
responde. O contrato liga os dois.

- **Como usar, com exemplo completo: [docs/guia.md](docs/guia.md)**
- Plano e arquitetura: [RFC-0001](docs/rfc/RFC-0001-fabrica-agentica.md)
- Framework de documentos usado pela fábrica:
  [doc-traceability-framework](https://github.com/michelpessoa/doc-traceability-framework)
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

Os repositórios de teste são públicos e só têm código fictício, feito pela fábrica:
[`fabrica-zero`](https://github.com/michelpessoa/fabrica-zero), o exemplo do guia, nascido vazio, e
[`fabrica-cobaia`](https://github.com/michelpessoa/fabrica-cobaia), com os casos de defeito plantado.
Neles, `main` só aceita PR com CI verde. Os testes marcados `docker` e `claude`,
`scripts/e2e_cobaia.py` e `scripts/avaliar_revisor.py` precisam de escrita num repositório assim:
quem usa a cópia pública cria o seu.

Para publicar uma versão, depois do merge da release em `main` e da pós-release. O script fica só
no privado, porque lista os nomes que esconde:

```sh
uv run python scripts/exportar_publico.py v0.6.0 /tmp/fabrica-publica   # recusa se sobrar termo privado
cd /tmp/fabrica-publica
git init -b main && git add . && git commit -m "Fábrica Agêntica 0.6.0"
git push --force git@github.com:michelpessoa/agentic-factory.git main
```

O push com `--force` vale só para o repositório público, que não tem histórico próprio. Sugestões
recebidas lá, por issue ou PR, entram no privado como `feature/*`.

## Preparação

```sh
git clone https://github.com/michelpessoa/doc-traceability-framework ~/doc-traceability-framework
export FABRICA_FRAMEWORK=~/doc-traceability-framework   # sem a variável: ~/doc-traceability-central
uv sync
docker compose -f docker/compose.yml --profile imagens build
docker compose -f docker/compose.yml up -d proxy
```

Token próprio da fábrica, gerado uma vez. O script salva sem passar pela área de
transferência, e o token não deve ir para print, chat ou commit:

```sh
uv run python scripts/gerar_token.py
```

## Operação

```sh
uv run python -m fabrica descobrir <projeto> "ideia"                     # conversa até o rascunho de SDD
uv run python -m fabrica aprovar <projeto> <sessao|caminho da SDD>       # só você, no terminal
uv run python -m fabrica iniciar <projeto> docs/sdd/SDD-X-0001.md        # do início até a PR de release
uv run python -m fabrica status                                          # todas as execuções
uv run python -m fabrica historico <run_id>                              # transições e dados de uma execução
uv run python -m fabrica retomar <projeto> <run_id>                      # depois de pausa ou queda
uv run python -m fabrica decidir <projeto> <run_id> <baixo|medio|alto>   # resposta a uma decisão de baixa confiança
uv run python -m fabrica vigiar <projeto> --intervalo 300                # dispara quando uma SDD é aprovada
uv run python -m fabrica release <projeto>                               # abre ou atualiza a PR de release
uv run python -m fabrica pos-release <projeto> 0.1.0                     # tag e develop, depois do seu merge
uv run python -m fabrica painel                                          # painel só leitura em http://127.0.0.1:8765
```

Avisos ficam em `.fabrica/status.log`, com toast do Windows. Cada projeto tem um arquivo em `projetos/`.
Toda SDD precisa de `fabrica aprovar`: a fábrica só aceita o conteúdo exato que você aprovou.

## Conta da fábrica no GitHub

Hoje a fábrica age com o login de quem roda o `gh` no computador. Antes do primeiro projeto real,
ela precisa de uma conta própria, por três motivos:

- **Autoria.** Com o mesmo login, o merge da fábrica em `develop` e o do owner são indistinguíveis, e
  a lista `permitidos` do projeto não separa ninguém. A aprovação presa ao hash
  ([ADR-0010](docs/adr/ADR-0010-descoberta-e-aprovacao-no-terminal.md)) prova que alguém aprovou neste
  computador, não quem.
- **Alcance.** O token pessoal com escopo `repo` alcança todos os repositórios do owner, não só os
  projetos da fábrica.
- **`main`.** Repositório privado no plano Free não tem proteção de branch. O merge em `main` é
  barrado só pelo código da fábrica (`PublicacaoRecusada`), e o workflow `alerta-main` apenas avisa
  depois.

O que o owner faz, sem colar token em chat:

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

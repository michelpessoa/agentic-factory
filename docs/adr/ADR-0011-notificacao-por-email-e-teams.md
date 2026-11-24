---
id: ADR-0011
status: aceita
data: 2026-11-05
---

# Notificação por e-mail e Teams, opcional e por caminho gratuito

## Contexto

A RFC-0001 previa Teams e e-mail na Fase 4, só por caminho gratuito. A ADR-0010 os deixou fora por decisão do
owner, e os avisos ficaram no `.fabrica/status.log` e no toast do Windows, que só alcançam quem está no
computador. O owner pediu os dois canais depois da Fase 4. Esta ADR muda só esse trecho da ADR-0010.

## Decisão

A fábrica avisa por e-mail e por Teams quando uma execução para à espera do humano, nos mesmos pontos em que
grava o `status.log`. Os dois canais são opcionais e vêm de `~/.config/fabrica/notificacao.toml`, fora do
repositório. Sem o arquivo, nada muda.

- **E-mail:** SMTP com STARTTLS antes do login, por exemplo Gmail com senha de app, sem custo.
- **Teams:** webhook do app Workflows, que recebe um Adaptive Card. Só `https`.

O arquivo guarda segredo (senha SMTP e URL do webhook, que vale como credencial) e só é lido com permissão
restrita ao dono. Fora disso, ou com campo faltando, o comando recusa antes de começar. Falha de envio fica no
`status.log` com o tipo do erro, sem a mensagem dele, que pode conter a URL, e não para a execução.

## Alternativas

Serviço de notificação de terceiro (ntfy, Pushover): mais um serviço e mais uma conta. Envio de dentro dos
contêineres: abriria o proxy para domínios além de `api.anthropic.com`. Os avisos saem do orquestrador, no
host.

## Consequências

O aviso sai do computador: nome da SDD, estado e até 300 caracteres do motivo vão para o provedor de e-mail e
para a Microsoft. Em projeto com dado sensível, o motivo pode trazer trecho dele, e o canal é decisão do owner
por projeto. O webhook do Workflows depende do plano do Teams do owner, e a entrega real só se confirma com a
configuração dele. A senha fica em texto no disco, com o mesmo risco aceito para o token do Claude (ADR-0002).

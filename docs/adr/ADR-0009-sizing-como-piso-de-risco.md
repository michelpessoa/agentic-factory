---
id: ADR-0009
status: aceita
data: 2026-11-05
substitui: ADR-0007
---

# Sizing como piso de risco, com regra decidindo só o risco alto

## Contexto

Pela ADR-0007, `sizing: small` definia risco baixo sem consultar ninguém, e os sinais de risco olhavam só título
e arquivos, sem termos de dinheiro e com `auth`, que não casa com "autenticação". "Corrigir autenticação de
usuários" e "Estorno de pagamento" saíam como risco baixo, sem testador nem revisão de segurança.

## Decisão

Regra em código só decide risco alto: caminho protegido, sinal no título, resumo, requisitos ou arquivos, ou
`sizing` `large` ou `complex`. Sinais são procurados sem acento. Fora disso, `decidir_risco` chama o `Decisor`,
um agente Haiku sem ferramentas e sem acesso ao código. O `sizing` vira piso: `medium` não fica abaixo de médio,
e o decisor pode subir o risco, nunca descer. Continuam da ADR-0007: confiança abaixo de 0,8 ou resposta inválida
pausa em `PAUSADA_DECISAO` e espera o humano; risco alto recebe revisão de segurança com Opus; risco médio e alto
passam pelo testador; o planejador só entra se a SDD não trouxer tarefas e o risco não for baixo.

## Alternativas

Só ampliar a lista de palavras: nos casos da Fase 3, ela ainda perde "agir como outro usuário" e "enviar lista
de clientes para parceiro", que o Haiku classificou como alto.

## Consequências

Quase toda SDD agora faz uma chamada ao Haiku, por cerca de US$ 0,0006 e 3 s. Mais SDDs vão pausar esperando o
humano: nos casos da Fase 3, 5 de 56 ficaram abaixo de 0,8, e tarefas simples reais ainda não foram medidas. Falso
alarme de palavra custa revisão a mais: "Produção não muda" já conta como sinal. Nenhuma lista prova que uma
tarefa é segura, e o risco baixo continua dependendo do decisor.

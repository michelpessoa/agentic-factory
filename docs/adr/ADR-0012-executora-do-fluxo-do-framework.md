---
id: ADR-0012
status: aceita
data: 2026-11-16
substitui: null
---

# Fábrica como executora do fluxo do framework, com o central como fonte das decisões

Emenda a ADR-0004 e a ADR-0010. Depende da RFC-DTF-0009 do framework, em `docs/DTF/01-rfc/` do
`doc-traceability-central`, aprovada pelo owner em 2026-11-16.

## Contexto

A fábrica usa do framework só três scripts, lidos do `HEAD` de `~/doc-traceability-central`, sem versão
fixada. Nunca lê nem escreve `docs/{PROJECT_CODE}/` do central: `check_source_docs.py` nunca roda, porque
`validar_entrada` é chamada sem `docs_central`, e as SDDs da descoberta saem com `source_docs: []`. Os
testes que chamam os scripts reais são pulados no CI, que não faz checkout do framework.

O owner decidiu em 2026-11-16 aprovar só a SPEC em mudança `medium` ou maior, a RFC e a ADR em mudança
`large` ou `complex`, e a release para `main`. A SDD e a decisão de risco com baixa confiança deixam de esperar por ele.
Os repositórios continuam separados, e tudo roda localmente antes da nuvem.

## Decisão

- **Versão do framework fixada por projeto.** `projetos/<nome>.yaml` declara a tag do framework e o caminho
  do central. A fábrica recusa iniciar se a versão do clone não for a declarada. O CI faz checkout do kit
  público nessa tag, e os testes marcados com `skipif` passam a rodar.
- **O adaptador passa a conhecer o contrato do executor** (`executor_contract` da RFC-DTF-0009) e o central.
  O núcleo segue sem conhecer o framework: a leitura e a escrita no central ficam atrás de uma interface nova
  do adaptador, ao lado de `FonteDeContrato`.
- **Leitura do central:** sizing, gates e ciclo de status vêm do `workflow-rules.yaml` na versão fixada; SPEC e
  ADR `approved` entram como `source_docs`; `check_source_docs.py` roda na entrada. As regras de risco da
  ADR-0009 continuam por cima, como piso.
- **Escrita no central só por PR**, nunca em `main`: rascunhos de SPEC e RFC na descoberta, `approved_by` com
  `kind: policy` na SDD, status `implemented` da origem, `LESSONS.md` e `entrega` no registry.
- **Aprovação da SDD por política**, no lugar de `fabrica aprovar` (emenda à ADR-0010): validadores do
  framework verdes e passo 0 do Verify aprovado. A aprovação continua presa ao hash do conteúdo.
- **Baixa confiança sobe o risco**, em vez de pausar em `PAUSADA_DECISAO`.
- **Release dupla:** a PR de release do projeto e a PR do central abrem juntas; a do central só é mergeada
  depois do merge da release em `main`.
- **Vigia do central:** SPEC aprovada por humano dispara a compilação da SDD e o pipeline, por consulta
  periódica.

## Alternativas

- **Manter a ADR-0004 como está:** a fábrica não consegue registrar no central quem aprovou, e a integração
  segue manual nos dois lados.
- **Unificar com o central:** o token da fábrica alcançaria os dados de todos os projetos. Avaliada e
  rejeitada na RFC-DTF-0009.
- **Hermes Agent como orquestrador:** põe o loop em torno do modelo, contra a RFC-0001. Se entrar, é só na
  entrada de demanda e na consulta de status.

## Consequências

O adaptador cresce e passa a ser boa parte da fábrica. Uma mudança no `executor_contract` do framework pede
versão nova da fábrica. Uma SDD fiel na forma e errada no conteúdo só aparece na release, que precisa mostrar
SPEC, SDD e resultado do Verify lado a lado.

Decidido pelo owner em 2026-11-16, conforme a RFC-DTF-0009:

- **Conta própria:** `fabricaagenticamichel` passa a ser a autora das PRs e o login do token. `permitidos`
  passa a conferir o autor real. Ela é colaboradora só dos repositórios de teste; não entra neste
  repositório, para não alterar os próprios gates, nem no central real antes do ensaio final.
- **Token até o ensaio final:** *classic* com escopo `repo`, porque o *fine-grained* não alcança repositório
  de outra conta pessoal. O limite é a lista de colaboradores. Antes do ensaio final, o central e os
  repositórios de projeto vão para uma organização, e o token passa a *fine-grained*.
- **Aprovação de SPEC e RFC/ADR por review:** o owner dá "Approve" na PR do central; a fábrica confere o
  login do revisor e o commit revisado, faz o merge e grava `approved_by`.
- **Testes híbridos:** as fases de escrita rodam contra um central de teste com dados fictícios; o central
  real recebe só um ensaio final antes do primeiro projeto.

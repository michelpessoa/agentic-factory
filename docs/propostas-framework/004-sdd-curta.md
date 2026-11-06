# 004: SDD curta com molde

## Problema

O sizing decide quantos documentos existem, mas a SDD `small` ainda repete o padrão no próprio corpo.
Tarefa rotineira, como um CRUD a mais, gera SDD longa sem informação nova.

## O que a fábrica já faz

Aceita `molde: <nome>` no front-matter, lê `docs/fabrica/moldes/<nome>.md` do projeto e entrega o texto no
contrato. `validate_doc.py` já tolera o campo. A SDD continua precisando das seções do template, com
requisito, critérios e arquivos: curta não significa sem critério verificável.

## Proposta

Declarar `molde` em `frontmatter_schema` como opcional, só em SDD `small`, e registrar um exemplo no
template. Nenhum gate muda: o piso continua sendo a SDD com critérios executáveis.

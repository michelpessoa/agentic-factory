# 001: SDD efêmera

## Problema

Depois de `implemented`, a SDD fica em `docs/sdd/` e continua sendo lida e encontrada por agentes. No
projeto real são 68 SDDs, com média de 32 KB.

## O que a fábrica já faz, sem mudar o framework

Depois do merge, uma PR própria move a SDD e o relatório para `docs/sdd/arquivo/` e acrescenta ao
registry `path` novo e `entrega: {pr, data, resultado}`. O status continua `implemented`. Agentes recebem
uma cópia sem essa pasta.

Testado com os scripts reais (`tests/test_arquivo.py`):

| Script | Resultado com SDD arquivada |
|---|---|
| `registry_tools.py validate` | Verde. O campo `entrega` é tolerado e o `path` novo resolve |
| `registry_tools.py trace` | Verde. A entrada continua no registry |
| `registry_tools.py audit` | Verde. O id continua conhecido, sem referência quebrada |
| `validate_state.py` | Verde na SDD arquivada |

**Arquivar em PR separada é necessário:** o gate de CI observa `docs/sdd/SDD-*.md`. Mover o arquivo na
mesma PR que muda o status esconderia a SDD do gate.

## Proposta

1. Declarar `docs/sdd/arquivo/` em `repository_topology`, como local válido de SDD entregue.
2. Declarar `entrega` em `registry.entry_fields`, hoje tolerado, mas não documentado.
3. Fazer `registry_tools.py trace` imprimir a `entrega` quando existir.

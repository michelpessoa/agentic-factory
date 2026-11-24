# Registry — Projeto FAB

_Gerado automaticamente a partir de `registry.yaml`. Não editar manualmente. Framework v2.8.0._

Repositório de código: https://github.com/michelpessoa/fabrica-agentica

Total de documentos: **12**


## SDD (12)

| ID | Título | Status | Owner | Atualizado | Relacionados |
|---|---|---|---|---|---|
| `SDD-FAB-0001` | Leitura do central: framework fixado em 2.5.0, caminho do central por projeto e validadores lidos pelo --json do executor_contract | implemented | Michel Pessoa | 2026-11-17 | — |
| `SDD-FAB-0002` | Regras do framework na entrada e origem do central na descoberta: sizing, documentos por nível, ciclo de status e --origem | implemented | Michel Pessoa | 2026-11-17 | SDD-FAB-0001 |
| `SDD-FAB-0003` | Escrita no central: rascunho de SPEC ou RFC por PR na descoberta e aprovação pela review, com approved_by gravado antes do merge | implemented | Michel Pessoa | 2026-11-19 | SDD-FAB-0001, SDD-FAB-0002 |
| `SDD-FAB-0004` | Progresso da descoberta no terminal: em que etapa do fluxo a sessão está e por quê, por eventos do núcleo e texto do CLI | implemented | Michel Pessoa | 2026-11-19 | SDD-FAB-0003 |
| `SDD-FAB-0005` | SDD enxuta na fábrica: descoberta com origem escreve requisitos por referência em projeto sob 2.7.0, compilador lê a Parte 2 e o EARS da SPEC no central, e framework 2.7.0 | implemented | Michel Pessoa | 2026-11-21 | SDD-FAB-0002, SDD-FAB-0003 |
| `SDD-FAB-0006` | SPEC da descoberta com as linhas '# Parte 1' e '# Parte 2' do template, para o compilador da SDD enxuta ler o desenho | implemented | Michel Pessoa | 2026-11-21 | SDD-FAB-0003, SDD-FAB-0005 |
| `SDD-FAB-0007` | Tabela de Requisitos funcionais da SPEC com o cabeçalho do template, para o EARS do kit ler o critério na 3ª coluna | implemented | Michel Pessoa | 2026-11-21 | SDD-FAB-0003, SDD-FAB-0006 |
| `SDD-FAB-0008` | Registry do projeto com documents em fluxo: a redação passa o documents para bloco antes de acrescentar a SDD nova, para o registry seguir YAML válido | implemented | Michel Pessoa | 2026-11-21 | SDD-FAB-0005 |
| `SDD-FAB-0009` | Vigia do central na fábrica: PR de documento conferida sozinha, SPEC aprovada compilada em SDD aprovada por política, entrada pela política e framework 2.8.0 | implemented | Michel Pessoa | 2026-11-21 | SDD-FAB-0005, SDD-FAB-0006, SDD-FAB-0007, SDD-FAB-0008 |
| `SDD-FAB-0010` | Correções do vigia do central depois da verificação e do A13 da SDD-FAB-0009: sensor do hash com o adaptador real, número da PR no aviso, etiqueta na PR do central, merge da fábrica na entrada por política e vigia que não cai sem a base | implemented | Michel Pessoa | 2026-11-23 | SDD-FAB-0009 |
| `SDD-FAB-0011` | Correções pequenas do vigia e da descoberta: número da PR da base no aviso com teste que discrimina e branch da PR da base sem o prefixo duplicado | approved | Michel Pessoa | 2026-11-24 | SDD-FAB-0009, SDD-FAB-0010 |
| `SDD-FAB-0012` | Passo 0 do verify-sdd na verificação da fábrica: SDD enxuta com source_docs chega a implemented com a linha "Fidelidade à origem" | approved | Michel Pessoa | 2026-11-24 | SDD-FAB-0009, SDD-FAB-0011 |

## Documentos originados

Nenhum documento com pai declarado.

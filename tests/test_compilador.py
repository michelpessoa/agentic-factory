import pytest

from adapters.doc_traceability.compilador import SddInvalida, compilar_sdd

SDD = """---
id: SDD-X-0001
title: "Retirada"
status: approved
sizing: small
source_docs: []
---

# Retirada

## Resumo executivo

Permite retirar.

## Requisitos consolidados

| RF-ID | Requisito | Critério de aceite (EARS) | Arquivos |
|---|---|---|---|
| RF01 | Retirada | Quando X, deve Y. | `a/b.py`, `tests/t.py` |

## Decomposição em tasks

| # | Task | RF(s) de origem | Arquivos tocados | Depende de (#) |
|---|---|---|---|---|
| 1 | Fazer | RF01 | `a/c.py` | |

## Critérios de aceite / definição de pronto

| # | Critério (origem: RF-ID / contrato) | Comando de verificação | Resultado esperado | Perfil esperado |
|---|---|---|---|---|
| 1 | RF01 | `pytest tests/t.py \\| tail -1` | exit 0 | automatizado |
| 2 | Revisão de texto | n/a | legível | manual |

## Instruções específicas para a IA implementadora

Toque só nos listados.

```text
## Não é seção
```
"""


def compilar(tmp_path, texto=SDD):
    caminho = tmp_path / "SDD.md"
    caminho.write_text(texto, encoding="utf-8")
    return compilar_sdd(caminho)


def problemas(tmp_path, texto):
    with pytest.raises(SddInvalida) as erro:
        compilar(tmp_path, texto)
    return erro.value.problemas


def test_compila_os_campos_do_contrato(tmp_path):
    entrada = compilar(tmp_path)
    assert entrada["sdd_id"] == "SDD-X-0001"
    assert entrada["requisitos"][0]["id"] == "RF01"
    assert entrada["arquivos_permitidos"] == ["a/b.py", "a/c.py", "tests/t.py"]
    assert entrada["instrucoes"].startswith("Toque só nos listados.")


def test_comando_preserva_pipe_escapado_e_remove_crases(tmp_path):
    assert compilar(tmp_path)["criterios"][0]["comando"] == "pytest tests/t.py | tail -1"


def test_criterio_manual_pode_ficar_sem_comando(tmp_path):
    assert compilar(tmp_path)["criterios"][1]["perfil"] == "manual"


def test_recusa_sdd_que_nao_esta_aprovada(tmp_path):
    texto = SDD.replace("status: approved", "status: draft")
    assert "status precisa ser approved, é 'draft'" in problemas(tmp_path, texto)


def test_recusa_sem_front_matter(tmp_path):
    assert problemas(tmp_path, "# Só título\n") == ["sem front-matter"]


def test_recusa_front_matter_invalido(tmp_path):
    assert "front-matter inválido" in problemas(tmp_path, "---\na: [\n---\ncorpo\n")[0]


def test_recusa_sem_tabela_de_criterios(tmp_path):
    texto = SDD.replace("## Critérios de aceite", "## Outra coisa")
    assert "sem tabela de critérios de aceite" in problemas(tmp_path, texto)


def test_recusa_tabela_sem_coluna_de_comando(tmp_path):
    texto = SDD.replace("Comando de verificação", "Como conferir")
    assert "tabela de critérios sem coluna de comando" in problemas(tmp_path, texto)


def test_recusa_criterio_automatizado_sem_comando(tmp_path):
    texto = SDD.replace("`pytest tests/t.py \\| tail -1`", "n/a")
    assert "critério 1 automatizado sem comando" in problemas(tmp_path, texto)


def test_recusa_quando_nenhum_criterio_e_automatizado(tmp_path):
    texto = SDD.replace("exit 0 | automatizado", "exit 0 | manual")
    assert "nenhum critério automatizado" in problemas(tmp_path, texto)


def test_recusa_sem_rf_id(tmp_path):
    texto = SDD.replace("| RF01 | Retirada |", "| R1 | Retirada |").replace(
        "| 1 | Fazer | RF01 |", "| 1 | Fazer | R1 |"
    )
    assert "sem requisitos com RF-ID" in problemas(tmp_path, texto)


def test_recusa_sem_lista_de_arquivos(tmp_path):
    texto = SDD.replace("`a/b.py`, `tests/t.py`", "").replace("`a/c.py`", "")
    assert any("sem lista de arquivos" in p for p in problemas(tmp_path, texto))


def test_reune_todos_os_problemas_de_uma_vez(tmp_path):
    texto = SDD.replace("status: approved", "status: draft").replace(
        "## Critérios de aceite", "## Outra coisa"
    )
    assert len(problemas(tmp_path, texto)) == 2

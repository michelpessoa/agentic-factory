import re

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


# SDD enxuta: a referência é resolvida no texto da SPEC e da ADR (SDD-FAB-0005, RF04)

ENXUTA = """---
id: SDD-X-0002
title: "Lista"
status: approved
sizing: medium
source_docs:
  - id: "SPEC-X-0001"
    url: "https://h/blob/main/docs/X/03-spec/SPEC-X-0001.md"
  - id: "ADR-X-0001"
    url: "https://h/blob/main/docs/X/02-adr/ADR-X-0001.md"
---

# Lista

## Resumo executivo

Lista tarefas.

## Requisitos consolidados

Desenho, decisão e critério EARS na SPEC e na ADR de source_docs, por referência.

| RF-ID | Origem | Requisito (resumo) | Arquivos |
|---|---|---|---|
| RF01 | SPEC-X-0001 | Adicionar | `a/lista.py` |
| RF02 | SPEC-X-0001 | Remover | `a/lista.py`, `tests/t.py` |

## Critérios de aceite / definição de pronto

| # | Critério (origem: RF-ID / contrato) | Comando de verificação | Resultado esperado | Perfil esperado |
|---|---|---|---|---|
| 1 | RF01, RF02 | `pytest tests/t.py` | exit 0 | automatizado |

## Instruções específicas para a IA implementadora

Só os listados.
"""

SPEC_X = """---
id: SPEC-X-0001
---

# Lista

## Requisitos funcionais

| RF-ID | Requisito | Critério de aceite (EARS) | Arquivos |
|---|---|---|---|
| RF-01 | Adicionar | Quando chamar adicionar, o sistema deve incluir no fim. | `a/lista.py` |
| RF02 | Remover | Quando chamar remover, o sistema deve tirar da lista. | `a/lista.py` |

---

# Parte 2 — Desenho (o COMO e o ONDE)

## Contratos técnicos

`adicionar(lista, texto) -> None`.

## Autorrevisão antes de status `in_review`

- [x] Revisado.

## Depois da autorrevisão

Fica.
"""

ADR_X = """---
id: ADR-X-0001
---

# Python

## Contexto

Precisa de linguagem.

## Decisão

Python 3, sem dependência.

## Consequências

Nenhuma.
"""

ORIGENS_X = {"SPEC-X-0001": SPEC_X, "ADR-X-0001": ADR_X}


def compilar_enxuta(tmp_path, texto=ENXUTA, origens=ORIGENS_X):
    caminho = tmp_path / "SDD.md"
    caminho.write_text(texto, encoding="utf-8")
    return compilar_sdd(caminho, None, origens)


def problemas_enxuta(tmp_path, texto=ENXUTA, origens=ORIGENS_X):
    with pytest.raises(SddInvalida) as erro:
        compilar_enxuta(tmp_path, texto, origens)
    return erro.value.problemas


def test_enxuta_especificacao_traz_a_parte_2_sem_autorrevisao_e_depois_a_decisao(tmp_path):
    entrada = compilar_enxuta(tmp_path)
    assert entrada["especificacao"] == (
        "# SPEC-X-0001\n\n"
        "# Parte 2 — Desenho (o COMO e o ONDE)\n\n"
        "## Contratos técnicos\n\n"
        "`adicionar(lista, texto) -> None`.\n\n"
        "## Depois da autorrevisão\n\n"
        "Fica.\n\n"
        "# ADR-X-0001\n\n"
        "Python 3, sem dependência."
    )


CERCA_PYTHON = (
    "```python\n"
    "def listar(diretorio, responsavel=None, status=None, texto=None) -> list[dict]:\n"
    "    ...\n"
    "```"
)


def _especificacao_da_spec(tmp_path, spec):
    entrada = compilar_enxuta(tmp_path, origens={"SPEC-X-0001": spec, "ADR-X-0001": ADR_X})
    return entrada["especificacao"].split("\n\n# ADR-X-0001")[0]


def test_enxuta_especificacao_mantem_bloco_cercado_da_parte_2(tmp_path):
    spec = SPEC_X.replace(
        "`adicionar(lista, texto) -> None`.\n",
        f"`adicionar(lista, texto) -> None`.\n\n{CERCA_PYTHON}\n",
    )
    especificacao = _especificacao_da_spec(tmp_path, spec)
    assert f"`adicionar(lista, texto) -> None`.\n\n{CERCA_PYTHON}\n\n## Depois" in especificacao
    assert "Autorrevisão antes" not in especificacao


def test_enxuta_parte_2_dentro_de_cerca_nao_conta(tmp_path):
    falsa = "```markdown\n# Parte 2 — dentro da cerca\n\nNão é aqui.\n```\n\n"
    spec = SPEC_X.replace("---\n\n# Parte 2", f"{falsa}---\n\n# Parte 2")
    especificacao = _especificacao_da_spec(tmp_path, spec)
    assert especificacao.startswith("# SPEC-X-0001\n\n# Parte 2 — Desenho (o COMO e o ONDE)")
    assert "Não é aqui." not in especificacao

    so_na_cerca = SPEC_X.split("---\n\n# Parte 2")[0] + falsa
    assert "SPEC-X-0001 sem '# Parte 2'" in problemas_enxuta(
        tmp_path, origens={"SPEC-X-0001": so_na_cerca, "ADR-X-0001": ADR_X}
    )


def test_enxuta_autorrevisao_dentro_de_cerca_nao_e_secao_e_fica(tmp_path):
    cerca = "```markdown\n## Autorrevisão de exemplo\n\n# comentário\n```"
    spec = SPEC_X.replace(
        "`adicionar(lista, texto) -> None`.\n", f"`adicionar(lista, texto) -> None`.\n\n{cerca}\n"
    ).replace("- [x] Revisado.\n", f"- [x] Revisado.\n\n{CERCA_PYTHON.replace('def', '# def')}\n")
    especificacao = _especificacao_da_spec(tmp_path, spec)
    assert f"{cerca}\n\n## Depois da autorrevisão\n\nFica." in especificacao
    assert "Revisado" not in especificacao
    assert "# def listar" not in especificacao


def test_enxuta_aceite_vem_do_ears_da_spec_mesmo_com_hifen(tmp_path):
    entrada = compilar_enxuta(tmp_path)
    assert entrada["requisitos"] == [
        {
            "id": "RF01",
            "requisito": "Adicionar",
            "aceite": "Quando chamar adicionar, o sistema deve incluir no fim.",
        },
        {
            "id": "RF02",
            "requisito": "Remover",
            "aceite": "Quando chamar remover, o sistema deve tirar da lista.",
        },
    ]
    assert entrada["arquivos_permitidos"] == ["a/lista.py", "tests/t.py"]


def test_enxuta_sem_origem_no_clone_levanta_com_o_id(tmp_path):
    assert "origem ADR-X-0001 não está no clone do central" in problemas_enxuta(
        tmp_path, origens={"SPEC-X-0001": SPEC_X}
    )
    assert "origem SPEC-X-0001 não está no clone do central" in problemas_enxuta(
        tmp_path, origens=None
    )


def test_enxuta_spec_sem_parte_2_e_adr_sem_decisao_levantam(tmp_path):
    sem_parte_2 = SPEC_X.split("---\n\n# Parte 2")[0]
    sem_decisao = ADR_X.replace("## Decisão", "## Escolha")
    achados = problemas_enxuta(
        tmp_path, origens={"SPEC-X-0001": sem_parte_2, "ADR-X-0001": sem_decisao}
    )
    assert "SPEC-X-0001 sem '# Parte 2'" in achados
    assert "ADR-X-0001 sem seção 'Decisão'" in achados


def test_enxuta_rf_sem_criterio_na_spec_levanta(tmp_path):
    texto = ENXUTA.replace("| RF02 | SPEC-X-0001 | Remover |", "| RF09 | SPEC-X-0001 | Remover |")
    assert "RF09 sem critério de aceite em SPEC-X-0001" in problemas_enxuta(tmp_path, texto)


def test_sdd_que_nao_e_enxuta_ignora_origens(tmp_path):
    caminho = tmp_path / "SDD.md"
    caminho.write_text(SDD, encoding="utf-8")
    assert compilar_sdd(caminho, None, ORIGENS_X) == compilar_sdd(caminho)


def test_sdd_completa_com_source_docs_nao_e_enxuta_e_ignora_origens(tmp_path):
    # A descoberta com --origem em projeto abaixo da 2.7.0 escreve a SDD completa com source_docs.
    texto = SDD.replace(
        "source_docs: []",
        'source_docs:\n  - id: "SPEC-X-0001"\n    url: "https://h/blob/main/docs/X/03-spec/SPEC-X-0001.md"\n'
        '  - id: "ADR-X-0001"\n    url: "https://h/blob/main/docs/X/02-adr/ADR-X-0001.md"',
    ).replace(
        "## Decomposição em tasks",
        "## Especificação técnica consolidada\n\nDesenho da própria SDD.\n\n## Decomposição em tasks",
    )
    caminho = tmp_path / "SDD.md"
    caminho.write_text(texto, encoding="utf-8")
    compilado = compilar_sdd(caminho, None, ORIGENS_X)
    assert compilado == compilar_sdd(caminho)
    assert compilado["especificacao"] == "Desenho da própria SDD."
    assert compilado["requisitos"][0]["aceite"] == "Quando X, deve Y."


def test_tabela_enxuta_sem_source_docs_nao_e_enxuta(tmp_path):
    texto = re.sub(r"source_docs:\n(  .*\n)+", "source_docs: []\n", ENXUTA)
    caminho = tmp_path / "SDD.md"
    caminho.write_text(texto, encoding="utf-8")
    assert compilar_sdd(caminho, None, ORIGENS_X) == compilar_sdd(caminho)

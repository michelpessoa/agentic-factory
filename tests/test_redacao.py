"""SDD enxuta na redação: formato pela versão do projeto e texto no template 2.7.0 (SDD-FAB-0005)."""

import copy
import hashlib

import pytest
import yaml

from adapters.doc_traceability.redacao import escrever_sdd, formato_da_sdd, montar_sdd
from adapters.doc_traceability.validadores import FRAMEWORK_PADRAO, Framework

ORIGENS = [
    {"id": "SPEC-ZERO-0001", "url": "https://h/blob/main/docs/ZERO/03-spec/SPEC-ZERO-0001.md"},
    {"id": "ADR-ZERO-0001", "url": "https://h/blob/main/docs/ZERO/02-adr/ADR-ZERO-0001.md"},
]

COMPLETO = {
    "titulo": "Lista de tarefas",
    "resumo": "Guarda tarefas pessoais.",
    "sizing": "small",
    "arquitetura": "Python 3, sem dependência.",
    "requisitos": [
        {
            "id": "RF01",
            "origem": None,
            "requisito": "Adicionar tarefa",
            "aceite": "Quando o usuário chamar adicionar(lista, texto), o sistema deve incluir a "
            "tarefa no fim da lista.",
            "arquivos": ["tarefas/lista.py", "tests/test_lista.py"],
        }
    ],
    "especificacao": "Função em tarefas/lista.py.",
    "criterios": [
        {
            "criterio": "RF01: inclui no fim",
            "comando": "python3 -m unittest -v",
            "esperado": "exit 0",
        }
    ],
    "instrucoes": "Sem dependência nova.",
    "tarefas": [],
}

ENXUTO = copy.deepcopy(COMPLETO) | {"arquitetura": None, "especificacao": None}
ENXUTO["requisitos"] = [
    {
        "id": "RF01",
        "origem": "SPEC-ZERO-0001",
        "requisito": "Adicionar tarefa no fim da lista",
        "aceite": None,
        "arquivos": ["tarefas/lista.py", "tests/test_lista.py"],
    }
]


def registry(repo, versao):
    (repo / "docs/sdd").mkdir(parents=True)
    (repo / "docs/sdd/registry.yaml").write_text(
        f'project: "ZERO"\nframework_version: "{versao}"\ndocuments:\n', encoding="utf-8"
    )


# RF01: formato pela versão do projeto


def test_formato_sem_origens_e_completo(tmp_path):
    registry(tmp_path, "2.7.0")
    assert formato_da_sdd(tmp_path, [], "2.7.0") == "completa"


@pytest.mark.parametrize(
    ("versao", "formato"),
    [("2.3.2", "completa"), ("2.6.0", "completa"), ("2.7.0", "enxuta"), ("2.10.0", "enxuta")],
)
def test_formato_com_origens_segue_o_registry_do_projeto(tmp_path, versao, formato):
    registry(tmp_path, versao)
    assert formato_da_sdd(tmp_path, ORIGENS, "2.7.0") == formato


@pytest.mark.parametrize(("kit", "formato"), [("2.7.0", "enxuta"), ("2.6.0", "completa")])
def test_formato_sem_registry_segue_a_versao_do_kit(tmp_path, kit, formato):
    assert formato_da_sdd(tmp_path, ORIGENS, kit) == formato


# RF03: SDD enxuta no formato do template 2.7.0


def test_sdd_enxuta_tem_a_tabela_por_referencia_e_nao_copia_a_origem():
    texto = montar_sdd(ENXUTO, "SDD-ZERO-0001", "ZERO", "Dona", "2026-11-20", "draft", ORIGENS)
    assert (
        "| RF-ID | Origem | Requisito (resumo) | Arquivos |\n"
        "|---|---|---|---|\n"
        "| RF01 | SPEC-ZERO-0001 | Adicionar tarefa no fim da lista | "
        "`tarefas/lista.py`, `tests/test_lista.py` |"
    ) in texto
    assert (
        "Desenho, decisão e critério EARS na SPEC e na ADR de source_docs, por referência."
    ) in texto
    assert "## Especificação técnica consolidada" not in texto
    assert "## Decisão(ões) de arquitetura aplicável(is)" not in texto
    assert "sizing: small" in texto
    secoes = [linha for linha in texto.splitlines() if linha.startswith("## ")]
    assert secoes == [
        "## Resumo executivo",
        "## Requisitos consolidados",
        "## Critérios de aceite / definição de pronto",
        "## Instruções específicas para a IA implementadora",
        "## Verificação de escopo (nada a mais, nada a menos)",
        "## Evidência de verificação (preencher antes de status `implemented`)",
        "## Rastreabilidade",
    ]


def test_sdd_completa_segue_identica_a_de_antes():
    texto = montar_sdd(COMPLETO, "SDD-ZERO-0001", "ZERO", "Dona", "2026-11-17", "approved")
    assert hashlib.sha256(texto.encode()).hexdigest() == (
        "22763a2ef87dbb6fe8ab1877b73802c853f78e078f9a82d9c54360e823525be7"
    )


SPEC = """---
id: SPEC-ZERO-0001
type: SPEC
title: "Lista"
status: approved
---

# Lista

## Requisitos funcionais

| RF-ID | Requisito | Critério de aceite (EARS) | Arquivos |
|---|---|---|---|
| RF01 | Adicionar | Quando chamar adicionar, o sistema deve incluir no fim. | `tarefas/lista.py` |
| RF02 | Remover | Quando chamar remover, o sistema deve tirar da lista. | `tarefas/lista.py` |
"""


def central(tmp_path):
    raiz = tmp_path / "central"
    (raiz / "docs/ZERO/03-spec").mkdir(parents=True)
    (raiz / "docs/ZERO/03-spec/SPEC-ZERO-0001.md").write_text(SPEC, encoding="utf-8")
    (raiz / "docs/ZERO/registry.yaml").write_text(
        'project: "ZERO"\nframework_version: "2.7.0"\ndocuments:\n'
        '  - id: SPEC-ZERO-0001\n    type: SPEC\n    title: "Lista"\n    status: approved\n'
        '    owner: "Dona"\n    created: "2026-11-20"\n    updated: "2026-11-20"\n'
        '    relates_to: []\n    path: "docs/ZERO/03-spec/SPEC-ZERO-0001.md"\n    tags: []\n',
        encoding="utf-8",
    )
    return raiz


@pytest.mark.skipif(not FRAMEWORK_PADRAO.is_dir(), reason="framework ausente")
def test_sdd_enxuta_passa_no_validate_doc_real_em_draft(tmp_path):
    repo = tmp_path / "repo"
    caminho = escrever_sdd(
        repo, ENXUTO, "ZERO", "Dona", "2026-11-20", "draft", "2.7.0", origens=ORIGENS[:1]
    )
    resultado = Framework().validar_documento(repo, repo / caminho)
    assert resultado.ok, resultado.problemas


@pytest.mark.skipif(not FRAMEWORK_PADRAO.is_dir(), reason="framework ausente")
def test_sdd_enxuta_sem_um_rf_da_spec_reprova_no_check_source_docs_real(tmp_path):
    raiz = central(tmp_path)
    repo = tmp_path / "repo"
    origens = [
        {"id": "SPEC-ZERO-0001", "url": "https://h/blob/main/docs/ZERO/03-spec/SPEC-ZERO-0001.md"}
    ]
    caminho = escrever_sdd(
        repo, ENXUTO, "ZERO", "Dona", "2026-11-20", "approved", "2.7.0", origens=origens
    )
    framework = Framework()
    _, _, fontes = framework.validar_entrada(repo, repo / caminho, raiz / "docs/ZERO")
    assert not fontes.ok
    assert any("RF02" in p for p in fontes.problemas), fontes.problemas


# SDD-FAB-0008: registry do projeto com documents em fluxo

CABECALHO_ZERO = 'project: "ZERO"\nframework_version: "2.7.0"\n'

ENTRADA_SDD_ZERO_0002 = (
    "  - id: SDD-ZERO-0002\n"
    "    type: SDD\n"
    '    title: "Lista de tarefas"\n'
    "    status: draft\n"
    '    owner: "Dona"\n'
    '    created: "2026-11-21"\n'
    '    updated: "2026-11-21"\n'
    "    relates_to: []\n"
    '    path: "docs/sdd/SDD-ZERO-0002.md"\n'
    "    tags: [fabrica-descoberta]\n"
)


def registrar_sobre(repo, texto):
    if texto is not None:
        (repo / "docs/sdd").mkdir(parents=True)
        (repo / "docs/sdd/registry.yaml").write_text(texto, encoding="utf-8")
    escrever_sdd(
        repo, COMPLETO, "ZERO", "Dona", "2026-11-21", "draft", "2.7.0", sdd_id="SDD-ZERO-0002"
    )
    return (repo / "docs/sdd/registry.yaml").read_text(encoding="utf-8")


def test_registry_em_fluxo_vazio_recebe_a_sdd_nova(tmp_path):
    gravado = yaml.safe_load(registrar_sobre(tmp_path, CABECALHO_ZERO + "documents: []\n"))
    assert [d["id"] for d in gravado["documents"]] == ["SDD-ZERO-0002"]
    assert gravado["project"] == "ZERO"


def test_registry_em_fluxo_com_item_mantem_a_ordem(tmp_path):
    antigo = {"id": "SDD-ZERO-0001", "type": "SDD", "status": "draft"}
    texto = CABECALHO_ZERO + "documents: [{id: SDD-ZERO-0001, type: SDD, status: draft}]\n"
    gravado = yaml.safe_load(registrar_sobre(tmp_path, texto))
    assert [d["id"] for d in gravado["documents"]] == ["SDD-ZERO-0001", "SDD-ZERO-0002"]
    assert gravado["documents"][0] == antigo


@pytest.mark.parametrize(
    "anterior",
    [
        CABECALHO_ZERO + "documents:\n",
        "# registry do projeto\n"
        + CABECALHO_ZERO
        + "documents:\n  - id: SDD-ZERO-0001\n    type: 'SDD'\n    status: draft\n",
    ],
    ids=["vazio", "com-item"],
)
def test_registry_em_bloco_segue_byte_a_byte(tmp_path, anterior):
    assert registrar_sobre(tmp_path, anterior) == anterior + ENTRADA_SDD_ZERO_0002


def test_registry_inexistente_nasce_em_bloco_como_hoje(tmp_path):
    esperado = CABECALHO_ZERO + "documents:\n" + ENTRADA_SDD_ZERO_0002
    assert registrar_sobre(tmp_path, None) == esperado


# SDD-FAB-0009, RF08: aprovação por política


@pytest.mark.skipif(not FRAMEWORK_PADRAO.is_dir(), reason="framework ausente")
def test_politica_grava_approved_by_que_o_validate_state_real_aceita(tmp_path):
    from adapters.doc_traceability.redacao import aprovar_por_politica

    raiz = central(tmp_path)
    repo = tmp_path / "repo"
    registry(repo, "2.7.0")
    origens = [
        {"id": "SPEC-ZERO-0001", "url": "https://h/blob/main/docs/ZERO/03-spec/SPEC-ZERO-0001.md"}
    ]
    completo = copy.deepcopy(ENXUTO)
    completo["requisitos"].append(
        completo["requisitos"][0] | {"id": "RF02", "requisito": "Remover tarefa da lista"}
    )
    caminho = escrever_sdd(
        repo, completo, "ZERO", "Dona", "2026-11-21", "approved", "2.7.0", origens=origens
    )
    framework = Framework()
    approved_by = aprovar_por_politica(repo, caminho, framework, "2026-11-21T14:00:00Z")
    assert approved_by == {
        "kind": "policy",
        "actor": "fabrica-agentica",
        "at": "2026-11-21T14:00:00Z",
        "content_sha256": approved_by["content_sha256"],
        "transitions": [
            {"from": "draft", "to": "in_review", "at": "2026-11-21T14:00:00Z"},
            {"from": "in_review", "to": "approved", "at": "2026-11-21T14:00:00Z"},
        ],
    }
    assert len(approved_by["content_sha256"]) == 64
    frente = yaml.safe_load((repo / caminho).read_text(encoding="utf-8").split("---\n")[1])
    assert frente["approved_by"] == approved_by
    assert frente["status"] == "approved"
    estado = framework.validar_estado(repo, repo / caminho)
    assert estado.ok, estado.problemas
    assert all(r.ok for r in framework.validar_entrada(repo, repo / caminho, raiz / "docs/ZERO"))


@pytest.mark.skipif(not FRAMEWORK_PADRAO.is_dir(), reason="framework ausente")
def test_politica_corpo_editado_depois_reprova_no_validate_state_real(tmp_path):
    from adapters.doc_traceability.redacao import aprovar_por_politica

    repo = tmp_path / "repo"
    registry(repo, "2.7.0")
    caminho = escrever_sdd(
        repo, ENXUTO, "ZERO", "Dona", "2026-11-21", "approved", "2.7.0", origens=ORIGENS[:1]
    )
    framework = Framework()
    aprovar_por_politica(repo, caminho, framework, "2026-11-21T14:00:00Z")
    arquivo = repo / caminho
    arquivo.write_text(arquivo.read_text(encoding="utf-8") + "\nEditado à mão.\n", "utf-8")
    assert not framework.validar_estado(repo, arquivo).ok

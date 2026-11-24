"""Integração com os validadores reais do framework, sem depender do repositório de teste."""

import json
from pathlib import Path

import pytest
import yaml

from adapters.doc_traceability.validadores import FRAMEWORK_PADRAO, Framework

pytestmark = pytest.mark.skipif(not FRAMEWORK_PADRAO.is_dir(), reason="framework ausente")
COBAIA = Path.home() / "projetos" / "fabrica-cobaia"
SEM_COBAIA = pytest.mark.skipif(not COBAIA.is_dir(), reason="repositório de teste ausente")
CENTRAL = Path.home() / "fabrica-central-teste"
SEM_CENTRAL = pytest.mark.skipif(not CENTRAL.is_dir(), reason="central de teste ausente")
DOCS_COBAIA = CENTRAL / "docs" / "COBAIA"


def test_sha_do_framework_e_registrado():
    assert len(Framework().sha()) == 40


@SEM_COBAIA
@SEM_CENTRAL
def test_sdd_valida_passa():
    sdd = COBAIA / "docs/sdd/SDD-COBAIA-0001.md"
    resultados = Framework().validar_entrada(COBAIA, sdd, DOCS_COBAIA)
    assert [r.nome for r in resultados] == [
        "validate_doc.py",
        "registry_tools.py",
        "check_source_docs.py",
    ]
    assert all(r.ok and not r.problemas for r in resultados)


@SEM_COBAIA
@SEM_CENTRAL
def test_needs_clarification_e_recusado():
    sdd = COBAIA / "docs/sdd/SDD-COBAIA-0003.md"
    resultados = {r.nome: r for r in Framework().validar_entrada(COBAIA, sdd, DOCS_COBAIA)}
    assert not resultados["validate_doc.py"].ok
    assert any("NEEDS CLARIFICATION" in m for m in resultados["validate_doc.py"].problemas)


def framework_com_script(raiz: Path, nome: str, corpo: str) -> Framework:
    scripts = raiz / "_framework" / "scripts"
    scripts.mkdir(parents=True)
    (scripts / nome).write_text(corpo, encoding="utf-8")
    return Framework(raiz)


def test_saida_que_nao_e_json_fica_fora_do_contrato(tmp_path):
    framework = framework_com_script(tmp_path, "validate_state.py", 'print("tudo certo")\n')
    resultado = framework.validar_estado(tmp_path, tmp_path / "SDD.md")
    assert resultado.ok is False
    assert resultado.problemas == (
        "saída fora do contrato dtf.resultado-validador/1: tudo certo\n",
    )


def test_json_de_outro_schema_fica_fora_do_contrato(tmp_path):
    corpo = 'import json\nprint(json.dumps({"schema": "outro/1", "ok": True}))\n'
    framework = framework_com_script(tmp_path, "validate_state.py", corpo)
    resultado = framework.validar_estado(tmp_path, tmp_path / "SDD.md")
    assert resultado.ok is False
    assert resultado.problemas[0].startswith("saída fora do contrato dtf.resultado-validador/1: ")


def test_trecho_fora_do_contrato_tem_no_maximo_300_caracteres(tmp_path):
    framework = framework_com_script(tmp_path, "validate_state.py", 'print("x" * 1000)\n')
    resultado = framework.validar_estado(tmp_path, tmp_path / "SDD.md")
    prefixo = "saída fora do contrato dtf.resultado-validador/1: "
    assert resultado.problemas == (prefixo + ("x" * 1000 + "\n")[-300:],)


def test_contrato_decide_pelo_ok_do_json_e_pede_json(tmp_path):
    corpo = (
        "import json, sys\n"
        "print(json.dumps({'schema': 'dtf.resultado-validador/1', 'ok': sys.argv[-1] != '--json',"
        " 'problemas': [{'mensagem': 'a'}, {'mensagem': 'b'}]}))\n"
    )
    framework = framework_com_script(tmp_path, "validate_state.py", corpo)
    resultado = framework.validar_estado(tmp_path, tmp_path / "SDD.md")
    assert resultado.ok is False
    assert resultado.problemas == ("a", "b")


URL_SPEC = "https://github.com/u/central/blob/main/docs/X/03-spec/SPEC-X-0001.md"


def central_com_spec(raiz: Path, status: str) -> Path:
    docs = raiz / "central" / "docs" / "X"
    (docs / "03-spec").mkdir(parents=True)
    (docs / "03-spec" / "SPEC-X-0001.md").write_text("# SPEC\n", encoding="utf-8")
    registry = {
        "project": "X",
        "documents": [
            {
                "id": "SPEC-X-0001",
                "type": "SPEC",
                "status": status,
                "path": "docs/X/03-spec/SPEC-X-0001.md",
            }
        ],
    }
    (docs / "registry.yaml").write_text(yaml.safe_dump(registry), encoding="utf-8")
    return docs


def sdd_citando(raiz: Path, source_docs: list) -> Path:
    sdd = raiz / "projeto" / "docs" / "sdd" / "SDD-X-0001.md"
    sdd.parent.mkdir(parents=True)
    frente = {"id": "SDD-X-0001", "type": "SDD", "source_docs": source_docs}
    sdd.write_text(f"---\n{yaml.safe_dump(frente)}---\n\n# SDD\n", encoding="utf-8")
    return sdd


def checagem_de_source_docs(sdd: Path, docs_central: Path):
    resultados = Framework().validar_entrada(sdd.parents[2], sdd, docs_central)
    return {r.nome: r for r in resultados}["check_source_docs.py"]


def test_source_docs_nao_aprovado_e_recusado(tmp_path):
    docs = central_com_spec(tmp_path, "draft")
    sdd = sdd_citando(tmp_path, [{"id": "SPEC-X-0001", "url": URL_SPEC}])
    resultado = checagem_de_source_docs(sdd, docs)
    assert not resultado.ok
    assert any("SPEC-X-0001" in m and "draft" in m for m in resultado.problemas)


def test_source_docs_aprovado_passa(tmp_path):
    docs = central_com_spec(tmp_path, "approved")
    sdd = sdd_citando(tmp_path, [{"id": "SPEC-X-0001", "url": URL_SPEC}])
    resultado = checagem_de_source_docs(sdd, docs)
    assert resultado.ok and resultado.problemas == ()


def test_source_docs_vazio_passa(tmp_path):
    docs = central_com_spec(tmp_path, "draft")
    resultado = checagem_de_source_docs(sdd_citando(tmp_path, []), docs)
    assert resultado.ok and resultado.problemas == ()


def test_saida_json_real_segue_o_contrato(tmp_path):
    docs = central_com_spec(tmp_path, "approved")
    resultado = checagem_de_source_docs(sdd_citando(tmp_path, []), docs)
    assert json.loads(resultado.saida)["schema"] == "dtf.resultado-validador/1"

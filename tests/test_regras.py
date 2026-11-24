"""Regras do framework fixado na entrada: sizing, documentos por nível e ciclo de status."""

import json
from pathlib import Path

import pytest
import yaml

from adapters.doc_traceability import FonteDocTraceability
from adapters.doc_traceability.regras import Regras
from adapters.doc_traceability.validadores import FRAMEWORK_PADRAO, Framework
from tests.test_evidencia import CAMINHO, REGISTRY, SDD, VALIDACAO

sem_framework = pytest.mark.skipif(not FRAMEWORK_PADRAO.is_dir(), reason="framework ausente")
ESQUEMA = Path(__file__).parent.parent / "contracts" / "resposta-descoberta.schema.json"


def regras_falsas(raiz: Path) -> Regras:
    pasta = raiz / "_framework" / "rules"
    pasta.mkdir(parents=True)
    dados = {
        "sizing": {
            "levels": [
                {"id": "tiny", "documents": ["SDD"]},
                {"id": "huge", "documents": ["STRAT (opcional)", "SPEC", "SDD"]},
            ]
        },
        "status_lifecycle": {"allowed_transitions": {"draft": ["implemented"], "approved": []}},
    }
    (pasta / "workflow-rules.yaml").write_text(yaml.safe_dump(dados), encoding="utf-8")
    return Regras(raiz)


def test_regras_vem_do_yaml_lido(tmp_path):
    regras = regras_falsas(tmp_path)
    assert regras.niveis() == ("tiny", "huge")
    assert regras.documentos("huge") == ("SPEC", "SDD")
    assert regras.documentos("medium") == ()
    assert regras.transicao_permitida("draft", "implemented")
    assert not regras.transicao_permitida("approved", "implemented")
    assert not regras.transicao_permitida("inexistente", "implemented")


@sem_framework
def test_regras_do_framework_fixado():
    regras = Regras(FRAMEWORK_PADRAO)
    assert regras.niveis() == ("small", "medium", "large", "complex")
    assert regras.documentos("medium") == ("SPEC", "SDD")
    assert regras.documentos("complex") == ("RFC", "ADR", "SPEC", "SDD")
    assert regras.transicao_permitida("approved", "implemented")
    assert not regras.transicao_permitida("draft", "implemented")


def test_tipo_do_central_vem_do_yaml_lido(tmp_path):
    pasta = tmp_path / "_framework" / "rules"
    pasta.mkdir(parents=True)
    dados = {
        "sizing": {"levels": [{"id": "medium", "documents": ["ADR", "SPEC", "SDD"]}]},
        "document_types": {
            "ADR": {"repo": "central", "folder": "docs/{PROJECT_CODE}/adr"},
            "SPEC": {"repo": "central", "folder": "docs/{PROJECT_CODE}/spec"},
            "SDD": {"repo": "project", "folder": "docs/sdd"},
        },
    }
    (pasta / "workflow-rules.yaml").write_text(yaml.safe_dump(dados), encoding="utf-8")
    regras = Regras(tmp_path)
    assert regras.tipo_do_central("medium") == "ADR"
    assert regras.tipo_do_central("small") is None
    assert regras.repositorio("SDD") == "project"
    assert regras.repositorio("RFC") is None
    assert regras.pasta("ADR", "ZERO") == "docs/ZERO/adr"


@sem_framework
def test_tipo_do_central_no_framework_fixado():
    regras = Regras(FRAMEWORK_PADRAO)
    assert regras.tipo_do_central("medium") == "SPEC"
    assert regras.tipo_do_central("large") == "RFC"
    assert regras.tipo_do_central("complex") == "RFC"
    assert regras.tipo_do_central("small") is None
    assert regras.repositorio("SPEC") == "central"
    assert regras.pasta("RFC", "ZERO") == "docs/ZERO/01-rfc"
    assert regras.pasta("SPEC", "COBAIA") == "docs/COBAIA/03-spec"


def test_sizing_large_no_schema_da_descoberta():
    esquema = json.loads(ESQUEMA.read_text(encoding="utf-8"))
    sizing = esquema["properties"]["rascunho"]["properties"]["sizing"]["enum"]
    assert sizing == ["small", "medium", "large", "complex"]


SPEC = """---
id: SPEC-X-0001
type: SPEC
title: "Soma"
status: approved
project: "X"
sizing: {sizing}
parent_adr: {adr}
---

# Soma
"""


def central_com_spec(raiz: Path, spec_sizing: str = "medium", adr: str = "null") -> Path:
    docs = raiz / "docs" / "X"
    (docs / "03-spec").mkdir(parents=True)
    (docs / "03-spec" / "SPEC-X-0001.md").write_text(
        SPEC.format(sizing=spec_sizing, adr=adr), encoding="utf-8"
    )
    registry = {
        "project": "X",
        "documents": [
            {
                "id": "SPEC-X-0001",
                "type": "SPEC",
                "title": "Soma",
                "status": "approved",
                "path": "docs/X/03-spec/SPEC-X-0001.md",
            }
        ],
    }
    (docs / "registry.yaml").write_text(yaml.safe_dump(registry), encoding="utf-8")
    return raiz


def repo_com_sdd(raiz: Path, sizing: str = "small", fontes: str = "[]") -> Path:
    (raiz / "docs/sdd").mkdir(parents=True)
    texto = SDD.replace("sizing: small", f"sizing: {sizing}").replace(
        "source_docs: []", f"source_docs: {fontes}"
    )
    (raiz / CAMINHO).write_text(texto, encoding="utf-8")
    (raiz / "docs/sdd/registry.yaml").write_text(REGISTRY, encoding="utf-8")
    return raiz


def problemas(tmp_path, sizing="small", fontes="[]", **spec) -> list[str]:
    repo = repo_com_sdd(tmp_path / "repo", sizing, fontes)
    central = central_com_spec(tmp_path / "central", **spec)
    return FonteDocTraceability(Framework(), central, "X").problemas_de_entrada(repo, CAMINHO)


SPEC_X = '[{id: "SPEC-X-0001", url: "https://h/SPEC-X-0001.md"}]'


@sem_framework
def test_sizing_fora_dos_niveis_e_recusado(tmp_path):
    achados = problemas(tmp_path, sizing="huge")
    assert "sizing 'huge' não é nível do framework: use small, medium, large, complex" in achados


@sem_framework
def test_sizing_small_sem_spec_passa(tmp_path):
    achados = problemas(tmp_path)
    assert not any("sizing" in p or "source_docs" in p for p in achados)


@sem_framework
def test_spec_exigida_em_medium(tmp_path):
    assert "sizing medium exige SPEC approved em source_docs" in problemas(tmp_path, "medium")


@sem_framework
def test_spec_com_sizing_divergente(tmp_path):
    achados = problemas(tmp_path, "medium", SPEC_X, spec_sizing="small")
    assert "sizing medium difere do sizing small da SPEC-X-0001" in achados
    assert "sizing medium exige SPEC approved em source_docs" not in achados


@sem_framework
def test_spec_com_parent_adr_fora_de_source_docs(tmp_path):
    achados = problemas(tmp_path, "medium", SPEC_X, adr="ADR-X-0002")
    assert "a SPEC-X-0001 vem da ADR-X-0002, que falta em source_docs" in achados


@sem_framework
def test_spec_com_parent_adr_presente_passa(tmp_path):
    fontes = SPEC_X[:-1] + ', {id: "ADR-X-0002", url: "https://h/ADR-X-0002.md"}]'
    achados = problemas(tmp_path, "medium", fontes, adr="ADR-X-0002")
    assert not any(p.startswith(("sizing", "a SPEC-")) for p in achados)


@sem_framework
def test_spec_fora_do_registry_fica_para_o_check_source_docs(tmp_path):
    fontes = '[{id: "SPEC-X-0009", url: "https://h/SPEC-X-0009.md"}]'
    achados = problemas(tmp_path, "medium", fontes)
    assert not any(p.startswith(("sizing", "a SPEC-")) for p in achados)


@sem_framework
def test_transicao_nao_permitida_nao_grava_evidencia(tmp_path):
    repo = repo_com_sdd(tmp_path)
    rascunho = (
        (repo / CAMINHO).read_text(encoding="utf-8").replace("status: approved", "status: draft")
    )
    (repo / CAMINHO).write_text(rascunho, encoding="utf-8")
    fonte = FonteDocTraceability(Framework())
    problemas_ = fonte.registrar_verificacao(repo, CAMINHO, VALIDACAO, "a", "b")
    assert problemas_ == ["o framework não permite draft → implemented"]
    assert (repo / CAMINHO).read_text(encoding="utf-8") == rascunho
    assert not (repo / "docs/sdd/validation-SDD-X-0001.md").exists()


@sem_framework
def test_transicao_permitida_grava_evidencia(tmp_path):
    repo = repo_com_sdd(tmp_path)
    assert (
        FonteDocTraceability(Framework()).registrar_verificacao(repo, CAMINHO, VALIDACAO, "a", "b")
        == []
    )

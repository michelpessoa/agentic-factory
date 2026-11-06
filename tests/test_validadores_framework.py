"""Integração com os validadores reais do framework, sem depender do repositório de teste."""

from pathlib import Path

import pytest

from adapters.doc_traceability.validadores import FRAMEWORK_PADRAO, Framework

pytestmark = pytest.mark.skipif(not FRAMEWORK_PADRAO.is_dir(), reason="framework ausente")
COBAIA = Path.home() / "projetos" / "fabrica-cobaia"
SEM_COBAIA = pytest.mark.skipif(not COBAIA.is_dir(), reason="repositório de teste ausente")


def test_sha_do_framework_e_registrado():
    assert len(Framework().sha()) == 40


@SEM_COBAIA
def test_sdd_valida_passa():
    sdd = COBAIA / "docs/sdd/SDD-COBAIA-0001.md"
    assert all(r.ok for r in Framework().validar_entrada(COBAIA, sdd))


@SEM_COBAIA
def test_needs_clarification_e_recusado():
    sdd = COBAIA / "docs/sdd/SDD-COBAIA-0003.md"
    resultados = {r.nome: r for r in Framework().validar_entrada(COBAIA, sdd)}
    assert not resultados["validate_doc.py"].ok
    assert "NEEDS CLARIFICATION" in resultados["validate_doc.py"].saida

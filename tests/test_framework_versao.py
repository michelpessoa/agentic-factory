"""A fábrica só roda com a versão do framework que o projeto declara."""

from pathlib import Path

import pytest
import yaml

from adapters.doc_traceability import FonteDocTraceability
from adapters.doc_traceability.validadores import FRAMEWORK_PADRAO, Framework, VersaoDivergente
from fabrica.__main__ import montar_fonte
from fabrica.pipeline import Projeto

RAIZ = Path(__file__).resolve().parents[1]


def framework_falso(raiz: Path, versao: str) -> Framework:
    (raiz / "_framework" / "scripts").mkdir(parents=True)
    regras = raiz / "_framework" / "rules"
    regras.mkdir()
    (regras / "workflow-rules.yaml").write_text(
        yaml.safe_dump({"framework": {"version": versao}}), encoding="utf-8"
    )
    return Framework(raiz)


def test_versao_igual_passa(tmp_path):
    framework_falso(tmp_path, "2.3.2").exigir_versao("2.3.2")


def test_versao_diferente_recusa(tmp_path):
    with pytest.raises(VersaoDivergente, match="exige o framework 2.3.2.*na 2.4.0"):
        framework_falso(tmp_path, "2.4.0").exigir_versao("2.3.2")


def test_projeto_sem_versao_recusa(tmp_path):
    with pytest.raises(VersaoDivergente, match="não declara a versão"):
        framework_falso(tmp_path, "2.3.2").exigir_versao("")


@pytest.mark.parametrize(
    "arquivo", sorted((RAIZ / "projetos").glob("*.yaml")), ids=lambda p: p.name
)
def test_todo_projeto_declara_versao(arquivo):
    assert yaml.safe_load(arquivo.read_text(encoding="utf-8")).get("framework")


@pytest.mark.parametrize(
    "arquivo", sorted((RAIZ / "projetos").glob("*.yaml")), ids=lambda p: p.name
)
def test_todo_projeto_declara_central(arquivo):
    assert yaml.safe_load(arquivo.read_text(encoding="utf-8")).get("central")


@pytest.mark.skipif(not FRAMEWORK_PADRAO.is_dir(), reason="framework ausente")
def test_clone_do_framework_e_a_versao_dos_projetos():
    """No CI, o checkout fixado precisa ser a versão que os projetos declaram."""
    versoes = {
        yaml.safe_load(p.read_text(encoding="utf-8"))["framework"]
        for p in (RAIZ / "projetos").glob("*.yaml")
    }
    assert versoes == {Framework().versao()}


def test_central_na_versao_passa(tmp_path):
    framework = framework_falso(tmp_path / "kit", "2.5.0")
    framework_falso(tmp_path / "central", "2.5.0")
    framework.exigir_central(tmp_path / "central", "2.5.0")


def test_central_vazio_recusa(tmp_path):
    with pytest.raises(VersaoDivergente, match="não declara o caminho do central"):
        framework_falso(tmp_path, "2.5.0").exigir_central(Path(""), "2.5.0")


def test_central_em_outra_versao_recusa(tmp_path):
    framework = framework_falso(tmp_path / "kit", "2.5.0")
    framework_falso(tmp_path / "central", "2.3.2")
    with pytest.raises(
        VersaoDivergente, match=r"exige o framework 2\.5\.0, e o central em .* está na 2\.3\.2"
    ):
        framework.exigir_central(tmp_path / "central", "2.5.0")


def test_central_inexistente_recusa(tmp_path):
    with pytest.raises(VersaoDivergente, match="central não encontrado"):
        framework_falso(tmp_path / "kit", "2.5.0").exigir_central(tmp_path / "nada", "2.5.0")


def test_fonte_sem_central_recusa(tmp_path):
    fonte = FonteDocTraceability(framework_falso(tmp_path, "2.5.0"))
    with pytest.raises(VersaoDivergente, match="não declara o caminho do central"):
        fonte.exigir_versao("2.5.0")


def test_fonte_confere_o_central_do_projeto(tmp_path):
    framework_falso(tmp_path / "central", "2.3.2")
    fonte = FonteDocTraceability(framework_falso(tmp_path / "kit", "2.5.0"), tmp_path / "central")
    with pytest.raises(VersaoDivergente, match="o central em .* está na 2.3.2"):
        fonte.exigir_versao("2.5.0")


@pytest.mark.skipif(not FRAMEWORK_PADRAO.is_dir(), reason="framework ausente")
def test_montar_fonte_sem_central_recusa():
    projeto = Projeto(codigo="X", repo="r", github="g", framework=Framework().versao())
    with pytest.raises(VersaoDivergente, match="não declara o caminho do central"):
        montar_fonte(projeto)

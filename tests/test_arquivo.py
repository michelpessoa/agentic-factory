"""SDD efêmera contra os scripts reais do framework: validate, trace e audit."""

import os
import subprocess
import sys

import pytest

from adapters.doc_traceability import FonteDocTraceability
from adapters.doc_traceability.arquivo import arquivar_sdd
from adapters.doc_traceability.compilador import SddInvalida, compilar_sdd
from adapters.doc_traceability.evidencia import registrar_evidencia
from adapters.doc_traceability.validadores import FRAMEWORK_PADRAO
from tests.test_evidencia import CAMINHO, REGISTRY, SDD, VALIDACAO

sem_framework = pytest.mark.skipif(not FRAMEWORK_PADRAO.is_dir(), reason="framework ausente")
SCRIPTS = FRAMEWORK_PADRAO / "_framework" / "scripts"
ARQUIVADA = "docs/sdd/arquivo/SDD-X-0001.md"


@pytest.fixture
def repo(tmp_path):
    (tmp_path / "docs/sdd").mkdir(parents=True)
    (tmp_path / CAMINHO).write_text(SDD, encoding="utf-8")
    (tmp_path / "docs/sdd/registry.yaml").write_text(REGISTRY, encoding="utf-8")
    registrar_evidencia(tmp_path, CAMINHO, VALIDACAO, "a", "b")
    return tmp_path


def registro(repo):
    return (repo / "docs/sdd/registry.yaml").read_text(encoding="utf-8")


def test_move_sdd_e_validacao_e_grava_a_entrega(repo):
    assert arquivar_sdd(repo, CAMINHO, 12, "2026-11-05") is True
    assert not (repo / CAMINHO).exists()
    assert (repo / ARQUIVADA).is_file()
    assert (repo / "docs/sdd/arquivo/validation-SDD-X-0001.md").is_file()
    assert f'path: "{ARQUIVADA}"' in registro(repo)
    assert 'entrega: {pr: 12, data: "2026-11-05", resultado: aprovado}' in registro(repo)


def test_status_continua_implemented(repo):
    arquivar_sdd(repo, CAMINHO, 12, "2026-11-05")
    assert "status: implemented" in registro(repo)
    assert "status: implemented" in (repo / ARQUIVADA).read_text(encoding="utf-8")


def test_arquivar_de_novo_nao_faz_nada(repo):
    arquivar_sdd(repo, CAMINHO, 12, "2026-11-05")
    antes = registro(repo)
    assert arquivar_sdd(repo, CAMINHO, 12, "2026-11-05") is False
    assert registro(repo) == antes


def test_sdd_fora_do_registry_e_erro(repo):
    (repo / "docs/sdd/registry.yaml").write_text('project: "X"\ndocuments: []\n', encoding="utf-8")
    with pytest.raises(ValueError, match="não encontrada"):
        arquivar_sdd(repo, CAMINHO, 12, "2026-11-05")


def rodar(repo, script, *args):
    env = {"PATH": os.environ["PATH"], "PYTHONDONTWRITEBYTECODE": "1"}
    return subprocess.run(
        [sys.executable, str(SCRIPTS / script), *args],
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


@sem_framework
def test_validate_real_verde_com_sdd_arquivada(repo):
    arquivar_sdd(repo, CAMINHO, 12, "2026-11-05")
    resultado = rodar(repo, "registry_tools.py", "validate", "docs/sdd")
    assert resultado.returncode == 0, resultado.stdout


@sem_framework
def test_trace_real_encontra_sdd_arquivada(repo):
    arquivar_sdd(repo, CAMINHO, 12, "2026-11-05")
    resultado = rodar(repo, "registry_tools.py", "trace", "docs/sdd", "SDD-X-0001")
    assert resultado.returncode == 0, resultado.stdout + resultado.stderr
    assert "SDD-X-0001" in resultado.stdout


@sem_framework
def test_audit_real_reconhece_commit_de_sdd_arquivada(repo):
    arquivar_sdd(repo, CAMINHO, 12, "2026-11-05")
    log = repo / "log.txt"
    log.write_text("abc\nfeat: x (SDD-X-0001)\n\n===END===\n", encoding="utf-8")
    resultado = rodar(repo, "registry_tools.py", "audit", str(log), "docs/sdd")
    assert "Cobertos (referência válida): 1" in resultado.stdout
    assert "Referência quebrada (id citado não existe em nenhum registry): 0" in resultado.stdout


@sem_framework
def test_estado_real_verde_com_sdd_arquivada(repo):
    arquivar_sdd(repo, CAMINHO, 12, "2026-11-05")
    assert rodar(repo, "validate_state.py", ARQUIVADA).returncode == 0


def test_aprovadas_nao_olham_o_arquivo(repo):
    arquivar_sdd(repo, CAMINHO, 12, "2026-11-05")
    (repo / "docs/sdd/SDD-X-0002.md").write_text(SDD, encoding="utf-8")
    (repo / "docs/sdd/arquivo/SDD-X-0003.md").write_text(SDD, encoding="utf-8")
    assert FonteDocTraceability.sdds_aprovadas(None, repo) == ["docs/sdd/SDD-X-0002.md"]


def sdd_com_molde():
    return SDD.replace("sizing: small", "sizing: small\nmolde: crud")


def test_molde_entra_no_contrato(repo):
    (repo / CAMINHO).write_text(sdd_com_molde(), encoding="utf-8")
    (repo / "docs/fabrica/moldes").mkdir(parents=True)
    (repo / "docs/fabrica/moldes/crud.md").write_text("Padrão de CRUD.\n", encoding="utf-8")
    assert compilar_sdd(repo / CAMINHO, repo)["molde"] == "Padrão de CRUD.\n"


def test_molde_inexistente_e_recusado(repo):
    (repo / CAMINHO).write_text(sdd_com_molde(), encoding="utf-8")
    with pytest.raises(SddInvalida, match="molde 'crud'"):
        compilar_sdd(repo / CAMINHO, repo)


def test_tarefas_da_sdd_sao_compiladas(repo):
    corpo = SDD.replace(
        "## Critérios de aceite",
        "## Decomposição em tasks\n\n| # | Task | RF(s) de origem | Arquivos tocados | Depende de (#) |\n"
        "|---|---|---|---|---|\n| 1 | Fazer | RF01 | `a.py` | |\n\n## Critérios de aceite",
    )
    (repo / CAMINHO).write_text(corpo, encoding="utf-8")
    tarefas = compilar_sdd(repo / CAMINHO, repo)["tarefas"]
    assert tarefas == [{"numero": "1", "descricao": "Fazer", "arquivos": ["a.py"]}]

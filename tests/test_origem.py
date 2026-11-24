"""Origem explícita da descoberta: SPEC ou ADR approved conferida no registry do central."""

import sys

import pytest
import yaml

from adapters.doc_traceability import FonteDocTraceability, OrigemInvalida
from adapters.doc_traceability.validadores import FRAMEWORK_PADRAO, Framework
from fabrica import __main__ as cli
from fabrica.descoberta import AGUARDANDO_APROVACAO
from tests.test_descoberta import RedatorFalso, RunnerFila, git, montar, rascunho, remoto  # noqa: F401

pytestmark = pytest.mark.skipif(not FRAMEWORK_PADRAO.is_dir(), reason="framework ausente")

DOCUMENTOS = [
    ("SPEC-X-0001", "SPEC", "approved", "docs/X/03-spec/SPEC-X-0001.md", "sizing: medium\n"),
    ("SPEC-X-0002", "SPEC", "draft", "docs/X/03-spec/SPEC-X-0002.md", "sizing: medium\n"),
    ("ADR-X-0001", "ADR", "approved", "docs/X/02-adr/ADR-X-0001.md", ""),
    ("RFC-X-0001", "RFC", "approved", "docs/X/01-rfc/RFC-X-0001.md", ""),
]


def central(raiz, remote="https://github.com/dona/central.git"):
    raiz.mkdir()
    git("init", "-q", cwd=raiz)
    git("remote", "add", "origin", remote, cwd=raiz)
    entradas = []
    for doc_id, tipo, status, path, extra in DOCUMENTOS:
        arquivo = raiz / path
        arquivo.parent.mkdir(parents=True, exist_ok=True)
        arquivo.write_text(
            f"---\nid: {doc_id}\ntype: {tipo}\nstatus: {status}\n{extra}---\n\n# Título {doc_id}\n",
            encoding="utf-8",
        )
        entradas.append(
            {"id": doc_id, "type": tipo, "title": f"Título {doc_id}", "status": status,
             "path": path}
        )  # fmt: skip
    registry = {"project": "X", "documents": entradas}
    (raiz / "docs/X/registry.yaml").write_text(yaml.safe_dump(registry), encoding="utf-8")
    return raiz


def fonte(tmp_path, remote="https://github.com/dona/central.git"):
    return FonteDocTraceability(Framework(), central(tmp_path / "central", remote), "X")


def test_origem_fora_do_registry(tmp_path):
    with pytest.raises(OrigemInvalida, match=r"^SPEC-X-0009 não está no registry do central em "):
        fonte(tmp_path).origem("SPEC-X-0009")


def test_origem_rfc_e_recusada(tmp_path):
    with pytest.raises(
        OrigemInvalida, match=r"^RFC-X-0001 é RFC: a origem da descoberta é SPEC ou ADR$"
    ):
        fonte(tmp_path).origem("RFC-X-0001")


def test_origem_em_draft_e_recusada(tmp_path):
    with pytest.raises(
        OrigemInvalida, match=r"^SPEC-X-0002 está draft: a origem precisa estar approved$"
    ):
        fonte(tmp_path).origem("SPEC-X-0002")


def test_origem_spec_approved_com_remote_https(tmp_path):
    origem = fonte(tmp_path).origem("SPEC-X-0001")
    assert (
        origem["url"] == "https://github.com/dona/central/blob/main/docs/X/03-spec/SPEC-X-0001.md"
    )
    assert origem["id"] == "SPEC-X-0001"
    assert origem["tipo"] == "SPEC"
    assert origem["titulo"] == "Título SPEC-X-0001"
    assert origem["sizing"] == "medium"
    assert origem["texto"].endswith("# Título SPEC-X-0001\n")


def test_origem_adr_approved_com_remote_ssh(tmp_path, monkeypatch):
    # Sem config global: um `url.*.insteadOf` do ambiente já devolveria https e esconderia a troca.
    monkeypatch.delenv("GIT_CONFIG_COUNT", raising=False)
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", "/dev/null")
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    f = fonte(tmp_path, "git@github.com:dona/central.git")
    assert git("remote", "get-url", "origin", cwd=tmp_path / "central").startswith("git@")
    origem = f.origem("ADR-X-0001")
    assert origem["url"] == "https://github.com/dona/central/blob/main/docs/X/02-adr/ADR-X-0001.md"
    assert origem["sizing"] is None


class RedatorComOrigem(RedatorFalso):
    def origem(self, doc_id):
        if doc_id != "SPEC-X-0001":
            raise OrigemInvalida(f"{doc_id} não está no registry do central em /c")
        return {"id": doc_id, "url": "https://h/s.md", "tipo": "SPEC", "titulo": "T",
                "sizing": "medium", "texto": "corpo"}  # fmt: skip


@pytest.fixture
def cli_com(montar, monkeypatch):  # noqa: F811 (fixture importada de test_descoberta)
    def _rodar(*argumentos):
        d = montar(RunnerFila(rascunho()), RedatorComOrigem())
        sessoes = []
        monkeypatch.setattr(cli, "carregar_projeto", lambda nome: d.projeto)
        monkeypatch.setattr(cli, "montar_descoberta", lambda projeto: d)
        monkeypatch.setattr(cli, "conversar", lambda desc, sessao: sessoes.append(sessao) or 0)
        monkeypatch.setattr(sys, "argv", ["fabrica", "descobrir", "zero", *argumentos])
        return cli.main(), d, sessoes

    return _rodar


def contar_sessoes(d):
    return d._db.execute("SELECT count(*) FROM descobertas").fetchone()[0]


def test_cli_origem_invalida_sai_com_2_sem_sessao(cli_com, capsys):
    saida, d, sessoes = cli_com("ideia", "--origem", "SPEC-X-0001", "--origem", "SPEC-X-0009")
    assert saida == 2
    assert "SPEC-X-0009 não está no registry do central em /c" in capsys.readouterr().out
    assert sessoes == []
    assert contar_sessoes(d) == 0


def test_cli_origem_com_retomar_sai_com_2(cli_com, capsys):
    saida, _, sessoes = cli_com("--retomar", "abc", "--origem", "SPEC-X-0001")
    assert saida == 2
    assert "--origem só vale ao iniciar uma descoberta" in capsys.readouterr().out
    assert sessoes == []


def test_cli_origem_valida_fica_na_sessao(cli_com):
    saida, d, sessoes = cli_com("ideia", "--origem", "SPEC-X-0001")
    assert saida == 0
    assert [o["id"] for o in d.dados(sessoes[0])["origens"]] == ["SPEC-X-0001"]
    assert d.avancar(sessoes[0]) == AGUARDANDO_APROVACAO


# Textos de origem para o compilador da SDD enxuta (SDD-FAB-0005, RF04)

SPEC_ENXUTA = """---
id: SPEC-X-0003
type: SPEC
status: implemented
---

# Lista

## Requisitos funcionais

| RF-ID | Requisito | Critério de aceite (EARS) | Arquivos |
|---|---|---|---|
| RF01 | Adicionar | Quando chamar adicionar, o sistema deve incluir no fim. | `a/lista.py` |

# Parte 2 — Desenho

## Contratos técnicos

`adicionar(lista, texto)`.
"""

SDD_ENXUTA = """---
id: SDD-X-0001
type: SDD
title: "Lista"
status: approved
sizing: medium
source_docs:
  - id: "SPEC-X-0003"
    url: "https://github.com/dona/central/blob/main/docs/X/03-spec/SPEC-X-0003.md"
  - id: "SPEC-X-0009"
    url: "https://github.com/dona/central/blob/main/docs/X/03-spec/SPEC-X-0009.md"
  - id: "SPEC-X-0004"
    url: "https://github.com/dona/central/blob/main/docs/X/03-spec/SPEC-X-0004.md"
  - id: "SPEC-X-0001"
    url: "https://github.com/dona/central/blob/main/docs/X/03-spec/SPEC-X-0001.md"
---

# Lista

## Requisitos consolidados

| RF-ID | Origem | Requisito (resumo) | Arquivos |
|---|---|---|---|
| RF01 | SPEC-X-0003 | Adicionar | `a/lista.py` |

## Critérios de aceite / definição de pronto

| # | Critério (origem: RF-ID / contrato) | Comando de verificação | Resultado esperado | Perfil esperado |
|---|---|---|---|---|
| 1 | RF01 | `pytest -q` | exit 0 | automatizado |
"""


def fonte_com_spec_enxuta(tmp_path):
    f = fonte(tmp_path)
    raiz = tmp_path / "central"
    (raiz / "docs/X/03-spec/SPEC-X-0003.md").write_text(SPEC_ENXUTA, encoding="utf-8")
    registro = raiz / "docs/X/registry.yaml"
    dados = yaml.safe_load(registro.read_text(encoding="utf-8"))
    dados["documents"] += [
        {"id": "SPEC-X-0003", "type": "SPEC", "title": "Lista", "status": "implemented",
         "path": "docs/X/03-spec/SPEC-X-0003.md"},
        {"id": "SPEC-X-0004", "type": "SPEC", "title": "Sem arquivo", "status": "approved",
         "path": "docs/X/03-spec/SPEC-X-0004.md"},
    ]  # fmt: skip
    registro.write_text(yaml.safe_dump(dados), encoding="utf-8")
    repo = tmp_path / "repo"
    (repo / "docs/sdd").mkdir(parents=True)
    (repo / "docs/sdd/SDD-X-0001.md").write_text(SDD_ENXUTA, encoding="utf-8")
    return f, repo


def test_textos_de_origem_pelo_registry_sem_conferir_status(tmp_path):
    f, repo = fonte_com_spec_enxuta(tmp_path)
    textos = f._textos_de_origem(repo / "docs/sdd/SDD-X-0001.md")
    assert sorted(textos) == ["SPEC-X-0001", "SPEC-X-0003"]
    assert textos["SPEC-X-0003"] == SPEC_ENXUTA


def test_textos_de_origem_sem_central_ou_sem_front_matter(tmp_path):
    repo = tmp_path / "repo"
    (repo / "docs/sdd").mkdir(parents=True)
    (repo / "docs/sdd/SDD-X-0001.md").write_text(SDD_ENXUTA, encoding="utf-8")
    assert (
        FonteDocTraceability(Framework())._textos_de_origem(repo / "docs/sdd/SDD-X-0001.md") == {}
    )
    (repo / "docs/sdd/SDD-X-0002.md").write_text("sem front-matter\n", encoding="utf-8")
    assert fonte(tmp_path)._textos_de_origem(repo / "docs/sdd/SDD-X-0002.md") == {}


def test_textos_de_origem_chegam_ao_compilar(tmp_path):
    f, repo = fonte_com_spec_enxuta(tmp_path)
    texto = (repo / "docs/sdd/SDD-X-0001.md").read_text(encoding="utf-8")
    sdd = texto.replace(
        '  - id: "SPEC-X-0009"\n    url: "https://github.com/dona/central/blob/main/docs/X/03-spec/SPEC-X-0009.md"\n'
        '  - id: "SPEC-X-0004"\n    url: "https://github.com/dona/central/blob/main/docs/X/03-spec/SPEC-X-0004.md"\n'
        '  - id: "SPEC-X-0001"\n    url: "https://github.com/dona/central/blob/main/docs/X/03-spec/SPEC-X-0001.md"\n',
        "",
    )
    (repo / "docs/sdd/SDD-X-0001.md").write_text(sdd, encoding="utf-8")
    entrada = f.compilar(repo, "docs/sdd/SDD-X-0001.md")
    assert entrada["especificacao"].startswith(
        "# SPEC-X-0003\n\n# Parte 2 — Desenho\n\n## Contratos técnicos"
    )
    assert entrada["requisitos"][0]["aceite"] == (
        "Quando chamar adicionar, o sistema deve incluir no fim."
    )


def test_formato_e_problemas_de_redacao_repassam_ao_kit(tmp_path):
    f = fonte(tmp_path)
    repo = tmp_path / "repo"
    assert f.formato_da_sdd(repo, [{"id": "SPEC-X-0001"}]) == "enxuta"
    assert f.formato_da_sdd(repo, []) == "completa"
    (repo / "docs/sdd").mkdir(parents=True)
    (repo / "docs/sdd/registry.yaml").write_text(
        'project: "X"\nframework_version: "2.7.0"\ndocuments: []\n', encoding="utf-8"
    )
    (repo / "docs/sdd/SDD-X-0001.md").write_text(
        SDD_ENXUTA.replace("status: approved", "status: draft"), encoding="utf-8"
    )
    problemas = f.problemas_de_redacao(repo, "docs/sdd/SDD-X-0001.md")
    assert problemas and all(p.startswith("validate_doc.py: ") for p in problemas), problemas


# SDD-FAB-0009, RF09: aprovação por política na entrada


def sdd_de_politica(tmp_path, corromper=False, kind="policy"):
    from adapters.doc_traceability.redacao import aprovar_por_politica, escrever_sdd
    from tests.test_redacao import ENXUTO, ORIGENS
    from tests.test_redacao import registry as registry_da_redacao

    repo = tmp_path / "repo"
    registry_da_redacao(repo, "2.7.0")
    caminho = escrever_sdd(
        repo, ENXUTO, "ZERO", "Dona", "2026-11-21", "approved", "2.7.0", origens=ORIGENS[:1]
    )
    if kind == "policy":
        aprovar_por_politica(repo, caminho, Framework(), "2026-11-21T14:00:00Z")
    if corromper:
        arquivo = repo / caminho
        arquivo.write_text(arquivo.read_text(encoding="utf-8") + "\nEditado.\n", "utf-8")
    return repo, caminho


def test_politica_verde_e_aprovada(tmp_path):
    repo, caminho = sdd_de_politica(tmp_path)
    assert FonteDocTraceability().aprovacao_por_politica(repo, caminho) == (True, [])


def test_politica_com_hash_quebrado_devolve_os_motivos(tmp_path):
    repo, caminho = sdd_de_politica(tmp_path, corromper=True)
    aprovada, motivos = FonteDocTraceability().aprovacao_por_politica(repo, caminho)
    assert aprovada is False
    assert any("mudou depois da aprovação" in m for m in motivos), motivos


def test_politica_sdd_sem_kind_policy_nao_e_de_politica(tmp_path):
    repo, caminho = sdd_de_politica(tmp_path, kind=None)
    assert FonteDocTraceability().aprovacao_por_politica(repo, caminho) == (False, [])


# SDD-FAB-0012, RF01: check_source_docs.py no host, contra origin/main do central


def central_com_remoto(tmp_path):
    """Central com a SPEC-ZERO-0001 approved, clonado de um remoto nu; devolve (clone, remoto)."""
    from tests.test_redacao import central as central_da_redacao

    inicial = central_da_redacao(tmp_path / "inicial")
    git("init", "-q", "-b", "main", cwd=inicial)
    git("add", "-A", cwd=inicial)
    git("commit", "-qm", "inicio", cwd=inicial)
    remoto_nu = tmp_path / "central.git"
    git("clone", "-q", "--bare", str(inicial), str(remoto_nu), cwd=tmp_path)
    clone = tmp_path / "central"
    git("clone", "-q", str(remoto_nu), str(clone), cwd=tmp_path)
    return clone, inicial, remoto_nu


def sdd_com_origem(tmp_path):
    import copy

    from adapters.doc_traceability.redacao import escrever_sdd
    from tests.test_redacao import ENXUTO
    from tests.test_redacao import registry as registry_da_redacao

    repo = tmp_path / "repo"
    registry_da_redacao(repo, "2.7.0")
    sdd = copy.deepcopy(ENXUTO)
    sdd["requisitos"].append(sdd["requisitos"][0] | {"id": "RF02", "requisito": "Remover"})
    origens = [
        {"id": "SPEC-ZERO-0001", "url": "https://h/blob/main/docs/ZERO/03-spec/SPEC-ZERO-0001.md"}
    ]
    caminho = escrever_sdd(
        repo, sdd, "ZERO", "Dona", "2026-11-24", "approved", "2.7.0", origens=origens
    )
    return repo, caminho


def test_fidelidade_com_spec_approved_devolve_a_linha_mecanica(tmp_path):
    clone, _, _ = central_com_remoto(tmp_path)
    repo, caminho = sdd_com_origem(tmp_path)
    ok, linha = FonteDocTraceability(Framework(), clone, "ZERO").fidelidade_a_origem(repo, caminho)
    assert ok is True, linha["saida"]
    assert linha["numero"] == "Fidelidade à origem (check_source_docs)"
    assert linha["passou"] is True
    assert "check_source_docs.py" in linha["comando"]
    assert caminho in linha["comando"]
    assert linha["sensor"] == "sem teste automatizado (script do kit)"
    assert (linha["assertion"], linha["perfil"]) == ("n/a", "n/a")


def test_fidelidade_le_origin_main_e_nao_a_arvore_do_clone(tmp_path):
    clone, inicial, remoto_nu = central_com_remoto(tmp_path)
    repo, caminho = sdd_com_origem(tmp_path)
    # A SPEC volta a draft em origin/main; a árvore do clone segue com approved.
    registro = inicial / "docs/ZERO/registry.yaml"
    registro.write_text(
        registro.read_text(encoding="utf-8").replace("status: approved", "status: draft"),
        encoding="utf-8",
    )
    git("commit", "-qam", "spec em draft", cwd=inicial)
    git("push", "-q", str(remoto_nu), "main", cwd=inicial)
    assert "status: approved" in (clone / "docs/ZERO/registry.yaml").read_text(encoding="utf-8")
    ok, linha = FonteDocTraceability(Framework(), clone, "ZERO").fidelidade_a_origem(repo, caminho)
    assert ok is False
    assert linha["passou"] is False
    assert "draft" in linha["saida"]


def test_fidelidade_com_fetch_falho_levanta_called_process_error(tmp_path):
    import shutil
    import subprocess

    clone, _, remoto_nu = central_com_remoto(tmp_path)
    repo, caminho = sdd_com_origem(tmp_path)
    shutil.rmtree(remoto_nu)
    with pytest.raises(subprocess.CalledProcessError):
        FonteDocTraceability(Framework(), clone, "ZERO").fidelidade_a_origem(repo, caminho)


def test_fidelidade_textos_de_origem_publico_le_pelo_registry(tmp_path):
    f, repo = fonte_com_spec_enxuta(tmp_path)
    textos = f.textos_de_origem(repo, "docs/sdd/SDD-X-0001.md")
    assert textos["SPEC-X-0003"] == SPEC_ENXUTA

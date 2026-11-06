import subprocess

import pytest

from fabrica import publicacao
from fabrica.publicacao import (
    LIMITE_CORPO_PR,
    Github,
    PublicacaoRecusada,
    concluir_release,
    enviar_ramo,
    montar_corpo_pr,
    preparar_release,
)


def git(*args, cwd):
    comando = ["git", "-c", "user.email=t@t", "-c", "user.name=t", *args]
    return subprocess.run(
        comando, cwd=cwd, check=True, capture_output=True, text=True
    ).stdout.strip()


@pytest.mark.parametrize("ramo", ["main", "develop", "master", "hotfix/1.0.0", "feature", "x/y"])
def test_push_recusado_fora_de_feature_e_release(ramo, tmp_path):
    with pytest.raises(PublicacaoRecusada):
        enviar_ramo(tmp_path, "url", ramo)


@pytest.mark.parametrize("base", ["main", "master", "release/1.0.0"])
def test_merge_recusado_com_destino_diferente_de_develop(base, monkeypatch):
    github = Github("o/r")
    chamadas = []
    monkeypatch.setattr(
        github, "_pr", lambda *_: {"baseRefName": base, "headRefOid": "abc", "state": "OPEN"}
    )
    monkeypatch.setattr(github, "_gh", lambda *a: chamadas.append(a) or "")
    with pytest.raises(PublicacaoRecusada, match="merge recusado"):
        github.fazer_merge_em_develop(1)
    assert chamadas == []


def test_merge_em_develop_fixa_o_commit_verificado(monkeypatch):
    github = Github("o/r")
    chamadas = []
    monkeypatch.setattr(
        github, "_pr", lambda *_: {"baseRefName": "develop", "headRefOid": "abc", "state": "OPEN"}
    )
    monkeypatch.setattr(github, "_gh", lambda *a: chamadas.append(a) or "")
    github.fazer_merge_em_develop(1)
    assert "--match-head-commit" in chamadas[0] and "abc" in chamadas[0]


def test_github_nao_tem_merge_generico():
    escrita = [n for n in dir(Github) if "merge" in n and n != "quem_mergeou_o_commit"]
    assert escrita == ["fazer_merge_em_develop"]


WORKFLOW_OK = {"name": "a", "status": "COMPLETED", "conclusion": "SUCCESS"}


@pytest.mark.parametrize(
    ("itens", "esperado"),
    [
        ([], ("sem_checks", "")),
        ([WORKFLOW_OK], ("passou", "")),
        ([{"name": "a", "status": "COMPLETED", "conclusion": "SKIPPED"}], ("passou", "")),
        ([WORKFLOW_OK, {"name": "b", "status": "IN_PROGRESS", "conclusion": ""}], ("pendente", "")),
        (
            [WORKFLOW_OK, {"name": "b", "status": "COMPLETED", "conclusion": "FAILURE"}],
            ("falhou", "b"),
        ),
        ([{"name": "b", "status": "COMPLETED", "conclusion": "CANCELLED"}], ("falhou", "b")),
        ([{"context": "ext", "state": "PENDING"}], ("pendente", "")),
        ([{"context": "ext", "state": "SUCCESS"}], ("passou", "")),
        ([{"context": "ext", "state": "FAILURE"}], ("falhou", "ext")),
    ],
)
def test_situacao_dos_checks(itens, esperado, monkeypatch):
    github = Github("o/r")
    monkeypatch.setattr(github, "_pr", lambda *_: {"statusCheckRollup": itens})
    assert github.checks(1) == esperado


def test_corpo_curto_leva_a_sdd_inteira():
    corpo = montar_corpo_pr("resumo", "conteúdo da SDD", "abc", "docs/s.md", "o/r")
    assert "conteúdo da SDD" in corpo and "cortada" not in corpo


def test_corpo_longo_respeita_o_limite_do_github():
    corpo = montar_corpo_pr("resumo", "x" * 76000, "abc", "docs/s.md", "o/r")
    assert len(corpo) <= LIMITE_CORPO_PR < 65536
    assert "https://github.com/o/r/blob/abc/docs/s.md" in corpo


class GithubDeRelease:
    def __init__(self, aberta=None):
        self.aberta = aberta
        self.abertas = []
        self.fechadas = []

    def release_aberta(self, principal):
        return self.aberta

    def abrir_pr(self, ramo, base, titulo, corpo):
        self.abertas.append((ramo, base, corpo))
        return 9

    def fechar_pr(self, numero, comentario):
        self.fechadas.append(numero)


@pytest.fixture
def remoto(tmp_path):
    origem = tmp_path / "origem"
    origem.mkdir()
    git("init", "-q", "-b", "main", cwd=origem)
    (origem / "a").write_text("a\n")
    git("add", "-A", cwd=origem)
    git("commit", "-qm", "chore: base", cwd=origem)
    git("tag", "-a", "v0.1.0", "-m", "x", cwd=origem)
    git("switch", "-qc", "develop", cwd=origem)
    (origem / "b").write_text("b\n")
    git("add", "-A", cwd=origem)
    git("commit", "-qm", "feat: novo", cwd=origem)
    git("switch", "-q", "main", cwd=origem)
    return origem


def test_release_abre_pr_para_main_com_a_versao_calculada(remoto):
    github = GithubDeRelease()
    assert preparar_release(github, str(remoto), "develop", "main") == (9, "0.2.0")
    ramo, base, corpo = github.abertas[0]
    assert (ramo, base) == ("release/0.2.0", "main")
    assert "feat: novo" in corpo and "aprovação humana" in corpo
    assert git("rev-parse", "release/0.2.0", cwd=remoto) == git("rev-parse", "develop", cwd=remoto)


def test_release_com_versao_nova_substitui_a_pr_aberta(remoto):
    github = GithubDeRelease(aberta=(5, "release/0.1.1"))
    preparar_release(github, str(remoto), "develop", "main")
    assert github.fechadas == [5]


def test_release_nao_toca_em_main(remoto):
    antes = git("rev-parse", "main", cwd=remoto)
    preparar_release(GithubDeRelease(), str(remoto), "develop", "main")
    assert git("rev-parse", "main", cwd=remoto) == antes


def test_sem_novidade_nao_abre_release(remoto):
    git("merge", "-q", "--ff-only", "develop", cwd=remoto)
    with pytest.raises(publicacao.FalhaDePublicacao, match="nada novo"):
        preparar_release(GithubDeRelease(), str(remoto), "develop", "main")


def test_pos_release_recusa_sem_o_merge_humano(remoto):
    preparar_release(GithubDeRelease(), str(remoto), "develop", "main")
    with pytest.raises(PublicacaoRecusada, match="merge humano"):
        concluir_release(str(remoto), "develop", "main", None, "0.2.0")
    assert "v0.2.0" not in git("tag", cwd=remoto)


def test_pos_release_cria_tag_e_atualiza_develop(remoto):
    preparar_release(GithubDeRelease(), str(remoto), "develop", "main")
    git("merge", "-q", "--no-ff", "-m", "merge humano", "release/0.2.0", cwd=remoto)
    concluir_release(str(remoto), "develop", "main", None, "0.2.0")
    assert "v0.2.0" in git("tag", cwd=remoto)
    assert git("rev-parse", "develop", cwd=remoto) == git("rev-parse", "main", cwd=remoto)


def test_release_mergeada_sem_pos_release_nao_reabre_o_mesmo_numero(remoto):
    preparar_release(GithubDeRelease(), str(remoto), "develop", "main")
    git("merge", "-q", "--no-ff", "-m", "merge humano", "release/0.2.0", cwd=remoto)
    antes = git("rev-parse", "release/0.2.0", cwd=remoto)
    git("switch", "-q", "develop", cwd=remoto)
    git("commit", "-q", "--allow-empty", "-m", "feat: depois da release", cwd=remoto)
    git("switch", "-q", "main", cwd=remoto)
    github = GithubDeRelease()
    with pytest.raises(publicacao.FalhaDePublicacao, match="pós-release"):
        preparar_release(github, str(remoto), "develop", "main")
    assert github.abertas == []
    assert git("rev-parse", "release/0.2.0", cwd=remoto) == antes


def test_pos_release_com_develop_adiantada_cria_a_tag_e_nao_mexe_em_develop(remoto):
    preparar_release(GithubDeRelease(), str(remoto), "develop", "main")
    git("merge", "-q", "--no-ff", "-m", "merge humano", "release/0.2.0", cwd=remoto)
    git("switch", "-q", "develop", cwd=remoto)
    git("commit", "-q", "--allow-empty", "-m", "feat: depois da release", cwd=remoto)
    git("switch", "-q", "main", cwd=remoto)
    develop = git("rev-parse", "develop", cwd=remoto)
    concluir_release(str(remoto), "develop", "main", None, "0.2.0")
    assert "v0.2.0" in git("tag", cwd=remoto)
    assert git("rev-parse", "develop", cwd=remoto) == develop

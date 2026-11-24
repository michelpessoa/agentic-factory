import json
import subprocess

import pytest

from fabrica import publicacao
from fabrica.publicacao import (
    LIMITE_CORPO_PR,
    Github,
    PublicacaoRecusada,
    concluir_release,
    enviar_ramo,
    enviar_ramo_documento,
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
    assert escrita == ["fazer_merge_de_documento", "fazer_merge_em_develop"]


RAMOS_FORA_DE_DOCUMENTO = [
    "main",
    "develop",
    "feature/x",
    "docs/adr-zero-0001",
    "docs/spec-zero-1",
    "docs/SPEC-ZERO-0001",
    "docs/spec-zero-0001/x",
    "docs/spec-0001",
]


@pytest.mark.parametrize("ramo", RAMOS_FORA_DE_DOCUMENTO)
def test_push_de_documento_recusado_fora_de_docs_id(ramo, tmp_path):
    with pytest.raises(PublicacaoRecusada, match="push recusado"):
        enviar_ramo_documento(tmp_path, "url", ramo)


def test_push_de_documento_envia_o_ramo_sem_force(tmp_path):
    nu = tmp_path / "nu.git"
    git("init", "-q", "--bare", str(nu), cwd=tmp_path)
    clone = tmp_path / "clone"
    clone.mkdir()
    git("init", "-q", "-b", "main", cwd=clone)
    (clone / "a").write_text("a\n")
    git("add", "-A", cwd=clone)
    git("commit", "-qm", "docs: a", cwd=clone)
    enviar_ramo_documento(clone, str(nu), "docs/rfc-zero-0002")
    assert git("rev-parse", "docs/rfc-zero-0002", cwd=nu) == git("rev-parse", "HEAD", cwd=clone)
    # Histórico divergente no remoto: sem `--force`, o push é recusado e o remoto não muda.
    git("commit", "-q", "--amend", "-m", "docs: outro", cwd=clone)
    remoto_antes = git("rev-parse", "docs/rfc-zero-0002", cwd=nu)
    with pytest.raises(publicacao.FalhaDePublicacao):
        enviar_ramo_documento(clone, str(nu), "docs/rfc-zero-0002")
    assert git("rev-parse", "docs/rfc-zero-0002", cwd=nu) == remoto_antes


@pytest.mark.parametrize("ramo", RAMOS_FORA_DE_DOCUMENTO)
def test_pr_de_documento_recusada_fora_de_docs_id(ramo, monkeypatch):
    github = Github("o/r")
    chamadas = []
    monkeypatch.setattr(github, "_gh", lambda *a: chamadas.append(a) or "")
    with pytest.raises(PublicacaoRecusada, match=f"push recusado para o ramo {ramo!r}"):
        github.abrir_pr_documento(ramo, "t", "c")
    assert chamadas == []


def test_pr_de_documento_vai_para_main_pela_api_rest(monkeypatch):
    github = Github("o/r")
    chamadas = []
    monkeypatch.setattr(github, "_gh", lambda *a: chamadas.append(a) or '{"number": 12}')
    assert github.abrir_pr_documento("docs/spec-zero-0001", "titulo", "corpo") == 12
    (chamada,) = [c for c in chamadas if "repos/o/r/pulls" in c]
    assert chamada[0] == "api" and "POST" in chamada
    assert "head=docs/spec-zero-0001" in chamada and "base=main" in chamada
    assert "title=titulo" in chamada and "body=corpo" in chamada


def _github_de_merge(monkeypatch, pr):
    github = Github("o/r")
    chamadas = []

    def gh(*args):
        chamadas.append(args)
        if args[-1] == "repos/o/r/pulls/5":
            return json.dumps(pr)
        return '{"sha": "merge123", "merged": true}'

    monkeypatch.setattr(github, "_gh", gh)
    return github, chamadas


@pytest.mark.parametrize(
    ("base", "head"),
    [("develop", "docs/spec-zero-0001"), ("main", "feature/x"), ("main", "docs/adr-zero-0001")],
)
def test_merge_de_documento_recusa_fora_de_docs_id_para_main(base, head, monkeypatch):
    pr = {"base": {"ref": base}, "head": {"ref": head, "sha": "abc"}, "merged": False}
    github, chamadas = _github_de_merge(monkeypatch, pr)
    with pytest.raises(PublicacaoRecusada, match=f"merge recusado: {head} → {base}"):
        github.fazer_merge_de_documento(5)
    assert not any("PUT" in c for c in chamadas)


def test_merge_de_documento_fixa_o_head_e_devolve_o_sha(monkeypatch):
    pr = {
        "base": {"ref": "main"},
        "head": {"ref": "docs/spec-zero-0001", "sha": "abc"},
        "merged": False,
    }
    github, chamadas = _github_de_merge(monkeypatch, pr)
    assert github.fazer_merge_de_documento(5) == "merge123"
    merge = chamadas[-1]
    assert "PUT" in merge and "repos/o/r/pulls/5/merge" in merge
    assert "merge_method=merge" in merge and "sha=abc" in merge


def test_merge_de_documento_ja_mergeado_devolve_o_merge(monkeypatch):
    pr = {
        "base": {"ref": "main"},
        "head": {"ref": "docs/rfc-zero-0003", "sha": "abc"},
        "merged": True,
        "merge_commit_sha": "feito",
    }
    github, chamadas = _github_de_merge(monkeypatch, pr)
    assert github.fazer_merge_de_documento(5) == "feito"
    assert len(chamadas) == 1


@pytest.mark.parametrize("base", ["main", "master"])
def test_documento_nao_abre_merge_em_develop_para_main(base, monkeypatch):
    github = Github("o/r")
    monkeypatch.setattr(
        github, "_pr", lambda *_: {"baseRefName": base, "headRefOid": "abc", "state": "OPEN"}
    )
    monkeypatch.setattr(github, "_gh", lambda *a: "")
    with pytest.raises(PublicacaoRecusada, match="merge recusado"):
        github.fazer_merge_em_develop(1)


def test_leitura_do_ramo_e_das_reviews_pela_api_rest(monkeypatch):
    github = Github("dono/central")
    chamadas = []

    def gh(*args):
        chamadas.append(args)
        if args[-1] == "user":
            return '{"login": "executor"}'
        if "reviews" in args[-1]:
            return '[{"id": 1}]'
        return '[{"number": 4}, {"number": 5}]'

    monkeypatch.setattr(github, "_gh", gh)
    assert github.login() == "executor"
    assert github.pr_aberta_do_ramo("docs/spec-zero-0001") == {"number": 4}
    assert github.reviews(4) == [{"id": 1}]
    assert chamadas[1][-1] == ("repos/dono/central/pulls?head=dono:docs/spec-zero-0001&state=open")
    assert chamadas[2][-1] == "repos/dono/central/pulls/4/reviews?per_page=100"
    monkeypatch.setattr(github, "_gh", lambda *a: "[]")
    assert github.pr_aberta_do_ramo("docs/spec-zero-0001") is None


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


def _github_gravando(monkeypatch, existentes):
    github = Github("o/r")
    chamadas = []

    def gh(*args):
        chamadas.append(args)
        if args[:2] == ("pr", "list"):
            return existentes
        if args[:2] == ("pr", "create"):
            return "https://github.com/o/r/pull/7\n"
        return ""

    monkeypatch.setattr(github, "_gh", gh)
    return github, chamadas


def _etiquetagem(chamadas, numero):
    return [
        c
        for c in chamadas
        if c[:2] == ("api", f"repos/o/r/issues/{numero}/labels")
        and f"labels[]={publicacao.ETIQUETA_PR}" in c
    ]


def test_pr_nova_sai_com_a_etiqueta_da_fabrica(monkeypatch):
    github, chamadas = _github_gravando(monkeypatch, "[]")
    assert github.abrir_pr("feature/x", "develop", "t", "c") == 7
    rotulo = next(c for c in chamadas if c[:2] == ("label", "create"))
    criacao = next(c for c in chamadas if c[:2] == ("pr", "create"))
    assert publicacao.ETIQUETA_PR in rotulo and "--force" in rotulo
    assert chamadas.index(rotulo) < chamadas.index(criacao)
    assert len(_etiquetagem(chamadas, 7)) == 1


def test_pr_ja_aberta_recebe_a_etiqueta(monkeypatch):
    github, chamadas = _github_gravando(monkeypatch, '[{"number": 3}]')
    assert github.abrir_pr("feature/x", "develop", "t", "corpo novo") == 3
    assert len(_etiquetagem(chamadas, 3)) == 1
    atualizacao = next(c for c in chamadas if "repos/o/r/pulls/3" in c)
    assert "PATCH" in atualizacao and "body=corpo novo" in atualizacao and "title=t" in atualizacao
    assert not any(c[:2] in {("pr", "create"), ("pr", "edit")} for c in chamadas)


# SDD-FAB-0010, RF03: a PR de documento do central sai com a etiqueta, para o vigia a conferir


def test_pr_de_documento_sai_com_a_etiqueta_da_fabrica(monkeypatch):
    github = Github("o/r")
    chamadas = []
    monkeypatch.setattr(github, "_gh", lambda *a: chamadas.append(a) or '{"number": 12}')
    assert github.abrir_pr_documento("docs/spec-zero-0001", "titulo", "corpo") == 12
    rotulo = next(c for c in chamadas if c[:2] == ("label", "create"))
    criacao = next(c for c in chamadas if "repos/o/r/pulls" in c and "POST" in c)
    (etiquetagem,) = _etiquetagem(chamadas, 12)
    assert publicacao.ETIQUETA_PR in rotulo and "--force" in rotulo
    assert chamadas.index(rotulo) < chamadas.index(criacao) < chamadas.index(etiquetagem)

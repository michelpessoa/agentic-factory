import subprocess

import pytest

from fabrica.aprovacoes import Aprovacoes
from fabrica.pipeline import ExecucaoEmAberto
from fabrica.vigia import Vigia


def git(*args, cwd):
    comando = ["git", "-c", "user.email=t@t", "-c", "user.name=t", *args]
    subprocess.run(comando, cwd=cwd, check=True, capture_output=True)


class FonteFalsa:
    def sdds_aprovadas(self, repo):
        pasta = repo / "docs/sdd"
        return sorted(
            str(c.relative_to(repo)) for c in pasta.glob("*.md") if "approved" in c.read_text()
        )


@pytest.fixture
def remoto(tmp_path):
    origem = tmp_path / "origem"
    (origem / "docs/sdd").mkdir(parents=True)
    git("init", "-q", "-b", "develop", cwd=origem)
    (origem / "docs/sdd/a.md").write_text("approved\n")
    git("add", "-A", cwd=origem)
    git("commit", "-qm", "a", cwd=origem)
    return origem


class AprovaTudo:
    def aprovada(self, projeto, sdd, conteudo):
        return True


@pytest.fixture
def vigia(remoto, tmp_path):
    return Vigia(tmp_path / "f.db", "X", str(remoto), "develop", FonteFalsa(), AprovaTudo())


def escrever(remoto, nome, conteudo):
    (remoto / nome).write_text(conteudo)
    git("add", "-A", cwd=remoto)
    git("commit", "-qm", nome, cwd=remoto)


def test_primeira_leitura_nao_dispara_o_que_ja_existe(vigia):
    disparadas = []
    assert vigia.verificar(disparadas.append) == []
    assert disparadas == []


def test_primeira_leitura_sem_nenhuma_sdd_aprovada_tambem_conta(remoto, vigia):
    escrever(remoto, "docs/sdd/a.md", "draft\n")
    vigia.verificar(lambda _: None)
    escrever(remoto, "docs/sdd/b.md", "approved\n")
    assert vigia.verificar(lambda _: None) == ["docs/sdd/b.md"]


def test_sdd_nova_aprovada_dispara_uma_vez(remoto, vigia):
    vigia.verificar(lambda _: None)
    escrever(remoto, "docs/sdd/b.md", "approved\n")
    disparadas = []
    assert vigia.verificar(disparadas.append) == ["docs/sdd/b.md"]
    assert disparadas == ["docs/sdd/b.md"]
    assert vigia.verificar(disparadas.append) == []


def test_sdd_em_rascunho_nao_dispara(remoto, vigia):
    vigia.verificar(lambda _: None)
    escrever(remoto, "docs/sdd/b.md", "draft\n")
    assert vigia.verificar(lambda _: None) == []


def test_passar_a_aprovada_dispara(remoto, vigia):
    escrever(remoto, "docs/sdd/b.md", "draft\n")
    vigia.verificar(lambda _: None)
    escrever(remoto, "docs/sdd/b.md", "approved\n")
    assert vigia.verificar(lambda _: None) == ["docs/sdd/b.md"]


def test_corrigir_e_reaprovar_dispara_de_novo(remoto, vigia):
    vigia.verificar(lambda _: None)
    escrever(remoto, "docs/sdd/a.md", "approved corrigida\n")
    assert vigia.verificar(lambda _: None) == ["docs/sdd/a.md"]


def test_estado_persiste_entre_processos(remoto, tmp_path):
    banco = tmp_path / "f.db"
    Vigia(banco, "X", str(remoto), "develop", FonteFalsa(), AprovaTudo()).verificar(lambda _: None)
    assert (
        Vigia(banco, "X", str(remoto), "develop", FonteFalsa(), AprovaTudo()).verificar(
            lambda _: None
        )
        == []
    )


def test_projetos_nao_se_misturam(remoto, tmp_path):
    banco = tmp_path / "f.db"
    Vigia(banco, "X", str(remoto), "develop", FonteFalsa(), AprovaTudo()).verificar(lambda _: None)
    outro = Vigia(banco, "Y", str(remoto), "develop", FonteFalsa(), AprovaTudo())
    assert outro.verificar(lambda _: None) == []


def test_sdd_com_execucao_em_aberto_nao_derruba_o_vigia(remoto, vigia):
    vigia.verificar(lambda _: None)
    escrever(remoto, "docs/sdd/b.md", "approved\n")
    escrever(remoto, "docs/sdd/c.md", "approved\n")
    disparadas = []

    def disparar(sdd):
        if sdd.endswith("b.md"):
            raise ExecucaoEmAberto("em aberto")
        disparadas.append(sdd)

    assert vigia.verificar(disparar) == ["docs/sdd/c.md"]


def test_sdd_sem_aprovacao_no_terminal_espera_e_dispara_depois_de_aprovada(remoto, tmp_path):
    aprovacoes = Aprovacoes(tmp_path / "f.db")
    vigia = Vigia(tmp_path / "f.db", "X", str(remoto), "develop", FonteFalsa(), aprovacoes)
    vigia.verificar(lambda _: None)
    escrever(remoto, "docs/sdd/b.md", "approved\n")
    assert vigia.verificar(lambda _: None) == []
    aprovacoes.registrar("X", "docs/sdd/b.md", b"approved\n", "terminal")
    assert vigia.verificar(lambda _: None) == ["docs/sdd/b.md"]

import copy
import subprocess

import pytest

from adapters.doc_traceability import FonteDocTraceability
from adapters.doc_traceability.validadores import FRAMEWORK_PADRAO
from fabrica import __main__ as cli
from fabrica.aprovacoes import Aprovacoes
from fabrica.contratos import Cartorio
from fabrica.descoberta import (
    AGUARDANDO_APROVACAO,
    AGUARDANDO_RESPOSTAS,
    APROVADA,
    PARADA,
    PUBLICANDO,
    Descoberta,
    DescobertaInvalida,
    problemas_do_rascunho,
)
from fabrica.execucao import ResultadoAgente
from fabrica.pipeline import Projeto

RASCUNHO = {
    "titulo": "Lista de tarefas",
    "resumo": "Guarda tarefas pessoais.",
    "sizing": "small",
    "arquitetura": "Python 3, sem dependência.",
    "requisitos": [
        {
            "id": "RF01",
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


def git(*args, cwd):
    comando = ["git", "-c", "user.email=t@t", "-c", "user.name=t", *args]
    return subprocess.run(comando, cwd=cwd, check=True, capture_output=True, text=True).stdout


@pytest.fixture
def remoto(tmp_path):
    origem = tmp_path / "origem"
    origem.mkdir()
    git("init", "-q", "-b", "develop", cwd=origem)
    (origem / "README.md").write_text("# Projeto novo\n")
    git("add", "-A", cwd=origem)
    git("commit", "-qm", "inicio", cwd=origem)
    git("config", "receive.denyCurrentBranch", "ignore", cwd=origem)
    return origem


def perguntas(*itens):
    return lambda c: resposta(c, "perguntas", list(itens), None)


def rascunho(valor=None):
    return lambda c: resposta(c, "rascunho", [], copy.deepcopy(valor or RASCUNHO))


def resposta(contrato, status, itens, conteudo):
    return {
        "contrato_id": contrato["contrato_id"],
        "token": contrato["token"],
        "etapa": "descoberta",
        "status": status,
        "perguntas": itens,
        "rascunho": conteudo,
    }


class RunnerFila:
    def __init__(self, *respostas):
        self.respostas = list(respostas)
        self.contratos = []

    def executar(self, prompt, schema, dir_trabalho, modelo, ferramentas):
        import json
        import re

        contrato = json.loads(re.search(r"```json\n(.*?)\n```", prompt, re.DOTALL).group(1))
        self.contratos.append(contrato)
        assert ferramentas == []
        assert list(dir_trabalho.iterdir()) == []
        return ResultadoAgente(self.respostas.pop(0)(contrato), 0.05)


class RedatorFalso:
    def __init__(self, *problemas):
        self.problemas = list(problemas)

    def escrever_sdd(self, repo, rascunho, codigo, owner, hoje, status, sdd_id=None):
        sdd_id = sdd_id or f"SDD-{codigo}-0001"
        caminho = f"docs/sdd/{sdd_id}.md"
        (repo / "docs/sdd").mkdir(parents=True, exist_ok=True)
        (repo / caminho).write_text(f"status: {status}\n{rascunho['titulo']}\n")
        return caminho

    def problemas_de_entrada(self, repo, caminho_sdd):
        return self.problemas.pop(0) if self.problemas else []


class GithubFalso:
    def __init__(self, checks=("passou", "")):
        self.checks = checks
        self.prs = []
        self.merges = []

    def abrir_pr(self, ramo, base, titulo, corpo):
        self.prs.append(ramo)
        return 5

    def esperar_checks(self, numero):
        return self.checks

    def fazer_merge_em_develop(self, numero):
        self.merges.append(numero)


@pytest.fixture
def montar(remoto, tmp_path):
    def _montar(runner, redator=None, github=None):
        projeto = Projeto("ZERO", str(remoto), "o/r", owner="Dona")
        banco = tmp_path / "f.db"
        return Descoberta(
            projeto,
            banco,
            Cartorio(banco),
            runner,
            redator or RedatorFalso(),
            Aprovacoes(banco),
            github or GithubFalso(),
            tmp_path / "descobertas",
        )

    return _montar


def test_pergunta_ao_humano_e_leva_as_respostas_para_a_rodada_seguinte(montar):
    runner = RunnerFila(perguntas("Quem usa?", "Qual linguagem?"), rascunho())
    d = montar(runner)
    sessao = d.criar("lista de tarefas")
    assert d.avancar(sessao) == AGUARDANDO_RESPOSTAS
    d.responder(sessao, ["só eu", "Python"])
    assert d.avancar(sessao) == AGUARDANDO_APROVACAO
    conversa = runner.contratos[1]["entrada"]["conversa"]
    assert conversa == [
        {"perguntas": ["Quem usa?", "Qual linguagem?"], "respostas": ["só eu", "Python"]}
    ]
    assert runner.contratos[1]["entrada"]["rodadas_restantes"] == 3
    dados = d.dados(sessao)
    assert dados["sdd_id"] == "SDD-ZERO-0001"
    with open(dados["arquivo"], encoding="utf-8") as arquivo:
        assert arquivo.read().startswith("status: draft")


def test_numero_de_respostas_precisa_bater(montar):
    d = montar(RunnerFila(perguntas("Quem usa?")))
    sessao = d.criar("x")
    d.avancar(sessao)
    with pytest.raises(DescobertaInvalida):
        d.responder(sessao, ["a", "b"])


def test_rascunho_reprovado_volta_ao_agente_com_os_problemas(montar):
    runner = RunnerFila(rascunho(), rascunho())
    d = montar(runner, RedatorFalso(["validate_doc: sem EARS"]))
    sessao = d.criar("x")
    assert d.avancar(sessao) == AGUARDANDO_APROVACAO
    assert runner.contratos[1]["entrada"]["problemas"] == ["validate_doc: sem EARS"]
    assert runner.contratos[1]["tentativa"] == 2
    assert d.dados(sessao)["recusas"] == [{"tentativa": 1, "problemas": ["validate_doc: sem EARS"]}]


def test_tres_rascunhos_reprovados_param(montar):
    errado = copy.deepcopy(RASCUNHO)
    errado["requisitos"][0]["arquivos"] = ["a/../../fora.py"]
    d = montar(RunnerFila(rascunho(errado), rascunho(errado), rascunho(errado)))
    sessao = d.criar("x")
    assert d.avancar(sessao) == PARADA
    assert "arquivo fora do código do projeto: a/../../fora.py" in d.dados(sessao)["problemas"]


def test_resposta_fora_do_contrato_conta_como_tentativa(montar):
    def invalida(contrato):
        return resposta(contrato, "rascunho", [], None) | {"token": "x" * 43}

    d = montar(RunnerFila(invalida, rascunho()))
    sessao = d.criar("x")
    assert d.avancar(sessao) == AGUARDANDO_APROVACAO
    assert d.dados(sessao)["tentativa"] == 2


def test_sem_rodadas_restantes_nao_aceita_mais_perguntas(montar):
    respostas = [
        perguntas("Pergunta 1?"),
        perguntas("Pergunta 2?"),
        perguntas("Pergunta 3?"),
        perguntas("Pergunta 4?"),
    ]
    d = montar(RunnerFila(*respostas, perguntas("Pergunta 5?"), rascunho()))
    sessao = d.criar("x")
    for _ in range(4):
        assert d.avancar(sessao) == AGUARDANDO_RESPOSTAS
        d.responder(sessao, ["r"])
    assert d.avancar(sessao) == AGUARDANDO_APROVACAO
    assert d.dados(sessao)["tentativa"] == 2


def test_aprovar_publica_a_sdd_aprovada_e_prende_a_aprovacao_ao_conteudo(montar, remoto):
    github = GithubFalso()
    d = montar(RunnerFila(rascunho()), github=github)
    sessao = d.criar("x")
    d.avancar(sessao)
    assert d.aprovar(sessao) == 5
    assert d.estado(sessao) == APROVADA
    assert github.merges == [5]
    ramo = github.prs[0]
    publicado = git("show", f"{ramo}:docs/sdd/SDD-ZERO-0001.md", cwd=remoto).encode()
    assert publicado.startswith(b"status: approved")
    assert d.aprovacoes.aprovada("ZERO", "docs/sdd/SDD-ZERO-0001.md", publicado)
    assert not d.aprovacoes.aprovada("ZERO", "docs/sdd/SDD-ZERO-0001.md", publicado + b" ")
    with pytest.raises(DescobertaInvalida):
        d.aprovar(sessao)


def test_aprovar_sem_rascunho_e_recusado(montar):
    d = montar(RunnerFila(perguntas("Quem usa?")))
    sessao = d.criar("x")
    d.avancar(sessao)
    with pytest.raises(DescobertaInvalida):
        d.aprovar(sessao)


def test_ci_reprovado_na_aprovacao_retoma_sem_abrir_outra_pr(montar):
    github = GithubFalso(checks=("falhou", "lint"))
    d = montar(RunnerFila(rascunho()), github=github)
    sessao = d.criar("x")
    d.avancar(sessao)
    with pytest.raises(DescobertaInvalida, match="falhou"):
        d.aprovar(sessao)
    assert d.estado(sessao) == PUBLICANDO
    github.checks = ("passou", "")
    d.aprovar(sessao)
    assert len(github.prs) == 1
    assert d.estado(sessao) == APROVADA


@pytest.mark.parametrize(
    ("mudanca", "problema"),
    [
        ({"arquivos": ["docs/sdd/x.md"]}, "arquivo fora do código do projeto: docs/sdd/x.md"),
        ({"arquivos": [".github/workflows/ci.yml"]}, "arquivo fora do código do projeto"),
        ({"id": "RF02"}, "RF02 sem critério de aceite"),
    ],
)
def test_problemas_do_rascunho(mudanca, problema):
    errado = copy.deepcopy(RASCUNHO)
    errado["requisitos"][0] |= mudanca
    assert any(problema in p for p in problemas_do_rascunho(errado))


def test_medium_com_varios_requisitos_exige_tarefas():
    medio = copy.deepcopy(RASCUNHO) | {"sizing": "medium"}
    medio["requisitos"].append(medio["requisitos"][0] | {"id": "RF02"})
    medio["criterios"].append({"criterio": "RF02: x", "comando": "true", "esperado": "exit 0"})
    assert problemas_do_rascunho(medio) == [
        "sizing medium com mais de um requisito precisa de tarefas"
    ]


def test_aprovar_fora_de_terminal_interativo_e_recusado(montar, capsys):
    d = montar(RunnerFila(rascunho()))
    sessao = d.criar("x")
    d.avancar(sessao)
    assert cli.aprovar(d, sessao) == 2
    assert d.estado(sessao) == AGUARDANDO_APROVACAO
    assert "terminal interativo" in capsys.readouterr().out


@pytest.mark.skipif(not FRAMEWORK_PADRAO.is_dir(), reason="framework ausente")
def test_rascunho_vira_sdd_que_passa_nos_validadores_reais_num_repo_vazio(montar):
    d = montar(RunnerFila(rascunho()), FonteDocTraceability())
    sessao = d.criar("x")
    assert d.avancar(sessao) == AGUARDANDO_APROVACAO, d.dados(sessao)["problemas"]
    with open(d.dados(sessao)["arquivo"], encoding="utf-8") as arquivo:
        texto = arquivo.read()
    assert "status: draft" in texto
    assert "| RF01 | Adicionar tarefa |" in texto


def test_historico_nao_mostra_token():
    from fabrica.__main__ import sem_tokens

    dados = {"validacao": {"token": "segredo", "criterios": [{"token": "x", "n": 1}]}, "pr": 2}
    assert sem_tokens(dados) == {"validacao": {"criterios": [{"n": 1}]}, "pr": 2}

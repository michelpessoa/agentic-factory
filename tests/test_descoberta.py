import copy
import hashlib
import subprocess

import pytest

from adapters.doc_traceability import FonteDocTraceability
from adapters.doc_traceability.redacao import montar_sdd
from adapters.doc_traceability.validadores import FRAMEWORK_PADRAO, Framework
from fabrica import __main__ as cli
from fabrica.aprovacoes import Aprovacoes
from fabrica.contratos import Cartorio
from fabrica.descoberta import (
    AGUARDANDO_APROVACAO,
    AGUARDANDO_RESPOSTAS,
    APROVADA,
    DIR_AGENTES,
    NO_CENTRAL,
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
            "origem": None,
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


def resposta(contrato, status, itens, conteudo, doc=None):
    return {
        "contrato_id": contrato["contrato_id"],
        "token": contrato["token"],
        "etapa": "descoberta",
        "status": status,
        "perguntas": itens,
        "rascunho": conteudo,
        "documento": doc,
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
    def __init__(self, *problemas, formato="completa", redacao=()):
        self.problemas = list(problemas)
        self.origens = []
        self.formato = formato
        self.formatos = []
        self.redacao = list(redacao)
        self.redacoes = []

    def formato_da_sdd(self, repo, origens):
        self.formatos.append(list(origens))
        return self.formato

    def problemas_de_redacao(self, repo, caminho_sdd):
        self.redacoes.append(caminho_sdd)
        return self.redacao.pop(0) if self.redacao else []

    def escrever_sdd(self, repo, rascunho, codigo, owner, hoje, status, sdd_id=None, origens=()):
        self.origens.append(origens)
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
    def _montar(runner, redator=None, github=None, escritor=None, progresso=None):
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
            escritor=escritor,
            progresso=progresso,
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


def test_branch_da_pr_da_base_sem_prefixo_duplicado(montar):
    github = GithubFalso()
    d = montar(RunnerFila(rascunho()), github=github)
    sessao = d.criar("x")
    d.avancar(sessao)
    d.aprovar(sessao)
    assert github.prs[0].startswith("feature/sdd-zero-0001-")
    assert "sdd-sdd-" not in github.prs[0]


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


@pytest.mark.skipif(not FRAMEWORK_PADRAO.is_dir(), reason="framework ausente")
def test_registry_em_documents_vazio_em_fluxo_passa_nos_validadores_na_tentativa_1(montar, remoto):
    (remoto / "docs/sdd").mkdir(parents=True)
    (remoto / "docs/sdd/registry.yaml").write_text(
        'project: "ZERO"\nframework_version: "2.7.0"\ndocuments: []\n', encoding="utf-8"
    )
    git("add", "-A", cwd=remoto)
    git("commit", "-qm", "registry vazio em fluxo", cwd=remoto)
    d = montar(RunnerFila(rascunho()), FonteDocTraceability())
    sessao = d.criar("x")
    assert d.avancar(sessao) == AGUARDANDO_APROVACAO, d.dados(sessao)["recusas"]
    assert d.dados(sessao)["tentativa"] == 1


def test_historico_nao_mostra_token():
    from fabrica.__main__ import sem_tokens

    dados = {"validacao": {"token": "segredo", "criterios": [{"token": "x", "n": 1}]}, "pr": 2}
    assert sem_tokens(dados) == {"validacao": {"criterios": [{"n": 1}]}, "pr": 2}


ORIGENS = [
    {"id": "SPEC-ZERO-0001", "url": "https://h/blob/main/docs/ZERO/03-spec/SPEC-ZERO-0001.md",
     "tipo": "SPEC", "titulo": "Lista", "sizing": "small", "texto": "---\nid: SPEC-ZERO-0001\n"},
    {"id": "ADR-ZERO-0001", "url": "https://h/blob/main/docs/ZERO/02-adr/ADR-ZERO-0001.md",
     "tipo": "ADR", "titulo": "Python", "sizing": None, "texto": "---\nid: ADR-ZERO-0001\n"},
]  # fmt: skip


def test_origem_chega_ao_agente_e_ao_redator(montar):
    runner = RunnerFila(rascunho())
    redator = RedatorFalso()
    d = montar(runner, redator)
    sessao = d.criar("lista", ORIGENS)
    assert d.avancar(sessao) == AGUARDANDO_APROVACAO
    assert runner.contratos[0]["entrada"]["origens"] == [
        {k: o[k] for k in ("id", "tipo", "titulo", "sizing", "texto")} for o in ORIGENS
    ]
    d.aprovar(sessao)
    assert redator.origens == [ORIGENS] * 3


def test_sem_origem_a_entrada_e_o_redator_recebem_lista_vazia(montar):
    runner = RunnerFila(rascunho())
    redator = RedatorFalso()
    d = montar(runner, redator)
    assert d.avancar(d.criar("lista")) == AGUARDANDO_APROVACAO
    assert runner.contratos[0]["entrada"]["origens"] == []
    assert redator.origens == [[], []]


def test_sdd_com_origem_leva_source_docs_e_os_ids():
    texto = montar_sdd(RASCUNHO, "SDD-ZERO-0001", "ZERO", "Dona", "2026-11-17", "approved", ORIGENS)
    assert (
        "source_docs:\n"
        '  - id: "SPEC-ZERO-0001"\n'
        '    url: "https://h/blob/main/docs/ZERO/03-spec/SPEC-ZERO-0001.md"\n'
        '  - id: "ADR-ZERO-0001"\n'
        '    url: "https://h/blob/main/docs/ZERO/02-adr/ADR-ZERO-0001.md"\n'
    ) in texto
    assert "Origem: SPEC-ZERO-0001, ADR-ZERO-0001, approved no central. Python 3" in texto
    assert "Sem ADR" not in texto
    assert "| source_docs | SPEC-ZERO-0001, ADR-ZERO-0001 |" in texto


def test_sdd_sem_origem_e_identica_a_de_antes():
    texto = montar_sdd(RASCUNHO, "SDD-ZERO-0001", "ZERO", "Dona", "2026-11-17", "approved")
    assert hashlib.sha256(texto.encode()).hexdigest() == (
        "22763a2ef87dbb6fe8ab1877b73802c853f78e078f9a82d9c54360e823525be7"
    )
    assert "source_docs: []" in texto


@pytest.mark.skipif(not FRAMEWORK_PADRAO.is_dir(), reason="framework ausente")
def test_sdd_com_origem_passa_no_validate_doc_real(tmp_path):
    repo = tmp_path / "repo"
    caminho = FonteDocTraceability().escrever_sdd(
        repo, RASCUNHO, "ZERO", "Dona", "2026-11-17", "approved", origens=ORIGENS
    )
    texto = (repo / caminho).read_text(encoding="utf-8")
    assert '  - id: "SPEC-ZERO-0001"\n' in texto
    assert '  - id: "ADR-ZERO-0001"\n' in texto
    assert "| source_docs | SPEC-ZERO-0001, ADR-ZERO-0001 |" in texto
    validate_doc = Framework()._rodar("validate_doc.py", str(repo / caminho), cwd=repo)
    assert validate_doc.ok, validate_doc.problemas


# Documento do central (SDD-FAB-0003, RF02 a RF04)


TIPOS_DO_CENTRAL = {"medium": "SPEC", "large": "RFC", "complex": "RFC"}


class EscritorFalso:
    """Faz o papel de `EscritaNoCentral` com o tipo por sizing do framework fixado."""

    def __init__(self, *problemas, erro=None):
        self.problemas_por_tentativa = list(problemas)
        self.erro = erro
        self.montados = []
        self.prs = []

    def tipo_do_central(self, sizing):
        return TIPOS_DO_CENTRAL.get(sizing)

    def montar(self, documento, owner, hoje):
        self.montados.append((documento, owner))
        doc_id = f"{documento['tipo']}-ZERO-0001"
        return doc_id, f"---\nid: {doc_id}\n---\n\n{documento['corpo']}"

    def problemas(self, texto):
        return self.problemas_por_tentativa.pop(0) if self.problemas_por_tentativa else []

    def abrir_pr(self, doc_id, tipo, texto, titulo):
        if self.erro:
            raise self.erro
        self.prs.append((doc_id, tipo, titulo))
        return 31


def doc(tipo="SPEC", sizing="medium"):
    valor = {"tipo": tipo, "titulo": "Avisos", "sizing": sizing, "corpo": "# Avisos\n"}
    return lambda c: resposta(c, "documento", [], None, copy.deepcopy(valor))


def medio():
    return copy.deepcopy(RASCUNHO) | {"sizing": "medium"}


@pytest.mark.parametrize(("tipo", "sizing"), [("SPEC", "medium"), ("RFC", "large")])
def test_documento_do_central_chega_a_pr(tipo, sizing, montar):
    escritor = EscritorFalso()
    d = montar(RunnerFila(doc(tipo, sizing)), escritor=escritor)
    sessao = d.criar("avisos")
    assert d.avancar(sessao) == NO_CENTRAL
    dados = d.dados(sessao)
    assert dados["pr"] == 31 and dados["doc_id"] == f"{tipo}-ZERO-0001"
    assert dados["documento"]["tipo"] == tipo and dados["problemas"] == []
    assert escritor.prs == [(f"{tipo}-ZERO-0001", tipo, "Avisos")]
    assert escritor.montados[0][1] == "Dona"


@pytest.mark.parametrize(
    ("resposta_do_agente", "origens", "motivo"),
    [
        (doc("RFC", "medium"), [], "sizing medium pede SPEC, não RFC"),
        (doc("SPEC", "large"), [], "sizing large pede RFC, não SPEC"),
        (doc("SPEC", "small"), [], "sizing small gera rascunho de SDD, não documento do central"),
        (
            doc("SPEC", "medium"),
            ORIGENS,
            "com --origem a descoberta entrega rascunho de SDD, não documento do central",
        ),
        (
            rascunho(medio()),
            [],
            "sizing medium sem --origem pede rascunho de SPEC no central, não de SDD",
        ),
        (
            lambda c: resposta(c, "documento", [], None, None),
            [],
            "status documento sem documento",
        ),
    ],
)
def test_documento_fora_do_caminho_e_recusado(resposta_do_agente, origens, motivo, montar):
    escritor = EscritorFalso()
    d = montar(
        RunnerFila(resposta_do_agente, resposta_do_agente, resposta_do_agente), escritor=escritor
    )
    sessao = d.criar("avisos", origens)
    assert d.avancar(sessao) == PARADA
    assert d.dados(sessao)["recusas"][0]["problemas"] == [motivo]
    assert escritor.prs == []


def test_documento_sem_escrita_configurada_e_recusado(montar):
    d = montar(RunnerFila(doc(), doc(), doc()))
    sessao = d.criar("avisos")
    assert d.avancar(sessao) == PARADA
    assert d.dados(sessao)["problemas"] == [
        "documento do central sem escrita no central configurada"
    ]


def test_documento_com_problemas_do_validador_volta_ao_agente(montar):
    escritor = EscritorFalso(["validate_doc.py: seção obrigatória ausente: 'Objetivo'."])
    runner = RunnerFila(doc(), doc())
    d = montar(runner, escritor=escritor)
    sessao = d.criar("avisos")
    assert d.avancar(sessao) == NO_CENTRAL
    assert runner.contratos[1]["entrada"]["problemas"] == [
        "validate_doc.py: seção obrigatória ausente: 'Objetivo'."
    ]
    assert len(escritor.prs) == 1


def test_documento_com_erro_ao_abrir_pr_nao_salva(montar):
    escritor = EscritorFalso(erro=RuntimeError("push recusado"))
    d = montar(RunnerFila(doc()), escritor=escritor)
    sessao = d.criar("avisos")
    with pytest.raises(RuntimeError, match="push recusado"):
        d.avancar(sessao)
    assert d.estado(sessao) == "PERGUNTANDO"


def test_documento_nao_muda_o_caminho_com_origem_nem_em_small(montar):
    escritor = EscritorFalso()
    d = montar(RunnerFila(rascunho(medio() | {"tarefas": []})), escritor=escritor)
    sessao = d.criar("lista", ORIGENS)
    assert d.avancar(sessao) == AGUARDANDO_APROVACAO
    d = montar(RunnerFila(rascunho()), escritor=escritor)
    assert d.avancar(d.criar("lista")) == AGUARDANDO_APROVACAO
    assert escritor.prs == []


@pytest.mark.skipif(not FRAMEWORK_PADRAO.is_dir(), reason="framework ausente")
def test_documento_descobridor_traz_o_sweep_do_kit():
    import ast
    from pathlib import Path

    fonte = (FRAMEWORK_PADRAO / "_framework" / "scripts" / "validate_doc.py").read_text("utf-8")
    atribuicao = next(
        no
        for no in ast.parse(fonte).body
        if isinstance(no, ast.Assign) and getattr(no.targets[0], "id", "") == "SWEEP_CATEGORIES"
    )
    categorias = ast.literal_eval(atribuicao.value)
    prompt = (Path(__file__).parent.parent / "agents" / "descobridor.md").read_text("utf-8")
    regra = next(
        linha for linha in prompt.splitlines() if "Requisitos transversais (sweep)` é" in linha
    )
    nomes = regra.split("nomes exatos: ", 1)[1].split(". `Destino`", 1)[0].split(", ")
    assert [nome.lower() for nome in nomes] == categorias
    assert "| Categoria | Destino (RF-ID ou n/a) | Motivo (obrigatório se n/a) |" in regra
    assert "com `n/a`, `Motivo` é obrigatório" in regra


# Progresso da descoberta no terminal (SDD-FAB-0004)


class Gravador:
    def __init__(self, ordem=None):
        self.eventos = []
        self.ordem = ordem if ordem is not None else []

    def __call__(self, evento, detalhes):
        self.eventos.append((evento, detalhes))
        self.ordem.append(evento)


def test_eventos_do_rascunho_na_ordem(montar):
    gravador = Gravador()
    runner = RunnerFila(perguntas("Quem usa?"), rascunho(), rascunho())
    d = montar(runner, RedatorFalso(["validate_doc: sem EARS"]), progresso=gravador)
    sessao = d.criar("lista")
    assert d.avancar(sessao) == AGUARDANDO_RESPOSTAS
    d.responder(sessao, ["só eu"])
    assert d.avancar(sessao) == AGUARDANDO_APROVACAO
    validando = {"tipo": "SDD", "sizing": "small", "origens": [], "tentativas": 3}
    assert gravador.eventos == [
        ("agente", {"tentativa": 1, "tentativas": 3, "respostas": False}),
        ("perguntas", {"quantidade": 1, "rodada": 1, "rodadas": 4}),
        ("agente", {"tentativa": 1, "tentativas": 3, "respostas": True}),
        ("validando", validando | {"tentativa": 1}),
        ("recusa", {"tentativa": 1, "tentativas": 3, "problemas": 1, "parando": False}),
        ("agente", {"tentativa": 2, "tentativas": 3, "respostas": True}),
        ("validando", validando | {"tentativa": 2}),
        (
            "pronto",
            {"sdd_id": "SDD-ZERO-0001", "tentativa": 2, "tentativas": 3, "automatica": False},
        ),
    ]


def test_eventos_da_parada_com_recusa_antes_do_redator(montar):
    errado = copy.deepcopy(RASCUNHO)
    errado["requisitos"][0]["arquivos"] = ["a/../x.py", "docs/y.md"]
    gravador = Gravador()
    d = montar(RunnerFila(*[rascunho(errado)] * 3), progresso=gravador)
    sessao = d.criar("x")
    assert d.avancar(sessao) == PARADA
    assert [e for e, _ in gravador.eventos] == ["agente", "validando", "recusa"] * 3
    recusas = [x for e, x in gravador.eventos if e == "recusa"]
    assert [r["parando"] for r in recusas] == [False, False, True]
    assert [r["tentativa"] for r in recusas] == [1, 2, 3]
    assert {r["problemas"] for r in recusas} == {2}


def test_eventos_do_documento_antes_da_pr(montar):
    ordem = []

    class EscritorQueGrava(EscritorFalso):
        def abrir_pr(self, doc_id, tipo, texto, titulo):
            ordem.append("abrir_pr")
            return super().abrir_pr(doc_id, tipo, texto, titulo)

    gravador = Gravador(ordem)
    d = montar(RunnerFila(doc()), escritor=EscritorQueGrava(), progresso=gravador)
    assert d.avancar(d.criar("avisos")) == NO_CENTRAL
    assert gravador.eventos == [
        ("agente", {"tentativa": 1, "tentativas": 3, "respostas": False}),
        (
            "validando",
            {"tipo": "SPEC", "sizing": "medium", "origens": [], "tentativa": 1, "tentativas": 3},
        ),
        ("pr_central", {"doc_id": "SPEC-ZERO-0001", "tipo": "SPEC", "tentativa": 1,
                        "tentativas": 3}),
    ]  # fmt: skip
    assert ordem == ["agente", "validando", "pr_central", "abrir_pr"]


def test_eventos_do_documento_de_tipo_errado_e_com_origem(montar):
    gravador = Gravador()
    errado = doc("RFC", "medium")
    d = montar(RunnerFila(errado, errado, errado), escritor=EscritorFalso(), progresso=gravador)
    assert d.avancar(d.criar("avisos")) == PARADA
    assert "validando" not in [e for e, _ in gravador.eventos]
    assert [e for e, _ in gravador.eventos].count("recusa") == 3

    gravador = Gravador()
    d = montar(
        RunnerFila(rascunho(medio() | {"tarefas": []})),
        escritor=EscritorFalso(),
        progresso=gravador,
    )
    assert d.avancar(d.criar("lista", ORIGENS)) == AGUARDANDO_APROVACAO
    validando = [x for e, x in gravador.eventos if e == "validando"]
    assert validando[0]["origens"] == ["SPEC-ZERO-0001", "ADR-ZERO-0001"]


def test_eventos_sem_callback_nao_mudam_os_dados(montar):
    def rodar(progresso):
        d = montar(RunnerFila(rascunho(), rascunho()), RedatorFalso(["x"]), progresso=progresso)
        sessao = d.criar("lista")
        assert d.avancar(sessao) == AGUARDANDO_APROVACAO
        return {k: v for k, v in d.dados(sessao).items() if k != "arquivo"}

    assert rodar(None) == rodar(Gravador())


def test_nucleo_nao_imprime():
    import ast
    from pathlib import Path

    import fabrica.descoberta as modulo

    arvore = ast.parse(Path(modulo.__file__).read_text(encoding="utf-8"))
    for no in ast.walk(arvore):
        if isinstance(no, ast.Call) and isinstance(no.func, ast.Name):
            assert no.func.id != "print"
        if isinstance(no, ast.Import):
            assert "sys" not in [a.name for a in no.names]
        if isinstance(no, ast.ImportFrom):
            assert no.module != "sys"


TEXTOS = [
    (
        "agente",
        {"tentativa": 1, "tentativas": 3, "respostas": False},
        ("── 1/6 Entender a ideia ──\n"
        "O agente lê a sua ideia e decide se já dá para escrever ou se falta informação.\n"
        "A chamada ao agente demora, e o terminal fica parado enquanto ela roda. Aguarde."),
    ),
    (
        "agente",
        {"tentativa": 1, "tentativas": 3, "respostas": True},
        "Respostas enviadas. O agente decide se ainda falta algo ou se já escreve. Aguarde.",
    ),
    (
        "perguntas",
        {"quantidade": 2, "rodada": 1, "rodadas": 4},
        ("O agente tem 2 pergunta(s) (rodada 1 de até 4).\n"
        "Por que perguntar: as respostas fecham o escopo, os critérios de aceite e o tamanho\n"
        "da mudança. O tamanho decide quais documentos o framework exige antes do código."),
    ),
    (
        "validando",
        {"tipo": "SDD", "sizing": "small", "origens": ["SPEC-ZERO-0001", "ADR-ZERO-0001"],
         "tentativa": 1, "tentativas": 3},
        ("── 2/6 Escrever o documento ──\n"
        "O agente entregou um rascunho de SDD, tamanho small.\n"
        "A SDD nasce de SPEC-ZERO-0001, ADR-ZERO-0001, já aprovada(s) no central.\n"
        "\n"
        "── 3/6 Validar ──\n"
        "Os validadores do framework conferem o rascunho como ele entraria na base, "
        "antes de você ler."),
    ),
    (
        "validando",
        {"tipo": "SDD", "sizing": "small", "origens": [], "tentativa": 1, "tentativas": 3},
        ("── 2/6 Escrever o documento ──\n"
        "O agente entregou um rascunho de SDD, tamanho small.\n"
        "small sem --origem: basta a SDD, sem SPEC nem RFC antes.\n"
        "\n"
        "── 3/6 Validar ──\n"
        "Os validadores do framework conferem o rascunho como ele entraria na base, "
        "antes de você ler."),
    ),
    (
        "validando",
        {"tipo": "SPEC", "sizing": "medium", "origens": [], "tentativa": 1, "tentativas": 3},
        ("── 2/6 Escrever o documento ──\n"
        "O agente entregou um rascunho de SPEC, tamanho medium.\n"
        "medium sem --origem: o framework pede uma SPEC aprovada no central antes da SDD.\n"
        "\n"
        "── 3/6 Validar ──\n"
        "Os validadores do framework conferem o rascunho como ele entraria no central, "
        "antes de você ler."),
    ),
    (
        "validando",
        {"tipo": "RFC", "sizing": "large", "origens": [], "tentativa": 2, "tentativas": 3},
        ("Tentativa 2 de 3: o agente entregou um novo rascunho de RFC (large), "
        "e os validadores o conferem."),
    ),
    (
        "recusa",
        {"tentativa": 1, "tentativas": 3, "problemas": 2, "parando": False},
        "Tentativa 1 de 3 recusada: 2 problema(s). O agente recebe os motivos e refaz. Aguarde.",
    ),
    (
        "pr_central",
        {"doc_id": "SPEC-ZERO-0003", "tipo": "SPEC", "tentativa": 1, "tentativas": 3},
        ("── 4/6 Aprovar ──\n"
        "SPEC-ZERO-0003 passou nos validadores na tentativa 1 de 3.\n"
        "Abrindo a PR no central, onde o documento fica em in_review."),
    ),
    (
        "pronto",
        {"sdd_id": "SDD-ZERO-0001", "tentativa": 2, "tentativas": 3},
        ("── 4/6 Aprovar ──\n"
        "SDD-ZERO-0001 passou nos validadores na tentativa 2 de 3.\n"
        "Agora é com você: nada entra na base sem a sua aprovação."),
    ),
]  # fmt: skip


@pytest.mark.parametrize(("evento", "detalhes", "texto"), TEXTOS)
def test_textos_do_progresso(evento, detalhes, texto, capsys):
    cli.mostrar_progresso(evento, detalhes)
    assert capsys.readouterr().out == f"\n{texto}\n"


@pytest.mark.parametrize(
    ("evento", "detalhes"),
    [
        ("agente", {"tentativa": 2, "tentativas": 3, "respostas": True}),
        ("recusa", {"tentativa": 3, "tentativas": 3, "problemas": 2, "parando": True}),
        ("desconhecido", {}),
    ],
)
def test_textos_do_progresso_que_nao_imprimem(evento, detalhes, capsys):
    cli.mostrar_progresso(evento, detalhes)
    assert capsys.readouterr().out == ""


def test_bloco_de_parada(capsys):
    recusas = [
        {"tentativa": 1, "problemas": ["c"]},
        {"tentativa": 2, "problemas": ["a", "b"]},
        {"tentativa": 3, "problemas": ["a", "b"]},
    ]
    cli.mostrar_parada("s1", {"recusas": recusas, "problemas": ["a", "b"]})
    assert capsys.readouterr().out == (
        "\n"
        "── Parada na etapa 3/6 Validar ──\n"
        "O rascunho foi recusado nas 3 tentativas. Nada foi gravado na base nem no central.\n"
        "\n"
        "Motivos da última tentativa (3 de 3), 2 problema(s):\n"
        "  1. a\n"
        "  2. b\n"
        "\n"
        "Tentativas anteriores:\n"
        "  tentativa 1: 1 problema(s)\n"
        "    1. c\n"
        "  tentativa 2: os mesmos motivos da tentativa 3\n"
        "\n"
        "O que fazer: ajuste a ideia com base nesses motivos e rode descobrir de novo.\n"
    )


def test_bloco_de_parada_sem_tentativas_anteriores(capsys):
    cli.mostrar_parada("s1", {"recusas": [{"tentativa": 3, "problemas": ["a"]}]})
    saida = capsys.readouterr().out
    assert "Motivos da última tentativa (3 de 3), 1 problema(s):\n  1. a\n" in saida
    assert "Tentativas anteriores" not in saida


def test_cli_progresso_montar_descoberta_liga_o_callback(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "montar_fonte", lambda projeto: RedatorFalso())
    monkeypatch.setattr(cli, "montar_escrita", lambda projeto: None)
    monkeypatch.setattr(cli, "ClaudeDockerRunner", lambda: None)
    monkeypatch.setattr(cli, "DIR_DADOS", tmp_path / "dados")
    d = cli.montar_descoberta(Projeto("ZERO", "/r", "o/r", owner="Dona"))
    assert d._progresso is cli.mostrar_progresso


def test_cli_progresso_conversar_mostra_mapa_avisos_e_proximo_passo(montar, monkeypatch, capsys):
    entradas = iter(["só eu"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(entradas))
    runner = RunnerFila(perguntas("Quem usa?"), rascunho(), rascunho())
    d = montar(runner, RedatorFalso(["x"]), progresso=cli.mostrar_progresso)
    sessao = d.criar("lista")
    assert cli.conversar(d, sessao) == 0
    saida = capsys.readouterr().out
    dados = d.dados(sessao)
    partes = [
        f"sessão {sessao}\n",
        cli.MAPA,
        "── 1/6 Entender a ideia ──",
        "O agente tem 1 pergunta(s) (rodada 1 de até 4).",
        "1. Quem usa?",
        "Respostas enviadas.",
        "── 2/6 Escrever o documento ──",
        "── 3/6 Validar ──",
        "Tentativa 1 de 3 recusada: 1 problema(s).",
        "Tentativa 2 de 3: o agente entregou um novo rascunho de SDD (small)",
        "── 4/6 Aprovar ──",
        (
            f"\nRascunho SDD-ZERO-0001 em {dados['arquivo']}\n"
            f"Leia e, se estiver certo: uv run python -m fabrica aprovar <projeto> {sessao}\n"
            "Depois de aprovada, a SDD vai para develop por PR e o vigia dispara a implementação "
            "(etapa 5).\n"
        ),
    ]
    posicao = 0
    for parte in partes:
        achada = saida.find(parte, posicao)
        assert achada >= 0, parte
        posicao = achada + len(parte)
    assert saida.endswith("(etapa 5).\n")
    assert next(entradas, None) is None


@pytest.mark.parametrize(
    ("doc_id", "linha"),
    [
        (
            "SPEC-ZERO-0003",
            "Com a SPEC aprovada, a SDD sai de outra descoberta com --origem SPEC-ZERO-0003.",
        ),
        (
            "RFC-ZERO-0002",
            (
                "Com a RFC aprovada, o fluxo segue no central até uma SPEC aprovada, "
                "que é a --origem da SDD."
            ),
        ),
    ],
)
def test_cli_progresso_no_central_diz_o_proximo_passo(doc_id, linha, capsys):
    class DescobertaNoCentral:
        def avancar(self, sessao):
            return NO_CENTRAL

        def dados(self, sessao):
            return {"doc_id": doc_id, "pr": 7}

    assert cli.conversar(DescobertaNoCentral(), "s1") == 0
    saida = capsys.readouterr().out
    assert saida.startswith(f"sessão s1\n{cli.MAPA}")
    assert saida.endswith(
        f"Rascunho {doc_id} na PR #7 do central, em in_review.\n"
        "Aprove por review na PR e depois: "
        f"uv run python -m fabrica central conferir <projeto> {doc_id}\n{linha}\n"
    )


def test_cli_progresso_parada_sai_com_1_e_mostra_o_bloco(montar, capsys):
    errado = copy.deepcopy(RASCUNHO)
    errado["requisitos"][0]["arquivos"] = ["a/../x.py"]
    d = montar(RunnerFila(*[rascunho(errado)] * 3), progresso=cli.mostrar_progresso)
    assert cli.conversar(d, d.criar("x")) == 1
    saida = capsys.readouterr().out
    assert "── Parada na etapa 3/6 Validar ──" in saida
    assert "  1. arquivo fora do código do projeto: a/../x.py\n" in saida
    assert "  tentativa 1: os mesmos motivos da tentativa 3\n" in saida
    assert "Parada: o rascunho" not in saida


# SDD enxuta na descoberta (SDD-FAB-0005, RF01 a RF03)

ORIGENS_ENXUTA = [
    {"id": "SPEC-ZERO-0001", "url": "https://h/blob/main/docs/ZERO/03-spec/SPEC-ZERO-0001.md",
     "tipo": "SPEC", "titulo": "Lista", "sizing": "small", "texto": "---\nid: SPEC-ZERO-0001\n"},
]  # fmt: skip


def rascunho_enxuto(**mudancas):
    valor = copy.deepcopy(RASCUNHO) | {"arquitetura": None, "especificacao": None}
    valor["requisitos"][0] |= {"origem": "SPEC-ZERO-0001", "aceite": None}
    for chave, novo in mudancas.items():
        if chave in valor["requisitos"][0]:
            valor["requisitos"][0][chave] = novo
        else:
            valor[chave] = novo
    return valor


def recusas(d, sessao):
    return [p for r in d.dados(sessao).get("recusas", []) for p in r["problemas"]]


def test_formato_vai_ao_agente_e_e_perguntado_uma_vez_por_sessao(montar):
    runner = RunnerFila(perguntas("Quem usa?"), rascunho(rascunho_enxuto()))
    redator = RedatorFalso(formato="enxuta")
    d = montar(runner, redator)
    sessao = d.criar("lista", ORIGENS_ENXUTA)
    assert d.avancar(sessao) == AGUARDANDO_RESPOSTAS
    d.responder(sessao, ["só eu"])
    assert d.avancar(sessao) == AGUARDANDO_APROVACAO, recusas(d, sessao)
    assert [c["entrada"]["sdd"] for c in runner.contratos] == ["enxuta", "enxuta"]
    assert redator.formatos == [ORIGENS_ENXUTA]


@pytest.mark.parametrize(
    ("mudancas", "mensagem"),
    [
        ({"especificacao": "Copiada da SPEC."},
         "SDD enxuta: especificacao vem null, o desenho fica na SPEC de origem"),
        ({"arquitetura": "Copiada da ADR."},
         "SDD enxuta: arquitetura vem null, o desenho fica na SPEC de origem"),
        ({"aceite": "Quando X, o sistema deve Y."},
         "SDD enxuta: RF01 traz aceite, que vem null: o critério EARS fica na SPEC de origem"),
        ({"origem": "SPEC-ZERO-0009"},
         "RF01 com origem 'SPEC-ZERO-0009' fora das SPECs da sessão: SPEC-ZERO-0001"),
        ({"requisito": "x" * 201},
         "RF01 com requisito de 201 caracteres: o limite da SDD enxuta é 200"),
    ],
)  # fmt: skip
def test_formato_enxuto_recusa_o_rascunho_que_copia_ou_sai_da_origem(montar, mudancas, mensagem):
    runner = RunnerFila(rascunho(rascunho_enxuto(**mudancas)), rascunho(rascunho_enxuto()))
    d = montar(runner, RedatorFalso(formato="enxuta"))
    sessao = d.criar("lista", ORIGENS_ENXUTA)
    assert d.avancar(sessao) == AGUARDANDO_APROVACAO
    assert mensagem in recusas(d, sessao)
    assert runner.contratos[1]["entrada"]["problemas"] == recusas(d, sessao)


def test_formato_enxuto_aceita_requisito_de_200_caracteres(montar):
    d = montar(
        RunnerFila(rascunho(rascunho_enxuto(requisito="x" * 200))), RedatorFalso(formato="enxuta")
    )
    sessao = d.criar("lista", ORIGENS_ENXUTA)
    assert d.avancar(sessao) == AGUARDANDO_APROVACAO
    assert recusas(d, sessao) == []


@pytest.mark.parametrize(
    ("mudancas", "mensagem"),
    [
        ({"arquitetura": None}, "SDD completa: arquitetura é obrigatório"),
        ({"especificacao": None}, "SDD completa: especificacao é obrigatório"),
        ({"aceite": None}, "SDD completa: RF01 sem aceite"),
    ],
)
def test_formato_completo_recusa_o_rascunho_sem_desenho(montar, mudancas, mensagem):
    valor = copy.deepcopy(RASCUNHO)
    for chave, novo in mudancas.items():
        (valor["requisitos"][0] if chave == "aceite" else valor)[chave] = novo
    runner = RunnerFila(rascunho(valor), rascunho())
    d = montar(runner)
    sessao = d.criar("lista")
    assert d.avancar(sessao) == AGUARDANDO_APROVACAO
    assert recusas(d, sessao) == [mensagem]


def test_redacao_do_draft_enxuto_recusa_sem_avisar_pronto(montar):
    eventos = []
    redator = RedatorFalso(formato="enxuta", redacao=[["validate_doc.py: problema do draft"]])
    runner = RunnerFila(rascunho(rascunho_enxuto()), rascunho(rascunho_enxuto()))
    d = montar(runner, redator, progresso=lambda evento, detalhes: eventos.append(evento))
    sessao = d.criar("lista", ORIGENS_ENXUTA)
    assert d.avancar(sessao) == AGUARDANDO_APROVACAO
    assert recusas(d, sessao) == ["validate_doc.py: problema do draft"]
    assert eventos.count("pronto") == 1
    assert eventos.index("recusa") < eventos.index("pronto")
    assert redator.redacoes == ["docs/sdd/SDD-ZERO-0001.md"] * 2


def test_redacao_do_draft_nao_roda_na_sdd_completa(montar):
    redator = RedatorFalso(redacao=[["não devia rodar"]])
    d = montar(RunnerFila(rascunho()), redator)
    assert d.avancar(d.criar("lista")) == AGUARDANDO_APROVACAO
    assert redator.redacoes == []


def test_esquema_aceita_o_rascunho_enxuto_e_exige_origem():
    from fabrica.contratos import erros_de_schema, schema_da_etapa

    schema = schema_da_etapa("descoberta")
    base = {"contrato_id": "c", "token": "t", "etapa": "descoberta", "status": "rascunho",
            "perguntas": [], "documento": None}  # fmt: skip
    assert erros_de_schema(base | {"rascunho": rascunho_enxuto()}, schema) == []
    assert erros_de_schema(base | {"rascunho": copy.deepcopy(RASCUNHO)}, schema) == []
    sem_origem = rascunho_enxuto()
    del sem_origem["requisitos"][0]["origem"]
    assert erros_de_schema(base | {"rascunho": sem_origem}, schema) != []
    origem_invalida = rascunho_enxuto(origem="spec-zero-1")
    assert erros_de_schema(base | {"rascunho": origem_invalida}, schema) != []


@pytest.mark.skipif(not FRAMEWORK_PADRAO.is_dir(), reason="framework ausente")
@pytest.mark.parametrize(("versao", "formato"), [("2.7.0", "enxuta"), ("2.3.2", "completa")])
def test_formato_com_redator_real_le_o_registry_da_base(montar, remoto, versao, formato):
    (remoto / "docs/sdd").mkdir(parents=True)
    (remoto / "docs/sdd/registry.yaml").write_text(
        f'project: "ZERO"\nframework_version: "{versao}"\ndocuments:\n', encoding="utf-8"
    )
    git("add", "-A", cwd=remoto)
    git("commit", "-qm", f"registry {versao}", cwd=remoto)
    runner = RunnerFila(perguntas("Quem usa?"))
    d = montar(runner, FonteDocTraceability())
    sessao = d.criar("lista", ORIGENS_ENXUTA)
    assert d.avancar(sessao) == AGUARDANDO_RESPOSTAS
    assert d.dados(sessao)["sdd"] == formato
    assert runner.contratos[0]["entrada"]["sdd"] == formato


# --- SDD-FAB-0009: compilação disparada pelo vigia e publicação por política (RF07, RF08) --

ORIGEM_DO_VIGIA = {
    "id": "SPEC-ZERO-0001",
    "url": "https://h/blob/main/docs/ZERO/03-spec/SPEC-ZERO-0001.md",
    "tipo": "SPEC",
    "titulo": "Lista",
    "sizing": "small",
    "texto": "# Lista\n",
}


class RedatorDoVigia(RedatorFalso):
    """Redator falso com a origem do central e a aprovação por política."""

    def __init__(self, *problemas, politica=(True, []), formato="enxuta"):
        super().__init__(*problemas, formato=formato)
        self.politica = politica
        self.politicas = []
        self.pedidas = []

    def origem(self, doc_id):
        self.pedidas.append(doc_id)
        return ORIGEM_DO_VIGIA | {"id": doc_id}

    def aprovar_por_politica(self, repo, caminho_sdd, agora):
        self.politicas.append((caminho_sdd, agora))
        arquivo = repo / caminho_sdd
        arquivo.write_text(arquivo.read_text() + "approved_by: policy\n")
        return {"kind": "policy"}

    def aprovacao_por_politica(self, repo, caminho_sdd):
        return self.politica


def test_compilar_abre_sessao_automatica_com_a_origem_e_o_pedido_fixo(montar):
    redator = RedatorDoVigia()
    runner = RunnerFila(rascunho(rascunho_enxuto()))
    d = montar(runner, redator)
    sessao = d.compilar("SPEC-ZERO-0001")
    dados = d.dados(sessao)
    assert redator.pedidas == ["SPEC-ZERO-0001"]
    assert dados["automatica"] is True
    assert dados["ideia"] == "Compilar a SDD enxuta de SPEC-ZERO-0001"
    assert [o["id"] for o in dados["origens"]] == ["SPEC-ZERO-0001"]
    assert runner.contratos[0]["entrada"]["ideia"] == "Compilar a SDD enxuta de SPEC-ZERO-0001"
    assert d.estado(sessao) == AGUARDANDO_APROVACAO


def test_compilar_agente_que_pergunta_fica_aguardando_respostas_sem_humano(montar):
    runner = RunnerFila(perguntas("Qual o limite?"))
    d = montar(runner, RedatorDoVigia())
    sessao = d.compilar("SPEC-ZERO-0001")
    assert d.estado(sessao) == AGUARDANDO_RESPOSTAS
    assert len(runner.contratos) == 1
    assert runner.respostas == []


def test_compilar_descobridor_traz_o_pedido_fixo():
    texto = (DIR_AGENTES / "descobridor.md").read_text(encoding="utf-8")
    assert "Compilar a SDD enxuta de <id>" in texto


def test_politica_publica_e_faz_merge_sem_registro_em_aprovacoes(montar, remoto):
    github = GithubFalso()
    redator = RedatorDoVigia()
    d = montar(RunnerFila(rascunho(rascunho_enxuto())), redator, github)
    sessao = d.compilar("SPEC-ZERO-0001")
    assert d.publicar_por_politica(sessao) == 5
    assert d.estado(sessao) == APROVADA
    assert github.merges == [5]
    assert [c for c, _ in redator.politicas] == ["docs/sdd/SDD-ZERO-0001.md"]
    ramo = github.prs[0]
    publicado = git("show", f"{ramo}:docs/sdd/SDD-ZERO-0001.md", cwd=remoto).encode()
    assert publicado.startswith(b"status: approved")
    assert b"approved_by: policy" in publicado
    assert not d.aprovacoes.aprovada("ZERO", "docs/sdd/SDD-ZERO-0001.md", publicado)
    mensagens = git("log", "--format=%s", ramo, cwd=remoto)
    assert "aprovada por política" in mensagens


def test_politica_sessao_interativa_termina_em_fabrica_aprovar(montar):
    d = montar(RunnerFila(rascunho(rascunho_enxuto())), RedatorDoVigia())
    sessao = d.criar("x", [ORIGEM_DO_VIGIA])
    d.avancar(sessao)
    with pytest.raises(DescobertaInvalida, match="^sessão interativa termina em fabrica aprovar$"):
        d.publicar_por_politica(sessao)


def test_politica_validador_vermelho_na_publicacao_nao_abre_pr(montar):
    github = GithubFalso()
    # A primeira lista de problemas é a da validação do rascunho; a segunda, a da publicação.
    redator = RedatorDoVigia([], ["check_source_docs.py: RF02 fora da SDD"])
    d = montar(RunnerFila(rascunho(rascunho_enxuto())), redator, github)
    sessao = d.compilar("SPEC-ZERO-0001")
    with pytest.raises(DescobertaInvalida, match="RF02 fora da SDD"):
        d.publicar_por_politica(sessao)
    assert github.prs == []
    assert d.estado(sessao) == PARADA


def test_politica_aprovacao_vermelha_no_kit_nao_abre_pr(montar):
    github = GithubFalso()
    redator = RedatorDoVigia(politica=(False, ["o documento mudou depois da aprovação"]))
    d = montar(RunnerFila(rascunho(rascunho_enxuto())), redator, github)
    sessao = d.compilar("SPEC-ZERO-0001")
    with pytest.raises(DescobertaInvalida, match="mudou depois da aprovação"):
        d.publicar_por_politica(sessao)
    assert github.prs == []
    assert d.estado(sessao) == PARADA


@pytest.mark.skipif(not FRAMEWORK_PADRAO.is_dir(), reason="framework ausente")
def test_politica_com_kit_real_sai_com_approved_by_que_o_validate_state_aceita(
    montar, remoto, tmp_path
):
    from tests.test_vigia_central import Central

    (tmp_path / "c").mkdir()
    central = Central(tmp_path / "c")
    spec_id = central.spec(1)
    central.publicar()
    # A url de source_docs sai do remote do clone; o kit exige url http(s).
    git("remote", "set-url", "origin", "https://github.com/dona/central.git", cwd=central.clone)
    (remoto / "docs/sdd").mkdir(parents=True)
    (remoto / "docs/sdd/registry.yaml").write_text(
        'project: "ZERO"\nframework_version: "2.7.0"\ndocuments:\n', encoding="utf-8"
    )
    git("add", "-A", cwd=remoto)
    git("commit", "-qm", "registry 2.7.0", cwd=remoto)
    enxuto = rascunho_enxuto(sizing="medium")
    github = GithubFalso()
    fonte = FonteDocTraceability(Framework(), central.clone, "ZERO")
    d = montar(RunnerFila(rascunho(enxuto)), fonte, github)
    sessao = d.compilar(spec_id)
    assert d.estado(sessao) == AGUARDANDO_APROVACAO, d.dados(sessao).get("recusas")
    assert d.publicar_por_politica(sessao) == 5
    ramo = github.prs[0]
    copia = tmp_path / "publicada"
    git("clone", "-q", "-b", ramo, str(remoto), str(copia), cwd=tmp_path)
    caminho = "docs/sdd/SDD-ZERO-0001.md"
    texto = (copia / caminho).read_text(encoding="utf-8")
    assert "kind: policy" in texto and "actor: fabrica-agentica" in texto
    assert fonte.aprovacao_por_politica(copia, caminho) == (True, [])
    assert not d.aprovacoes.aprovada("ZERO", caminho, texto.encode())


# SDD-FAB-0013, RF04: a SPEC de outra pasta achada pela coluna Projeto chega ao rascunho


@pytest.mark.skipif(not FRAMEWORK_PADRAO.is_dir(), reason="framework ausente")
def test_compilar_spec_de_outra_pasta_chega_ao_rascunho_sem_origem_invalida(
    montar, remoto, tmp_path
):
    from adapters.doc_traceability.central import LeituraDoCentral
    from tests.test_vigia_central import Central

    (tmp_path / "c").mkdir()
    central = Central(tmp_path / "c")
    spec_id = central.spec(40, codigo="DTF", projetos="DTF, ZERO")
    central.publicar()
    git("remote", "set-url", "origin", "https://github.com/dona/central.git", cwd=central.clone)
    leitor = tmp_path / "leitor"
    git("clone", "-q", str(central.nu), str(leitor), cwd=tmp_path)
    assert [i for i, _ in LeituraDoCentral(leitor, "ZERO", Framework()).specs_aprovadas()] == [
        spec_id
    ]
    (remoto / "docs/sdd").mkdir(parents=True)
    (remoto / "docs/sdd/registry.yaml").write_text(
        'project: "ZERO"\nframework_version: "2.7.0"\ndocuments:\n', encoding="utf-8"
    )
    git("add", "-A", cwd=remoto)
    git("commit", "-qm", "registry 2.7.0", cwd=remoto)
    enxuto = rascunho_enxuto(
        sizing="medium", origem=spec_id, requisito="Aviso de mudança", arquivos=["app/avisos.py"]
    )
    fonte = FonteDocTraceability(Framework(), central.clone, "ZERO")
    d = montar(RunnerFila(rascunho(enxuto)), fonte)
    sessao = d.compilar(spec_id)
    origem = d.dados(sessao)["origens"][0]
    assert (
        origem["url"] == f"https://github.com/dona/central/blob/main/docs/DTF/03-spec/{spec_id}.md"
    )
    assert d.estado(sessao) == AGUARDANDO_APROVACAO, d.dados(sessao).get("recusas")


# SDD-FAB-0010, RF06: a compilação automática não pede fabrica aprovar


def test_cli_progresso_pronto_automatica_nao_pede_fabrica_aprovar(capsys):
    detalhes = {"sdd_id": "SDD-ZERO-0001", "tentativa": 1, "tentativas": 3}
    cli.mostrar_progresso("pronto", detalhes | {"automatica": True})
    automatica = capsys.readouterr().out
    assert "aprovada por política" in automatica
    assert "Agora é com você" not in automatica
    cli.mostrar_progresso("pronto", detalhes | {"automatica": False})
    assert "Agora é com você: nada entra na base sem a sua aprovação." in capsys.readouterr().out


def test_progresso_automatica_vai_no_evento_pronto_da_compilacao(montar):
    eventos = []
    d = montar(
        RunnerFila(rascunho(rascunho_enxuto())),
        RedatorDoVigia(),
        progresso=lambda e, det: eventos.append((e, det)),
    )
    d.compilar("SPEC-ZERO-0001")
    assert [det["automatica"] for e, det in eventos if e == "pronto"] == [True]

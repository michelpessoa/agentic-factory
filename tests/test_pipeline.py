import json
import re
import subprocess
from pathlib import Path

import pytest

from fabrica import pipeline as modulo
from fabrica.aprovacoes import Aprovacoes
from fabrica.contratos import Cartorio
from fabrica.decisao import Decisao, decidir_risco
from fabrica.estados import Historico
from fabrica.execucao import FalhaDeExecucao, ResultadoAgente
from fabrica.pipeline import Pipeline, Projeto

SDD_ID = "SDD-X-0001"
CAMINHO_SDD = "docs/sdd/SDD-X-0001.md"
ENTRADA = {
    "sdd_id": SDD_ID,
    "titulo": "Soma",
    "sizing": "small",
    "requisitos": [{"id": "RF01"}],
    "criterios": [{"numero": "1", "comando": "true"}],
    "arquivos_permitidos": ["a.py", "tests/*.py"],
}


def git(*args, cwd):
    comando = ["git", "-c", "user.email=t@t", "-c", "user.name=t", *args]
    return subprocess.run(
        comando, cwd=cwd, check=True, capture_output=True, text=True
    ).stdout.strip()


@pytest.fixture
def remoto(tmp_path):
    origem = tmp_path / "origem"
    origem.mkdir()
    git("init", "-q", "-b", "develop", cwd=origem)
    (origem / "docs/sdd").mkdir(parents=True)
    (origem / CAMINHO_SDD).write_text("# SDD\n")
    (origem / "a.py").write_text("x = 1\n")
    git("add", "-A", cwd=origem)
    git("commit", "-qm", "base", cwd=origem)
    git("config", "receive.denyCurrentBranch", "ignore", cwd=origem)
    return origem


class FonteFalsa:
    def __init__(self, problemas=None, **extras):
        self.problemas = problemas or []
        self.registradas = []
        self.arquivadas = []
        self.extras = extras

    def identificador(self):
        return "falsa@1"

    def problemas_de_entrada(self, repo, caminho_sdd):
        return self.problemas

    def compilar(self, repo, caminho_sdd):
        return ENTRADA | self.extras

    def caminhos_historicos(self):
        return ("docs/sdd/arquivo",)

    def arquivar(self, repo, caminho_sdd, pr, data):
        self.arquivadas.append((caminho_sdd, pr))
        (repo / caminho_sdd).rename(repo / "arquivada.md")
        return True

    def registrar_verificacao(self, repo, caminho_sdd, validacao, base, head):
        self.registradas.append(validacao)
        (repo / caminho_sdd).write_text("# SDD implementada\n")
        return []


class AmbienteFalso:
    def __init__(self, codigos=None):
        self.codigos = codigos or {}

    def extrair_patch(self, trabalho, base, excluir=()):
        git("add", "-A", cwd=trabalho)
        saida = git("diff", "--cached", "--binary", base, cwd=trabalho)
        return saida + "\n" if saida else ""

    def rodar(self, copia, comando, tempo_segundos=900):
        return self.codigos.get(comando, 0), "saida"

    def procurar_segredos(self, copia):
        return self.codigos.get("segredos", 0), "segredo"

    def analisar_codigo(self, copia):
        return self.codigos.get("semgrep", 0), "achado"


class GithubFalso:
    def __init__(self, aprovador="owner", checks=("passou", "")):
        self.aprovador = aprovador
        self.situacao_checks = checks
        self.merges = []
        self.prs = []
        self.fechadas = []

    def quem_mergeou_o_commit(self, sha):
        return self.aprovador

    def abrir_pr(self, ramo, base, titulo, corpo):
        self.prs.append((ramo, base, corpo))
        return 7 if "arquivar" not in ramo else 70

    def esperar_checks(self, numero):
        return self.situacao_checks

    def fazer_merge_em_develop(self, numero):
        self.merges.append(numero)

    def fechar_pr(self, numero, comentario):
        self.fechadas.append(numero)


class AprovaTudo:
    def aprovada(self, projeto, sdd, conteudo):
        return True


class NotificadorFalso:
    def __init__(self):
        self.mensagens = []

    def avisar(self, mensagem):
        self.mensagens.append(mensagem)


def contrato_do(prompt):
    return json.loads(re.search(r"```json\n(.*?)\n```", prompt, re.DOTALL).group(1))


def aprovacao(contrato):
    criterio = {
        "numero": "1",
        "comando": "true",
        "saida": "ok",
        "sensor": "falhou com a mutação",
        "passou": True,
        "assertion": "a.py:1",
        "perfil": "automatizado",
    }
    return {
        "contrato_id": contrato["contrato_id"],
        "token": contrato["token"],
        "etapa": "verificacao",
        "status": "aprovado",
        "testes": {"passaram": 1, "falharam": 0},
        "evidencias": [],
        "causa": None,
        "tentativa": contrato["tentativa"],
        "criterios": [criterio],
        "descompassos": [],
    }


def reprovacao(contrato, causa="implementacao"):
    resposta = aprovacao(contrato) | {
        "status": "reprovado",
        "causa": causa,
        "testes": {"passaram": 0, "falharam": 1},
        "descompassos": ["RF01 sem código"],
    }
    resposta["criterios"][0]["passou"] = False
    return resposta


class RunnerFalso:
    """Desenvolvedor que escreve arquivos e revisor com vereditos em fila."""

    def __init__(self, vereditos=None, arquivo="a.py", dev=None, agentes=None):
        self.vereditos = list(vereditos or [aprovacao])
        self.arquivo = arquivo
        self.dev = dev
        self.agentes = {"decisao": decisor("baixo", 0.95)} | (agentes or {})
        self.contratos = []
        self.vistos = []

    def executar(self, prompt, schema, dir_trabalho, modelo, ferramentas):
        contrato = contrato_do(prompt)
        self.contratos.append(contrato)
        if contrato["etapa"] == "verificacao":
            return ResultadoAgente(self.vereditos.pop(0)(contrato), 0.1)
        if contrato["etapa"] != "desenvolvimento":
            return ResultadoAgente(self.agentes[contrato["etapa"]](contrato, dir_trabalho), 0.1)
        self.vistos.append((dir_trabalho / "a.py").read_text())
        if self.dev:
            return ResultadoAgente(self.dev(contrato, dir_trabalho), 0.1)
        alvo = dir_trabalho / self.arquivo
        alvo.parent.mkdir(parents=True, exist_ok=True)
        alvo.write_text(f"x = {contrato['tentativa'] + 1}\n")
        return ResultadoAgente(resposta_dev(contrato), 0.1)


def resposta_dev(contrato, **extras):
    return {
        "contrato_id": contrato["contrato_id"],
        "token": contrato["token"],
        "etapa": "desenvolvimento",
        "status": "concluido",
        "resumo": "feito",
        "evidencias": [],
    } | extras


@pytest.fixture
def montar(remoto, tmp_path, monkeypatch):
    releases = []

    def preparar_release_falsa(github, url, base, principal):
        releases.append((base, principal))
        return 8, "0.1.1"

    monkeypatch.setattr(modulo, "preparar_release", preparar_release_falsa)

    def _montar(runner=None, fonte=None, ambiente=None, github=None, aprovacoes=None):
        banco = tmp_path / "f.db"
        projeto = Projeto(
            "X", str(remoto), "o/r", permitidos=("owner",), comandos={"testes": "rodar-testes"}
        )
        p = Pipeline(
            projeto,
            Historico(banco),
            Cartorio(banco),
            fonte or FonteFalsa(),
            runner or RunnerFalso(),
            ambiente or AmbienteFalso(),
            github or GithubFalso(),
            NotificadorFalso(),
            tmp_path / "runs",
            aprovacoes=aprovacoes or AprovaTudo(),
        )
        p.releases = releases
        return p

    return _montar


def caminho(p, run_id):
    return [destino for _, destino, _ in p.historico.transicoes(run_id)]


def test_caminho_feliz_vai_ate_a_release(montar):
    p = montar()
    run_id = p.iniciar(CAMINHO_SDD)
    assert caminho(p, run_id) == [
        "DETECTADO", "ENTRADA_OK", "ROTEADO", "CONTRATO_EMITIDO", "AGENTE_RODANDO",
        "RESPOSTA_VALIDA", "GATES_LOCAIS", "SEGURANCA", "VERIFY_SDD", "PR_PARA_DEVELOP",
        "CI_E2E", "MERGE_EM_DEVELOP", "ARQUIVAMENTO", "MEDIDA",
    ]  # fmt: skip
    assert p.github.merges == [7, 70]
    assert p.releases == [("develop", "main")]
    assert p.fonte.arquivadas == [(CAMINHO_SDD, 7)]
    assert "0.1.1" in p.notificador.mensagens[-1]


def test_pr_vai_para_develop_com_a_sdd_no_corpo(montar, remoto):
    p = montar()
    run_id = p.iniciar(CAMINHO_SDD)
    ramo, base, corpo = p.github.prs[0]
    assert base == "develop" and ramo == f"feature/sdd-x-0001-{run_id[:8]}-t1"
    assert "# SDD implementada" in corpo
    assert git("show", f"{ramo}:a.py", cwd=remoto) == "x = 2"


def test_evidencia_vem_so_do_revisor_aprovado(montar):
    fonte = FonteFalsa()
    p = montar(fonte=fonte)
    p.iniciar(CAMINHO_SDD)
    assert fonte.registradas[0]["status"] == "aprovado"


def test_causa_implementacao_volta_ao_desenvolvedor_com_o_relatorio(montar):
    runner = RunnerFalso(vereditos=[reprovacao, aprovacao])
    p = montar(runner=runner)
    run_id = p.iniciar(CAMINHO_SDD)
    assert p.historico.estado(run_id) == "MEDIDA"
    assert p.historico.dados(run_id)["tentativa"] == 2
    segundo_dev = [c for c in runner.contratos if c["etapa"] == "desenvolvimento"][1]
    assert segundo_dev["entrada"]["correcao"]["descompassos"] == ["RF01 sem código"]


def test_correcao_parte_da_tentativa_anterior(montar):
    runner = RunnerFalso(vereditos=[reprovacao, aprovacao])
    montar(runner=runner).iniciar(CAMINHO_SDD)
    assert runner.vistos == ["x = 1\n", "x = 2\n"]


def test_para_na_terceira_tentativa(montar):
    runner = RunnerFalso(vereditos=[reprovacao, reprovacao, reprovacao])
    p = montar(runner=runner)
    run_id = p.iniciar(CAMINHO_SDD)
    assert p.historico.estado(run_id) == "PARADA_LIMITE"
    assert p.github.merges == []
    assert "PARADA_LIMITE" in p.notificador.mensagens[-1]


def test_cada_tentativa_tem_contrato_e_token_novos(montar):
    runner = RunnerFalso(vereditos=[reprovacao, aprovacao])
    montar(runner=runner).iniciar(CAMINHO_SDD)
    tokens = [c["token"] for c in runner.contratos]
    assert len(tokens) == len(set(tokens)) == 5


def test_causa_especificacao_para_e_nao_chama_o_desenvolvedor_de_novo(montar):
    runner = RunnerFalso(vereditos=[lambda c: reprovacao(c, "especificacao")])
    p = montar(runner=runner)
    run_id = p.iniciar(CAMINHO_SDD)
    assert p.historico.estado(run_id) == "PARADA_ESPECIFICACAO"
    assert len([c for c in runner.contratos if c["etapa"] == "desenvolvimento"]) == 1


def test_causa_ambiente_pausa_sem_consumir_tentativa_e_retoma(montar):
    runner = RunnerFalso(vereditos=[lambda c: reprovacao(c, "ambiente"), aprovacao])
    p = montar(runner=runner)
    run_id = p.iniciar(CAMINHO_SDD)
    assert p.historico.estado(run_id) == "PAUSADA_AMBIENTE"
    assert p.retomar(run_id) == "MEDIDA"
    assert p.historico.dados(run_id)["tentativa"] == 1


def test_desenvolvedor_bloqueado_para_por_especificacao(montar):
    def dev(contrato, _):
        return resposta_dev(contrato, status="bloqueado", bloqueio="limite não definido")

    p = montar(runner=RunnerFalso(dev=dev))
    run_id = p.iniciar(CAMINHO_SDD)
    assert p.historico.estado(run_id) == "PARADA_ESPECIFICACAO"
    assert "limite não definido" in p.notificador.mensagens[-1]


def test_arquivo_fora_do_escopo_reprova_antes_do_revisor(montar):
    runner = RunnerFalso(arquivo="fora.py", vereditos=[])
    p = montar(runner=runner)
    run_id = p.iniciar(CAMINHO_SDD)
    assert p.historico.estado(run_id) == "PARADA_LIMITE"
    assert not [c for c in runner.contratos if c["etapa"] == "verificacao"]
    assert "fora.py" in p.historico.transicoes(run_id)[-1][2]


def test_workflow_plantado_e_recusado_mesmo_se_estivesse_no_escopo(montar):
    runner = RunnerFalso(arquivo=".github/workflows/x.yml", vereditos=[])
    p = montar(runner=runner)
    run_id = p.iniciar(CAMINHO_SDD)
    assert ".github/workflows/x.yml" in p.historico.dados(run_id)["relatorio"]["evidencias"][0]


def test_patch_vazio_reprova(montar):
    p = montar(runner=RunnerFalso(dev=lambda c, _: resposta_dev(c), vereditos=[]))
    run_id = p.iniciar(CAMINHO_SDD)
    assert "patch vazio" in p.historico.dados(run_id)["relatorio"]["evidencias"][0]


def test_teste_reprovado_nao_chega_ao_revisor(montar):
    runner = RunnerFalso(vereditos=[])
    p = montar(runner=runner, ambiente=AmbienteFalso({"rodar-testes": 1}))
    p.iniciar(CAMINHO_SDD)
    assert not [c for c in runner.contratos if c["etapa"] == "verificacao"]


@pytest.mark.parametrize("varredura", ["segredos", "semgrep"])
def test_gate_de_seguranca_reprova(montar, varredura):
    runner = RunnerFalso(vereditos=[])
    p = montar(runner=runner, ambiente=AmbienteFalso({varredura: 1}))
    run_id = p.iniciar(CAMINHO_SDD)
    assert p.historico.estado(run_id) == "PARADA_LIMITE"
    assert p.github.merges == []


def test_varredura_que_nao_rodou_nao_vale_como_aprovacao(montar):
    p = montar(ambiente=AmbienteFalso({"segredos": 2}))
    run_id = p.iniciar(CAMINHO_SDD)
    assert p.historico.estado(run_id) == "PAUSADA_AMBIENTE"


def test_comando_inexistente_e_ambiente_e_nao_implementacao(montar):
    p = montar(ambiente=AmbienteFalso({"rodar-testes": 127}))
    run_id = p.iniciar(CAMINHO_SDD)
    assert p.historico.estado(run_id) == "PAUSADA_AMBIENTE"
    assert p.historico.dados(run_id)["tentativa"] == 1


def test_token_errado_e_recusado_e_conta_tentativa(montar):
    def dev(contrato, trabalho):
        (trabalho / "a.py").write_text("x = 9\n")
        if contrato["tentativa"] == 1:
            return resposta_dev(contrato, token="x" * 43)
        return resposta_dev(contrato)

    p = montar(runner=RunnerFalso(dev=dev))
    run_id = p.iniciar(CAMINHO_SDD)
    assert "RESPOSTA_RECUSADA" in caminho(p, run_id)
    assert p.historico.estado(run_id) == "MEDIDA"


def test_evidencia_inventada_e_recusada(montar):
    def dev(contrato, trabalho):
        (trabalho / "a.py").write_text("x = 9\n")
        if contrato["tentativa"] == 1:
            return resposta_dev(contrato, evidencias=["nao/existe.py:1 — feito"])
        return resposta_dev(contrato)

    p = montar(runner=RunnerFalso(dev=dev))
    run_id = p.iniciar(CAMINHO_SDD)
    assert "RESPOSTA_RECUSADA" in caminho(p, run_id)


def test_veredito_com_contas_erradas_e_recusado(montar):
    def errado(contrato):
        return aprovacao(contrato) | {"testes": {"passaram": 9, "falharam": 0}}

    p = montar(runner=RunnerFalso(vereditos=[errado, aprovacao]))
    run_id = p.iniciar(CAMINHO_SDD)
    assert "RESPOSTA_RECUSADA" in caminho(p, run_id)


class Quebra(Exception):
    pass


def test_retoma_apos_queda_com_agente_rodando_e_contrato_novo(montar):
    class RunnerQueCai(RunnerFalso):
        def __init__(self):
            super().__init__()
            self.caiu = False

        def executar(self, prompt, schema, dir_trabalho, modelo, ferramentas):
            if not self.caiu and contrato_do(prompt)["etapa"] == "desenvolvimento":
                self.caiu = True
                self.contratos.append(contrato_do(prompt))
                raise Quebra
            return super().executar(prompt, schema, dir_trabalho, modelo, ferramentas)

    runner = RunnerQueCai()
    p = montar(runner=runner)
    with pytest.raises(Quebra):
        p.iniciar(CAMINHO_SDD)
    run_id = p.historico.listar()[0][0]
    assert p.historico.estado(run_id) == "AGENTE_RODANDO"

    depois_da_queda = montar(runner=runner)
    assert depois_da_queda.executar(run_id) == "MEDIDA"
    tokens = [c["token"] for c in runner.contratos if c["etapa"] == "desenvolvimento"]
    assert len(set(tokens)) == 2
    assert depois_da_queda.historico.dados(run_id)["tentativa"] == 1


def test_limite_de_uso_pausa_e_retoma_sem_consumir_tentativa(montar):
    class RunnerNoLimite(RunnerFalso):
        def __init__(self):
            super().__init__()
            self.limite = True

        def executar(self, prompt, schema, dir_trabalho, modelo, ferramentas):
            if self.limite:
                self.limite = False
                raise FalhaDeExecucao("limite_uso", "limite atingido")
            return super().executar(prompt, schema, dir_trabalho, modelo, ferramentas)

    p = montar(runner=RunnerNoLimite())
    run_id = p.iniciar(CAMINHO_SDD)
    assert p.historico.estado(run_id) == "PAUSADA_LIMITE_USO"
    assert p.retomar(run_id) == "MEDIDA"
    assert p.historico.dados(run_id)["tentativa"] == 1


def test_ci_reprovado_volta_ao_desenvolvedor(montar):
    class GithubCiInstavel(GithubFalso):
        def __init__(self):
            super().__init__()
            self.fila = [("falhou", "e2e"), ("passou", ""), ("passou", "")]

        def esperar_checks(self, numero):
            return self.fila.pop(0)

    p = montar(github=GithubCiInstavel(), runner=RunnerFalso(vereditos=[aprovacao, aprovacao]))
    run_id = p.iniciar(CAMINHO_SDD)
    assert p.historico.estado(run_id) == "MEDIDA"
    assert p.historico.dados(run_id)["tentativa"] == 2
    assert p.github.merges == [7, 70]
    assert p.github.fechadas == [7]
    assert [ramo for ramo, _, _ in p.github.prs][:2] == [
        f"feature/sdd-x-0001-{run_id[:8]}-t1",
        f"feature/sdd-x-0001-{run_id[:8]}-t2",
    ]


def test_ci_sem_resultado_nao_faz_merge(montar):
    p = montar(github=GithubFalso(checks=("sem_checks", "")))
    run_id = p.iniciar(CAMINHO_SDD)
    assert p.historico.estado(run_id) == "PAUSADA_AMBIENTE"
    assert p.github.merges == []


@pytest.mark.parametrize("aprovador", [None, "outra-pessoa"])
def test_sdd_sem_aprovacao_por_pr_de_quem_pode_e_recusada(montar, aprovador):
    runner = RunnerFalso()
    p = montar(runner=runner, github=GithubFalso(aprovador=aprovador))
    run_id = p.iniciar(CAMINHO_SDD)
    assert p.historico.estado(run_id) == "RECUSADA_ENTRADA"
    assert runner.contratos == []


def test_sdd_inexistente_e_recusada(montar):
    p = montar()
    assert p.historico.estado(p.iniciar("docs/sdd/nada.md")) == "RECUSADA_ENTRADA"


def test_sdd_invalida_para_antes_de_gastar_agente(montar):
    runner = RunnerFalso()
    p = montar(runner=runner, fonte=FonteFalsa(problemas=["NEEDS CLARIFICATION pendente"]))
    run_id = p.iniciar(CAMINHO_SDD)
    assert p.historico.estado(run_id) == "PARADA_ESPECIFICACAO"
    assert runner.contratos == []


def test_falha_do_repositorio_pausa(montar, monkeypatch):
    def falha(*_):
        raise modulo.FalhaDePublicacao("sem rede")

    monkeypatch.setattr(modulo, "enviar_ramo", falha)
    p = montar()
    run_id = p.iniciar(CAMINHO_SDD)
    assert p.historico.estado(run_id) == "PAUSADA_AMBIENTE"
    monkeypatch.undo()
    monkeypatch.setattr(modulo, "preparar_release", lambda *a: (8, "0.1.1"))
    assert p.retomar(run_id) == "MEDIDA"


def test_nao_sobra_copia_de_trabalho_do_agente(montar, tmp_path):
    p = montar()
    run_id = p.iniciar(CAMINHO_SDD)
    assert not Path(tmp_path / "runs" / run_id / "trabalho").exists()


# Fase 2


def plano(contrato, _):
    return {
        "contrato_id": contrato["contrato_id"],
        "token": contrato["token"],
        "etapa": "planejamento",
        "status": "concluido",
        "tarefas": [{"numero": "1", "descricao": "Fazer", "arquivos": ["a.py"]}],
    }


def escrever_testes(contrato, trabalho):
    (trabalho / "tests").mkdir(exist_ok=True)
    (trabalho / "tests/test_a.py").write_text("assert True\n")
    return resposta_testador(contrato)


def resposta_testador(contrato, **extras):
    return {
        "contrato_id": contrato["contrato_id"],
        "token": contrato["token"],
        "etapa": "testes",
        "status": "concluido",
        "resumo": "testes",
        "evidencias": [],
    } | extras


MEDIO = {"sizing": "medium"}


def test_risco_baixo_nao_chama_planejador_nem_testador(montar):
    runner = RunnerFalso()
    montar(runner=runner).iniciar(CAMINHO_SDD)
    assert [c["etapa"] for c in runner.contratos] == [
        "decisao",
        "desenvolvimento",
        "verificacao",
    ]


def test_risco_medio_passa_por_planejador_e_testador(montar, remoto):
    runner = RunnerFalso(agentes={"planejamento": plano, "testes": escrever_testes})
    p = montar(runner=runner, fonte=FonteFalsa(**MEDIO))
    run_id = p.iniciar(CAMINHO_SDD)
    assert p.historico.estado(run_id) == "MEDIDA"
    assert [c["etapa"] for c in runner.contratos] == [
        "decisao",
        "planejamento",
        "desenvolvimento",
        "testes",
        "verificacao",
    ]
    assert runner.contratos[2]["entrada"]["tarefas"][0]["descricao"] == "Fazer"
    ramo = p.github.prs[0][0]
    assert git("show", f"{ramo}:tests/test_a.py", cwd=remoto) == "assert True"
    assert git("show", f"{ramo}:a.py", cwd=remoto) == "x = 2"


def test_sdd_com_tarefas_dispensa_o_planejador(montar):
    runner = RunnerFalso(agentes={"testes": escrever_testes})
    fonte = FonteFalsa(tarefas=[{"numero": "1"}], **MEDIO)
    montar(runner=runner, fonte=fonte).iniciar(CAMINHO_SDD)
    assert "planejamento" not in [c["etapa"] for c in runner.contratos]


def test_planejador_bloqueado_para_por_especificacao(montar):
    def bloqueado(contrato, _):
        return plano(contrato, _) | {"status": "bloqueado", "bloqueio": "ambígua", "tarefas": []}

    p = montar(runner=RunnerFalso(agentes={"planejamento": bloqueado}), fonte=FonteFalsa(**MEDIO))
    assert p.historico.estado(p.iniciar(CAMINHO_SDD)) == "PARADA_ESPECIFICACAO"


def test_plano_fora_do_escopo_e_ignorado(montar):
    def fora(contrato, _):
        resposta = plano(contrato, _)
        resposta["tarefas"][0]["arquivos"] = ["segredo.py"]
        return resposta

    runner = RunnerFalso(agentes={"planejamento": fora, "testes": escrever_testes})
    p = montar(runner=runner, fonte=FonteFalsa(**MEDIO))
    run_id = p.iniciar(CAMINHO_SDD)
    assert "segredo.py" in " ".join(m for _, _, m in p.historico.transicoes(run_id))
    assert "tarefas" not in runner.contratos[1]["entrada"]


def test_testador_barrado_ao_mexer_em_producao(montar):
    def sabotador(contrato, trabalho):
        if contrato["tentativa"] == 1:
            (trabalho / "a.py").write_text("x = 'testador'\n")
            return resposta_testador(contrato)
        return escrever_testes(contrato, trabalho)

    runner = RunnerFalso(agentes={"planejamento": plano, "testes": sabotador})
    p = montar(runner=runner, fonte=FonteFalsa(**MEDIO))
    run_id = p.iniciar(CAMINHO_SDD)
    transicoes = p.historico.transicoes(run_id)
    assert any("testador alterou produção: a.py" in m for _, _, m in transicoes)
    assert p.historico.estado(run_id) == "MEDIDA"
    assert p.historico.dados(run_id)["tentativa"] == 2


def test_alteracao_recusada_do_testador_nao_chega_a_pr(montar, remoto):
    def sabotador(contrato, trabalho):
        (trabalho / "a.py").write_text("x = 'testador'\n")
        return resposta_testador(contrato)

    runner = RunnerFalso(agentes={"planejamento": plano, "testes": sabotador}, vereditos=[])
    p = montar(runner=runner, fonte=FonteFalsa(**MEDIO))
    run_id = p.iniciar(CAMINHO_SDD)
    assert p.historico.estado(run_id) == "PARADA_LIMITE"
    assert p.github.prs == []


def seguranca(status="aprovado", achados=()):
    def agente(contrato, _):
        return {
            "contrato_id": contrato["contrato_id"],
            "token": contrato["token"],
            "etapa": "seguranca",
            "status": status,
            "achados": list(achados),
        }

    return agente


ALTO = {"sizing": "large", "tarefas": [{"numero": "1"}]}


def test_risco_alto_passa_por_revisao_de_seguranca_com_opus(montar):
    runner = RunnerFalso(agentes={"testes": escrever_testes, "seguranca": seguranca()})
    p = montar(runner=runner, fonte=FonteFalsa(**ALTO))
    run_id = p.iniciar(CAMINHO_SDD)
    assert p.historico.estado(run_id) == "MEDIDA"
    assert "seguranca" in [c["etapa"] for c in runner.contratos]
    assert p.historico.dados(run_id)["modelo"] == "claude-opus-5-5"


def test_achado_de_seguranca_volta_ao_desenvolvedor(montar):
    fila = [seguranca("reprovado", ["a.py:1 — segredo no código"]), seguranca()]
    runner = RunnerFalso(
        agentes={"testes": escrever_testes, "seguranca": lambda c, t: fila.pop(0)(c, t)},
        vereditos=[aprovacao],
    )
    p = montar(runner=runner, fonte=FonteFalsa(**ALTO))
    run_id = p.iniciar(CAMINHO_SDD)
    assert p.historico.estado(run_id) == "MEDIDA"
    segundo = [c for c in runner.contratos if c["etapa"] == "desenvolvimento"][1]
    assert "segredo no código" in segundo["entrada"]["correcao"]["evidencias"][0]


def test_aprovado_com_achado_nao_vale(montar):
    runner = RunnerFalso(
        agentes={
            "testes": escrever_testes,
            "seguranca": seguranca("aprovado", ["a.py:1 — falha"]),
        },
        vereditos=[],
    )
    p = montar(runner=runner, fonte=FonteFalsa(**ALTO))
    assert p.historico.estado(p.iniciar(CAMINHO_SDD)) == "PARADA_LIMITE"


def decisor(risco="baixo", confianca=0.9):
    def agente(contrato, _):
        return {
            "contrato_id": contrato["contrato_id"],
            "token": contrato["token"],
            "etapa": "decisao",
            "risco": risco,
            "confianca": confianca,
            "justificativa": "motivo",
        }

    return agente


def test_regra_de_risco_alto_decide_sem_chamar_o_decisor(montar):
    runner = RunnerFalso(agentes={"testes": escrever_testes, "seguranca": seguranca()})
    montar(runner=runner, fonte=FonteFalsa(**ALTO)).iniciar(CAMINHO_SDD)
    assert "decisao" not in [c["etapa"] for c in runner.contratos]


def test_sizing_small_sem_sinal_passa_pelo_decisor(montar):
    runner = RunnerFalso()
    p = montar(runner=runner)
    run_id = p.iniciar(CAMINHO_SDD)
    assert runner.contratos[0]["etapa"] == "decisao"
    assert p.historico.dados(run_id)["risco"] == "baixo"


def test_decisor_nao_desce_abaixo_do_piso_do_sizing():
    class Decisor:
        def classificar_risco(self, entrada):
            return Decisao("baixo", 0.95, "motivo", "decisor")

    assert decidir_risco({"sizing": "medium"}, Decisor()).risco == "medio"
    assert decidir_risco({"sizing": "small"}, Decisor()).risco == "baixo"


def test_decisor_pode_subir_acima_do_piso():
    class Decisor:
        def classificar_risco(self, entrada):
            return Decisao("alto", 0.95, "motivo", "decisor")

    assert decidir_risco({"sizing": "small"}, Decisor()).risco == "alto"


def test_sem_regra_o_decisor_classifica(montar):
    runner = RunnerFalso(agentes={"decisao": decisor("baixo", 0.95)})
    p = montar(runner=runner, fonte=FonteFalsa(sizing=None))
    run_id = p.iniciar(CAMINHO_SDD)
    assert runner.contratos[0]["etapa"] == "decisao"
    assert p.historico.estado(run_id) == "MEDIDA"


def test_baixa_confianca_vai_para_o_humano_e_segue_com_a_resposta_dele(montar):
    runner = RunnerFalso(agentes={"decisao": decisor("baixo", 0.5)})
    p = montar(runner=runner, fonte=FonteFalsa(sizing=None))
    run_id = p.iniciar(CAMINHO_SDD)
    assert p.historico.estado(run_id) == "PAUSADA_DECISAO"
    assert [c["etapa"] for c in runner.contratos] == ["decisao"]
    with pytest.raises(ValueError, match="decidir"):
        p.retomar(run_id)
    assert p.decidir(run_id, "baixo") == "MEDIDA"
    assert p.historico.dados(run_id)["risco"] == "baixo"


def test_resposta_invalida_do_decisor_vai_para_o_humano(montar):
    def invalida(contrato, _):
        return decisor()(contrato, _) | {"token": "x" * 43}

    p = montar(runner=RunnerFalso(agentes={"decisao": invalida}), fonte=FonteFalsa(sizing=None))
    assert p.historico.estado(p.iniciar(CAMINHO_SDD)) == "PAUSADA_DECISAO"


def test_small_com_diff_grande_para_por_especificacao(montar):
    def dev(contrato, trabalho):
        for nome in ["a.py", "tests/1.py", "tests/2.py", "tests/3.py", "tests/4.py"]:
            (trabalho / nome).parent.mkdir(exist_ok=True)
            (trabalho / nome).write_text("y = 1\n")
        return resposta_dev(contrato)

    runner = RunnerFalso(dev=dev)
    p = montar(runner=runner)
    run_id = p.iniciar(CAMINHO_SDD)
    assert p.historico.estado(run_id) == "PARADA_ESPECIFICACAO"
    assert "5 arquivos" in p.notificador.mensagens[-1]


def test_agente_nao_ve_o_historico_arquivado(montar, remoto):
    (remoto / "docs/sdd/arquivo").mkdir()
    (remoto / "docs/sdd/arquivo/SDD-X-0000.md").write_text("antiga\n")
    git("add", "-A", cwd=remoto)
    git("commit", "-qm", "arquivo", cwd=remoto)

    def dev(contrato, trabalho):
        assert not (trabalho / "docs/sdd/arquivo").exists()
        (trabalho / "a.py").write_text("x = 3\n")
        return resposta_dev(contrato)

    p = montar(runner=RunnerFalso(dev=dev))
    assert p.historico.estado(p.iniciar(CAMINHO_SDD)) == "MEDIDA"


def test_contexto_vivo_entra_no_contrato(montar, remoto):
    (remoto / "docs/fabrica").mkdir(parents=True)
    (remoto / "docs/fabrica/contexto.md").write_text("Use utc.\n")
    git("add", "-A", cwd=remoto)
    git("commit", "-qm", "contexto", cwd=remoto)
    runner = RunnerFalso()
    montar(runner=runner).iniciar(CAMINHO_SDD)
    desenvolvimento = next(c for c in runner.contratos if c["etapa"] == "desenvolvimento")
    assert desenvolvimento["entrada"]["contexto_vivo"] == "Use utc.\n"


def test_contexto_vivo_acima_do_limite_para(montar, remoto):
    (remoto / "docs/fabrica").mkdir(parents=True)
    (remoto / "docs/fabrica/contexto.md").write_text("x" * 8001)
    git("add", "-A", cwd=remoto)
    git("commit", "-qm", "contexto", cwd=remoto)
    runner = RunnerFalso()
    p = montar(runner=runner)
    assert p.historico.estado(p.iniciar(CAMINHO_SDD)) == "PARADA_ESPECIFICACAO"
    assert runner.contratos == []


def test_ci_do_arquivamento_reprovado_pausa_sem_merge(montar):
    class GithubArquivamento(GithubFalso):
        def __init__(self):
            super().__init__()
            self.fila = [("passou", ""), ("falhou", "lint"), ("passou", "")]

        def esperar_checks(self, numero):
            return self.fila.pop(0)

    p = montar(github=GithubArquivamento())
    run_id = p.iniciar(CAMINHO_SDD)
    assert p.historico.estado(run_id) == "PAUSADA_AMBIENTE"
    assert p.github.merges == [7]
    assert p.retomar(run_id) == "MEDIDA"
    assert p.github.merges == [7, 70]
    assert len([ramo for ramo, _, _ in p.github.prs if "arquivar" in ramo]) == 1


def test_mesma_sdd_nao_roda_duas_vezes_em_aberto(montar):
    runner = RunnerFalso(vereditos=[lambda c: reprovacao(c, "ambiente"), aprovacao])
    p = montar(runner=runner)
    run_id = p.iniciar(CAMINHO_SDD)
    assert p.historico.estado(run_id) == "PAUSADA_AMBIENTE"
    with pytest.raises(modulo.ExecucaoEmAberto, match=run_id):
        p.iniciar(CAMINHO_SDD)


def test_sdd_parada_pode_rodar_de_novo(montar):
    primeira = RunnerFalso(vereditos=[lambda c: reprovacao(c, "especificacao")])
    p = montar(runner=primeira)
    assert p.historico.estado(p.iniciar(CAMINHO_SDD)) == "PARADA_ESPECIFICACAO"
    p.runner = RunnerFalso()
    assert p.historico.estado(p.iniciar(CAMINHO_SDD)) == "MEDIDA"


def test_sdd_sem_aprovacao_no_terminal_e_recusada(montar, tmp_path):
    runner = RunnerFalso()
    p = montar(runner=runner, aprovacoes=Aprovacoes(tmp_path / "a.db"))
    run_id = p.iniciar(CAMINHO_SDD)
    assert p.historico.estado(run_id) == "RECUSADA_ENTRADA"
    assert "aprovar" in p.historico.transicoes(run_id)[-1][2]
    assert runner.contratos == []


def test_aprovacao_de_outro_conteudo_nao_vale(montar, tmp_path):
    aprovacoes = Aprovacoes(tmp_path / "a.db")
    aprovacoes.registrar("X", CAMINHO_SDD, b"# SDD antes da mudanca\n", "terminal")
    p = montar(aprovacoes=aprovacoes)
    assert p.historico.estado(p.iniciar(CAMINHO_SDD)) == "RECUSADA_ENTRADA"


def test_aprovacao_do_conteudo_atual_libera_a_entrada(montar, remoto, tmp_path):
    aprovacoes = Aprovacoes(tmp_path / "a.db")
    aprovacoes.registrar("X", CAMINHO_SDD, (remoto / CAMINHO_SDD).read_bytes(), "terminal")
    p = montar(aprovacoes=aprovacoes)
    assert p.historico.estado(p.iniciar(CAMINHO_SDD)) == "MEDIDA"

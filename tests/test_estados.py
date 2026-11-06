import pytest

from fabrica.estados import TERMINAIS, TRANSICOES, Historico, TransicaoInvalida


@pytest.fixture
def historico(tmp_path):
    return Historico(tmp_path / "f.db")


def test_nao_pula_etapa(historico):
    run_id = historico.criar("X", "a.md")
    with pytest.raises(TransicaoInvalida):
        historico.avancar(run_id, "MERGE_EM_DEVELOP", "atalho")
    assert historico.estado(run_id) == "DETECTADO"
    assert len(historico.transicoes(run_id)) == 1


def test_transicao_grava_historico_e_dados(historico):
    run_id = historico.criar("X", "a.md", {"a": 1})
    historico.avancar(run_id, "ENTRADA_OK", "ok", {"b": 2})
    assert historico.dados(run_id) == {"a": 1, "b": 2}
    assert historico.transicoes(run_id)[-1] == ("DETECTADO", "ENTRADA_OK", "ok")


def test_terminal_nao_tem_saida(historico):
    run_id = historico.criar("X", "a.md")
    historico.avancar(run_id, "RECUSADA_ENTRADA", "não")
    with pytest.raises(TransicaoInvalida):
        historico.avancar(run_id, "ENTRADA_OK", "volta")


def test_estado_persiste_entre_processos(tmp_path):
    banco = tmp_path / "f.db"
    run_id = Historico(banco).criar("X", "a.md")
    Historico(banco).avancar(run_id, "ENTRADA_OK", "ok")
    assert Historico(banco).estado(run_id) == "ENTRADA_OK"


def antecessores(destino):
    return {origem for origem, destinos in TRANSICOES.items() if destino in destinos}


# Invariantes herdadas das leis do framework: ordem documento -> código -> verificação -> merge.
def test_merge_so_depois_do_ci():
    assert antecessores("MERGE_EM_DEVELOP") == {"CI_E2E", "PAUSADA_AMBIENTE"}


def test_ci_so_depois_da_pr_e_pr_so_depois_da_verificacao():
    assert antecessores("CI_E2E") == {"PR_PARA_DEVELOP", "PAUSADA_AMBIENTE"}
    assert antecessores("PR_PARA_DEVELOP") == {"VERIFY_SDD", "PAUSADA_AMBIENTE"}


def test_verificacao_so_depois_da_seguranca_e_dos_gates():
    assert antecessores("VERIFY_SDD") == {"SEGURANCA", "PAUSADA_AMBIENTE", "PAUSADA_LIMITE_USO"}
    assert antecessores("SEGURANCA") == {"GATES_LOCAIS", "PAUSADA_AMBIENTE", "PAUSADA_LIMITE_USO"}
    assert antecessores("GATES_LOCAIS") == {
        "RESPOSTA_VALIDA",
        "TESTADOR_RODANDO",
        "PAUSADA_AMBIENTE",
    }


def test_agente_so_com_contrato():
    assert antecessores("AGENTE_RODANDO") == {"CONTRATO_EMITIDO"}


def test_entrada_nao_salta_direto_para_o_agente():
    assert TRANSICOES["DETECTADO"].isdisjoint({"AGENTE_RODANDO", "CONTRATO_EMITIDO"})


def test_toda_transicao_aponta_para_estado_conhecido():
    assert all(d in TRANSICOES for destinos in TRANSICOES.values() for d in destinos)
    assert TERMINAIS == {"RECUSADA_ENTRADA", "PARADA_ESPECIFICACAO", "PARADA_LIMITE", "MEDIDA"}

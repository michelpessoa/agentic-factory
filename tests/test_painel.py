import http.client
import sqlite3
import threading

import pytest

from fabrica.estados import Historico
from fabrica.painel import _ler, criar_servidor, pagina_da_execucao, pagina_inicial

TOKEN = "token-ficticio-de-contrato-usado-so-neste-teste"
INJECAO = "<script>alert(1)</script>"


@pytest.fixture
def banco(tmp_path):
    return tmp_path / "f.db"


@pytest.fixture
def execucao(banco):
    historico = Historico(banco)
    run_id = historico.criar(
        "COBAIA",
        f"docs/{INJECAO}.md",
        {"tentativa": 2, "custo_usd": 0.5, "risco": "alto", "validacao": {"token": TOKEN}},
    )
    historico.avancar(run_id, "ENTRADA_OK", f"motivo {INJECAO}")
    historico.avancar(run_id, "PAUSADA_DECISAO", "baixa confiança")
    return run_id


@pytest.fixture
def servidor(banco, execucao):
    instancia = criar_servidor(banco, 0)
    threading.Thread(target=instancia.serve_forever, daemon=True).start()
    yield instancia.server_address[1]
    instancia.shutdown()
    instancia.server_close()


def pedir(porta, caminho, metodo="GET", host=None):
    conexao = http.client.HTTPConnection("127.0.0.1", porta)
    conexao.putrequest(metodo, caminho, skip_host=True)
    conexao.putheader("Host", host or f"127.0.0.1:{porta}")
    conexao.endheaders()
    resposta = conexao.getresponse()
    corpo = resposta.read().decode("utf-8")
    conexao.close()
    return resposta, corpo


def test_inicial_mostra_estado_custo_e_o_que_espera_o_humano(banco, execucao):
    html = pagina_inicial(banco)
    assert "PAUSADA_DECISAO" in html
    assert "US$ 0.50" in html
    assert "<b>1</b>esperando você" in html


def test_detalhe_mostra_transicoes_e_como_seguir(banco, execucao):
    html = pagina_da_execucao(banco, execucao)
    assert "baixa confiança" in html
    assert "python -m fabrica decidir" in html


def test_texto_de_agente_nao_vira_html(banco, execucao):
    for html in (pagina_inicial(banco), pagina_da_execucao(banco, execucao)):
        assert INJECAO not in html
        assert "&lt;script&gt;" in html


def test_token_do_contrato_nao_aparece(banco, execucao):
    assert TOKEN not in pagina_inicial(banco)
    assert TOKEN not in pagina_da_execucao(banco, execucao)


def test_execucao_inexistente_devolve_404(servidor):
    resposta, _ = pedir(servidor, "/execucao/nao-existe")
    assert resposta.status == 404


def test_pagina_sai_com_politica_que_impede_script(servidor):
    resposta, _ = pedir(servidor, "/")
    assert resposta.status == 200
    assert "default-src 'none'" in resposta.getheader("Content-Security-Policy")


def test_host_de_fora_e_recusado(servidor):
    resposta, corpo = pedir(servidor, "/", host="malicioso.example")
    assert resposta.status == 403
    assert "COBAIA" not in corpo


def test_nao_aceita_escrita_nem_abre_banco_para_escrever(banco, execucao, servidor):
    antes = sqlite3.connect(banco).execute("SELECT COUNT(*) FROM transicoes").fetchone()
    resposta, _ = pedir(servidor, f"/execucao/{execucao}", metodo="POST")
    assert resposta.status == 501
    assert sqlite3.connect(banco).execute("SELECT COUNT(*) FROM transicoes").fetchone() == antes


def test_leitura_do_painel_nao_consegue_escrever(banco, execucao):
    with pytest.raises(sqlite3.OperationalError):
        _ler(banco, "DELETE FROM transicoes")


def test_escuta_so_na_interface_local(servidor, banco):
    instancia = criar_servidor(banco, 0)
    try:
        assert instancia.server_address[0] == "127.0.0.1"
    finally:
        instancia.server_close()

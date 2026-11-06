import pytest

from fabrica.contratos import (
    Cartorio,
    RespostaRecusada,
    problemas_de_coerencia,
    problemas_de_evidencia,
)


@pytest.fixture
def cartorio(tmp_path):
    return Cartorio(tmp_path / "fabrica.db")


def validacao_para(contrato, **extras):
    criterio = {
        "numero": "1",
        "comando": "pytest",
        "saida": "1 passed",
        "sensor": "falhou com a condição invertida",
        "passou": True,
        "assertion": "tests/a.py:3",
        "perfil": "automatizado",
    }
    resposta = {
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
    return resposta | extras


def emitir(cartorio, tentativa=1):
    return cartorio.emitir("run-1", "COBAIA", "verificacao", tentativa, {"sdd_id": "SDD-X-0001"})


def test_aceita_resposta_dentro_do_contrato(cartorio):
    contrato = emitir(cartorio)
    assert (
        cartorio.receber(contrato["contrato_id"], validacao_para(contrato))["status"] == "aprovado"
    )


def test_recusa_token_reutilizado(cartorio):
    contrato = emitir(cartorio)
    cartorio.receber(contrato["contrato_id"], validacao_para(contrato))
    with pytest.raises(RespostaRecusada, match="reutilizado"):
        cartorio.receber(contrato["contrato_id"], validacao_para(contrato))


def test_recusa_token_errado(cartorio):
    contrato = emitir(cartorio)
    with pytest.raises(RespostaRecusada, match="token inválido"):
        cartorio.receber(contrato["contrato_id"], validacao_para(contrato, token="x" * 43))


def test_recusa_token_de_outro_contrato(cartorio):
    antigo, novo = emitir(cartorio), emitir(cartorio, tentativa=2)
    resposta = validacao_para(novo, token=antigo["token"])
    with pytest.raises(RespostaRecusada, match="token inválido"):
        cartorio.receber(novo["contrato_id"], resposta)


def test_recusa_contrato_desconhecido(cartorio):
    with pytest.raises(RespostaRecusada, match="desconhecido"):
        cartorio.receber("nao-existe", {})


def test_resposta_fora_do_schema_nao_consome_o_token(cartorio):
    contrato = emitir(cartorio)
    with pytest.raises(RespostaRecusada, match="fora do schema"):
        cartorio.receber(contrato["contrato_id"], validacao_para(contrato, extra="x"))
    assert cartorio.receber(contrato["contrato_id"], validacao_para(contrato))


def test_recusa_tentativa_diferente_do_contrato(cartorio):
    contrato = emitir(cartorio)
    with pytest.raises(RespostaRecusada, match="tentativa"):
        cartorio.receber(contrato["contrato_id"], validacao_para(contrato, tentativa=2))


@pytest.mark.parametrize(
    "extras",
    [
        {"status": "aprovado", "causa": "implementacao"},
        {"status": "reprovado", "causa": None},
        {"status": "aprovado", "testes": {"passaram": 0, "falharam": 1}},
        {"causa": "outra"},
        {"evidencias": ["sem formato"]},
    ],
)
def test_schema_recusa_veredito_incoerente(cartorio, extras):
    contrato = emitir(cartorio)
    with pytest.raises(RespostaRecusada, match="fora do schema"):
        cartorio.receber(contrato["contrato_id"], validacao_para(contrato, **extras))


def test_token_em_claro_nao_fica_no_banco(tmp_path):
    caminho = tmp_path / "fabrica.db"
    contrato = emitir(Cartorio(caminho))
    assert contrato["token"].encode() not in caminho.read_bytes()


def test_evidencia_confere_arquivo_e_linha(tmp_path):
    (tmp_path / "a.py").write_text("um\ndois\n")
    assert problemas_de_evidencia(tmp_path, ["a.py:2 — ok"]) == []
    assert "linha inexistente" in problemas_de_evidencia(tmp_path, ["a.py:3 — x"])[0]
    assert "arquivo inexistente" in problemas_de_evidencia(tmp_path, ["b.py:1 — x"])[0]


def test_evidencia_nao_sai_da_raiz(tmp_path):
    raiz = tmp_path / "raiz"
    raiz.mkdir()
    (tmp_path / "segredo").write_text("x\n")
    (raiz / "link").symlink_to(tmp_path / "segredo")
    assert "arquivo inexistente" in problemas_de_evidencia(raiz, ["../segredo:1 — x"])[0]
    assert "arquivo inexistente" in problemas_de_evidencia(raiz, ["link:1 — x"])[0]


def test_coerencia_recusa_aprovado_com_criterio_reprovado(cartorio):
    resposta = validacao_para(emitir(cartorio))
    resposta["criterios"][0]["passou"] = False
    assert "aprovado sem todos os critérios aprovados" in problemas_de_coerencia(resposta)


def test_coerencia_recusa_aprovado_sem_criterios(cartorio):
    resposta = validacao_para(emitir(cartorio), criterios=[], testes={"passaram": 0, "falharam": 0})
    assert problemas_de_coerencia(resposta) == ["aprovado sem todos os critérios aprovados"]


def test_coerencia_confere_as_contas(cartorio):
    resposta = validacao_para(emitir(cartorio), testes={"passaram": 5, "falharam": 0})
    assert problemas_de_coerencia(resposta) == ["testes.passaram não bate com os critérios"]


@pytest.mark.parametrize("etapa", ["desenvolvimento", "testes"])
def test_comando_citado_como_evidencia_fica_fora_do_schema(cartorio, etapa):
    contrato = cartorio.emitir("r", "X", etapa, 1, {})
    resposta = {
        "contrato_id": contrato["contrato_id"],
        "token": contrato["token"],
        "etapa": etapa,
        "status": "concluido",
        "resumo": "feito",
        "evidencias": ["python3 -m unittest — 5 testes OK"],
    }
    with pytest.raises(RespostaRecusada, match="fora do schema"):
        cartorio.receber(contrato["contrato_id"], resposta)
    resposta |= {"evidencias": ["a.py:1 — ok"], "comandos": ["python3 -m unittest"]}
    assert cartorio.receber(contrato["contrato_id"], resposta)

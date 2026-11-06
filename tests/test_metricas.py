from pathlib import Path

import pytest
import yaml

from fabrica.metricas import brier, ece, mcnemar_exato, resumir, wilson

CASOS = Path(__file__).resolve().parent.parent / "avaliacao" / "casos-decisor.yaml"


def resposta(id_, esperado, risco, confianca, ambiguo=False):
    return {
        "id": id_,
        "esperado": esperado,
        "risco": risco,
        "confianca": confianca,
        "ambiguo": ambiguo,
    }


def test_wilson_com_amostra_pequena_e_largo_e_sem_amostra_nao_afirma_nada():
    assert wilson(0, 0) == (0.0, 1.0)
    baixo, alto = wilson(9, 10)
    assert 0.55 < baixo < 0.6 and 0.98 < alto < 0.99


def test_ece_zero_quando_confianca_bate_com_acerto_e_alto_quando_nao_bate():
    assert ece([(1.0, True), (1.0, True)]) == 0.0
    assert ece([(0.95, False), (0.95, False)]) == pytest.approx(0.95)


def test_brier_mede_a_distancia_ate_o_acerto():
    assert brier([(1.0, True)]) == 0.0
    assert brier([(1.0, False)]) == 1.0


def test_mcnemar_exato():
    assert mcnemar_exato(0, 0) == 1.0
    assert mcnemar_exato(5, 5) == 1.0
    assert mcnemar_exato(0, 6) == pytest.approx(2 / 64)


def test_resumir_conta_so_a_subestimacao_acima_do_limiar_como_erro_perigoso():
    resumo = resumir(
        [
            resposta("certo", "alto", "alto", 0.9),
            resposta("perigoso", "alto", "baixo", 0.9),
            resposta("exagerado", "baixo", "alto", 0.9),
            resposta("foi-ao-humano", "alto", "baixo", 0.5),
            resposta("ambiguo", "alto", "medio", 0.3, ambiguo=True),
        ],
        0.8,
    )
    assert resumo["casos"] == 4
    assert resumo["aceitas"] == 3
    assert resumo["cobertura"] == 0.75
    assert resumo["acerto_aceitas"] == pytest.approx(1 / 3)
    assert resumo["subestimadas"] == ["perigoso"]
    assert (resumo["ambiguos_ao_humano"], resumo["ambiguos"]) == (1, 1)


def test_todo_caso_tem_gabarito_valido():
    casos = yaml.safe_load(CASOS.read_text(encoding="utf-8"))["casos"]
    assert len({c["id"] for c in casos}) == len(casos)
    for caso in casos:
        assert caso["risco"] in {"baixo", "medio", "alto"}

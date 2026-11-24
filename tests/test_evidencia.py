"""Cenários vindos das falhas reais do `LESSONS.md` de projetos com o framework."""

import pytest

from adapters.doc_traceability import FonteDocTraceability
from adapters.doc_traceability.compilador import SddInvalida, compilar_sdd
from adapters.doc_traceability.evidencia import registrar_evidencia
from adapters.doc_traceability.validadores import FRAMEWORK_PADRAO, Framework

SDD = """---
id: SDD-X-0001
type: SDD
title: "Soma"
status: approved
project: "X"
owner: "Dono"
created: "2026-11-05"
updated: "2026-11-05"
relates_to: []
source_docs: []
consumption_instructions: "Leia inteira."
sizing: small
supersedes: null
superseded_by: null
tags: []
---

# Soma

## Resumo executivo

Soma dois números.

## Decisão(ões) de arquitetura aplicável(is)

Sem ADR: sizing `small`.

## Requisitos consolidados

| RF-ID | Requisito | Critério de aceite (EARS) | Arquivos |
|---|---|---|---|
| RF01 | Soma | Quando somar, o sistema deve devolver o total. | `a.py` |

## Especificação técnica consolidada

`soma(a, b)` em `a.py`.

## Critérios de aceite / definição de pronto

| # | Critério (origem: RF-ID / contrato) | Comando de verificação | Resultado esperado | Perfil esperado |
|---|---|---|---|---|
| 1 | RF01 | `python3 -m unittest` | exit 0 | automatizado |

## Instruções específicas para a IA implementadora

Toque só em `a.py`.

## Verificação de escopo (nada a mais, nada a menos)

- [ ] Todo requisito consolidado acima tem código correspondente.
- [ ] Todo arquivo tocado aparece nesta SDD.
- [ ] Nenhuma abstração extra.

## Evidência de verificação (preencher antes de status `implemented`)

**Verificador independente:** sim

| # | Comando rodado | Saída (resumo) | Sensor | Passou? | Assertion (file:line) | Perfil usado |
|---|---|---|---|---|---|---|

## Rastreabilidade

| Campo | Valor |
|---|---|
| source_docs | nenhum |
"""
REGISTRY = """project: "X"
framework_version: "2.3.2"
documents:
  - id: SDD-X-0001
    type: SDD
    title: "Soma"
    status: approved
    owner: "Dono"
    created: "2026-11-05"
    updated: "2026-11-05"
    relates_to: []
    path: "docs/sdd/SDD-X-0001.md"
    tags: []
"""
VALIDACAO = {
    "status": "aprovado",
    "criterios": [
        {
            "numero": "1",
            "comando": "python3 -m unittest | tail -1",
            "saida": "OK",
            "sensor": "falhou com a soma invertida",
            "passou": True,
            "assertion": "tests/t.py:7",
            "perfil": "automatizado",
        }
    ],
    "descompassos": [],
}


@pytest.fixture
def repo(tmp_path):
    (tmp_path / "docs/sdd").mkdir(parents=True)
    (tmp_path / "docs/sdd/SDD-X-0001.md").write_text(SDD, encoding="utf-8")
    (tmp_path / "docs/sdd/registry.yaml").write_text(REGISTRY, encoding="utf-8")
    return tmp_path


CAMINHO = "docs/sdd/SDD-X-0001.md"


def test_evidencia_fica_na_propria_sdd(repo):
    """Lição: `implemented` com a tabela vazia e o PASS só na validation."""
    registrar_evidencia(repo, CAMINHO, VALIDACAO, "aaa", "bbb")
    texto = (repo / CAMINHO).read_text(encoding="utf-8")
    assert "status: implemented" in texto
    assert "falhou com a soma invertida" in texto
    assert "- [ ]" not in texto


def test_relatorio_com_o_nome_que_o_gate_de_ci_exige(repo):
    """Lição: o gate exige validation-SDD-*.md, e o projeto gravava outro nome."""
    caminho = registrar_evidencia(repo, CAMINHO, VALIDACAO, "aaa", "bbb")
    assert caminho == "docs/sdd/validation-SDD-X-0001.md"
    assert "**Veredito:** PASS" in (repo / caminho).read_text(encoding="utf-8")
    assert "**Diff verificado:** aaa..bbb" in (repo / caminho).read_text(encoding="utf-8")


def test_pipe_no_comando_nao_quebra_a_tabela(repo):
    registrar_evidencia(repo, CAMINHO, VALIDACAO, "a", "b")
    assert "unittest \\| tail -1" in (repo / CAMINHO).read_text(encoding="utf-8")


def test_registry_e_documento_mudam_juntos(repo):
    registrar_evidencia(repo, CAMINHO, VALIDACAO, "a", "b")
    assert "status: implemented" in (repo / "docs/sdd/registry.yaml").read_text(encoding="utf-8")


def test_verificacao_reprovada_nao_vira_evidencia(repo):
    with pytest.raises(ValueError, match="aprovada"):
        registrar_evidencia(repo, CAMINHO, VALIDACAO | {"status": "reprovado"}, "a", "b")
    assert "status: approved" in (repo / CAMINHO).read_text(encoding="utf-8")


def test_sdd_em_draft_nao_entra(repo):
    """Lição: SDD implementada ainda em `draft`, sem nunca passar por aprovação."""
    (repo / CAMINHO).write_text(SDD.replace("status: approved", "status: draft"), encoding="utf-8")
    with pytest.raises(SddInvalida, match="approved"):
        compilar_sdd(repo / CAMINHO)


sem_framework = pytest.mark.skipif(not FRAMEWORK_PADRAO.is_dir(), reason="framework ausente")


@sem_framework
def test_validate_state_real_aceita_a_evidencia_gravada(repo):
    fonte = FonteDocTraceability(Framework())
    assert fonte.registrar_verificacao(repo, CAMINHO, VALIDACAO, "a", "b") == []


@sem_framework
def test_validate_state_real_reprova_sem_o_sensor(repo):
    sem_sensor = {
        "status": "aprovado",
        "descompassos": [],
        "criterios": [VALIDACAO["criterios"][0] | {"sensor": " "}],
    }
    fonte = FonteDocTraceability(Framework())
    problemas = fonte.registrar_verificacao(repo, CAMINHO, sem_sensor, "a", "b")
    assert problemas
    assert not any('"schema"' in p for p in problemas)


@sem_framework
def test_entrada_real_junta_validadores_e_compilador(repo):
    fonte = FonteDocTraceability(Framework(), repo, "X")
    assert fonte.problemas_de_entrada(repo, CAMINHO) == []
    (repo / CAMINHO).write_text(SDD.replace("## Critérios de aceite", "## Outra"), encoding="utf-8")
    assert fonte.problemas_de_entrada(repo, CAMINHO)


@sem_framework
def test_entrada_real_da_uma_linha_por_problema_do_json(repo):
    fonte = FonteDocTraceability(Framework(), repo, "X")
    (repo / CAMINHO).write_text(SDD + "\n[NEEDS CLARIFICATION: qual soma?]\n", encoding="utf-8")
    problemas = fonte.problemas_de_entrada(repo, CAMINHO)
    assert any(
        p.startswith("validate_doc.py: SDD-X-0001: tem `NEEDS CLARIFICATION`") for p in problemas
    )


# SDD-FAB-0012, RF03: linha "Fidelidade à origem" na evidência

LINHA_MECANICA = {
    "numero": "Fidelidade à origem (check_source_docs)",
    "comando": "python3 kit/_framework/scripts/check_source_docs.py docs/sdd/SDD-ZERO-0001.md c",
    "saida": "ok",
    "sensor": "sem teste automatizado (script do kit)",
    "passou": True,
    "assertion": "n/a",
    "perfil": "n/a",
}
ITEM_DO_REVISOR = {
    "numero": "Fidelidade à origem",
    "comando": "leitura da SPEC-ZERO-0001 contra a SDD",
    "saida": "nenhum critério relaxado; contratos iguais",
    "sensor": "sem teste automatizado",
    "passou": True,
    "assertion": "n/a",
    "perfil": "manual",
}


def test_fidelidade_linhas_extras_antes_das_do_revisor(repo):
    caminho = registrar_evidencia(repo, CAMINHO, VALIDACAO, "a", "b", [LINHA_MECANICA])
    for arquivo in (repo / CAMINHO, repo / caminho):
        texto = arquivo.read_text(encoding="utf-8")
        mecanica = texto.index("| Fidelidade à origem (check_source_docs) |")
        assert mecanica < texto.index("falhou com a soma invertida")


def sdd_enxuta_de_politica(tmp_path):
    import copy

    from adapters.doc_traceability.redacao import aprovar_por_politica, escrever_sdd
    from tests.test_redacao import ENXUTO
    from tests.test_redacao import registry as registry_da_redacao

    repo = tmp_path / "repo"
    registry_da_redacao(repo, "2.7.0")
    sdd = copy.deepcopy(ENXUTO)
    sdd["requisitos"].append(sdd["requisitos"][0] | {"id": "RF02", "requisito": "Remover"})
    origens = [
        {"id": "SPEC-ZERO-0001", "url": "https://h/blob/main/docs/ZERO/03-spec/SPEC-ZERO-0001.md"}
    ]
    caminho = escrever_sdd(
        repo, sdd, "ZERO", "Dona", "2026-11-24", "approved", "2.7.0", origens=origens
    )
    aprovar_por_politica(repo, caminho, Framework(), "2026-11-24T00:00:00Z")
    return repo, caminho


@sem_framework
def test_fidelidade_sdd_enxuta_chega_a_implemented_no_validate_state_real(tmp_path):
    repo, caminho = sdd_enxuta_de_politica(tmp_path)
    validacao = VALIDACAO | {"criterios": [ITEM_DO_REVISOR, *VALIDACAO["criterios"]]}
    fonte = FonteDocTraceability(Framework())
    problemas = fonte.registrar_verificacao(
        repo, caminho, validacao, "a", "b", linhas_extras=[LINHA_MECANICA]
    )
    assert problemas == []
    texto = (repo / caminho).read_text(encoding="utf-8")
    assert "status: implemented" in texto
    assert "| Fidelidade à origem (check_source_docs) |" in texto


@sem_framework
def test_fidelidade_sem_as_duas_linhas_o_validate_state_real_recusa(tmp_path):
    repo, caminho = sdd_enxuta_de_politica(tmp_path)
    problemas = FonteDocTraceability(Framework()).registrar_verificacao(
        repo, caminho, VALIDACAO, "a", "b"
    )
    assert any("RF04, SPEC-DTF-0014" in p for p in problemas), problemas

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
    assert fonte.registrar_verificacao(repo, CAMINHO, sem_sensor, "a", "b")


@sem_framework
def test_entrada_real_junta_validadores_e_compilador(repo):
    fonte = FonteDocTraceability(Framework())
    assert fonte.problemas_de_entrada(repo, CAMINHO) == []
    (repo / CAMINHO).write_text(SDD.replace("## Critérios de aceite", "## Outra"), encoding="utf-8")
    assert fonte.problemas_de_entrada(repo, CAMINHO)

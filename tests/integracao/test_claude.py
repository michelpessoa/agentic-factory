"""`claude -p` no contêiner, com o token da fábrica. Rodar com `pytest -m claude`."""

import json

import pytest

from fabrica.contratos import schema_da_etapa
from fabrica.execucao import ClaudeDockerRunner

pytestmark = pytest.mark.claude
MODELO = "claude-haiku-5-5"
SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["valor"],
    "properties": {"valor": {"type": "string"}},
}


@pytest.fixture
def runner():
    return ClaudeDockerRunner()


def test_devolve_json_no_schema(runner, tmp_path):
    resultado = runner.executar(
        "Responda com valor igual a pong.", SCHEMA, tmp_path, MODELO, ["Read"]
    )
    assert resultado.resposta == {"valor": "pong"}


@pytest.mark.parametrize("etapa", ["desenvolvimento", "verificacao"])
def test_cli_aceita_os_schemas_reais_dos_contratos(runner, tmp_path, etapa):
    """Sem isso, a CLI ou a API recusam o schema e nenhum agente chega a rodar."""
    prompt = f"Teste de formato. Preencha o schema com valores mínimos, etapa {etapa}, status de bloqueio ou reprovação."
    assert runner.executar(prompt, schema_da_etapa(etapa), tmp_path, MODELO, ["Read"]).resposta


def rodar_medicao(runner, trabalho, script):
    (trabalho / "medir.sh").write_text(script)
    prompt = (
        "Rode com Bash exatamente: sh /trabalho/medir.sh . Depois responda com valor igual a ok."
    )
    runner.executar(prompt, SCHEMA, trabalho, MODELO, ["Bash"])
    return (trabalho / "medicao.txt").read_text().strip()


def test_token_nao_esta_no_ambiente_dos_comandos(runner, tmp_path):
    script = (
        'test -n "$CLAUDE_CODE_OAUTH_TOKEN" && echo presente > /trabalho/medicao.txt '
        "|| echo ausente > /trabalho/medicao.txt\n"
    )
    assert rodar_medicao(runner, tmp_path, script) == "ausente"


def test_risco_residual_token_legivel_no_processo_do_claude(runner, tmp_path):
    """Documenta o risco aceito no ADR-0002. Se falhar, o risco mudou: revise o ADR."""
    script = (
        "for p in /proc/[0-9]*; do "
        "tr '\\\\0' '\\\\n' < $p/environ 2>/dev/null | grep -q '^CLAUDE_CODE_OAUTH_TOKEN=.' "
        "&& cat $p/comm; done > /trabalho/medicao.txt\n"
    )
    assert "claude" in rodar_medicao(runner, tmp_path, script)


def test_hook_plantado_no_repositorio_nao_executa(runner, tmp_path):
    (tmp_path / ".claude").mkdir()
    hook = {"type": "command", "command": "touch /trabalho/hook-executou"}
    configuracao = {"hooks": {"SessionStart": [{"matcher": "*", "hooks": [hook]}]}}
    (tmp_path / ".claude" / "settings.json").write_text(json.dumps(configuracao))
    runner.executar("Responda com valor igual a pong.", SCHEMA, tmp_path, MODELO, ["Read"])
    assert not (tmp_path / "hook-executou").exists()

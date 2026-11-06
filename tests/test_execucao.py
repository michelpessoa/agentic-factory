import json
import subprocess

import pytest

from fabrica.execucao import (
    AmbienteInvalido,
    ClaudeDockerRunner,
    FalhaDeExecucao,
    ambiente_minimo_docker,
    carregar_token,
    interpretar_saida_do_claude,
    preparar_copia,
    verificar_host,
)


def test_recusa_host_com_chave_de_api():
    with pytest.raises(AmbienteInvalido, match="ANTHROPIC_API_KEY"):
        verificar_host({"ANTHROPIC_API_KEY": "x"})


def test_runner_recusa_host_com_chave_de_api(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "x")
    with pytest.raises(AmbienteInvalido):
        ClaudeDockerRunner(token="t")


def test_token_exige_permissao_600(tmp_path):
    caminho = tmp_path / "token"
    caminho.write_text("segredo\n")
    caminho.chmod(0o644)
    with pytest.raises(AmbienteInvalido, match="600"):
        carregar_token(caminho)
    caminho.chmod(0o600)
    assert carregar_token(caminho) == "segredo"


def test_token_ausente_e_ambiente_invalido(tmp_path):
    with pytest.raises(AmbienteInvalido, match="não encontrado"):
        carregar_token(tmp_path / "nada")


@pytest.fixture
def comando(tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    runner = ClaudeDockerRunner(token="SEGREDO")
    return runner.montar_comando({"type": "object"}, tmp_path, "modelo", ["Read", "Bash"])


def test_token_nao_aparece_na_linha_de_comando(comando):
    assert not any("SEGREDO" in parte for parte in comando)
    assert "CLAUDE_CODE_OAUTH_TOKEN" in comando


def test_unica_montagem_e_o_diretorio_de_trabalho(comando, tmp_path):
    montagens = [comando[i + 1] for i, parte in enumerate(comando) if parte == "--mount"]
    assert montagens == [f"type=bind,source={tmp_path},target=/trabalho"]
    assert "--volume" not in comando and "-v" not in comando


@pytest.mark.parametrize(
    "opcao",
    ["--cap-drop=ALL", "--read-only", "--rm", "no-new-privileges", "fabrica-interna"],
)
def test_isolamento_obrigatorio(comando, opcao):
    assert opcao in comando


def test_nao_roda_privilegiado_nem_na_rede_do_host(comando):
    assert "--privileged" not in comando
    assert "host" not in comando


def test_conteiner_e_etiquetado_para_ser_encerrado_depois_de_uma_queda(comando, tmp_path):
    assert f"fabrica.diretorio={tmp_path}" in comando


def test_ignora_configuracao_plantada_no_repositorio(comando):
    assert comando[comando.index("--setting-sources") + 1] == "user"


def test_ambiente_do_docker_nao_herda_segredos(monkeypatch):
    monkeypatch.setenv("GH_TOKEN", "x")
    monkeypatch.setenv("SSH_AUTH_SOCK", "/tmp/s")
    env = ambiente_minimo_docker({"A": "1"})
    assert "GH_TOKEN" not in env and "SSH_AUTH_SOCK" not in env and env["A"] == "1"


def test_saida_valida_devolve_structured_output():
    saida = json.dumps({"structured_output": {"a": 1}, "total_cost_usd": 0.5, "duration_ms": 9})
    resultado = interpretar_saida_do_claude(0, saida, "")
    assert resultado.resposta == {"a": 1} and resultado.custo_usd == 0.5


@pytest.mark.parametrize(
    ("codigo", "stdout", "stderr", "causa"),
    [
        (1, "não é json", "boom", "ambiente"),
        (1, "", "You've hit your limit", "limite_uso"),
        (0, json.dumps({"is_error": True, "result": "Usage limit reached"}), "", "limite_uso"),
        (0, json.dumps({"is_error": True, "result": "erro qualquer"}), "", "ambiente"),
        (0, json.dumps({"result": "sem schema"}), "", "fora_do_contrato"),
    ],
)
def test_falhas_sao_classificadas(codigo, stdout, stderr, causa):
    with pytest.raises(FalhaDeExecucao) as erro:
        interpretar_saida_do_claude(codigo, stdout, stderr)
    assert erro.value.causa == causa


def git(*args, cwd):
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    ).stdout


@pytest.fixture
def repo(tmp_path):
    origem = tmp_path / "origem"
    origem.mkdir()
    git("init", "-q", "-b", "main", cwd=origem)
    git("config", "user.email", "t@t", cwd=origem)
    git("config", "user.name", "t", cwd=origem)
    (origem / "a.txt").write_text("a\n")
    git("add", "-A", cwd=origem)
    git("commit", "-qm", "base", cwd=origem)
    return origem


def test_copia_sem_remoto_e_sem_hooks(repo, tmp_path):
    copia = preparar_copia(repo, "main", tmp_path / "copia")
    assert (copia / "a.txt").read_text() == "a\n"
    assert git("remote", cwd=copia).strip() == ""
    assert not (copia / ".git" / "hooks").exists()


def test_cli_recebe_schema_sem_metadados_de_dialeto(tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    schema = {"$schema": "x", "$id": "y", "allOf": [], "type": "object"}
    comando = ClaudeDockerRunner(token="t").montar_comando(schema, tmp_path, "m", ["Read"])
    assert json.loads(comando[comando.index("--json-schema") + 1]) == {"type": "object"}

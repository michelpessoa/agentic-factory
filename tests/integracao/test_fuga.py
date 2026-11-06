"""Teste de fuga: o que o agente consegue alcançar de dentro do contêiner.

Roda os mesmos argumentos de isolamento do runner, sem Claude. Rodar com `pytest -m docker`.
"""

import os
import subprocess
from pathlib import Path

import pytest

from fabrica.execucao import (
    IMAGEM_AGENTE,
    IMAGEM_GATES,
    REDE_INTERNA,
    URL_PROXY,
    ambiente_minimo_docker,
    argumentos_de_isolamento,
    extrair_patch,
    preparar_copia,
)

pytestmark = pytest.mark.docker
HOME_HOST = Path.home()


def no_conteiner(script, trabalho, imagem=IMAGEM_AGENTE, rede=REDE_INTERNA, extras=None):
    comando = [
        "docker", "run", *argumentos_de_isolamento(trabalho, rede),
        "--env", f"HTTPS_PROXY={URL_PROXY}", "--env", f"HTTP_PROXY={URL_PROXY}",
        imagem, "sh", "-c", script,
    ]  # fmt: skip
    return subprocess.run(
        comando,
        env=ambiente_minimo_docker(extras),
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


@pytest.mark.parametrize(
    "caminho",
    [
        HOME_HOST / ".ssh",
        HOME_HOST / ".config" / "gh" / "hosts.yml",
        HOME_HOST / ".claude" / ".credentials.json",
        "/home/agente/.ssh",
        "/home/agente/.config/gh/hosts.yml",
        "/home/agente/.claude/.credentials.json",
        "/var/run/docker.sock",
        "/run/docker.sock",
    ],
)
def test_credencial_do_host_nao_existe_no_conteiner(tmp_path, caminho):
    assert no_conteiner(f"test -e '{caminho}'", tmp_path).returncode == 1


def test_arquivo_vizinho_do_diretorio_de_trabalho_nao_e_visivel(tmp_path):
    trabalho = tmp_path / "trabalho"
    trabalho.mkdir()
    (tmp_path / "canario").write_text("segredo")
    resultado = no_conteiner("cat ../canario /canario; find / -name canario 2>/dev/null", trabalho)
    assert "segredo" not in resultado.stdout and "canario" not in resultado.stdout


def test_variavel_de_ambiente_do_host_nao_entra(tmp_path, monkeypatch):
    monkeypatch.setenv("GH_TOKEN", "canario-gh")
    monkeypatch.setenv("SSH_AUTH_SOCK", "/tmp/canario")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "canario-api")
    saida = no_conteiner("env", tmp_path).stdout
    assert "canario" not in saida


def test_conteiner_nao_tem_root_nem_capacidades(tmp_path):
    saida = no_conteiner(
        "id -u; grep -E 'CapEff|CapBnd|NoNewPrivs' /proc/self/status", tmp_path
    ).stdout
    assert saida.splitlines()[0] == str(os.getuid()) != "0"
    assert "CapBnd:\t0000000000000000" in saida and "NoNewPrivs:\t1" in saida


def test_sistema_de_arquivos_e_somente_leitura(tmp_path):
    raiz = no_conteiner("awk '$2 == \"/\" {print $4}' /proc/mounts", tmp_path).stdout
    assert raiz.split(",")[0] == "ro"
    assert no_conteiner("touch /trabalho/permitido", tmp_path).returncode == 0
    assert (tmp_path / "permitido").exists()


@pytest.mark.parametrize("url", ["https://example.com", "https://github.com", "https://pypi.org"])
def test_proxy_recusa_dominio_fora_da_lista(tmp_path, url):
    resultado = no_conteiner(f"curl -s -m 20 -o /dev/null -w '%{{http_connect}}' {url}", tmp_path)
    assert resultado.stdout == "403"


def test_sem_saida_direta_para_a_internet(tmp_path):
    script = "curl -sS -m 10 --noproxy '*' -o /dev/null https://1.1.1.1"
    assert no_conteiner(script, tmp_path).returncode != 0


def test_dns_externo_nao_resolve(tmp_path):
    assert no_conteiner("getent hosts example.com", tmp_path).returncode != 0


def test_proxy_alcanca_a_api_permitida(tmp_path):
    script = "curl -s -m 20 -o /dev/null -w '%{http_connect}' https://api.anthropic.com/"
    assert no_conteiner(script, tmp_path).stdout == "200"


def test_push_para_o_github_falha(tmp_path):
    script = (
        "git init -q . && git -c user.email=a@a -c user.name=a commit -q --allow-empty -m x && "
        "GIT_TERMINAL_PROMPT=0 git push -q https://github.com/michelpessoa/fabrica-cobaia.git "
        "HEAD:refs/heads/fuga"
    )
    assert no_conteiner(script, tmp_path).returncode != 0


def test_gates_sem_rede_nenhuma(tmp_path):
    resultado = no_conteiner(
        "python3 -c \"import socket; socket.create_connection(('1.1.1.1', 443), 5)\"",
        tmp_path,
        imagem=IMAGEM_GATES,
        rede="none",
    )
    assert resultado.returncode != 0


@pytest.fixture
def copia(tmp_path):
    origem = tmp_path / "origem"
    origem.mkdir()
    git = ["git", "-c", "user.email=t@t", "-c", "user.name=t"]
    subprocess.run([*git, "init", "-q", "-b", "main"], cwd=origem, check=True)
    (origem / "a.txt").write_text("a\n")
    subprocess.run([*git, "add", "-A"], cwd=origem, check=True)
    subprocess.run([*git, "commit", "-qm", "base"], cwd=origem, check=True)
    return preparar_copia(origem, "main", tmp_path / "copia")


def base_de(copia):
    resultado = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=copia, capture_output=True, text=True, check=True
    )
    return resultado.stdout.strip()


def test_patch_inclui_edicao_e_arquivo_novo(copia):
    base = base_de(copia)
    (copia / "a.txt").write_text("alterado\n")
    (copia / "novo.txt").write_text("novo\n")
    patch = extrair_patch(copia, base)
    assert "+alterado" in patch and "+novo" in patch


def test_configuracao_plantada_nao_executa_ao_extrair_o_patch(copia, tmp_path):
    base = base_de(copia)
    marca_host = tmp_path / "executou-no-host"
    plantado = copia / "plantado.sh"
    plantado.write_text(f"#!/bin/sh\ntouch {marca_host}\ntouch /trabalho/executou\n")
    plantado.chmod(0o755)
    with (copia / ".git" / "config").open("a") as config:
        config.write(f"[core]\n\tfsmonitor = {plantado}\n")
    extrair_patch(copia, base)
    assert not marca_host.exists()
    assert not (copia / "executou").exists()


def test_patch_nao_inclui_o_que_foi_ocultado(tmp_path):
    origem = tmp_path / "origem"
    (origem / "docs/sdd/arquivo").mkdir(parents=True)
    git = ["git", "-c", "user.email=t@t", "-c", "user.name=t"]
    subprocess.run([*git, "init", "-q", "-b", "main"], cwd=origem, check=True)
    (origem / "docs/sdd/arquivo/antiga.md").write_text("antiga\n")
    (origem / "a.txt").write_text("a\n")
    subprocess.run([*git, "add", "-A"], cwd=origem, check=True)
    subprocess.run([*git, "commit", "-qm", "base"], cwd=origem, check=True)
    ocultos = ("docs/sdd/arquivo",)
    copia = preparar_copia(origem, "main", tmp_path / "copia", ocultos)
    assert not (copia / "docs/sdd/arquivo").exists()
    base = base_de(copia)
    (copia / "a.txt").write_text("b\n")
    patch = extrair_patch(copia, base, excluir=ocultos)
    assert "+b" in patch and "antiga" not in patch

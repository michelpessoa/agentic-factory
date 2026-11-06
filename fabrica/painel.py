"""Painel local, só leitura: mostra o que está no banco da fábrica, sem nenhuma ação.

Título, motivo e evidência podem trazer texto escrito por agente, então tudo é escapado e a página
não roda script. Só campos da lista saem de `dados`, que também guarda o token de cada contrato.
"""

import json
import sqlite3
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote, unquote

from fabrica.estados import PAUSAS, TERMINAIS

ENDERECO = "127.0.0.1"
CAMPOS_DA_EXECUCAO = ("risco", "modelo", "tentativa", "custo_usd", "pr", "release", "gates")
ESTADOS_DE_SUCESSO = {"MEDIDA"}
ACAO_DA_PAUSA = {
    "PAUSADA_DECISAO": "decidir <projeto> <run_id> <baixo|medio|alto>",
    "PAUSADA_AMBIENTE": "retomar <projeto> <run_id>",
    "PAUSADA_LIMITE_USO": "retomar <projeto> <run_id>",
}
ESTILO = """
body{font:15px/1.5 system-ui,sans-serif;margin:2rem auto;max-width:72rem;padding:0 1rem;color:#222}
table{border-collapse:collapse;width:100%}th,td{text-align:left;padding:.4rem .6rem;
border-bottom:1px solid #ddd;vertical-align:top}th{font-weight:600}.num{text-align:right}
.selo{padding:.1rem .45rem;border-radius:.3rem;background:#eee;font-size:13px;white-space:nowrap}
.ok{background:#dcefe0}.parada{background:#f6dcdc}.pausa{background:#f8ecc8}code{font-size:13px}
.resumo{display:flex;gap:2rem;margin:1rem 0 1.5rem}.resumo b{display:block;font-size:1.4rem}
"""


def _ler(banco: Path, consulta: str, *parametros) -> list[tuple]:
    # Modo `ro` no próprio SQLite: um defeito aqui não consegue escrever no banco da fábrica.
    conexao = sqlite3.connect(f"file:{quote(str(banco))}?mode=ro", uri=True)
    try:
        return conexao.execute(consulta, parametros).fetchall()
    finally:
        conexao.close()


def _selo(estado: str) -> str:
    classe = (
        "ok"
        if estado in ESTADOS_DE_SUCESSO
        else "pausa"
        if estado in PAUSAS
        else "parada"
        if estado in TERMINAIS
        else ""
    )
    return f'<span class="selo {classe}">{escape(estado)}</span>'


def _custo(valor) -> str:
    return f"US$ {valor:.2f}" if isinstance(valor, int | float) else "-"


def _pagina(titulo: str, corpo: str) -> str:
    return (
        f'<!doctype html><html lang="pt-BR"><meta charset="utf-8"><title>{escape(titulo)}</title>'
        f"<style>{ESTILO}</style><body><h1>{escape(titulo)}</h1>{corpo}</body></html>"
    )


def pagina_inicial(banco: Path) -> str:
    linhas = _ler(
        banco,
        """
        SELECT e.run_id, e.projeto, e.sdd, e.estado, e.dados, MAX(t.em)
        FROM execucoes e LEFT JOIN transicoes t ON t.run_id = e.run_id
        GROUP BY e.run_id ORDER BY MAX(t.em) DESC
        """,
    )
    custo_total = 0.0
    pausadas = 0
    tabela = []
    for run_id, projeto, sdd, estado, bruto, ultima in linhas:
        dados = json.loads(bruto)
        custo_total += dados.get("custo_usd") or 0
        pausadas += estado in PAUSAS
        tabela.append(
            f'<tr><td><a href="/execucao/{quote(run_id)}">{escape(sdd)}</a></td>'
            f"<td>{escape(projeto)}</td><td>{_selo(estado)}</td>"
            f"<td>{escape(str(dados.get('risco', '-')))}</td>"
            f'<td class="num">{escape(str(dados.get("tentativa", "-")))}</td>'
            f'<td class="num">{_custo(dados.get("custo_usd"))}</td>'
            f"<td>{escape((ultima or '-')[:16].replace('T', ' '))} UTC</td></tr>"
        )
    resumo = (
        f'<div class="resumo"><div><b>{len(linhas)}</b>execuções</div>'
        f"<div><b>{pausadas}</b>esperando você</div>"
        f"<div><b>{_custo(custo_total)}</b>custo somado</div></div>"
    )
    if not linhas:
        return _pagina("Fábrica Agêntica", resumo + "<p>Nenhuma execução ainda.</p>")
    cabecalho = (
        "<tr><th>SDD</th><th>Projeto</th><th>Estado</th><th>Risco</th>"
        '<th class="num">Tentativa</th><th class="num">Custo</th><th>Última mudança</th></tr>'
    )
    return _pagina("Fábrica Agêntica", f"{resumo}<table>{cabecalho}{''.join(tabela)}</table>")


def pagina_da_execucao(banco: Path, run_id: str) -> str | None:
    linhas = _ler(
        banco, "SELECT projeto, sdd, estado, dados FROM execucoes WHERE run_id = ?", run_id
    )
    if not linhas:
        return None
    projeto, sdd, estado, bruto = linhas[0]
    dados = json.loads(bruto)
    itens = "".join(
        f"<tr><th>{escape(campo)}</th><td>{escape(_mostrar(campo, dados[campo]))}</td></tr>"
        for campo in CAMPOS_DA_EXECUCAO
        if campo in dados
    )
    transicoes = "".join(
        f"<tr><td>{escape(em[:19].replace('T', ' '))}</td><td>{_selo(destino)}</td>"
        f"<td>{escape(motivo)}</td></tr>"
        for destino, motivo, em in _ler(
            banco,
            "SELECT destino, motivo, em FROM transicoes WHERE run_id = ? ORDER BY id",
            run_id,
        )
    )
    acao = ""
    if estado in ACAO_DA_PAUSA:
        comando = ACAO_DA_PAUSA[estado]
        acao = f"<p>Para seguir: <code>uv run python -m fabrica {escape(comando)}</code></p>"
    return _pagina(
        sdd,
        f'<p><a href="/">voltar</a> · {escape(projeto)} · {_selo(estado)} · '
        f"<code>{escape(run_id)}</code></p>{acao}<table>{itens}</table>"
        f"<h2>Transições</h2><table><tr><th>UTC</th><th>Estado</th><th>Motivo</th></tr>"
        f"{transicoes}</table>",
    )


def _mostrar(campo: str, valor) -> str:
    if campo == "custo_usd":
        return _custo(valor)
    if isinstance(valor, list):
        return ", ".join(str(item) for item in valor)
    return str(valor)


def criar_servidor(banco: Path, porta: int) -> ThreadingHTTPServer:
    class Manipulador(BaseHTTPRequestHandler):
        def do_GET(self):
            # Sem isto, uma página da internet alcançaria o painel por DNS rebinding.
            if self.headers.get("Host") != f"{ENDERECO}:{self.server.server_address[1]}":
                self._responder(403, _pagina("Recusado", "<p>Abra pelo endereço local.</p>"))
                return
            html = None
            if self.path == "/":
                html = pagina_inicial(banco)
            elif self.path.startswith("/execucao/"):
                html = pagina_da_execucao(banco, unquote(self.path.removeprefix("/execucao/")))
            if html is None:
                self._responder(404, _pagina("Não encontrado", '<p><a href="/">voltar</a></p>'))
            else:
                self._responder(200, html)

        def _responder(self, codigo: int, html: str) -> None:
            corpo = html.encode("utf-8")
            self.send_response(codigo)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(corpo)))
            self.send_header(
                "Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'"
            )
            self.send_header("X-Frame-Options", "DENY")
            self.end_headers()
            self.wfile.write(corpo)

        def log_message(self, *_):
            pass

    return ThreadingHTTPServer((ENDERECO, porta), Manipulador)

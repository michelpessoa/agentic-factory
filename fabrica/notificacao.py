"""Notificação: arquivo de status, toast do Windows e, se configurados, e-mail e Teams.

E-mail e Teams são opcionais e saem de `~/.config/fabrica/notificacao.toml`, que guarda segredo
(senha SMTP e URL do webhook) e por isso só é lido com permissão restrita ao dono (ADR-0011).
"""

import base64
import json
import smtplib
import stat
import subprocess
import tomllib
import urllib.request
from datetime import UTC, datetime
from email.message import EmailMessage
from pathlib import Path
from xml.sax.saxutils import escape

CAMINHO_CONFIG = Path.home() / ".config" / "fabrica" / "notificacao.toml"
ASSUNTO = "Fábrica Agêntica"

SCRIPT_TOAST = """
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null
[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] > $null
$xml = New-Object Windows.Data.Xml.Dom.XmlDocument
$xml.LoadXml('<toast><visual><binding template="ToastText02"><text id="1">Fábrica Agêntica</text><text id="2">{texto}</text></binding></visual></toast>')
$toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('Fabrica Agentica').Show($toast)
"""


class ConfiguracaoInvalida(Exception):
    """Arquivo de notificação inseguro ou incompleto: a fábrica não começa com ele assim."""


class Email:
    def __init__(self, servidor: str, porta: int, usuario: str, senha: str, para: list[str]):
        self.servidor = servidor
        self.porta = porta
        self.usuario = usuario
        self.senha = senha
        self.para = para

    def enviar(self, mensagem: str) -> None:
        email = EmailMessage()
        email["Subject"] = f"{ASSUNTO}: {mensagem[:80]}"
        email["From"] = self.usuario
        email["To"] = ", ".join(self.para)
        email.set_content(mensagem)
        with smtplib.SMTP(self.servidor, self.porta, timeout=30) as smtp:
            smtp.starttls()
            smtp.login(self.usuario, self.senha)
            smtp.send_message(email)


class Teams:
    """Webhook do app Workflows do Teams, que recebe um Adaptive Card."""

    def __init__(self, url: str):
        self.url = url

    def enviar(self, mensagem: str) -> None:
        cartao = {
            "type": "AdaptiveCard",
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "version": "1.4",
            "body": [
                {"type": "TextBlock", "text": ASSUNTO, "weight": "Bolder"},
                {"type": "TextBlock", "text": mensagem, "wrap": True},
            ],
        }
        corpo = {
            "type": "message",
            "attachments": [
                {"contentType": "application/vnd.microsoft.card.adaptive", "content": cartao}
            ],
        }
        pedido = urllib.request.Request(
            self.url,
            data=json.dumps(corpo).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(pedido, timeout=30):
            pass


def carregar_canais(caminho: Path = CAMINHO_CONFIG) -> list:
    if not caminho.exists():
        return []
    if caminho.stat().st_mode & (stat.S_IRWXG | stat.S_IRWXO):
        raise ConfiguracaoInvalida(f"{caminho} guarda segredo: rode chmod 600 {caminho}")
    try:
        config = tomllib.loads(caminho.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as erro:
        raise ConfiguracaoInvalida(f"{caminho}: {erro}") from erro
    canais = []
    try:
        if "email" in config:
            email = config["email"]
            para = email["para"]
            if not isinstance(para, list) or not para:
                raise ConfiguracaoInvalida(f"{caminho}: email.para precisa de ao menos um endereço")
            canais.append(
                Email(
                    email["servidor"],
                    int(email.get("porta", 587)),
                    email["usuario"],
                    email["senha"],
                    para,
                )
            )
        if "teams" in config:
            url = config["teams"]["url"]
            if not url.startswith("https://"):
                raise ConfiguracaoInvalida(f"{caminho}: teams.url precisa ser https")
            canais.append(Teams(url))
    except KeyError as erro:
        raise ConfiguracaoInvalida(f"{caminho}: falta o campo {erro}") from erro
    return canais


class Notificador:
    def __init__(self, arquivo_status: Path, toast: bool = True, canais: list | None = None):
        self._arquivo = arquivo_status
        self._toast = toast
        self._canais = canais or []

    def avisar(self, mensagem: str) -> None:
        self._registrar(mensagem)
        if self._toast:
            self._enviar_toast(mensagem)
        # Canal externo é conveniência: a falha dele fica no log e não para a fábrica.
        for canal in self._canais:
            try:
                canal.enviar(mensagem)
            except Exception as erro:  # noqa: BLE001
                self._registrar(
                    f"falha ao avisar por {type(canal).__name__}: {type(erro).__name__}"
                )

    def _registrar(self, mensagem: str) -> None:
        self._arquivo.parent.mkdir(parents=True, exist_ok=True)
        with self._arquivo.open("a", encoding="utf-8") as saida:
            saida.write(f"{datetime.now(UTC).isoformat()} {mensagem}\n")

    def _enviar_toast(self, mensagem: str) -> None:
        texto = escape(mensagem[:200]).replace("'", "''")
        script = SCRIPT_TOAST.format(texto=texto)
        codificado = base64.b64encode(script.encode("utf-16-le")).decode()
        # Toast é conveniência: a falha dele não pode parar a fábrica.
        try:
            subprocess.run(
                ["powershell.exe", "-NoProfile", "-EncodedCommand", codificado],
                capture_output=True,
                timeout=30,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            pass

"""Notificação local: arquivo de status e toast do Windows, sem depender de serviço externo."""

import base64
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from xml.sax.saxutils import escape

SCRIPT_TOAST = """
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null
[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] > $null
$xml = New-Object Windows.Data.Xml.Dom.XmlDocument
$xml.LoadXml('<toast><visual><binding template="ToastText02"><text id="1">Fábrica Agêntica</text><text id="2">{texto}</text></binding></visual></toast>')
$toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('Fabrica Agentica').Show($toast)
"""


class Notificador:
    def __init__(self, arquivo_status: Path, toast: bool = True):
        self._arquivo = arquivo_status
        self._toast = toast

    def avisar(self, mensagem: str) -> None:
        self._arquivo.parent.mkdir(parents=True, exist_ok=True)
        with self._arquivo.open("a", encoding="utf-8") as saida:
            saida.write(f"{datetime.now(UTC).isoformat()} {mensagem}\n")
        if self._toast:
            self._enviar_toast(mensagem)

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
